from typing import TYPE_CHECKING

from nonebot import get_plugin_config

from .by_minisearch_index import search as by_minisearch_index
from .by_sitemap_html import search as by_sitemap_html
from .config import Config

if TYPE_CHECKING:
    from .by import AbstractEntry

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


async def handle(message: str) -> str:
    """回复消息"""
    keywords = message.split()

    # Search until first match
    relevant: list[AbstractEntry] | None = None
    for search in [by_sitemap_html, by_minisearch_index]:
        relevant = await search(keywords)
        if relevant:
            break

    if relevant:
        max_len = 5
        reply = "\n\n".join(
            f"{e.human()}\n{BASE_URL}{e.url}" for e in relevant[:max_len]
        )
        if len(relevant) > max_len:
            reply += "\n\n……"
        return reply
    else:
        return f"未找到结果，建议手动搜索。\n{BASE_URL}/guide/ask-computer.html"
