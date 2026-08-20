from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ShockScenario(str, Enum):
    LEHMAN = "lehman"
    YEN_SURGE = "yen-surge"
    RATE_SPIKE = "rate-spike"
    CUSTOM = "custom"


class JobStatus(str, Enum):
    QUEUED = "queued"
    SCALING = "scaling"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


PoolMode = Literal["autoscale", "always-on"]


class SimulationRequest(BaseModel):
    scenario: ShockScenario = ShockScenario.LEHMAN
    paths: int = Field(default=5_000_000, ge=100_000, le=50_000_000)
    target_nodes: int = Field(default=10, ge=1, le=10)
    execution_mode: Literal["local", "azure"] | None = None
    pool_mode: PoolMode = "autoscale"
    iteration: int = Field(default=1, ge=1, le=2)
    parent_job_id: str | None = None
    volatility_scale: float = Field(default=1.0, ge=0.5, le=2.0)
    hedge_ratio_percent: float = Field(default=0.0, ge=0.0, le=60.0)


class HedgeRecommendation(BaseModel):
    name: str
    predicted_loss_billion_yen: float
    verified_loss_billion_yen: float
    error_percent: float
    hedge_cost_billion_yen: float


class SimulationResult(BaseModel):
    baseline_loss_billion_yen: float
    value_at_risk_billion_yen: float
    expected_shortfall_billion_yen: float
    elapsed_seconds: float
    estimated_legacy_seconds: int
    estimated_cost_yen: int
    evaluations_per_second: int
    recommendations: list[HedgeRecommendation]
    loss_contributors: dict[str, float]


class SimulationJob(BaseModel):
    id: str
    scenario: ShockScenario
    execution_mode: Literal["local", "azure"]
    pool_mode: PoolMode = "autoscale"
    status: JobStatus
    progress: int
    active_nodes: int
    completed_paths: int
    total_paths: int
    target_nodes: int
    iteration: int
    parent_job_id: str | None = None
    volatility_scale: float
    hedge_ratio_percent: float
    created_at: datetime
    updated_at: datetime
    result: SimulationResult | None = None
    error: str | None = None


class AiSimulationCandidate(BaseModel):
    source_job_id: str
    scenario: ShockScenario
    paths: int
    target_nodes: int
    pool_mode: PoolMode
    volatility_scale: float
    hedge_ratio_percent: float
    predicted_loss_billion_yen: float
    selected_strategy: str
    reasoning: str


class RuntimeConfiguration(BaseModel):
    default_execution_mode: Literal["local", "azure"]
    azure_batch_configured: bool
    azure_batch_pool_id: str
    missing_azure_settings: list[str]
