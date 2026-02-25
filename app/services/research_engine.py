"""Research engine — orchestrates the full research pipeline.

This is the core logic: search → analyze → compile report.
Uses direct LLM calls instead of CrewAI for simplicity and control.
CrewAI can be layered on top later if needed.
"""

import json
import logging
import time
from datetime import datetime

from app.models.schemas import (
    ResearchJob,
    ResearchReport,
    SWOTAnalysis,
    Trend,
    Source,
    LeaderProfile,
    ICPFitAssessment,
    CompanyFinancials,
    RevenueYear,
    JobStatus,
    FundingIntelligence,
    FundingMilestone,
)
from app.services import search_service, llm_service
from app.prompts.templates import (
    SWOT_PROMPT,
    TRENDS_PROMPT,
    LEADERS_PROMPT,
    ICP_FIT_PROMPT,
    FINANCIALS_PROMPT,
    REPORT_PROMPT,
    FUNDING_INTELLIGENCE_PROMPT,
)

logger = logging.getLogger(__name__)


def _parse_json_response(text: str) -> dict | list:
    """Parse JSON from LLM response, handling common issues."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try finding JSON object/array boundaries
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    logger.warning(f"Failed to parse JSON from LLM response: {text[:200]}")
    return {}


def _extract_swot(data) -> SWOTAnalysis:
    """Robustly extract SWOT from various LLM response formats.

    Handles:
    - Direct: {"strengths": [...], "weaknesses": [...], ...}
    - Nested: {"swot": {"strengths": [...], ...}}
    - Case variations: {"Strengths": [...]}
    - Wrapped: {"CompanyA_vs_CompanyB": {"strengths": [...]}}
    """
    if not isinstance(data, dict):
        return SWOTAnalysis()

    swot_keys = {"strengths", "weaknesses", "opportunities", "threats"}

    def _find_swot_keys(d: dict) -> dict:
        """Find SWOT keys in a dict, case-insensitive."""
        result = {}
        lower_map = {k.lower(): v for k, v in d.items()}
        for key in swot_keys:
            if key in lower_map and isinstance(lower_map[key], list):
                result[key] = lower_map[key]
        return result

    # Try direct extraction
    found = _find_swot_keys(data)
    if len(found) >= 2:  # At least 2 SWOT keys found
        return SWOTAnalysis(**{k: found.get(k, []) for k in swot_keys})

    # Try one level deeper (nested under "swot" or a wrapper key)
    for key, val in data.items():
        if isinstance(val, dict):
            found = _find_swot_keys(val)
            if len(found) >= 2:
                return SWOTAnalysis(**{k: found.get(k, []) for k in swot_keys})
            # Try two levels deep (e.g. {"analysis": {"swot": {...}}})
            for key2, val2 in val.items():
                if isinstance(val2, dict):
                    found = _find_swot_keys(val2)
                    if len(found) >= 2:
                        return SWOTAnalysis(**{k: found.get(k, []) for k in swot_keys})

    logger.warning(f"Could not extract SWOT from LLM response keys: {list(data.keys())}")
    return SWOTAnalysis()


def _coerce_str_list(value) -> list[str]:
    """Convert JSON-ish values to a clean list[str]."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_leaders(data) -> list[LeaderProfile]:
    """Extract structured leader records from variable LLM JSON shapes."""
    raw_items: list[dict] = []

    if isinstance(data, list):
        raw_items = [i for i in data if isinstance(i, dict)]
    elif isinstance(data, dict):
        for key in ["leaders", "leadership_team", "executives", "team", "items"]:
            value = data.get(key)
            if isinstance(value, list):
                raw_items = [i for i in value if isinstance(i, dict)]
                break
        if not raw_items:
            # Fallback: treat dict itself as a single record if it resembles one.
            if any(k in data for k in ["name", "title", "role", "position"]):
                raw_items = [data]

    leaders: list[LeaderProfile] = []
    seen: set[tuple[str, str]] = set()

    for item in raw_items:
        name = str(item.get("name") or item.get("full_name") or "").strip()
        title = str(item.get("title") or item.get("role") or item.get("position") or "").strip()
        function = str(item.get("function") or item.get("department") or item.get("area") or "Other").strip()
        source_url = str(item.get("source_url") or item.get("source") or item.get("url") or "").strip()
        evidence = str(item.get("evidence") or item.get("snippet") or "").strip()
        confidence = str(item.get("confidence") or "medium").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"

        if not name and not title:
            continue

        dedupe_key = (name.lower(), title.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        leaders.append(
            LeaderProfile(
                name=name,
                title=title,
                function=function,
                source_url=source_url,
                evidence=evidence,
                confidence=confidence,
            )
        )

    return leaders[:12]


def _extract_icp_fit(data) -> ICPFitAssessment:
    """Extract ICP fit assessment with defensive defaults."""
    if not isinstance(data, dict):
        return ICPFitAssessment()

    score_raw = data.get("fit_score", data.get("score", data.get("icp_score", 0)))
    try:
        fit_score = int(float(score_raw))
    except (TypeError, ValueError):
        fit_score = 0
    fit_score = max(0, min(100, fit_score))

    fit_tier = str(data.get("fit_tier", data.get("tier", ""))).strip().lower()
    if fit_tier not in {"high", "medium", "low"}:
        if fit_score >= 80:
            fit_tier = "high"
        elif fit_score >= 50:
            fit_tier = "medium"
        else:
            fit_tier = "low"

    summary = str(data.get("summary", data.get("overview", ""))).strip()
    reasons = _coerce_str_list(data.get("reasons", data.get("signals", [])))
    pitch_angles = _coerce_str_list(data.get("recommended_pitch_angles", data.get("pitch_angles", data.get("next_steps", []))))
    concerns = _coerce_str_list(data.get("concerns", data.get("risks", data.get("blockers", []))))

    return ICPFitAssessment(
        fit_score=fit_score,
        fit_tier=fit_tier,
        summary=summary,
        reasons=reasons,
        recommended_pitch_angles=pitch_angles,
        concerns=concerns,
    )


def _extract_financials(data) -> CompanyFinancials:
    """Extract financials with defensive defaults."""
    if not isinstance(data, dict):
        return CompanyFinancials()

    core_business_summary = str(data.get("core_business_summary", "")).strip()
    market_cap = str(data.get("market_cap", "Private or Unknown")).strip()
    funding_stage = str(data.get("funding_stage", "Unknown")).strip()
    
    revenue_history = []
    raw_history = data.get("revenue_history", [])
    if isinstance(raw_history, list):
        for item in raw_history:
            if isinstance(item, dict):
                year = str(item.get("year", "")).strip()
                amount = str(item.get("amount", "")).strip()
                if year and amount:
                    revenue_history.append(RevenueYear(year=year, amount=amount))

    return CompanyFinancials(
        core_business_summary=core_business_summary,
        market_cap=market_cap,
        funding_stage=funding_stage,
        revenue_history=revenue_history,
    )

def _extract_funding_intel(data) -> FundingIntelligence:
    """Extract funding intelligence with fallback values"""
    if not isinstance(data, dict):
        return FundingIntelligence()
        
    timeline_raw = data.get("funding_timeline", [])
    timeline = []
    if isinstance(timeline_raw, list):
        for item in timeline_raw:
            if isinstance(item, dict):
                timeline.append(FundingMilestone(
                    date_or_round=str(item.get("date_or_round", "")),
                    amount=str(item.get("amount", "")),
                    investors=_coerce_str_list(item.get("investors", []))
                ))

    return FundingIntelligence(
        investor_types=_coerce_str_list(data.get("investor_types", [])),
        funding_timeline=timeline,
        capital_allocation_purpose=str(data.get("capital_allocation_purpose", "Unknown")),
        e2e_compute_lead_status=str(data.get("e2e_compute_lead_status", "Cold")),
        compute_spending_evidence=str(data.get("compute_spending_evidence", "No evidence found"))
    )

async def run_research(job: ResearchJob) -> ResearchJob:
    """Execute the full research pipeline for a company.

    Updates the job status as it progresses through each stage.

    Args:
        job: The ResearchJob to execute.

    Returns:
        The completed (or failed) ResearchJob.
    """
    start_time = time.time()

    try:
        # --- Stage 1: Search ---
        job.status = JobStatus.SEARCHING
        logger.info(f"[{job.job_id}] Stage 1: Searching for '{job.query}'")

        search_results = search_service.search_company(job.query)
        context = search_service.format_search_context(search_results)

        logger.info(f"[{job.job_id}] Search complete: {len(context)} chars of context")

        # --- Stage 2: Analyze (SWOT + Trends + Leaders + ICP + Financials) ---
        job.status = JobStatus.ANALYZING
        logger.info(f"[{job.job_id}] Stage 2: Analyzing (SWOT + Trends + Leaders + ICP + Financials)")

        # Generate SWOT analysis
        swot_prompt = SWOT_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        swot_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are a senior market research analyst. Respond only in valid JSON."},
            {"role": "user", "content": swot_prompt},
        ])
        swot_data = _parse_json_response(swot_response)
        swot = _extract_swot(swot_data)

        logger.info(f"[{job.job_id}] SWOT generated: {len(swot.strengths)}S/{len(swot.weaknesses)}W/{len(swot.opportunities)}O/{len(swot.threats)}T")

        # Generate trends
        trends_prompt = TRENDS_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        trends_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are a market intelligence analyst. Respond only in valid JSON."},
            {"role": "user", "content": trends_prompt},
        ])
        trends_data = _parse_json_response(trends_response)
        trends = [Trend(**t) for t in trends_data] if isinstance(trends_data, list) else []

        logger.info(f"[{job.job_id}] Trends generated: {len(trends)} trends")

        # Generate leadership discovery
        leaders_prompt = LEADERS_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        leaders_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are a B2B sales intelligence analyst. Respond only in valid JSON."},
            {"role": "user", "content": leaders_prompt},
        ])
        leaders_data = _parse_json_response(leaders_response)
        leaders = _extract_leaders(leaders_data)
        logger.info(f"[{job.job_id}] Leaders extracted: {len(leaders)}")

        # Generate ICP fit for E2E Networks
        icp_prompt = ICP_FIT_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        icp_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are an enterprise GTM analyst. Respond only in valid JSON."},
            {"role": "user", "content": icp_prompt},
        ])
        icp_data = _parse_json_response(icp_response)
        icp_fit = _extract_icp_fit(icp_data)
        logger.info(f"[{job.job_id}] ICP fit scored: {icp_fit.fit_score} ({icp_fit.fit_tier})")
        
        # Generate Deep Funding Intelligence
        funding_prompt = FUNDING_INTELLIGENCE_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        funding_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are a Tech Venture Analyst. Respond only in valid JSON."},
            {"role": "user", "content": funding_prompt},
        ])
        funding_data = _parse_json_response(funding_response)
        funding_intel = _extract_funding_intel(funding_data)
        logger.info(f"[{job.job_id}] Funding Intel generated. Lead status: {funding_intel.e2e_compute_lead_status}")

        # Generate financials and core business metrics
        financials_prompt = FINANCIALS_PROMPT.format(
            company_name=job.query,
            context=context,
        )
        financials_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are a financial performance analyst. Respond only in valid JSON."},
            {"role": "user", "content": financials_prompt},
        ])
        financials_data = _parse_json_response(financials_response)
        financials = _extract_financials(financials_data)
        logger.info(f"[{job.job_id}] Financials extracted: Cap={financials.market_cap}, RevYrs={len(financials.revenue_history)}")

        # --- Stage 3: Compile Report ---
        job.status = JobStatus.COMPILING
        logger.info(f"[{job.job_id}] Stage 3: Compiling report")

        report_prompt = REPORT_PROMPT.format(
            company_name=job.query,
            context=context,
            swot=json.dumps(swot.model_dump(), indent=2),
            trends=json.dumps([t.model_dump() for t in trends], indent=2),
        )
        report_response = await llm_service.chat_completion([
            {"role": "system", "content": "You are an expert business writer. Respond only in valid JSON."},
            {"role": "user", "content": report_prompt},
        ])
        report_data = _parse_json_response(report_response)

        # Build sources from all search results
        sources = [
            Source(
                url=s["url"],
                title=s["title"],
                scraped_at=datetime.fromisoformat(s["scraped_at"]) if s.get("scraped_at") else None,
            )
            for s in search_results.get("all_sources", [])
        ]

        # Assemble final report
        job.report = ResearchReport(
            company_overview=report_data.get("company_overview", ""),
            swot=swot,
            trends=trends,
            competitive_landscape=report_data.get("competitive_landscape", ""),
            key_findings=report_data.get("key_findings", []),
            sources=sources,
        )

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.duration_seconds = round(time.time() - start_time, 1)

        logger.info(
            f"[{job.job_id}] Research complete for '{job.query}' "
            f"in {job.duration_seconds}s"
        )

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        job.duration_seconds = round(time.time() - start_time, 1)
        logger.error(f"[{job.job_id}] Research failed: {e}", exc_info=True)

    return job
