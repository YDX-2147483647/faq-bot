"""根据 /sitemap.html 搜索一级标题和 URL"""

from collections.abc import Generator
from dataclasses import dataclass

import httpx
from nonebot import get_plugin_config

from .by import AbstractEntry
from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


@dataclass
class Entry(AbstractEntry):
    url: str
    title: str

    def human(self) -> str:
        return self.title


async def search(keywords: list[str]) -> list[Entry]:
    """搜索"""
    sitemap = await get_sitemap()
    return [
        Entry(url=url, title=title)
        for url, title in sitemap
        if match(keywords, [url, title])
    ]


def match(keywords: list[str], documents: list[str]) -> bool:
    """判断是否有某一`documents`包含某一`fragements`"""
    for key in keywords:
        for doc in documents:
            if key in doc:
                return True
    return False


# `functools.cache` does not work properly with async functions.
SITEMAP_CACHE: list[tuple[str, str]] | None = None


async def get_sitemap() -> list[tuple[str, str]]:
    """获取网站地图

    返回格式为 (URL, 标题)[]。注意为方便搜索，URL 以`/`开头，不带`BASE_URL`。
    """
    global SITEMAP_CACHE

    if SITEMAP_CACHE is None:
        async with httpx.AsyncClient() as client:
            sitemap_html = (await client.get(f"{BASE_URL}/sitemap.html")).text
        SITEMAP_CACHE = list(parse_sitemap_html(sitemap_html))

    return SITEMAP_CACHE


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
