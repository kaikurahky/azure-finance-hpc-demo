import json
from datetime import UTC, datetime
from uuid import uuid4

from azure.batch import BatchServiceClient
from azure.batch.models import BatchErrorException, JobAddParameter, PoolInformation, TaskAddParameter
from azure.identity import DefaultAzureCredential
from msrest.authentication import BasicTokenAuthentication

from .config import Settings
from .models import JobStatus, SimulationJob, SimulationRequest
from .simulation import SCENARIO_LOSSES, _adjusted_baseline, _build_result


class AzureBatchConfigurationError(RuntimeError):
    pass


class AzureIdentityBatchCredential(BasicTokenAuthentication):
    def __init__(self) -> None:
        super().__init__({"access_token": ""})
        self._credential = DefaultAzureCredential()

    def signed_session(self, session=None):
        access_token = self._credential.get_token(
            "https://batch.core.windows.net/.default"
        )
        self.token["access_token"] = access_token.token
        return super().signed_session(session)


class AzureBatchSimulationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.jobs: dict[str, SimulationJob] = {}

    def _client(self) -> BatchServiceClient:
        missing = self.settings.azure_batch_missing_settings()
        if missing:
            raise AzureBatchConfigurationError(
                "Azure Batchモードに必要な設定がありません: " + ", ".join(missing)
            )
        return BatchServiceClient(
            AzureIdentityBatchCredential(),
            batch_url=self.settings.azure_batch_account_url,
        )

    def create(self, request: SimulationRequest) -> SimulationJob:
        client = self._client()
        app_job_id = str(uuid4())
        batch_job_id = f"finance-risk-{app_job_id[:8]}"
        partitions = min(request.target_nodes, 200)
        try:
            client.job.add(
                JobAddParameter(
                    id=batch_job_id,
                    pool_info=PoolInformation(pool_id=self.settings.azure_batch_pool_id),
                )
            )
            tasks = [
                TaskAddParameter(
                    id=f"mc-{index:04d}",
                    command_line=self._task_command(request, index, partitions),
                )
                for index in range(partitions)
            ]
            client.task.add_collection(batch_job_id, tasks)
        except BatchErrorException as exc:
            message = getattr(getattr(exc, "error", None), "message", None)
            detail = getattr(message, "value", None) or str(exc)
            raise RuntimeError(f"Azure Batchジョブの投入に失敗しました: {detail}") from exc

        now = datetime.now(UTC)
        job = SimulationJob(
            id=app_job_id,
            scenario=request.scenario,
            execution_mode="azure",
            status=JobStatus.QUEUED,
            progress=0,
            active_nodes=0,
            completed_paths=0,
            total_paths=request.paths,
            target_nodes=request.target_nodes,
            iteration=request.iteration,
            parent_job_id=request.parent_job_id,
            volatility_scale=request.volatility_scale,
            hedge_ratio_percent=request.hedge_ratio_percent,
            created_at=now,
            updated_at=now,
        )
        self.jobs[app_job_id] = job
        job.error = json.dumps({"batchJobId": batch_job_id})
        return job

    def get(self, job_id: str) -> SimulationJob | None:
        job = self.jobs.get(job_id)
        if not job:
            return None
        metadata = json.loads(job.error or "{}")
        batch_job_id = metadata.get("batchJobId")
        if not batch_job_id:
            return job
        client = self._client()
        tasks = list(client.task.list(batch_job_id))
        completed = sum(1 for task in tasks if str(task.state).lower().endswith("completed"))
        running = sum(1 for task in tasks if str(task.state).lower().endswith("running"))
        total = max(len(tasks), 1)
        job.progress = int(completed / total * 100)
        job.completed_paths = int(job.total_paths * completed / total)
        job.active_nodes = running
        job.status = JobStatus.COMPLETED if completed == total else JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)
        if job.status == JobStatus.COMPLETED:
            baseline = _adjusted_baseline(
                SCENARIO_LOSSES[job.scenario],
                job.volatility_scale,
                job.hedge_ratio_percent,
            )
            job.result = _build_result(baseline, 0.0, job.total_paths)
            job.error = None
        return job

    @staticmethod
    def _task_command(request: SimulationRequest, index: int, partitions: int) -> str:
        samples = max(1, request.paths // partitions)
        mean = -0.024 * (1 - request.hedge_ratio_percent / 100 * 0.8)
        sigma = 0.18 * request.volatility_scale
        code = (
            "import json,random,statistics;"
            f"r=random.Random({index});"
            f"x=[r.gauss({mean},{sigma}) for _ in range({samples})];"
            "x.sort();"
            "n=max(1,int(len(x)*0.01));"
            "print(json.dumps({'mean':statistics.fmean(x),'tail':statistics.fmean(x[:n]),'count':len(x)}))"
        )
        return f'/bin/bash -c "python3 -c \\"{code}\\""'
