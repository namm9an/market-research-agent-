"""FastAPI main application — Market Research AI Agent."""

import asyncio
import json
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

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
from app.services import llm_service, search_service
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

LEADERSHIP_QUERY_RE = re.compile(
    r"\b(leader|leaders|leadership|ceo|cfo|cto|coo|executive|executives|board|founder|president|chair|managing director|country manager|general manager|vp|svp|head|heads)\b",
    flags=re.IGNORECASE,
)
ACQUISITION_QUERY_RE = re.compile(
    r"\b(acquisition|acquisitions|acquire|acquired|buyout|merger|merged|takeover|deal|deals)\b",
    flags=re.IGNORECASE,
)
REASONING_LEAK_RE = re.compile(
    r"\b(the user asks|let'?s think|better to answer|given uncertainty|actually i think|not sure\.)\b",
    flags=re.IGNORECASE,
)
REASONING_LINE_RE = re.compile(
    r"(?i)^\s*(we need to|let'?s|i think|actually|not sure|could be|maybe|better to|given uncertainty|target company:|output requirements:|must end each bullet|we can answer|the user asks)"
)
CITATION_RE = re.compile(r"\[\d+\]")
CITATION_ONLY_RE = re.compile(r"^\s*(\[\d+\]\s*)+$")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{7,}\d)")
COMPLIANCE_RE = re.compile(r"\b(soc\s*2|soc2|iso\s*\d+|hipaa|gdpr|pci\s*dss|dpdp|compliant|certified)\b", flags=re.IGNORECASE)
PRICING_RE = re.compile(r"(?:₹|\$|cost|pricing|price|/hr|per hour|monthly|yearly|save|savings|lower costs?)", flags=re.IGNORECASE)
LEADERSHIP_TITLE_RE = re.compile(
    r"\b(ceo|cto|cfo|coo|chief|director|president|vice president|vp|svp|head|founder|managing director|country manager|general manager|officer)\b",
    flags=re.IGNORECASE,
)


def _parse_json_from_text(text: str) -> dict | list:
    """Parse JSON from plain or markdown-wrapped model responses."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidate = text.strip()
    if "```json" in candidate:
        candidate = candidate.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in candidate:
        candidate = candidate.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = candidate.find(start_char)
        end = candidate.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            snippet = candidate[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    return {}


def _as_clean_list(value, max_items: int = 10) -> list[str]:
    """Normalize unknown JSON values into list[str] with dedupe."""
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = [str(v) for v in value]
    else:
        items = []

    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        cleaned = re.sub(r"\s+", " ", item).strip(" -•\t\r\n")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= max_items:
            break
    return out


def _compact_crawl_text(text: str) -> str:
    """Clean crawl text: collapse whitespace and dedupe noisy repeated lines."""
    if not isinstance(text, str):
        return ""
    lines = text.splitlines()
    seen: set[str] = set()
    kept: list[str] = []
    for raw in lines:
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 3:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def _build_crawl_context(seed_url: str, crawl_result: dict, max_chars: int = 22000) -> str:
    """Build compact multi-source context string from Tavily crawl output."""
    results = crawl_result.get("results", [])
    if not isinstance(results, list):
        return ""

    chunks: list[str] = []
    total = 0
    for idx, item in enumerate(results[:10], 1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip() or seed_url
        title = str(item.get("title", "")).strip()
        body = _compact_crawl_text(str(item.get("raw_content") or item.get("content") or ""))
        if len(body) > 4500:
            body = f"{body[:4500]}..."

        chunk = (
            f"Source [{idx}]\n"
            f"URL: {url}\n"
            f"Title: {title}\n"
            f"Content:\n{body}"
        )
        if total + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        total += len(chunk)

    return "\n\n---\n\n".join(chunks)


def _normalize_company_profile(profile: dict, seed_url: str, crawl_result: dict) -> dict:
    """Force company profile shape for frontend stability."""
    if not isinstance(profile, dict):
        profile = {}

    sources: list[dict[str, str]] = []
    raw_results = crawl_result.get("results", [])
    if isinstance(raw_results, list):
        for item in raw_results[:10]:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            if url:
                sources.append({"url": url, "title": title})

    raw_leadership = profile.get("leadership") or profile.get("leaders") or []
    leadership: list[dict[str, str]] = []
    if isinstance(raw_leadership, list):
        for entry in raw_leadership[:12]:
            if isinstance(entry, dict):
                name = str(entry.get("name", "")).strip()
                title = str(entry.get("title", entry.get("role", ""))).strip()
            else:
                name = str(entry).strip()
                title = ""
            if name:
                leadership.append({"name": name, "title": title})

    contact_raw = profile.get("contact", {})
    if not isinstance(contact_raw, dict):
        contact_raw = {}

    normalized = {
        "company_name": str(profile.get("company_name", profile.get("name", ""))).strip(),
        "website": str(profile.get("website", seed_url)).strip() or seed_url,
        "one_liner": str(profile.get("one_liner", profile.get("tagline", ""))).strip(),
        "overview": str(profile.get("overview", profile.get("description", ""))).strip(),
        "offerings": _as_clean_list(profile.get("offerings", profile.get("products_services", [])), max_items=12),
        "target_audiences": _as_clean_list(profile.get("target_audiences", profile.get("target_customers", []))),
        "differentiators": _as_clean_list(profile.get("differentiators", profile.get("value_props", []))),
        "proof_points": _as_clean_list(profile.get("proof_points", profile.get("proof", [])), max_items=12),
        "compliance": _as_clean_list(profile.get("compliance", profile.get("certifications", [])), max_items=8),
        "pricing_signals": _as_clean_list(profile.get("pricing_signals", profile.get("pricing", [])), max_items=8),
        "notable_facts": _as_clean_list(profile.get("notable_facts", profile.get("facts", [])), max_items=10),
        "leadership": leadership,
        "contact": {
            "emails": _as_clean_list(contact_raw.get("emails", profile.get("emails", [])), max_items=5),
            "phones": _as_clean_list(contact_raw.get("phones", profile.get("phones", [])), max_items=5),
            "cta": _as_clean_list(contact_raw.get("cta", contact_raw.get("cta_links", profile.get("cta_links", []))), max_items=8),
        },
        "sources": sources,
    }
    return normalized


async def _extract_company_profile_from_crawl(seed_url: str, crawl_result: dict) -> dict:
    """Generate normalized company profile object from crawl output."""
    context = _build_crawl_context(seed_url, crawl_result)
    if not context.strip():
        return {}

    prompt = (
        "You are a B2B research extractor. Convert crawled company website text into a normalized JSON profile.\n"
        "Rules:\n"
        "- Return valid JSON only. No markdown.\n"
        "- Deduplicate repeated navbar/footer text.\n"
        "- Use only provided context; do not invent facts.\n"
        "- Keep arrays concise and useful.\n\n"
        "JSON schema:\n"
        "{\n"
        '  "company_name": "",\n'
        '  "website": "",\n'
        '  "one_liner": "",\n'
        '  "overview": "",\n'
        '  "offerings": [],\n'
        '  "target_audiences": [],\n'
        '  "differentiators": [],\n'
        '  "proof_points": [],\n'
        '  "compliance": [],\n'
        '  "pricing_signals": [],\n'
        '  "notable_facts": [],\n'
        '  "leadership": [{"name": "", "title": ""}],\n'
        '  "contact": {"emails": [], "phones": [], "cta": []}\n'
        "}\n"
    )

    raw = await llm_service.chat_completion(
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Primary URL: {seed_url}\n\n"
                    f"Crawled Context:\n{context}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    parsed = _parse_json_from_text(raw)
    if not isinstance(parsed, dict):
        return {}
    return _normalize_company_profile(parsed, seed_url=seed_url, crawl_result=crawl_result)


def _needs_followup_web_context(question: str) -> bool:
    """Detect follow-up questions that likely need fresh factual lookup."""
    q = question.lower()
    if LEADERSHIP_QUERY_RE.search(q):
        return True
    if "who is" in q or "who are" in q or "current" in q or "latest" in q:
        return True
    if "pull up" in q or "data on" in q or "names and titles" in q:
        return True
    return False


def _result_mentions_company(item: dict, company_tokens: list[str]) -> bool:
    """Basic relevance gate to reduce wrong-company snippets in follow-up context."""
    if not company_tokens:
        return True

    haystack = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("url", "")),
            str(item.get("content", "")),
            str(item.get("raw_content", "")),
        ]
    ).lower()

    for token in company_tokens:
        # Keep short acronym matching strict (e.g., "amd" as a whole word).
        if token.isalpha() and len(token) <= 4:
            if re.search(rf"\b{re.escape(token)}\b", haystack):
                return True
        elif token in haystack:
            return True
    return False


def _build_web_context(company: str, question: str, previous_questions: list[str] | None = None) -> str:
    """Fetch and format compact Tavily context for follow-up factual questions."""
    q = question.lower()
    search_queries = [f"{company} {question}"]

    if previous_questions and (len(question.split()) <= 7 or re.search(r"\b(they|them|their|it|its|those|these)\b", q)):
        search_queries.insert(0, f"{company} {previous_questions[-1]} {question}")

    if LEADERSHIP_QUERY_RE.search(q):
        search_queries.extend(
            [
                f"{company} leadership team executives official",
                f"{company} CEO CFO executive leadership",
            ]
        )

    if "india" in q:
        search_queries.append(f"{company} India leadership country manager general manager")

    collected_results: list[dict] = []
    fallback_results: list[dict] = []
    seen_urls: set[str] = set()
    company_tokens = [
        t for t in re.split(r"[^a-zA-Z0-9]+", company.lower())
        if t and len(t) >= 3
    ]

    for sq in search_queries:
        result = search_service.search(
            query=sq,
            topic="general",
            use_cache=False,
            max_results=4,
        )

        for item in result.get("results", [])[:4]:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if isinstance(url, str) and url and url not in seen_urls:
                seen_urls.add(url)
                if _result_mentions_company(item, company_tokens):
                    collected_results.append(item)
                else:
                    fallback_results.append(item)

    # Fallback to recency-focused search if general web retrieval is sparse.
    if len(collected_results) < 3:
        fallback_query = f"{company} {question}"
        if LEADERSHIP_QUERY_RE.search(q):
            fallback_query = f"{fallback_query} leadership executives"
        fallback = search_service.search(
            query=fallback_query,
            topic="news",
            time_range="year",
            use_cache=False,
            max_results=5,
        )
        for item in fallback.get("results", [])[:5]:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if isinstance(url, str) and url and url not in seen_urls:
                seen_urls.add(url)
                if _result_mentions_company(item, company_tokens):
                    collected_results.append(item)
                else:
                    fallback_results.append(item)

    # If strict company filtering leaves too little context, allow best-effort fallback.
    if len(collected_results) < 2 and fallback_results:
        collected_results.extend(fallback_results[: 2 - len(collected_results)])

    lines: list[str] = []

    for i, item in enumerate(collected_results[:7], 1):
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        snippet = (item.get("content") or item.get("raw_content") or "").strip()
        if len(snippet) > 700:
            snippet = f"{snippet[:700]}..."
        lines.append(
            f"[{i}] {title}\n"
            f"URL: {url}\n"
            f"Snippet: {snippet}"
        )

    return "\n\n".join(lines)


def _sanitize_followup_answer(text: str) -> str:
    """Strip leaked chain-of-thought style reasoning before sending to frontend."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    # Remove model reasoning tags if present.
    cleaned = re.sub(r"(?is)<think>.*?</think>", "", cleaned).strip()
    cleaned = re.sub(r"(?is)<thinking>.*?</thinking>", "", cleaned).strip()
    if not cleaned:
        return ""

    # If the answer clearly contains internal reasoning, remove those lines.
    if REASONING_LEAK_RE.search(cleaned):
        kept_lines: list[str] = []
        for line in cleaned.splitlines():
            if not REASONING_LEAK_RE.search(line) and not REASONING_LINE_RE.search(line):
                kept_lines.append(line)
        candidate = "\n".join(kept_lines).strip()
        if candidate:
            cleaned = candidate

    # Second line-level sweep for "reasoning voice" leakage.
    filtered_lines: list[str] = []
    for line in cleaned.splitlines():
        if REASONING_LINE_RE.search(line):
            continue
        filtered_lines.append(line)
    cleaned = "\n".join(filtered_lines).strip()

    return cleaned


def _has_citations(text: str) -> bool:
    """Check whether answer includes source citation markers like [1], [2]."""
    return bool(CITATION_RE.search(text or ""))


def _looks_like_reasoning_leak(text: str) -> bool:
    """Detect responses that still look like internal reasoning instead of final answer."""
    if not text:
        return False
    lowered = text.lower()
    markers = [
        "we need to answer",
        "let's think",
        "i think",
        "not sure",
        "output requirements",
        "target company",
        "must end each bullet",
        "given uncertainty",
    ]
    if any(m in lowered for m in markers):
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    flagged = sum(1 for ln in lines if REASONING_LINE_RE.search(ln))
    return flagged >= 2


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

    # Financials
    fin = getattr(r, "financials", None)
    if fin:
        md += f"## Core Business & Financials\n\n"
        md += f"**Core Business:** {fin.core_business_summary}\n\n"
        md += f"- **Market Cap:** {fin.market_cap}\n"
        md += f"- **Funding Stage:** {fin.funding_stage}\n"
        if fin.revenue_history:
            md += f"\n**Revenue History:**\n"
            for rev in fin.revenue_history:
                md += f"- {rev.year}: {rev.amount}\n"
        md += "\n"

    md += f"\n## Leader Discovery\n\n"
    leaders = getattr(r, "leaders", []) or []
    if leaders:
        for leader in leaders:
            confidence = getattr(leader, "confidence", "medium")
            function = getattr(leader, "function", "")
            source_url = getattr(leader, "source_url", "")
            evidence = getattr(leader, "evidence", "")
            md += f"- **{leader.name}** — {leader.title}"
            if function:
                md += f" ({function})"
            md += f" | confidence: {confidence}\n"
            if source_url:
                md += f"  - Source: {source_url}\n"
            if evidence:
                md += f"  - Evidence: {evidence}\n"
    else:
        md += "- No reliable leaders extracted from available context.\n"

    icp_fit = getattr(r, "icp_fit", None)
    md += f"\n## ICP Fit (E2E Networks)\n\n"
    if icp_fit:
        md += f"- **Fit Score:** {icp_fit.fit_score}/100\n"
        md += f"- **Fit Tier:** {icp_fit.fit_tier}\n"
        if icp_fit.summary:
            md += f"- **Summary:** {icp_fit.summary}\n"
        if icp_fit.reasons:
            md += "\n### Fit Reasons\n"
            for reason in icp_fit.reasons:
                md += f"- {reason}\n"
        if icp_fit.recommended_pitch_angles:
            md += "\n### Recommended Pitch Angles\n"
            for angle in icp_fit.recommended_pitch_angles:
                md += f"- {angle}\n"
        if icp_fit.concerns:
            md += "\n### Concerns / Mitigations\n"
            for concern in icp_fit.concerns:
                md += f"- {concern}\n"

    # Deep Funding Intelligence
    fund = getattr(r, "funding_intelligence", None)
    if fund:
        md += "\n## Capital Allocation & GPU Spending Intent\n\n"
        md += f"**Compute Lead Status:** {fund.e2e_compute_lead_status.upper()}\n\n"
        md += f"**Analysis of IT/Compute Spend:**\n{fund.capital_allocation_purpose}\n\n"
        md += f"> {fund.compute_spending_evidence}\n\n"
        
        if fund.investor_types:
            md += "**Investor Profile:** " + ", ".join(fund.investor_types) + "\n\n"

        if fund.funding_timeline:
            md += "**Major Funding Rounds:**\n"
            for round_data in fund.funding_timeline:
                inv_text = ", ".join(round_data.investors) if round_data.investors else "Unknown Investors"
                md += f"- {round_data.date_or_round}: {round_data.amount} ({inv_text})\n"
            md += "\n"
            md += "\n### Recommended Pitch Angles\n"
            for angle in icp_fit.recommended_pitch_angles:
                md += f"- {angle}\n"
        if icp_fit.concerns:
            md += "\n### Concerns / Risks\n"
            for concern in icp_fit.concerns:
                md += f"- {concern}\n"
    else:
        md += "- ICP fit assessment unavailable.\n"

    md += f"\n## Market Trends\n\n"
    for trend in r.trends:
        md += f"### {trend.title} ({trend.relevance})\n"
        md += f"{trend.description}\n\n"

    md += f"## Competitive Landscape\n\n{r.competitive_landscape}\n\n"

    md += f"## Key Findings\n\n"
    for i, finding in enumerate(r.key_findings, 1):
        md += f"{i}. {finding}\n"

    md += f"\n## SWOT Analysis\n\n"
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

    md += f"\n## Sources\n\n"
    for source in r.sources:
        md += f"- [{source.title}]({source.url})\n"

    qa_history = getattr(job, "qa_history", [])
    if qa_history:
        md += f"\n## Follow-up Q&A\n\n"
        for item in qa_history:
            md += f"**Q: {item['question']}**\n\n"
            md += f"{item['answer']}\n\n"

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


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from history."""
    job = jobs.pop(job_id, None)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Best-effort cleanup of persisted report artifact for research jobs.
    report_file = REPORTS_DIR / f"{job_id}.json"
    if report_file.exists():
        report_file.unlink(missing_ok=True)

    return {"success": True, "job_id": job_id}

# --- Search, Crawl & Extract ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query")
    topic: str = Field("general", description="The category of the search (e.g., 'general', 'news')")
    search_depth: str = Field("basic", description="The depth of the search ('basic' or 'advanced')")
    max_results: int = Field(10, ge=1, le=20, description="Max search results to return")
    days: int = Field(30, ge=1, le=365, description="Number of days back to search (for news)")

class ExtractRequest(BaseModel):
    urls: list[str] = Field(..., description="List of URLs to extract content from")

class CrawlRequest(BaseModel):
    url: str = Field(..., min_length=5, description="URL to crawl")

@app.post("/api/search")
@limiter.limit("20/minute")
async def raw_search(payload: SearchRequest, request: Request):
    """Execute a raw search using the Tavily API without LLM analysis."""
    from app.services.search_service import search

    started_at = datetime.utcnow()
    job = ResearchJob(
        query=payload.query,
        job_kind=JobKind.SEARCH,
        status=JobStatus.SEARCHING,
    )
    jobs[job.job_id] = job

    try:
        results = search(
            query=payload.query,
            topic=payload.topic,
            search_depth=payload.search_depth,
            max_results=payload.max_results,
            days=payload.days
        )
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        job.duration_seconds = (job.completed_at - started_at).total_seconds()
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    job.status = JobStatus.COMPLETED
    job.operation_result = results
    job.completed_at = datetime.utcnow()
    job.duration_seconds = (job.completed_at - started_at).total_seconds()

    return results

@app.post("/api/extract")
@limiter.limit("10/minute")
async def extract_content(payload: ExtractRequest, request: Request):
    """Extract content from URLs using Tavily extract API and structure via LLM."""
    from app.services.search_service import extract_urls
    from app.prompts.templates import CRAWL_STRUCTURING_PROMPT
    from app.services.research_engine import _parse_json_response

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
    utc_today = datetime.utcnow().date().isoformat()
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

    # Always perform a fresh web lookup for each Q&A ask.
    # This prevents stale/cross-question drift and keeps follow-ups live-grounded.
    web_context = ""
    is_factual_followup = _needs_followup_web_context(request.question)
    try:
        previous_questions = [qa["question"] for qa in job.qa_history[-3:]]
        web_context = _build_web_context(job.query, request.question, previous_questions=previous_questions)
    except Exception as e:
        logger.warning(f"[{job_id}] Web context lookup failed: {e}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strategic market research analyst.\n"
                f"Target company for this question: {job.query}.\n"
                "Do not switch to another company unless explicitly asked by the user.\n"
                "Return final answer only. Never reveal hidden reasoning, self-talk, or analysis process.\n"
                "Use REPORT DATA as primary context for analysis questions. "
                "For people/title/current-entity questions, prioritize WEB CONTEXT and cite source numbers like [1], [2].\n"
                f"As-of date for your answer: {utc_today} (UTC).\n"
                "If context is insufficient, say what is missing instead of guessing.\n"
                "If prior assistant messages conflict with WEB CONTEXT, correct them explicitly.\n\n"
                f"REPORT DATA:\n{report_context}\n\n"
                f"WEB CONTEXT:\n{web_context if web_context else 'None'}"
            ),
        },
    ]

    # Add limited Q&A history as user-questions only to avoid propagating prior wrong answers.
    for qa in job.qa_history[-6:]:
        messages.append({"role": "user", "content": qa["question"]})

    messages.append({"role": "user", "content": request.question})

    logger.info(f"[{job_id}] Q&A question ({job.qa_remaining} remaining): {request.question[:80]}")

    raw_answer = await llm_service.chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=500,
    )
    answer = _sanitize_followup_answer(raw_answer)
    if is_factual_followup:
        if not web_context.strip():
            answer = (
                f"I couldn't fetch reliable live web context for {job.query} right now. "
                "Please retry in a minute."
            )
        elif not _has_citations(answer):
            # Second pass: enforce strict web-grounded answer format with citations.
            strict_messages = [
                {
                    "role": "system",
                    "content": (
                        "Answer using ONLY WEB CONTEXT. Do not use prior memory.\n"
                        f"Target company: {job.query}\n"
                        f"As-of date: {utc_today} (UTC)\n"
                        "Output requirements:\n"
                        "- Provide concise bullet points with names and titles.\n"
                        "- Every factual bullet must end with citation markers like [1], [2].\n"
                        "- If reliable names are not present, say so clearly.\n"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {request.question}\n\n"
                        f"WEB CONTEXT:\n{web_context}"
                    ),
                },
            ]
            strict_raw = await llm_service.chat_completion(
                messages=strict_messages,
                temperature=0.1,
                max_tokens=400,
            )
            strict_answer = _sanitize_followup_answer(strict_raw)
            if strict_answer and _has_citations(strict_answer):
                answer = strict_answer
            else:
                answer = (
                    "I couldn't verify this reliably from live sources for your question. "
                    "Please retry with a more specific question (for example: "
                    f"'{job.query} acquisitions in 2024 with sources')."
                )
    elif not answer:
        answer = "I don't have enough reliable context to answer that accurately."

    # Final safety net: if reasoning text still leaked, force a clean rewrite.
    if _looks_like_reasoning_leak(answer):
        rewrite_messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the assistant answer as FINAL OUTPUT ONLY.\n"
                    "Do not include planning, self-talk, or process language.\n"
                    "Use only the provided contexts; if uncertain, say so briefly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {request.question}\n\n"
                    f"REPORT DATA:\n{report_context}\n\n"
                    f"WEB CONTEXT:\n{web_context if web_context else 'None'}\n\n"
                    f"DRAFT ANSWER:\n{answer}"
                ),
            },
        ]
        rewrite_raw = await llm_service.chat_completion(
            messages=rewrite_messages,
            temperature=0.1,
            max_tokens=500,
        )
        rewritten = _sanitize_followup_answer(rewrite_raw)
        if rewritten:
            answer = rewritten

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
