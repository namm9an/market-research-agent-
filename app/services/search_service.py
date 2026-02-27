"""Search service — wraps SearXNG (search) and Crawl4AI (extract/crawl)."""

import re
import json
import hashlib
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.config import SEARXNG_BASE_URL, MAX_SEARCH_RESULTS, CACHE_DIR

logger = logging.getLogger(__name__)


# ── Cache helpers ───────────────────────────────────────────────


def _cache_key(query: str, topic: str, search_depth: str, days: int | None, time_range: str | None) -> str:
    """Generate a cache key from query parameters."""
    raw = f"{query}|{topic}|{search_depth}|{days}|{time_range}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache(key: str) -> dict | None:
    """Load cached search results if they exist."""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        logger.info(f"Cache hit: {key}")
        return json.loads(cache_file.read_text())
    return None


def _save_cache(key: str, data: dict) -> None:
    """Save search results to cache."""
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(json.dumps(data, default=str, indent=2))
    logger.info(f"Cached: {key}")


# ── SearXNG Search ──────────────────────────────────────────────


def search(
    query: str,
    topic: str = "general",
    search_depth: str = "advanced",
    max_results: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    use_cache: bool = True,
) -> dict:
    """Search the web using self-hosted SearXNG.

    Args:
        query: Search query string.
        topic: "general" or "news".
        search_depth: Ignored for SearXNG (kept for API compat).
        max_results: Override default max results.
        time_range: "day", "week", "month", "year" or None.
        days: Number of days — mapped to time_range if set.
        use_cache: Whether to check/save cache.

    Returns:
        Dict with 'results' and 'answer' keys (same shape as before).
    """
    # Check cache first
    key = _cache_key(query, topic, search_depth, days, time_range)
    if use_cache:
        cached = _load_cache(key)
        if cached:
            return cached

    effective_max = max_results or MAX_SEARCH_RESULTS

    # Map days → SearXNG time_range
    effective_time_range = time_range
    if not effective_time_range and days:
        if days <= 1:
            effective_time_range = "day"
        elif days <= 7:
            effective_time_range = "week"
        elif days <= 30:
            effective_time_range = "month"
        else:
            effective_time_range = "year"

    # Map our topic to SearXNG categories
    categories = "general"
    if topic == "news":
        categories = "news"

    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "pageno": 1,
    }
    if effective_time_range:
        params["time_range"] = effective_time_range

    logger.info(f"SearXNG search: query='{query}', topic={topic}")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{SEARXNG_BASE_URL}/search", params=params)
            resp.raise_for_status()
            raw = resp.json()
    except Exception as e:
        logger.error(f"SearXNG search failed: {e}")
        return {"results": [], "answer": ""}

    # Map SearXNG response to our standard format
    searxng_results = raw.get("results", [])[:effective_max]
    results = []
    for r in searxng_results:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": clean_extracted_content(r.get("content", "")),
            "raw_content": clean_extracted_content(r.get("content", "")),
            "score": r.get("score", 0),
        })

    response = {
        "results": results,
        "answer": "",  # SearXNG doesn't generate AI summaries; our LLM handles this
    }

    # Save to cache
    if use_cache:
        _save_cache(key, response)

    logger.info(f"SearXNG returned {len(results)} results")
    return response


def search_company(company_name: str) -> dict:
    """Run all strategic queries for a company and return combined results.

    Returns:
        Dict with keys: 'overview', 'news', 'financial', 'competitors', 'leadership',
        each containing search results.
    """
    logger.info(f"Starting comprehensive search for: {company_name}")

    results = {}

    # Query 1: Company overview
    results["overview"] = search(
        query=f"{company_name} overview products services market position",
        topic="general",
    )

    # Query 2: Recent news
    results["news"] = search(
        query=f"{company_name} latest news acquisitions partnerships 2026",
        topic="news",
        time_range="month",
    )

    # Query 3: Financial data
    results["financial"] = search(
        query=f"{company_name} revenue growth funding valuation",
        topic="general",
    )

    # Query 4: Competitive landscape
    results["competitors"] = search(
        query=f"{company_name} competitors industry comparison market share",
        topic="general",
    )

    # Query 5: Leadership (for sales intelligence / outreach)
    results["leadership"] = search(
        query=f"{company_name} leadership team executives board CTO CIO VP engineering",
        topic="general",
    )

    # Collect all sources
    all_sources = []
    for category, data in results.items():
        for result in data.get("results", []):
            all_sources.append({
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "category": category,
                "scraped_at": datetime.utcnow().isoformat(),
            })

    results["all_sources"] = all_sources
    results["company_name"] = company_name

    logger.info(
        f"Search complete for {company_name}: "
        f"{len(all_sources)} total sources across {len(results) - 2} queries"
    )
    return results


def format_search_context(search_results: dict) -> str:
    """Format search results into a single text context for the LLM.

    Takes the combined output from search_company() and creates a clean,
    readable text block that fits within the LLM's context window.
    Target: ~12,000 chars (~3,000 tokens) to leave room for prompts + response.
    """
    MAX_TOTAL_CHARS = 12000
    MAX_PER_RESULT = 500  # chars per search result
    sections = []
    total_chars = 0

    for category in ["overview", "news", "financial", "competitors", "leadership"]:
        data = search_results.get(category, {})
        answer = data.get("answer", "")
        results = data.get("results", [])

        section_title = category.upper()
        section_parts = [f"\n## {section_title}\n"]

        if answer:
            truncated_answer = answer[:800]
            section_parts.append(f"Summary: {truncated_answer}\n")
            total_chars += len(truncated_answer)

        for r in results[:5]:  # Max 5 results per category
            if total_chars >= MAX_TOTAL_CHARS:
                break
            title = r.get("title", "Untitled")
            content = r.get("content", "")
            url = r.get("url", "")

            # Truncate content to keep things manageable
            text = content[:MAX_PER_RESULT] if content else ""

            section_parts.append(f"### {title}")
            section_parts.append(f"Source: {url}")
            section_parts.append(text)
            section_parts.append("")
            total_chars += len(text) + len(title)

        sections.append("\n".join(section_parts))

    context = "\n".join(sections)
    logger.info(f"Context formatted: {len(context)} chars (~{len(context)//4} tokens)")
    return context


def clean_extracted_content(raw_content: str) -> str:
    """Remove JSON blobs, script noise, and theme data from extracted content."""
    if not isinstance(raw_content, str):
        return raw_content
    lines = raw_content.split('\n')
    cleaned = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines clusters
        if not stripped:
            continue
            
        # Skip lines that look like JSON/JS objects (theme configs, etc.)
        if stripped.startswith('{') and '":"' in stripped:
            continue
            
        # Skip lines with CSS variable patterns
        if re.search(r'(primary-color|pcsx-|varTheme|customTheme|themeOptions|font-family)', stripped):
            continue
            
        # Skip lines that are mostly special characters
        if len(re.sub(r'[^a-zA-Z0-9\s]', '', stripped)) < len(stripped) * 0.4:
            continue
            
        # Skip very short noise lines, but allow markdown headers & lists
        if len(stripped) < 15 and not stripped.startswith(('#', '-', '*', '>')):
            continue
            
        cleaned.append(line)
    return '\n'.join(cleaned).strip()


# ── Crawl4AI Extract & Crawl ───────────────────────────────────


def _run_async(coro):
    """Run an async coroutine from sync code safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (e.g., FastAPI)
        # Create a new thread to run the async code
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


async def _crawl4ai_fetch(url: str) -> dict:
    """Use Crawl4AI to extract content from a single URL."""
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig()

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
        return {
            "url": url,
            "raw_content": clean_extracted_content(result.markdown or ""),
            "success": result.success,
        }


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def extract_urls(urls: list[str]) -> dict:
    """Extract content from a list of URLs using Crawl4AI.

    Returns same shape as old Tavily extract: {results: [{url, raw_content}], failed_results: []}
    """
    logger.info(f"Crawl4AI extract: urls={urls}")
    results = []
    failed = []

    for url in urls:
        try:
            data = _run_async(_crawl4ai_fetch(url))
            if data.get("success"):
                results.append({
                    "url": data["url"],
                    "raw_content": data["raw_content"],
                })
            else:
                failed.append({"url": url, "error": "Crawl4AI extraction failed"})
        except Exception as e:
            logger.error(f"Failed to extract {url}: {e}")
            failed.append({"url": url, "error": str(e)})

    return {"results": results, "failed_results": failed}


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def crawl_url(url: str, extract_depth: str = "advanced") -> dict:
    """Crawl a URL using Crawl4AI.

    Returns same shape as old Tavily crawl: {results: [{url, raw_content}]}
    """
    logger.info(f"Crawl4AI crawl: url='{url}'")
    try:
        data = _run_async(_crawl4ai_fetch(url))
        if data.get("success"):
            return {
                "results": [{
                    "url": data["url"],
                    "raw_content": data["raw_content"],
                }]
            }
        else:
            return {"failed": True, "error": "Crawl4AI failed to crawl this URL"}
    except Exception as e:
        logger.error(f"Failed to crawl URL {url}: {e}")
        return {"failed": True, "error": str(e)}
