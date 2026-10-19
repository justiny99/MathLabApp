from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.config import settings

from crawl4ai import AsyncWebCrawler as crawler, CrawlerRunConfig
from crawl4ai.processors.pdf import PDFContentScrapingStrategy


async def crawl_url(url: str) -> str:
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=3, 
                include_external=False
        ),
        url_matcher="*.pdf",
        scraping_strategy=PDFContentScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

        print(f"Crawled {len(result)} pages in total")

        for result in results[:10]:  # Show first 10 results
            print(f"URL: {result.url}")
            print(f"Depth: {result.metadata.get('depth', 0)}")
    
    markdown = getattr(result, "markdown", None) or ""
    if hasattr(markdown, "raw_markdown"):
        markdown = markdown.raw_markdown

    text = str(markdown).strip()
    if not text:
        raise RuntimeError(f"crawl4ai returned empty markdown for {url}")
    return text


def crawl_to_raw(textbook_id: str, url: str) -> Path:
    markdown = asyncio.run(crawl_url(url))
    raw_dir = settings.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{textbook_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
