from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .ai_candidate import infer_next_candidate
from .azure_batch import AzureBatchConfigurationError, AzureBatchSimulationService
from .config import get_settings
from .models import (
    AiSimulationCandidate,
    RuntimeConfiguration,
    SimulationJob,
    SimulationRequest,
)
from .simulation import LocalSimulationService

settings = get_settings()
app = FastAPI(title="Market Shock War Room API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

local_service = LocalSimulationService()
azure_service = AzureBatchSimulationService(settings)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/api/config", response_model=RuntimeConfiguration)
def runtime_configuration() -> RuntimeConfiguration:
    missing = settings.azure_batch_missing_settings()
    return RuntimeConfiguration(
        default_execution_mode=settings.execution_mode,
        azure_batch_configured=not missing,
        azure_batch_pool_id=settings.azure_batch_pool_id,
        missing_azure_settings=missing,
    )


@app.post("/api/simulations", response_model=SimulationJob, status_code=status.HTTP_202_ACCEPTED)
async def create_simulation(request: SimulationRequest) -> SimulationJob:
    mode = request.execution_mode or settings.execution_mode
    try:
        if mode == "azure":
            return azure_service.create(request)
        return local_service.create(request)
    except AzureBatchConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@app.get("/api/simulations/{job_id}", response_model=SimulationJob)
def get_simulation(job_id: str) -> SimulationJob:
    job = local_service.get(job_id) or azure_service.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません")
    return job


@app.post(
    "/api/simulations/{job_id}/next-candidate",
    response_model=AiSimulationCandidate,
)
def create_next_candidate(job_id: str) -> AiSimulationCandidate:
    job = local_service.get(job_id) or azure_service.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません")
    try:
        return infer_next_candidate(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


frontend_dist = Path(__file__).resolve().parents[2] / "frontend-dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
