import json
import re

import httpx
from nonebot import get_plugin_config

from .by_sitemap_html import search
from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


async def handle(message: str) -> str:
    """回复消息"""
    keywords = message.split()
    relevant = await search(keywords)

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
