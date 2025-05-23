from nonebot import get_plugin_config, on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from .config import Config
from .handle import handle

__plugin_meta__ = PluginMetadata(
    name="search-faq",
    description="搜索FAQ",
    usage="/repeat ……（可以同时引用之前的消息）",
    config=Config,
)

config = get_plugin_config(Config)

repeat = on_command("repeat", rule=to_me(), aliases={"重复"}, priority=5, block=True)


@repeat.handle()
async def handle_repeat(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = []

    if m := args.extract_plain_text().strip():
        message.append(m)

    # 如果引用了消息，一并附上
    if event.reply:
        quoted = event.reply.message.extract_plain_text().strip()
        message.append([f"> {line}" for line in quoted.splitlines()])

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
