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
  #set page("a4")

默认会设置中文字体为 Noto Serif CJK SC，包括正文、公式、代码。可用字体还有 Noto Sans CJK SC、Noto Serif CJK JP 等，详见`/typtyp fonts`。

默认会设置语言为 zh，但不会设置地区。

如果引用了先前发言，会存入`re.typ`，可以 import 或 include。只考虑直接引用，不考虑引用的引用。引用中开头的“/typtyp ”或“typ ”会被删除。

若在群中使用时误发代码，可撤回原消息，机器人会跟着撤回，除非消息太久远了。
""".strip(),
)
PREAMBLE: Final = """
#set page(width: 74mm, height: 52mm)
#set text(lang: "zh", font: (
  (name: "Libertinus Serif", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
#show math.equation: set text(font: (
  (name: "New Computer Modern", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
  "New Computer Modern Math",
))
#show raw: set text(font: (
  (name: "DejaVu Sans Mono", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
""".strip()
# We do not use `#set page(paper: "a8", flipped: true)` here,
# because it will exchange the meaning of `width` and `height`.

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
        message = reply_to_sender + result.pages
        if result.stderr is not None:
            message.append(result.stderr)
    else:
        message = reply_to_sender + result.stderr

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
    stderr: str | None
    """Warnings, if exists"""


@dataclass
class Err:
    stderr: str


def compile(
    document: str,
    /,
    *,
    reply: str | None = None,
    preamble=PREAMBLE,
) -> Ok | Err:
    """Run typst compile.

    Returns:
        Ok: If the compilation is successful, containing the PNG pages.
        Err: If the compilation fails, containing stderr.
    """
    # A temp dir is necessary to restrict read access appropriately.
    with TemporaryDirectory(prefix="typst-") as _cwd:
        cwd = Path(_cwd)
        logger.info(f"Compiling in {cwd}…")

        if reply is not None:
            re_typ = cwd / "re.typ"
            re_typ.write_text(reply, encoding="utf-8")
            logger.info(f"Written reply to {re_typ}.")

        # Compile

        result = run(
            [
                "typst",
                "compile",
                "-",
                "{0p}.png",
                "--root=.",
            ],
            cwd=cwd,
            input="\n".join([preamble, document]),
            capture_output=True,
            text=True,
        )

        stderr = improve_diagnostics(
            result.stderr,
            # Number of lines in the `preamble`
            # Adding one because of `"\n".join`.
            line_number_shift=preamble.count("\n") + 1,
            cwd=cwd,
        )

        # Return the result

        if result.returncode == 0:
            # We can also collect pages from `--make-deps`, but parsing Makefile is fragile.
            pages = sorted(cwd.glob("*.png"))
            return Ok(
                pages=Message(MessageSegment.image(p.read_bytes()) for p in pages),
                stderr=stderr if stderr != "" else None,
            )
        else:
            return Err(stderr=stderr)


def improve_diagnostics(
    stderr: str, *, line_number_shift=0, cwd: Path | None = None
) -> str:
    """Improve diagnostic errors and warnings

    Assuming `stderr` is emitted by `typst compile … --diagnostic-format=human`.
    """

    # Remove sensitive/distractive info
    if cwd is not None:
        stderr = stderr.replace(cwd.as_posix(), "")

    def translate(line: str, *, pad: bool) -> str:
        n = str(int(line) - line_number_shift)
        if not pad:
            return n
        else:
            return " " * (len(line) - len(n)) + n

    def fix_line_number(*, pad: bool):
        def repl(match: re.Match) -> str:
            m = match.groupdict()
            return "".join(
                [
                    m["prefix"],
                    translate(m["line"], pad=pad),
                    m["suffix"],
                ]
            )

        return repl

    stderr = re.sub(
        r"^(?P<prefix>\s{2,}┌─ .*<stdin>:)(?P<line>\d+)(?P<suffix>:)",
        fix_line_number(pad=False),
        stderr,
        flags=re.MULTILINE,
    )
    stderr = re.sub(
        r"^(?P<prefix>\s*)(?P<line>\d+)(?P<suffix> │ )",
        fix_line_number(pad=True),
        stderr,
        flags=re.MULTILINE,
    )
    return stderr


def typst_fonts() -> str:
    """Lists all discovered fonts with their style variants."""
    fonts = run(["typst", "fonts", "--variants"], capture_output=True, text=True).stdout
    return fonts
