import json
import re
from collections.abc import Generator

import httpx
from nonebot import get_plugin_config

from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


async def handle(message: str) -> str:
    """回复消息"""
    sitemap = await get_sitemap()
    keywords = message.split()
    relevant = [(url, title) for url, title in sitemap if match(keywords, [url, title])]

    if relevant:
        max_len = 5
        reply = "\n\n".join(
            f"{title}\n{BASE_URL}{url}" for url, title in relevant[:max_len]
        )
        if len(relevant) > max_len:
            reply += "\n\n……"
        return reply
    else:
        return f"未找到结果，建议手动搜索。\n{BASE_URL}/guide/ask-computer.html"


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


async def get_search_index() -> dict:
    """获取 MiniSearch 索引

    https://lucaong.github.io/minisearch/

    目前未使用。
    """
    async with httpx.AsyncClient() as client:
        index_html = (await client.get(BASE_URL)).text
        m = re.search(r'href="(/assets/chunks/theme\.\w+\.js)"', index_html)
        assert m is not None
        theme_url = f"{BASE_URL}{m.group(1)}"

        theme_js = (await client.get(theme_url)).text
        m = re.search(r'"(assets/chunks/VPLocalSearchBox\.\w+\.js)"', theme_js)
        assert m is not None
        search_box_url = f"{BASE_URL}/{m.group(1)}"

        search_box_js = (await client.get(search_box_url)).text
        m = re.search(r'import\("\.(/@localSearchIndexroot\.\w+\.js)"\)', search_box_js)
        assert m is not None
        search_index_url = f"{BASE_URL}/assets/chunks{m.group(1)}"

        search_index_js = (await client.get(search_index_url)).text
        search_index = (
            search_index_js.strip()
            .removeprefix("const t=`")
            .removesuffix("`;export{t as default};")
            .replace(R"\`", "`")
        )
    return json.loads(search_index)
