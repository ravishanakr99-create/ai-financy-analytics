"""API request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UploadMetadata(BaseModel):
    """Optional metadata for report upload."""

    user_id: Optional[str] = None
    category: Optional[str] = None


class RuleDecision(BaseModel):
    """Single rule evaluation result."""

    rule_id: str
    rule_name: str
    passed: bool
    message: str
    details: Optional[dict] = None


class SalaryRow(BaseModel):
    month: str
    employer: str
    amount: float
    confidence: float = Field(ge=0, le=1)


class ObligationRow(BaseModel):
    lender: str
    obligation_type: str
    monthly_amount: float
    outstanding_amount: float


class PendingFormItem(BaseModel):
    form_code: str
    form_name: str
    reason: str


class PredictedQuery(BaseModel):
    query: str
    confidence: float = Field(ge=0, le=1)
    rationale: str


class EligibilityResult(BaseModel):
    """Output from document extraction + rules."""

    eligible: bool
    decisions: list[RuleDecision] = Field(default_factory=list)
    extracted_data: dict = Field(default_factory=dict)
    salary_breakdown: list[SalaryRow] = Field(default_factory=list)
    obligations: list[ObligationRow] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    pending_forms: list[PendingFormItem] = Field(default_factory=list)
    predicted_queries: list[PredictedQuery] = Field(default_factory=list)
    confidence_summary: dict = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportCreate(BaseModel):
    """Response after successful upload."""

    report_id: str
    message: str = "Report uploaded and processed successfully"
    eligibility: bool


class ReportResult(BaseModel):
    """Full report result for GET /reports/{id}."""

    report_id: str
    created_at: datetime
    eligibility: bool
    decisions: list[RuleDecision]
    extracted_data: dict
    salary_breakdown: list[SalaryRow] = Field(default_factory=list)
    obligations: list[ObligationRow] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    pending_forms: list[PendingFormItem] = Field(default_factory=list)
    predicted_queries: list[PredictedQuery] = Field(default_factory=list)
    confidence_summary: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    pdf_available: bool = True
