# from ast import TypeAlias
from collections.abc import Awaitable
from itertools import repeat
from typing import Callable

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from faq_bot.shared.search.by import SearchFn

Handler = Callable[[str], Awaitable[str]]
"""回复消息"""


def check_base_url(v: str) -> None:
    assert v.startswith("https://")
    assert not v.endswith("/")


def build_handler(
    *,
    base_url: str | list[str],
    methods: list[SearchFn],
    if_no_result: str,
    max_n_results: int = 5,
) -> Handler:
    """构造回复消息的方法

    Args:
        base_url: Base URL (e.g. a VitePress site), without a trailing slash
        methods: 一系列搜索方法；从前向后依次调用，直至首个有结果的
        if_no_result: 搜索完全无结果时的回复
        max_n_results: 回复中搜索结果的最大数量

    若只提供单个`base_url`，则用于所有`methods`；若提供多个`base_url`，则与`methods`对应使用。

    注意，回复中无论包含多少搜索结果，这些结果都必然仅是`methods`中某一种方法的结果，不可能是多种方法结果的混合。
    """
    # Check and normalize `base_url` to `base_urls`
    if isinstance(base_url, list):
        for u in base_url:
            check_base_url(u)
        assert len(base_url) == len(methods)
        base_urls = base_url
    else:
        check_base_url(base_url)
        base_urls = repeat(base_url)

    async def handle(message: str) -> str:
        keywords = message.split()

        # Search until first match
        for base, search in zip(base_urls, methods):
            relevant = await search(base, keywords)
            if relevant:
                reply = "\n\n".join(
                    f"{e.human()}\n{base}{e.url}" for e in relevant[:max_n_results]
                )
                if len(relevant) > max_n_results:
                    reply += "\n\n……"
                return reply

        return if_no_result

    return handle


def add_handler(cmd: type[Matcher], handler: Handler) -> None:
    """向事件响应器添加回复消息的处理函数

    支持 OneBot 和 Console，OneBot 时还支持引用。
    """

    @cmd.handle()
    async def handle_cmd(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
        message = []

        if m := args.extract_plain_text().strip():
            message.append(m)

        # 如果引用了消息，一并附上
        if event.reply:
            quoted = event.reply.message.extract_plain_text().strip()
            message.append(quoted)

        reply = await handler("\n\n".join(message))

        await cmd.finish(reply)

    try:
        # Dev dependencies
        from nonebot.adapters.console import Bot as ConsoleBot

        @cmd.handle()
        async def handle_cmd_console(bot: ConsoleBot, args: Message = CommandArg()):
            # Console 不支持引用消息，简化处理

            message = []

            if m := args.extract_plain_text().strip():
                message.append(m)

            reply = await handler("\n\n".join(message))

            await cmd.finish(reply)

    except ImportError:
        pass
