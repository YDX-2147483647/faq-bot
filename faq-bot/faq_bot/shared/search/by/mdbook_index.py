"""根据 mdBook 网站的索引搜索各级标题

https://rust-lang.github.io/mdBook
"""

import json
from collections.abc import Generator
from dataclasses import dataclass
from datetime import timedelta

import httpx
from async_lru import alru_cache

from . import AbstractEntry, SearchFn, match


@dataclass
class Entry(AbstractEntry):
    url: str
    """URL without base, starting with `/`"""
    title: str
    """`Fake italic & Text shadows`, etc."""
    breadcrumbs: str
    """`Typst Snippets » Text » Fake italic & Text shadows » Fake italic & Text shadows`, etc."""

    def human(self) -> str:
        return " - ".join([self.title, self.breadcrumbs])


async def search_impl(base_url: str, keywords: list[str]) -> list[Entry]:
    """搜索"""
    entries = await get_entries(base_url)
    # 只匹配标题
    return [e for e in entries if match(keywords, [e.title])]


search: SearchFn = search_impl
"""根据 mdBook 网站的索引搜索各级标题"""


@alru_cache(ttl=timedelta(days=3).total_seconds())
async def get_entries(base_url: str) -> list[Entry]:
    index = await get_search_index(base_url)
    return list(parse_search_index(index))


async def get_search_index(base_url: str) -> dict:
    """获取索引"""
    assert not base_url.endswith("/")

    async with httpx.AsyncClient() as client:
        search_index = (await client.get(f"{base_url}/searchindex.json")).text

    return json.loads(search_index)


def parse_search_index(index: dict) -> Generator[Entry]:
    assert (
        index["index"]["documentStore"]["length"]
        == len(index["doc_urls"])
        == len(index["index"]["documentStore"]["docs"])
    )

    for id_, doc in index["index"]["documentStore"]["docs"].items():
        yield Entry(
            url=index["doc_urls"][int(id_)],
            breadcrumbs=doc["breadcrumbs"],
            title=doc["title"],
        )
