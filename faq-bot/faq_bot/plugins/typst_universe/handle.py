"""预览 typst.app/universe 上的包"""

from datetime import timedelta

import httpx
from async_lru import alru_cache
from bs4 import BeautifulSoup


async def handle(message: str) -> str:
    """回复消息"""
    package = message.strip()
    url = as_url(package)
    example = await get_example(url)
    if example:
        return compile(url, example)
    else:
        return f"🙁 未在 {url} 找到 {package} 的示例代码。"


def as_url(package: str) -> str:
    return f"https://typst.app/universe/package/{package}"


@alru_cache(ttl=timedelta(days=30).total_seconds())
async def get_example(url: str) -> str | None:
    """Get the first example code of a package"""

    async with httpx.AsyncClient() as client:
        html = (await client.get(url)).text
    soup = BeautifulSoup(html, "html.parser")
    examples = soup.find_all("code", class_=["language-typ", "language-typst"])
    for example in examples:
        if "#import " in example.text:
            return str(example.text).replace("@local/", "@preview/")


def compile(url: str, typ: str) -> str:
    """利用群里的 Nana 机器人编译"""
    return f"typ // {url}\n{typ.strip()}"
