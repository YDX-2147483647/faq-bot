from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupRecallNoticeEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .clean import clean_reply
from .history import pop_history, push_history
from .typst import PREAMBLE_USAGE, Ok, typst_compile, typst_fonts

__plugin_meta__ = PluginMetadata(
    name="typtyp",
    description="编译 typst 文档",
    usage=f"""
编译 typst 文档。

用法：
/typtyp ⟨文档⟩
/typtyp fonts

{PREAMBLE_USAGE}

如果引用了先前发言，会存入`re.typ`，可以 import 或 include。只考虑直接引用，不考虑引用的引用。引用中开头的“/typtyp ”或“typ ”会被删除。

若在群中使用时误发代码，可撤回原消息，机器人会跟着撤回，除非消息太久远了。
""".strip(),
)
typtyp = on_command("typtyp", priority=5, block=True)
recall = on_notice(priority=5, block=False)


@typtyp.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = args.extract_plain_text()
    reply = clean_reply(event.reply.message) if event.reply else None

    async def finish(message: str | Message) -> None:
        """Execute `typtyp.finish(message)` and save history."""
        sent = await typtyp.send(message)
        push_history(event.message_id, sent["message_id"])
        await typtyp.finish()

    match (message.strip(), reply):
        case ("fonts", _):
            await finish(typst_fonts())
            return
        case ("", None):
            await finish(__plugin_meta__.usage)
            return
        case ("", _):
            assert reply is not None  # Fix Pylance
            result = typst_compile(reply)
        case (_, _):
            result = typst_compile(message, reply=reply)

    # Reply with the compiled image
    reply_to_sender = MessageSegment.reply(event.message_id)
    if isinstance(result, Ok):
        message = reply_to_sender + Message(map(MessageSegment.image, result.pages))
        if result.stderr is not None:
            message.append(result.stderr)
    else:
        message = reply_to_sender + result.stderr

    await finish(message)


@recall.handle()
async def _(bot: Bot, event: GroupRecallNoticeEvent):
    sent = pop_history(event.message_id)
    if sent is not None:
        await bot.delete_msg(message_id=sent)
