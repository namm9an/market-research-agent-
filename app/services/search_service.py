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
        # Force exact match for entities in news to prevent fuzzy fallback.
        # If it's short (1-3 words) and not a question, wrap in quotes so engines treat it as a proper noun.
        is_question = any(q in query.lower() for q in ["what", "how", "who", "why", "when", "?", "latest news on"])
        words = query.strip().split()
        if not query.startswith('"') and len(words) <= 3 and not is_question:
            query = f'"{query}"'

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
    searxng_results = raw.get("results", [])[:effective_max * 2]  # fetch extra for filtering
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

    # Query 5: C-suite & Founders
    results["leadership_csuite"] = search(
        query=f"{company_name} CEO CTO CIO CFO founder co-founder managing director",
        topic="general",
    )

    # Query 6: VP & Head level leadership
    results["leadership_vp"] = search(
        query=f"{company_name} VP engineering VP sales VP product head of infrastructure head of AI head of data",
        topic="general",
    )

    # Query 7: LinkedIn leadership profiles (all levels)
    results["linkedin_leaders"] = search(
        query=f"{company_name} CEO CTO VP engineering head infrastructure site:linkedin.com",
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

    for category in ["overview", "news", "financial", "competitors", "leadership_csuite", "leadership_vp", "linkedin_leaders"]:
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
        content = clean_extracted_content(result.markdown or "")
        # Truncate to ~4000 chars (~1000 tokens) to fit within LLM context window
        if len(content) > 4000:
            content = content[:4000] + "\n\n[... content truncated for LLM processing ...]"
        return {
            "url": url,
            "raw_content": content,
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
    """Deep-crawl a URL using Crawl4AI: scrape the seed page, discover internal
    links, then scrape up to 5 linked pages for richer context.

    Returns: {results: [{url, raw_content}, ...]}
    """
    from urllib.parse import urlparse, urljoin

    logger.info(f"Crawl4AI deep-crawl: url='{url}'")
    parsed_seed = urlparse(url)
    seed_domain = parsed_seed.netloc

    try:
        # Step 1: Crawl the seed URL
        seed_data = _run_async(_crawl4ai_fetch(url))
        if not seed_data.get("success"):
            return {"failed": True, "error": "Crawl4AI failed to crawl the seed URL"}

        all_results = [{
            "url": seed_data["url"],
            "raw_content": seed_data["raw_content"],
        }]

        # Step 2: Discover internal links from the seed page's markdown
        link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
        discovered_links = []
        for _text, href in link_pattern.findall(seed_data["raw_content"]):
            link_parsed = urlparse(href)
            # Only follow internal links (same domain)
            if link_parsed.netloc == seed_domain and href != url:
                if href not in discovered_links:
                    discovered_links.append(href)

        # Step 3: Crawl up to 5 discovered internal pages
        max_sub_pages = min(5, len(discovered_links))
        logger.info(f"Deep-crawl: found {len(discovered_links)} internal links, crawling {max_sub_pages}")

        for sub_url in discovered_links[:max_sub_pages]:
            try:
                sub_data = _run_async(_crawl4ai_fetch(sub_url))
                if sub_data.get("success") and sub_data.get("raw_content"):
                    all_results.append({
                        "url": sub_data["url"],
                        "raw_content": sub_data["raw_content"],
                    })
            except Exception as e:
                logger.warning(f"Sub-page crawl failed for {sub_url}: {e}")
                continue

        # Step 4: Combine all page content, with a total cap of 6000 chars
        combined_content = ""
        for i, r in enumerate(all_results):
            page_header = f"\n\n--- PAGE {i+1}: {r['url']} ---\n\n"
            combined_content += page_header + r["raw_content"]

        if len(combined_content) > 6000:
            combined_content = combined_content[:6000] + "\n\n[... content truncated ...]"

        logger.info(f"Deep-crawl complete: {len(all_results)} pages, {len(combined_content)} chars")

        return {
            "results": [{
                "url": url,
                "raw_content": combined_content,
            }]
        }
    except Exception as e:
        logger.error(f"Failed to deep-crawl URL {url}: {e}")
        return {"failed": True, "error": str(e)}
