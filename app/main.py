"""FastAPI main application — Market Research AI Agent."""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import MODEL_NAME, TAVILY_API_KEY, REPORTS_DIR
from app.models.schemas import (
    ResearchRequest,
    ResearchJob,
    ResearchStartResponse,
    HealthResponse,
    JobStatus,
    JobKind,
    AskRequest,
    AskResponse,
)
from app.services import llm_service
from app.services.research_engine import run_research
from app.services.pdf_service import generate_pdf

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- App ---
app = FastAPI(
    title="Market Research AI Agent",
    description="AI-powered market research using NVIDIA Nemotron Nano on E2E Networks",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory job store ---
jobs: dict[str, ResearchJob] = {}


# --- Background task runner ---
async def _run_research_task(job_id: str) -> None:
    """Run research in the background and update the job store."""
    job = jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    await run_research(job)

    # Save completed report to disk
    if job.status == JobStatus.COMPLETED and job.report:
        report_file = REPORTS_DIR / f"{job_id}.json"
        report_file.write_text(
            json.dumps(job.model_dump(), default=str, indent=2)
        )
        logger.info(f"Report saved: {report_file}")


# --- Endpoints ---

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Check if all services are running."""
    vllm_ok = await llm_service.check_vllm_health()
    return HealthResponse(
        status="ok" if vllm_ok else "degraded",
        model=MODEL_NAME,
        vllm_connected=vllm_ok,
        tavily_configured=bool(TAVILY_API_KEY),
    )


@app.post("/api/research", response_model=ResearchStartResponse)
@limiter.limit("5/minute")
async def start_research(
    payload: ResearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Start a new market research job.

    Returns immediately with a job_id. Poll GET /api/research/{job_id}
    for status and results.
    """
    # Create job
    job = ResearchJob(
        query=payload.query,
        type=payload.type,
    )
    jobs[job.job_id] = job

    logger.info(f"New research job: {job.job_id} for '{payload.query}'")

    # Start background task
    background_tasks.add_task(_run_research_task, job.job_id)

    return ResearchStartResponse(
        job_id=job.job_id,
        status=job.status,
    )


@app.get("/api/research/{job_id}")
async def get_research(job_id: str):
    """Get the status and results of a research job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.get("/api/research/{job_id}/export")
async def export_research(job_id: str, format: str = "md"):
    """Export a completed research report as Markdown."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status != JobStatus.COMPLETED or not job.report:
        raise HTTPException(status_code=400, detail="Report not yet completed")

    if format == "json":
        return job.report

    if format == "pdf":
        pdf_bytes = generate_pdf(job)
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{job.query}_report.pdf"'},
        )

    # Markdown export (default)
    r = job.report
    md = f"# Market Research Report: {job.query}\n\n"
    md += f"*Generated on {job.completed_at or datetime.utcnow()}*\n\n"
    md += f"---\n\n"

    md += f"## Company Overview\n\n{r.company_overview}\n\n"

    md += f"## SWOT Analysis\n\n"
    md += f"### Strengths\n"
    for s in r.swot.strengths:
        md += f"- {s}\n"
    md += f"\n### Weaknesses\n"
    for w in r.swot.weaknesses:
        md += f"- {w}\n"
    md += f"\n### Opportunities\n"
    for o in r.swot.opportunities:
        md += f"- {o}\n"
    md += f"\n### Threats\n"
    for t in r.swot.threats:
        md += f"- {t}\n"

    md += f"\n## Market Trends\n\n"
    for trend in r.trends:
        md += f"### {trend.title} ({trend.relevance})\n"
        md += f"{trend.description}\n\n"

    md += f"## Competitive Landscape\n\n{r.competitive_landscape}\n\n"

    md += f"## Key Findings\n\n"
    for i, finding in enumerate(r.key_findings, 1):
        md += f"{i}. {finding}\n"

    md += f"\n## Sources\n\n"
    for source in r.sources:
        md += f"- [{source.title}]({source.url})\n"

    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={job.query}_report.md"},
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all research jobs."""
    return [
        {
            "job_id": job.job_id,
            "job_kind": job.job_kind,
            "query": job.query,
            "status": job.status,
            "created_at": job.created_at,
            "duration_seconds": job.duration_seconds,
        }
        for job in sorted(jobs.values(), key=lambda j: j.created_at, reverse=True)
    ]

# --- Crawl & Extract ---

class ExtractRequest(BaseModel):
    urls: list[str] = Field(..., description="List of URLs to extract content from")

class CrawlRequest(BaseModel):
    url: str = Field(..., min_length=5, description="URL to crawl")

@app.post("/api/extract")
@limiter.limit("10/minute")
async def extract_content(payload: ExtractRequest, request: Request):
    """Extract content from URLs using Tavily extract API."""
    from app.services.search_service import extract_urls

    if not payload.urls:
        raise HTTPException(status_code=400, detail="At least one URL is required")

    started_at = datetime.utcnow()
    query_label = payload.urls[0] if len(payload.urls) == 1 else f"{payload.urls[0]} (+{len(payload.urls) - 1} more)"
    job = ResearchJob(
        query=query_label,
        job_kind=JobKind.EXTRACT,
        status=JobStatus.SEARCHING,
    )
    jobs[job.job_id] = job

    # We use extract_depth="advanced" to force Tavily to render JavaScript pages
    result = extract_urls(payload.urls)
    if result.get("failed"):
        job.status = JobStatus.FAILED
        job.error = result.get("error", "Extraction failed")
        job.completed_at = datetime.utcnow()
        job.duration_seconds = (job.completed_at - started_at).total_seconds()
        raise HTTPException(status_code=400, detail=job.error)

    job.status = JobStatus.COMPLETED
    job.operation_result = result
    job.completed_at = datetime.utcnow()
    job.duration_seconds = (job.completed_at - started_at).total_seconds()
    return result

@app.post("/api/crawl")
@limiter.limit("10/minute")
async def crawl_content(payload: CrawlRequest, request: Request):
    """Crawl a URL using Tavily crawl API."""
    from app.services.search_service import crawl_url

    started_at = datetime.utcnow()
    job = ResearchJob(
        query=payload.url,
        job_kind=JobKind.CRAWL,
        status=JobStatus.SEARCHING,
    )
    jobs[job.job_id] = job

    result = crawl_url(payload.url)
    if result.get("failed"):
        job.status = JobStatus.FAILED
        job.error = result.get("error", "Crawl failed")
        job.completed_at = datetime.utcnow()
        job.duration_seconds = (job.completed_at - started_at).total_seconds()
        raise HTTPException(status_code=400, detail=job.error)

    job.status = JobStatus.COMPLETED
    job.operation_result = result
    job.completed_at = datetime.utcnow()
    job.duration_seconds = (job.completed_at - started_at).total_seconds()
    return result


# --- Follow-up Q&A ---

@app.post("/api/research/{job_id}/ask", response_model=AskResponse)
async def ask_question(job_id: str, request: AskRequest):
    """Ask a follow-up question about a completed research report.

    Limited to 10 questions per report. Returns proactive suggestions.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status != JobStatus.COMPLETED or not job.report:
        raise HTTPException(status_code=400, detail="Report not yet completed")
    if job.qa_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail="Question limit reached (10 per report)",
        )

    # Build context from the report
    r = job.report
    report_context = (
        f"Company: {job.query}\n"
        f"Overview: {r.company_overview}\n"
        f"Strengths: {', '.join(r.swot.strengths)}\n"
        f"Weaknesses: {', '.join(r.swot.weaknesses)}\n"
        f"Opportunities: {', '.join(r.swot.opportunities)}\n"
        f"Threats: {', '.join(r.swot.threats)}\n"
        f"Competitive Landscape: {r.competitive_landscape}\n"
        f"Key Findings: {'; '.join(r.key_findings)}\n"
    )

    # Include previous Q&A for continuity
    qa_context = ""
    for qa in job.qa_history:
        qa_context += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strategic market research analyst. Use the research report below "
                "to answer questions. Ground your responses in the report data, but also:\n"
                "- Make intelligent inferences and business connections from the data\n"
                "- Identify sales opportunities, partnership angles, and strategic implications\n"
                "- Reason about industry dynamics even if not explicitly stated in the report\n"
                "- When asked about pitching, positioning, or go-to-market, provide actionable advice\n"
                "Be specific, cite data points from the report, and be direct about what is "
                "a fact vs. your inference.\n\n"
                f"REPORT DATA:\n{report_context}"
            ),
        },
    ]

    # Add Q&A history as conversation
    for qa in job.qa_history:
        messages.append({"role": "user", "content": qa["question"]})
        messages.append({"role": "assistant", "content": qa["answer"]})

    messages.append({"role": "user", "content": request.question})

    logger.info(f"[{job_id}] Q&A question ({job.qa_remaining} remaining): {request.question[:80]}")

    answer = await llm_service.chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=500,
    )

    # Track Q&A
    job.qa_history.append({"question": request.question, "answer": answer})
    job.qa_remaining -= 1

    # Generate proactive follow-up suggestions (if questions remain)
    suggested_questions: list[str] = []
    if job.qa_remaining > 0:
        try:
            suggestion_messages = [
                {
                    "role": "system",
                    "content": (
                        "Based on the market research report and the Q&A conversation below, "
                        "suggest exactly 3 concise follow-up questions the user might want to ask next. "
                        "Return ONLY the 3 questions, one per line, numbered 1-3. No other text.\n\n"
                        f"REPORT: {job.query}\n"
                        f"Last question: {request.question}\n"
                        f"Last answer: {answer}\n"
                        f"Previous Q&A count: {len(job.qa_history)}\n"
                        f"Report topics: SWOT, trends, competitive landscape, key findings"
                    ),
                },
                {
                    "role": "user",
                    "content": "Suggest 3 follow-up questions:",
                },
            ]
            raw = await llm_service.chat_completion(
                messages=suggestion_messages,
                temperature=0.5,
                max_tokens=200,
            )
            # Parse numbered lines
            for line in raw.strip().split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove leading number, dot, and whitespace
                    q = line.lstrip("0123456789").lstrip(".").lstrip(")").strip()
                    if q:
                        suggested_questions.append(q)
            suggested_questions = suggested_questions[:3]
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to generate suggestions: {e}")

    return AskResponse(
        answer=answer,
        question=request.question,
        remaining_questions=job.qa_remaining,
        suggested_questions=suggested_questions,
    )


# --- Startup ---

@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("Market Research AI Agent starting...")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Tavily configured: {bool(TAVILY_API_KEY)}")
    vllm_ok = await llm_service.check_vllm_health()
    logger.info(f"vLLM connected: {vllm_ok}")
    logger.info("=" * 50)
