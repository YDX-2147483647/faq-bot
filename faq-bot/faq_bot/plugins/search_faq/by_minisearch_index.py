"""根据 MiniSearch 索引搜索各级标题"""

import json
import re
from collections.abc import Generator
from dataclasses import dataclass

import httpx
from nonebot import get_plugin_config

from .by import AbstractEntry, SearchFn, match
from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


@dataclass
class Entry(AbstractEntry):
    url: str
    """URL without base, starting with `/`"""
    title: str
    titles: list[str]
    """从高级标题到低级标题，不含`title`，可能为空"""

    def human(self) -> str:
        return " - ".join([self.title, *reversed(self.titles)])


async def search_impl(keywords: list[str]) -> list[Entry]:
    """搜索"""
    entries = await get_entries()
    return [e for e in entries if match(keywords, [e.title])]


search: SearchFn = search_impl


# `functools.cache` does not work properly with async functions.
ENTRIES_CACHE: list[Entry] | None = None


async def get_entries() -> list[Entry]:
    global ENTRIES_CACHE

    if ENTRIES_CACHE is None:
        index = await get_search_index()
        ENTRIES_CACHE = list(parse_search_index(index))

    return ENTRIES_CACHE


async def get_search_index() -> dict:
    """获取 MiniSearch 索引

    https://lucaong.github.io/minisearch/
    """
    assert not BASE_URL.endswith("/")
    base_url = httpx.URL(BASE_URL)
    root = base_url.path.removesuffix("/")

    async with httpx.AsyncClient() as client:
        index_html = (await client.get(BASE_URL, follow_redirects=True)).text
        m = re.search(rf'href="({root}/assets/chunks/theme\.\w+\.js)"', index_html)
        assert m is not None
        theme_url = base_url.copy_with(path=m.group(1))

        theme_js = (await client.get(theme_url)).text
        m = re.search(r'"(assets/chunks/VPLocalSearchBox\.[-\w]+\.js)"', theme_js)
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
            .removeprefix("const t='")
            .removesuffix("';export{t as default};")
            .removesuffix("`;export{t as default};")
            .replace(R"\`", "`")
        )
    return json.loads(search_index)


def parse_search_index(index: dict) -> Generator[Entry]:
    assert index["serializationVersion"] == 2
    assert (
        index["documentCount"]
        == len(index["documentIds"])
        == len(index["storedFields"])
    )
    root = httpx.URL(BASE_URL).path.removesuffix("/")

    for key, value in index["storedFields"].items():
        url = index["documentIds"][key].removeprefix(root)

        # 若是顶级标题，移除 URL 中的 hash
        if not value["titles"]:
            url = str(httpx.URL(url).copy_with(fragment=None))

        yield Entry(url=url, **value)
