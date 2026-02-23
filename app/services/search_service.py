"""Search service — wraps Tavily API for AI-native web search."""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from tavily import TavilyClient

from app.config import TAVILY_API_KEY, MAX_SEARCH_RESULTS, CACHE_DIR

logger = logging.getLogger(__name__)

# Initialize Tavily client
_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    """Lazy-init Tavily client."""
    global _client
    if _client is None:
        if not TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY not set in environment")
        _client = TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def _cache_key(query: str, topic: str) -> str:
    """Generate a cache key from query + topic."""
    raw = f"{query}|{topic}".lower().strip()
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
    max_results: int | None = None,
    time_range: str | None = None,
    use_cache: bool = True,
) -> dict:
    """Search the web using Tavily.

    Args:
        query: Search query string.
        topic: "general", "news", or "finance".
        max_results: Override default max results.
        time_range: "day", "week", "month", "year" or None.
        use_cache: Whether to check/save cache.

    Returns:
        Tavily search response dict with 'results', 'answer', etc.
    """
    # Check cache first
    key = _cache_key(query, topic)
    if use_cache:
        cached = _load_cache(key)
        if cached:
            return cached

    client = _get_client()

    kwargs = {
        "query": query,
        "search_depth": "advanced",
        "topic": topic,
        "max_results": max_results or MAX_SEARCH_RESULTS,
        "include_raw_content": "markdown",
        "include_answer": True,
        "include_images": False,
    }

    if time_range:
        kwargs["time_range"] = time_range

    logger.info(f"Tavily search: query='{query}', topic={topic}")
    response = client.search(**kwargs)

    # Save to cache
    if use_cache:
        _save_cache(key, response)

    logger.info(f"Tavily returned {len(response.get('results', []))} results")
    return response


def search_company(company_name: str) -> dict:
    """Run all 4 strategic queries for a company and return combined results.

    Returns:
        Dict with keys: 'overview', 'news', 'financial', 'competitors',
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


def extract_url(url: str) -> dict:
    """Extract content from a URL using Tavily's extract API.

    Args:
        url: The URL to crawl and extract content from.

    Returns:
        Dict with 'url', 'raw_content', and metadata.
    """
    client = _get_client()
    logger.info(f"Tavily extract: url='{url}'")

    try:
        response = client.extract(urls=[url])
        results = response.get("results", [])
        if results:
            result = results[0]
            return {
                "url": result.get("url", url),
                "raw_content": result.get("raw_content", ""),
                "failed": False,
            }
        return {"url": url, "raw_content": "", "failed": True, "error": "No content extracted"}
    except Exception as e:
        logger.error(f"Tavily extract failed for {url}: {e}")
        return {"url": url, "raw_content": "", "failed": True, "error": str(e)}

