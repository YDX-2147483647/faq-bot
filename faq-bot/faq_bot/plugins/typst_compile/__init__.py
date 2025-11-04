from collections import deque
from typing import Literal

from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupRecallNoticeEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .clean import clean_reply
from .history import pop_history, push_history
from .preprocess import expand_magic
from .typst import (
    PREAMBLE_BASIC,
    PREAMBLE_FIT_PAGE,
    PREAMBLE_USAGE,
    Ok,
    typst_compile,
    typst_fonts,
)

__plugin_meta__ = PluginMetadata(
    name="typtyp",
    description="编译 typst 文档",
    usage=f"""
编译 typst 文档。

用法：
/typtyp ⟨文档⟩
/typ ⟨文档⟩
/typm ⟨数学公式⟩
/typdev ⟨文档⟩
/typtyp fonts

/typtyp 和 /typ 使用发布版 typst，而 /typdev 使用开发版 typst。如有需要，可联系 Y.D.X. 更新。
“/typm ⟨数学公式⟩”相当于“/typ $ ⟨数学公式⟩ $”。

{PREAMBLE_USAGE}

如果引用了先前发言，会存入`re.typ`，可以 import、include 或 read。只考虑直接引用，不考虑引用的引用。引用中开头的“/typtyp ”“typ ”等类似内容会被删除。
此外，若引用了先前发言但⟨文档⟩留空，则会将先前发言作为⟨文档⟩。⟨数学公式⟩也类似。

⟨文档⟩和先前发言中，一行开头的`!!⟨package⟩`会被展开为`#import "@preview/⟨package⟩:⟨version⟩": *;`，其中⟨version⟩是当前最新版本。

若在群中使用时误发代码，可撤回原消息，机器人会跟着撤回，除非消息太久远了。
""".strip(),
)
typtyp = on_command("typtyp", priority=5, block=True)
typ = on_command("typ", priority=5, block=True)
typm = on_command("typm", priority=5, block=True)
typdev = on_command("typdev", priority=5, block=True)
recall = on_notice(priority=5, block=False)


@typtyp.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    await handle(typtyp, event, args, profile="basic")


@typ.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    await handle(typ, event, args, profile="fit-page")


@typm.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    await handle(typm, event, args, profile="math")


@typdev.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    await handle(typdev, event, args, profile="dev")


async def handle(
    cmd: type[Matcher],
    event: MessageEvent,
    args: Message = CommandArg(),
    *,
    profile: Literal["basic", "fit-page", "math", "dev"] = "basic",
):
    message = args.extract_plain_text()
    reply = clean_reply(event.reply.message) if event.reply else None

    async def finish(message: str | Message) -> None:
        """Execute `typtyp.finish(message)` and save history."""
        sent = await cmd.send(message)
        push_history(event.message_id, sent["message_id"])
        await cmd.finish()

    # Response to simple commands
    match (message.strip(), reply):
        case ("fonts", _):
            await finish(typst_fonts(list_variants=False))
            return
        case ("fonts --variants" | "fonts variants", _):
            await finish(typst_fonts(list_variants=True))
            return
        case ("", None):
            await finish(__plugin_meta__.usage)
            return
        case _:
            pass

    # Select preamble
    match profile:
        case "basic" | "dev":
            preamble = PREAMBLE_BASIC
        case "fit-page" | "math":
            preamble = PREAMBLE_FIT_PAGE

    hints: deque[str] = deque()
    documents: list[str] = []

    # Select executable
    match profile:
        case "dev":
            # TODO: Remove hard-coded name and version
            executable = "typst-dev"
            hints.append("typst version: v0.14.0-rc.2 (2025-10-17).")
        case _:
            executable = None

    # Parse documents
    for part in (message, reply):
        if part is not None and part.strip():
            doc, hint = await expand_magic(part)
            hints.extend(hint)

            if profile == "math":
                doc = doc.strip()
                # Wrap with `$ … $` if it is not already `$ … $` or `$…$`
                if not (doc.startswith("$") and doc.endswith("$")):
                    doc = f"$ {doc} $"
            documents.append(doc)

    assert len(documents) in (1, 2)

    # Compile
    result = typst_compile(
        documents[0],
        reply=documents[1] if len(documents) > 1 else None,
        preamble=preamble,
        executable=executable,
    )

    # Reply with the compiled image
    reply_to_sender = MessageSegment.reply(event.message_id)
    if isinstance(result, Ok):
        message = reply_to_sender + Message(map(MessageSegment.image, result.pages))
        if result.stderr is not None:
            message.append(result.stderr)
    else:
        message = reply_to_sender + result.stderr

    # Attach hints
    if hints:
        message.append("\n".join(hints))

    await finish(message)


@recall.handle()
async def _(bot: Bot, event: GroupRecallNoticeEvent):
    sent = pop_history(event.message_id)
    if sent is not None:
        await bot.delete_msg(message_id=sent)
