"""搜索的抽象接口和相关通用工具"""

from abc import abstractmethod
from collections.abc import Awaitable
from typing import Callable, Protocol, TypeAlias, TypeVar

from nonebot import get_plugin_config

from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


class AbstractEntry(Protocol):
    url: str
    """URL without base, starting with `/`"""

    @abstractmethod
    def human(self) -> str:
        """返回人类可读的字符串"""
        ...


T = TypeVar("T", bound=AbstractEntry, covariant=True)
SearchFn: TypeAlias = Callable[[list[str]], Awaitable[list[T]]]
"""搜索

keywords ↦ relevant entries
"""


def match(keywords: list[str], documents: list[str]) -> bool:
    """判断是否有某一`documents`包含某一`fragements`"""
    for key in keywords:
        for doc in documents:
            if key in doc:
                return True
    return False
