from nonebot import get_plugin_config, on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from .config import Config
from .handle import handle

__plugin_meta__ = PluginMetadata(
    name="搜索",
    description="搜索 BIThesis 网站",
    usage="""
搜索 bithesis.bitnp.net 的标题和 URL。目前不会搜索网页内容和标签。

用法：
/search ⟨关键词⟩…
/搜索 ⟨关键词⟩…

关键词可直接写，也可引用之前的消息。

若提供多个关键词，则按照“或”理解。例如`/search A B`的结果是`/search A`与`/search B`之并。

只支持精确搜索；模糊搜索请直接使用网页上的搜索栏。

为避免刷屏，最多显示五条结果；结果的顺序随机。

使用示例：
/search download
/search 生僻字
/search font 字体
""".strip(),
    config=Config,
)

config = get_plugin_config(Config)

repeat = on_command("search", rule=to_me(), aliases={"搜索"}, priority=5, block=True)


@repeat.handle()
async def handle_repeat(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = []

    if m := args.extract_plain_text().strip():
        message.append(m)

    # 如果引用了消息，一并附上
    if event.reply:
        quoted = event.reply.message.extract_plain_text().strip()
        message.append("\n".join(f"> {line}" for line in quoted.splitlines()))

    reply = await handle("\n\n".join(message))

    await repeat.finish(reply)


try:
    # Dev dependencies
    from nonebot.adapters.console import Bot as ConsoleBot

    @repeat.handle()
    async def handle_repeat_console(bot: ConsoleBot, args: Message = CommandArg()):
        # Console 不支持引用消息，简化处理

        message = []

        if m := args.extract_plain_text().strip():
            message.append(m)

        reply = await handle("\n\n".join(message))

        await repeat.finish(reply)

except ImportError:
    pass
