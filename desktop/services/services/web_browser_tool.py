"""
Web Browser Tool — Gives the LLM agent access to web search for datasheets and docs.
Uses DuckDuckGo Instant Answer API (free, no key required).
"""

import aiohttp
from typing import Optional


DDGS_URL = "https://api.duckduckgo.com/"


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo and return relevant results."""
    try:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                DDGS_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []

                    # Abstract (main answer)
                    if data.get("Abstract"):
                        results.append({
                            "title": data.get("Heading", ""),
                            "snippet": data.get("Abstract", ""),
                            "url": data.get("AbstractURL", ""),
                            "source": data.get("AbstractSource", ""),
                        })

                    # Related topics
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append({
                                "title": topic.get("Text", "")[:80],
                                "snippet": topic.get("Text", ""),
                                "url": topic.get("FirstURL", ""),
                                "source": "DuckDuckGo",
                            })

                    return results[:max_results]
                return []
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return []


async def fetch_datasheet_info(component: str) -> str:
    """Search for component datasheet information."""
    results = await web_search(f"{component} datasheet pinout specifications")
    if not results:
        return f"No datasheet information found for {component}"

    info = f"## {component} — Datasheet Summary\n\n"
    for r in results[:3]:
        info += f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}\n\n"

    return info


async def search_library_docs(library_name: str, platform: str = "ESP32") -> str:
    """Search for library documentation and usage examples."""
    results = await web_search(f"{library_name} {platform} Arduino library documentation examples")
    if not results:
        return f"No documentation found for {library_name}"

    info = f"## {library_name} — Library Documentation\n\n"
    for r in results[:3]:
        info += f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}\n\n"

    return info
