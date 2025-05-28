"""搜索的抽象接口"""

from abc import ABC, abstractmethod

from nonebot import get_plugin_config

from .config import Config

config = get_plugin_config(Config).search_faq
BASE_URL = config.base_url


class AbstractEntry(ABC):
    url: str
    """URL without base, starting with `/`"""

    @abstractmethod
    def human(self) -> str:
        """返回人类可读的字符串"""
        ...


async def search(keywords: list[str]) -> list[AbstractEntry]:
    """搜索"""
    ...
