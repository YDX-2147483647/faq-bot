# from ast import TypeAlias
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Callable

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from faq_bot.shared.search.by import SearchFn

if TYPE_CHECKING:
    from faq_bot.shared.search.by import AbstractEntry

Handler = Callable[[str], Awaitable[str]]
"""回复消息"""


def check_base_url(v: str) -> None:
    assert v.startswith("https://")
    assert not v.endswith("/")


def build_handler(
    *, base_url: str, methods: list[SearchFn], if_no_result: str, max_n_results: int = 5
) -> Handler:
    """构造回复消息的方法

    Args:
        base_url: Base URL of the VitePress site, without a trailing slash
        methods: 一系列搜索方法；从前向后依次调用，直至首个有结果的
        if_no_result: 搜索完全无结果时的回复
        max_n_results: 回复中搜索结果的最大数量

    注意，回复中无论包含多少搜索结果，这些结果都必然仅是`methods`中某一种方法的结果，不可能是多种方法结果的混合。
    """
    check_base_url(base_url)

    async def handle(message: str) -> str:
        keywords = message.split()

        # Search until first match
        relevant: list[AbstractEntry] | None = None
        for search in methods:
            relevant = await search(base_url, keywords)
            if relevant:
                break

        if relevant:
            reply = "\n\n".join(
                f"{e.human()}\n{base_url}{e.url}" for e in relevant[:max_n_results]
            )
            if len(relevant) > max_n_results:
                reply += "\n\n……"
            return reply
        else:
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
