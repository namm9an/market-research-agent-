"""FastAPI main application — Market Research AI Agent."""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import MODEL_NAME, TAVILY_API_KEY, REPORTS_DIR
from app.models.schemas import (
    ResearchRequest,
    ResearchJob,
    ResearchStartResponse,
    HealthResponse,
    JobStatus,
)
from app.services import llm_service
from app.services.research_engine import run_research

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- App ---
app = FastAPI(
    title="Market Research AI Agent",
    description="AI-powered market research using NVIDIA Nemotron Nano on E2E Networks",
    version="0.1.0",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """Start a new market research job.

    Returns immediately with a job_id. Poll GET /api/research/{job_id}
    for status and results.
    """
    # Create job
    job = ResearchJob(
        query=request.query,
        type=request.type,
    )
    jobs[job.job_id] = job

    logger.info(f"New research job: {job.job_id} for '{request.query}'")

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

    # Markdown export
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
            "query": job.query,
            "status": job.status,
            "created_at": job.created_at,
            "duration_seconds": job.duration_seconds,
        }
        for job in sorted(jobs.values(), key=lambda j: j.created_at, reverse=True)
    ]


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
