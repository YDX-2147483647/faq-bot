"""根据 typst 官方文档搜索标题"""

import json
from dataclasses import dataclass
from datetime import timedelta

import httpx
from async_lru import alru_cache

from faq_bot.shared.search.by import AbstractEntry, SearchFn, match


@dataclass
class Entry(AbstractEntry):
    kind: str
    """`Chapter`, `Function`, `Parameter of terms`, etc."""
    title: str
    """`0.13.1`, `Term List`, `Hanging Indent`, etc."""
    url: str

    def human(self) -> str:
        return " - ".join([self.title, self.kind])


async def search_impl(base_url: str, keywords: list[str]) -> list[Entry]:
    """搜索"""
    entries = await get_entries(base_url)
    return [
        e
        for e in entries
        # 特殊类型匹配标题和类型名，其余只匹配标题
        if match(
            keywords,
            [e.title, e.url.removesuffix("/").split("/")[-1]]
            if e.kind in ["Function", "Type"]
            else [e.title],
        )
    ]


search: SearchFn = search_impl
"""根据 MiniSearch 索引搜索各级标题"""


@alru_cache(ttl=timedelta(days=10).total_seconds())
async def get_entries(base_url: str) -> list[Entry]:
    return await get_search(base_url)


async def get_search(base_url: str) -> list[Entry]:
    """获取 search.json"""
    url = base_url + "/assets/search.json?bust=20230915"
    async with httpx.AsyncClient() as client:
        search = (await client.get(url)).text
    items = json.loads(search)["items"]
    return [Entry(kind=i["kind"], title=i["title"], url=i["route"]) for i in items]
