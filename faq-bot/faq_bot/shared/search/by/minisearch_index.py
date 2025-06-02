"""根据 MiniSearch 索引搜索各级标题"""

import json
import re
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
    titles: list[str]
    """从高级标题到低级标题，不含`title`，可能为空"""

    def human(self) -> str:
        return " - ".join([self.title, *reversed(self.titles)])


async def search_impl(base_url: str, keywords: list[str]) -> list[Entry]:
    """搜索"""
    entries = await get_entries(base_url)
    return [
        e
        for e in entries
        # 顶级标题匹配标题和 URL，其余只匹配标题
        if match(keywords, [e.title] if e.titles else [e.title, e.url])
    ]


search: SearchFn = search_impl
"""根据 MiniSearch 索引搜索各级标题"""


@alru_cache(ttl=timedelta(days=3).total_seconds())
async def get_entries(base_url: str) -> list[Entry]:
    index = await get_search_index(base_url)
    return list(parse_search_index(base_url, index))


async def get_search_index(base_url: str) -> dict:
    """获取 MiniSearch 索引

    https://lucaong.github.io/minisearch/
    """
    assert not base_url.endswith("/")
    parsed = httpx.URL(base_url)
    root = parsed.path.removesuffix("/")

    async with httpx.AsyncClient() as client:
        index_html = (await client.get(base_url, follow_redirects=True)).text
        m = re.search(rf'href="({root}/assets/chunks/theme\.\w+\.js)"', index_html)
        assert m is not None
        theme_url = parsed.copy_with(path=m.group(1))

        theme_js = (await client.get(theme_url)).text
        m = re.search(r'"(assets/chunks/VPLocalSearchBox\.[-\w]+\.js)"', theme_js)
        assert m is not None
        search_box_url = f"{base_url}/{m.group(1)}"

        search_box_js = (await client.get(search_box_url)).text
        m = re.search(r'import\("\.(/@localSearchIndexroot\.\w+\.js)"\)', search_box_js)
        assert m is not None
        search_index_url = f"{base_url}/assets/chunks{m.group(1)}"

        search_index_js = (await client.get(search_index_url)).text
        search_index = (
            search_index_js.strip()
            .removeprefix("const t=`")
            .removeprefix("const t='")
            .removesuffix("';export{t as default};")
            .removesuffix("`;export{t as default};")
            .replace(R"\`", "`")
        )
    return json.loads(search_index)


def parse_search_index(base_url: str, index: dict) -> Generator[Entry]:
    assert index["serializationVersion"] == 2
    assert (
        index["documentCount"]
        == len(index["documentIds"])
        == len(index["storedFields"])
    )
    root = httpx.URL(base_url).path.removesuffix("/")

    for key, value in index["storedFields"].items():
        url = index["documentIds"][key].removeprefix(root)

        # 若是顶级标题，移除 URL 中的 hash
        if not value["titles"]:
            url = str(httpx.URL(url).copy_with(fragment=None))

        yield Entry(url=url, **value)
