"""根据 /sitemap.html 搜索一级标题和 URL"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import timedelta

import httpx
from async_lru import alru_cache

from . import AbstractEntry, SearchFn, match


@dataclass
class Entry(AbstractEntry):
    url: str
    title: str

    def human(self) -> str:
        return self.title


async def search_impl(base_url: str, keywords: list[str]) -> list[Entry]:
    """搜索"""
    sitemap = await get_sitemap(base_url)
    return [
        Entry(url=url, title=title)
        for url, title in sitemap
        if match(keywords, [url, title])
    ]


search: SearchFn = search_impl
"""根据 /sitemap.html 搜索一级标题和 URL"""


@alru_cache(ttl=timedelta(days=3).total_seconds())
async def get_sitemap(base_url: str) -> list[tuple[str, str]]:
    """获取网站地图

    返回格式为 (URL, 标题)[]。注意为方便搜索，URL 以`/`开头，不带`BASE_URL`。
    """
    async with httpx.AsyncClient() as client:
        sitemap_html = (await client.get(f"{base_url}/sitemap.html")).text
    return list(parse_sitemap_html(sitemap_html))


def parse_sitemap_html(html: str) -> Generator[tuple[str, str], None, None]:
    """解析 sitemap.html"""
    items = html.strip().splitlines()[1:-1]  # Drop <ul>
    for i in items:
        href, title = (
            i.removeprefix('<li><a href="')
            .removesuffix("</a></li>")
            .split('">', maxsplit=1)
        )
        yield href, title
