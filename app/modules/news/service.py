"""
News service — business logic layer.
"""

import asyncio

import httpx

from app.external_apis.rss.rss_client import fetch_feed
from app.external_apis.rss.rss_mapper import map_entry
from app.external_apis.rss.rss_sources import FEEDS
from app.modules.news.entities import NewsTag
from app.modules.news.repository import NewsRepository


class NewsService:
    """Business logic for news entities."""

    def __init__(self, repository: NewsRepository):
        self._repository = repository

    def get_news_topics(self) -> list[NewsTag]:
        """Get all available news topics."""
        return self._repository.get_all_news_tags()

    async def get_latest_news(self) -> list[dict]:
        """Obtiene las últimas noticias desde RSS feeds."""
        async with httpx.AsyncClient() as client:
            tasks = [fetch_feed(client, url) for url in FEEDS]
            feeds = await asyncio.gather(*tasks, return_exceptions=True)

        news: list[dict] = []
        for feed in feeds:
            if isinstance(feed, BaseException):
                continue

            feed_meta = getattr(feed, "feed", {})
            entries = getattr(feed, "entries", [])
            source = (
                feed_meta.get("title", "desconocida")
                if hasattr(feed_meta, "get")
                else "desconocida"
            )

            for entry in entries:
                news.append(map_entry(entry, source))

        news.sort(key=lambda item: item.get("published") or 0, reverse=True)
        unique = {item.get("link"): item for item in news if item.get("link")}
        return list(unique.values())[:50]
