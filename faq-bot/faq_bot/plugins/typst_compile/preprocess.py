import re
from collections import deque
from collections.abc import Iterable
from datetime import timedelta
from itertools import groupby
from operator import itemgetter
from typing import TypeVar

import httpx
from async_lru import alru_cache

T = TypeVar("T")


def last(iterable: Iterable[T]) -> T:
    """Return the last item of `iterable`, or `IndexError` if `iterable` is empty.
    https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.last
    """
    return deque(iterable, maxlen=1)[-1]


async def expand_magic(document: str) -> tuple[str, deque[str]]:
    """Expand magic strings in the document.

    - `!!⟨package⟩` ⇒ `#import "@preview/⟨package⟩:⟨latest⟩": *`

    Returns `(processed document, hints)`.
    """
    registry = await load_registry()

    hints: deque[str] = deque()

    def repl(m: re.Match[str]) -> str:
        name = m.groupdict()["package"]
        version = registry.get(name, None)
        if version is not None:
            hints.append(f"Using {name} {version}.")
            return f'#import "@preview/{name}:{version}": *;'
        else:
            it = m.group()
            hints.append(f"Ignoring “{it}” because {name} is not in package registry.")
            return it

    return re.sub(
        r"^\s*[!！]{2}\s*(?P<package>[-0-9a-z]+)(?=\s|$)",
        repl,
        document,
        count=0,
        flags=re.MULTILINE,
    ), hints


@alru_cache(ttl=timedelta(days=30).total_seconds())
async def load_registry() -> dict[str, str]:
    """Load the registry as a map from package name to the latest version"""
    async with httpx.AsyncClient() as client:
        raw_index = (
            await client.get("https://packages.typst.org/preview/index.json")
        ).json()

    # name ⇒ latest version
    return {
        name: last(records)[1]  # get the version of the last record
        for name, records in groupby(
            map(itemgetter("name", "version"), raw_index),
            key=itemgetter(0),  # group by name
        )
    }
