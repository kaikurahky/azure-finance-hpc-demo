import asyncio
import random
import time
from datetime import UTC, datetime
from uuid import uuid4

from .models import (
    HedgeRecommendation,
    JobStatus,
    ShockScenario,
    SimulationJob,
    SimulationRequest,
    SimulationResult,
)


SCENARIO_LOSSES = {
    ShockScenario.LEHMAN: 124.0,
    ShockScenario.YEN_SURGE: 89.0,
    ShockScenario.RATE_SPIKE: 97.0,
    ShockScenario.CUSTOM: 72.0,
}


class LocalSimulationService:
    def __init__(self) -> None:
        self.jobs: dict[str, SimulationJob] = {}

    def create(self, request: SimulationRequest) -> SimulationJob:
        now = datetime.now(UTC)
        job = SimulationJob(
            id=str(uuid4()),
            scenario=request.scenario,
            execution_mode="local",
            status=JobStatus.QUEUED,
            progress=0,
            active_nodes=0,
            completed_paths=0,
            total_paths=request.paths,
            target_nodes=request.target_nodes,
            created_at=now,
            updated_at=now,
        )
        self.jobs[job.id] = job
        asyncio.create_task(self._run(job.id))
        return job

    def get(self, job_id: str) -> SimulationJob | None:
        return self.jobs.get(job_id)

    async def _run(self, job_id: str) -> None:
        job = self.jobs[job_id]
        started = time.monotonic()
        try:
            stages = [
                (JobStatus.SCALING, 8, 18),
                (JobStatus.SCALING, 20, 62),
                (JobStatus.RUNNING, 38, 100),
                (JobStatus.RUNNING, 58, job.target_nodes),
                (JobStatus.RUNNING, 76, job.target_nodes),
                (JobStatus.RUNNING, 91, job.target_nodes),
                (JobStatus.VERIFYING, 97, max(8, job.target_nodes // 4)),
            ]
            for status, progress, nodes in stages:
                await asyncio.sleep(0.65)
                job.status = status
                job.progress = progress
                job.active_nodes = nodes
                job.completed_paths = int(job.total_paths * progress / 100)
                job.updated_at = datetime.now(UTC)

            await asyncio.sleep(0.7)
            baseline = SCENARIO_LOSSES[job.scenario]
            jitter = random.Random(job.id).uniform(-1.2, 1.2)
            job.result = _build_result(baseline + jitter, time.monotonic() - started, job.total_paths)
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.active_nodes = 0
            job.completed_paths = job.total_paths
            job.updated_at = datetime.now(UTC)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = f"ローカルシミュレーションに失敗しました: {exc}"
            job.updated_at = datetime.now(UTC)


def _build_result(baseline: float, elapsed: float, paths: int) -> SimulationResult:
    recommendations = [
        HedgeRecommendation(
            name="為替ヘッジを20%追加",
            predicted_loss_billion_yen=baseline * 0.66,
            verified_loss_billion_yen=baseline * 0.68,
            error_percent=2.4,
            hedge_cost_billion_yen=1.2,
        ),
        HedgeRecommendation(
            name="金利デュレーションを15%削減",
            predicted_loss_billion_yen=baseline * 0.60,
            verified_loss_billion_yen=baseline * 0.61,
            error_percent=1.3,
            hedge_cost_billion_yen=1.8,
        ),
        HedgeRecommendation(
            name="複合ヘッジ最適化",
            predicted_loss_billion_yen=baseline * 0.49,
            verified_loss_billion_yen=baseline * 0.51,
            error_percent=3.2,
            hedge_cost_billion_yen=2.1,
        ),
    ]
    return SimulationResult(
        baseline_loss_billion_yen=round(baseline, 1),
        value_at_risk_billion_yen=round(baseline * 0.82, 1),
        expected_shortfall_billion_yen=round(baseline * 1.14, 1),
        elapsed_seconds=round(elapsed, 1),
        estimated_legacy_seconds=15_600,
        estimated_cost_yen=max(980, int(paths / 4_000)),
        evaluations_per_second=int(paths / max(elapsed, 1)),
        recommendations=recommendations,
        loss_contributors={
            "株式": 42,
            "金利": 27,
            "為替": 19,
            "クレジット": 12,
        },
    )

