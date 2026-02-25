"""Pydantic models for API request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


# --- Enums ---

class ResearchType(str, Enum):
    COMPANY = "company"
    INDUSTRY = "industry"


class JobStatus(str, Enum):
    QUEUED = "queued"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"


class JobKind(str, Enum):
    RESEARCH = "research"
    CRAWL = "crawl"
    EXTRACT = "extract"
    SEARCH = "search"


# --- Request Models ---

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Company or industry name")
    type: ResearchType = Field(default=ResearchType.COMPANY, description="Research type")


# --- Report Sub-Models ---

class SWOTAnalysis(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)


class Trend(BaseModel):
    title: str
    description: str
    relevance: str = Field(default="medium", description="high | medium | low")


class Source(BaseModel):
    url: str
    title: str
    scraped_at: Optional[datetime] = None


class LeaderProfile(BaseModel):
    name: str = ""
    title: str = ""
    function: str = ""
    source_url: str = ""
    evidence: str = ""
    confidence: str = Field(default="medium", description="high | medium | low")


class ICPFitAssessment(BaseModel):
    fit_score: int = Field(default=0, ge=0, le=100)
    fit_tier: str = Field(default="medium", description="high | medium | low")
    summary: str = ""
    reasons: list[str] = Field(default_factory=list)
    recommended_pitch_angles: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class RevenueYear(BaseModel):
    year: str = ""
    amount: str = ""

class CompanyFinancials(BaseModel):
    core_business_summary: str = ""
    market_cap: str = "Private or Unknown"
    funding_stage: str = "Unknown"
    revenue_history: list[RevenueYear] = Field(default_factory=list)

class FundingMilestone(BaseModel):
    date_or_round: str = ""
    amount: str = ""
    investors: list[str] = Field(default_factory=list)

class FundingIntelligence(BaseModel):
    investor_types: list[str] = Field(default_factory=list, description="e.g. Tier 1 VC, Corporate, PE")
    funding_timeline: list[FundingMilestone] = Field(default_factory=list)
    capital_allocation_purpose: str = "Unknown"
    e2e_compute_lead_status: str = Field(default="Cold", description="Hot | Warm | Cold")
    compute_spending_evidence: str = "No explicit evidence of GPU/AI infrastructure scaling found."

class ResearchReport(BaseModel):
    company_overview: str = ""
    financials: CompanyFinancials = Field(default_factory=CompanyFinancials)
    funding_intelligence: FundingIntelligence = Field(default_factory=FundingIntelligence)
    swot: SWOTAnalysis = Field(default_factory=SWOTAnalysis)
    trends: list[Trend] = Field(default_factory=list)
    competitive_landscape: str = ""
    key_findings: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


# --- Response Models ---

class ResearchJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    job_kind: JobKind = JobKind.RESEARCH
    status: JobStatus = JobStatus.QUEUED
    query: str = ""
    type: ResearchType = ResearchType.COMPANY
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    report: Optional[ResearchReport] = None
    operation_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    # Follow-up Q&A
    qa_history: list[dict] = Field(default_factory=list)
    qa_remaining: int = Field(default=10)


class ResearchStartResponse(BaseModel):
    job_id: str
    status: JobStatus


class HealthResponse(BaseModel):
    status: str = "ok"
    model: str = ""
    vllm_connected: bool = False
    tavily_configured: bool = False


# --- Q&A Models ---

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="Follow-up question about the report")


class AskResponse(BaseModel):
    answer: str
    question: str
    remaining_questions: int
    suggested_questions: list[str] = Field(default_factory=list)
