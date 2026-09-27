from pydantic import BaseModel, Field


class HoldingInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    weight: float = Field(gt=0, le=1)


class WarRoomRequest(BaseModel):
    thesis: str = Field(min_length=10, max_length=2000)
    holdings: list[HoldingInput] = Field(default_factory=list)


class ScenarioRequest(BaseModel):
    scenario_id: str
    holdings: list[HoldingInput] = Field(default_factory=list)
    shocks: dict[str, float] | None = None
    name: str | None = None
    description: str | None = None


class ThesisRequest(BaseModel):
    thesis: str = Field(min_length=10, max_length=2000)


class PortfolioRecord(BaseModel):
    id: str
    name: str
    holdings: list[HoldingInput]


class EvidenceRecord(BaseModel):
    id: str
    source: str
    observed_at: str
    period: str | None = None
    confidence: float = Field(ge=0, le=1)


class RiskMetricRecord(BaseModel):
    name: str
    value: float
    method: str
    source: str


class CommitteeRunRecord(BaseModel):
    run_id: str
    portfolio_id: str
    thesis: str
    status: str
    created_at: str


class ETFHoldingRecord(BaseModel):
    etf_ticker: str
    security_ticker: str
    weight: float = Field(ge=0, le=1)
    as_of: str
    source: str


class ETFRecord(BaseModel):
    ticker: str
    name: str
    holdings_as_of: str
    source: str


class SecurityRecord(BaseModel):
    ticker: str
    name: str
    sector: str
    geography: str | None = None


class SectorRecord(BaseModel):
    name: str
    taxonomy: str


class PortfolioExposureRecord(BaseModel):
    portfolio_id: str
    security_ticker: str
    weight: float
    effective_weight: float
    as_of: str


class InvestmentThesisRecord(BaseModel):
    id: str
    portfolio_id: str
    thesis: str
    created_at: str


class ScenarioRecord(BaseModel):
    id: str
    name: str
    assumptions: list[str] = Field(default_factory=list)
    shocks: dict[str, float]


class ScenarioRunRecord(BaseModel):
    id: str
    portfolio_id: str
    scenario_id: str
    result: dict
    created_at: str


class AgentArgumentRecord(BaseModel):
    agent: str
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class AgentRecord(BaseModel):
    name: str
    role: str
    model: str
    mode: str


class InvestmentReportRecord(BaseModel):
    id: str
    committee_run_id: str
    sections: dict
    created_at: str


class VoiceBriefingRecord(BaseModel):
    id: str
    report_id: str
    provider: str
    status: str
    created_at: str
