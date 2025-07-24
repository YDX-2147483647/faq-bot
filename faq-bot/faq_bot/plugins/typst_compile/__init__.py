import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Final

from nonebot import logger, on_command, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupRecallNoticeEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="typtyp",
    description="编译 typst 文档",
    usage="""
编译 typst 文档。

用法：
/typtyp ⟨文档⟩
/typtyp fonts

默认设置页面为横向 A8，可用以下代码恢复 typst 默认。支持多页。
  #set page(paper: "a4", flipped: false)

默认不设置字体，会随机回落。可用字体有 Noto Sans CJK SC、Noto Serif CJK SC 等，详见`/typtyp fonts`。

如果引用了先前发言，会存入`re.typ`，可以 import 或 include。只考虑直接引用，不考虑引用的引用。引用中开头的“/typtyp ”或“typ ”会被删除。

若在群中使用时误发代码，可撤回原消息，机器人会跟着撤回，除非消息太久远了。
""".strip(),
)

typtyp = on_command("typtyp", priority=5, block=True)
recall = on_notice(priority=5, block=False)

_history: OrderedDict[int, int] = OrderedDict()
"""An ordered map from human_message_id to bot_reply_id.

Later replies come at last. Recalled messages will be removed.

Only works for single-threading.
"""
_MAX_HISTORY: Final = 10


@typtyp.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = args.extract_plain_text()
    reply = (
        remove_regex_patterns(
            clean_reply(event.reply.message),
            [
                r"^/typtyp\s+",  # This plugin
                r"^typ\s+",  # Nana
            ],
        )
        if event.reply
        else None
    )

    match (message.strip(), reply):
        case ("fonts", _):
            await typtyp.finish(typst_fonts())
            return
        case ("", None):
            await typtyp.finish(__plugin_meta__.usage)
            return
        case ("", _):
            assert reply is not None  # Fix Pylance
            result = compile(reply)
        case (_, _):
            result = compile(message, reply=reply)

    # Reply with the compiled image
    reply_to_sender = MessageSegment.reply(event.message_id)
    if isinstance(result, Ok):
        message = result.pages + reply_to_sender
    else:
        message = result.stderr + reply_to_sender

    sent = await typtyp.send(message)

    # Update history
    while len(_history) >= _MAX_HISTORY:
        _history.popitem(last=False)
    _history[event.message_id] = sent["message_id"]
    _history.move_to_end(event.message_id, last=True)

    await typtyp.finish()


@recall.handle()
async def _(bot: Bot, event: GroupRecallNoticeEvent):
    sent = _history.pop(event.message_id, default=None)
    if sent is not None:
        await bot.delete_msg(message_id=sent)


def remove_regex_patterns(string: str, patterns: list[str | re.Pattern]) -> str:
    """Remove patterns (as regular expressions) in order."""
    for p in patterns:
        string = re.sub(p, "", string, count=1)
    return string


def clean_reply(reply: Message) -> str:
    """Clean a `event.reply.message` into plain text.

    The API does not parse at (@) segments correctly. (should be `MessageSegment(type="at")`, but actually `MessageSegment(type="text")`)
    As a result, `message.extract_plain_text()` contains redundant `@…` that will be parsed as `ref` in typst.
    """
    texts: list[str] = []
    for seg in reply:
        if seg.is_text():
            if len(texts) > 0:
                # Parse it as usual
                texts.append(seg.data["text"])
            else:
                # Parse it more conservatively
                t: str = seg.data["text"]
                if t.strip() and (not t.startswith("@") or "\n" in t):
                    texts.append(t)

    return "".join(texts)


@dataclass
class Ok:
    pages: Message


@dataclass
class Err:
    stderr: str


def compile(
    document: str,
    /,
    *,
    reply: str | None = None,
    preamble='#set page(paper: "a8", flipped: true)',
) -> Ok | Err:
    """Run typst compile.

    Returns:
        Ok: If the compilation is successful, containing the PNG pages.
        Err: If the compilation fails, containing stderr.
    """
    # A temp dir is necessary to restrict read access appropriately.
    with TemporaryDirectory(prefix="typst-") as _dir:
        dir = Path(_dir)
        logger.info(f"Compiling in {dir}…")

        if reply is not None:
            re_typ = dir / "re.typ"
            re_typ.write_text(reply, encoding="utf-8")
            logger.info(f"Written reply to {re_typ}.")

        result = run(
            [
                "typst",
                "compile",
                "-",
                "{0p}.png",
                "--root=.",
            ],
            cwd=dir,
            input="\n".join([preamble, document]),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # We can also collect pages from `--make-deps`, but parsing Makefile is fragile.
            pages = sorted(dir.glob("*.png"))
            return Ok(
                pages=Message(MessageSegment.image(p.read_bytes()) for p in pages)
            )
        else:
            return Err(stderr=result.stderr.replace(dir.as_posix(), ""))


def typst_fonts() -> str:
    """Lists all discovered fonts with their style variants."""
    fonts = run(["typst", "fonts", "--variants"], capture_output=True, text=True).stdout
    return fonts
