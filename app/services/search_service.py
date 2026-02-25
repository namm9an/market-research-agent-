"""Search service — wraps Tavily API for AI-native web search."""

import re
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from httpx import HTTPStatusError
from tavily import TavilyClient, MissingAPIKeyError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.config import TAVILY_API_KEY, MAX_SEARCH_RESULTS, CACHE_DIR

logger = logging.getLogger(__name__)

# Initialize Tavily client
_tavily_client: TavilyClient | None = None

try:
    _tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
except MissingAPIKeyError:
    logger.warning("TAVILY_API_KEY not found. Search functionality will be disabled.")
    _tavily_client = None


def _get_client() -> TavilyClient:
    """Returns the initialized Tavily client."""
    if _tavily_client is None:
        raise ValueError("TAVILY_API_KEY not set or Tavily client failed to initialize.")
    return _tavily_client


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


def search(
    query: str,
    topic: str = "general",
    search_depth: str = "advanced",
    max_results: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    use_cache: bool = True,
) -> dict:
    """Search the web using Tavily.

    Args:
        query: Search query string.
        topic: "general", "news", or "finance".
        search_depth: "basic" or "advanced".
        max_results: Override default max results.
        time_range: "day", "week", "month", "year" or None.
        days: Number of days back (for news topic).
        use_cache: Whether to check/save cache.

    Returns:
        Tavily search response dict with 'results', 'answer', etc.
    """
    # Check cache first
    key = _cache_key(query, topic, search_depth, days, time_range)
    if use_cache:
        cached = _load_cache(key)
        if cached:
            return cached

    client = _get_client()

    kwargs = {
        "query": query,
        "search_depth": search_depth,
        "topic": topic,
        "max_results": max_results or MAX_SEARCH_RESULTS,
        "include_raw_content": "markdown",
        "include_answer": True,
        "include_images": False,
    }

    if time_range:
        kwargs["time_range"] = time_range
    if days:
        kwargs["days"] = days

    logger.info(f"Tavily search: query='{query}', topic={topic}")
    response = client.search(**kwargs)

    # Clean the raw content of each search result to prevent JSON/CSS noise
    if response.get("results"):
        for result in response["results"]:
            if result.get("content"):
                result["content"] = clean_extracted_content(result["content"])
            if result.get("raw_content"):
                result["raw_content"] = clean_extracted_content(result["raw_content"])

    # Save to cache
    if use_cache:
        _save_cache(key, response)

    logger.info(f"Tavily returned {len(response.get('results', []))} results")
    return response


def search_company(company_name: str) -> dict:
    """Run all strategic queries for a company and return combined results.

    Returns:
        Dict with keys: 'overview', 'news', 'financial', 'competitors', 'leadership',
        each containing Tavily search results.
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
        topic="finance",
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
        f"{len(all_sources)} total sources across 4 queries"
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

    for category in ["overview", "news", "financial", "competitors"]:
        data = search_results.get(category, {})
        answer = data.get("answer", "")
        results = data.get("results", [])

        section_title = category.upper()
        section_parts = [f"\n## {section_title}\n"]

        if answer:
            # Tavily's AI summary — very useful and concise
            truncated_answer = answer[:800]
            section_parts.append(f"Summary: {truncated_answer}\n")
            total_chars += len(truncated_answer)

        for r in results[:5]:  # Max 5 results per category
            if total_chars >= MAX_TOTAL_CHARS:
                break
            title = r.get("title", "Untitled")
            content = r.get("content", "")  # Use snippet, NOT raw_content
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


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((Exception, HTTPStatusError)),
    reraise=True
)
def extract_urls(urls: list[str]) -> dict:
    """Extract content directly from a list of URLs using the Tavily extract API."""
    client = _get_client()
    logger.info(f"Tavily extract: urls={urls} depth='advanced'")
    try:
        response = client.extract(urls=urls, extract_depth="advanced")
        
        # Clean each result's raw_content before returning
        if response.get("results"):
            for result in response["results"]:
                if result.get("raw_content"):
                    result["raw_content"] = clean_extracted_content(result["raw_content"])
                    
        return response
    except Exception as e:
        logger.error(f"Failed to extract URLs {urls}: {e}")
        return {"failed": True, "error": str(e)}

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((Exception, HTTPStatusError)),
    reraise=True
)
def crawl_url(url: str, extract_depth: str = "advanced") -> dict:
    """Crawl a URL using the Tavily crawl API."""
    client = _get_client()
    logger.info(f"Tavily crawl: url='{url}' depth='{extract_depth}'")
    try:
        response = client.crawl(url=url, extract_depth=extract_depth)
        
        # Clean each result's raw_content before returning
        if response.get("results"):
            for result in response["results"]:
                if result.get("raw_content"):
                    result["raw_content"] = clean_extracted_content(result["raw_content"])
                    
        return response
    except Exception as e:
        logger.error(f"Failed to crawl URL {url}: {e}")
        return {"failed": True, "error": str(e)}

