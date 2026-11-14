from typing import Any
from pydantic import BaseModel, Field

class BalanceGoal(BaseModel):
    goal: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    matches: int = Field(default=100, ge=1)
    iterations: int = Field(default=2, ge=1)
    scoring: dict[str, float] = Field(default_factory=lambda: {"target": 1.0, "regression": 2.0, "disruption": 0.1, "breaking": 10.0})

class Change(BaseModel):
    path: str
    value: Any

class PatchProposal(BaseModel):
    name: str
    changes: list[Change] = Field(min_length=1)
    rationale: str
    predicted_tradeoffs: str

class ExperimentPlan(BaseModel):
    scenarios: list[dict[str, Any]]
    seeds: list[int]
    workers: int = Field(default=1, ge=1)

class Finding(BaseModel):
    kind: str
    message: str
    seed: int | None = None
    scenario_id: str | None = None
    repro_config: dict[str, Any] | None = None

class AgentReport(BaseModel):
    goal: BalanceGoal
    mode: str
    baseline: dict[str, Any]
    candidates: list[dict[str, Any]]
    recommendation: dict[str, Any] | None = None
    findings: list[Finding] = Field(default_factory=list)
    tool_log: list[dict[str, Any]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    reproduction: str
