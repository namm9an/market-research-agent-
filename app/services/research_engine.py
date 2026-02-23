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
    JobStatus,
)
from app.services import search_service, llm_service
from app.prompts.templates import SWOT_PROMPT, TRENDS_PROMPT, REPORT_PROMPT

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

        # --- Stage 2: Analyze (SWOT + Trends) ---
        job.status = JobStatus.ANALYZING
        logger.info(f"[{job.job_id}] Stage 2: Analyzing")

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

        # Build sources from search results
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
