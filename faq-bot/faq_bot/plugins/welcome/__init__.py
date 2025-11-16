import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run

from nonebot import logger, on_command, on_notice
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupIncreaseNoticeEvent,
    MessageEvent,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="welcome",
    description="欢迎加入群聊",
    usage="""
TODO
""".strip(),
)

welcome = on_command("welcome", aliases={"欢迎"}, priority=5, block=True)

new_member = on_notice()

TEMPLATE_TYP = Path(__file__).parent / "welcome.typ"
assert TEMPLATE_TYP.exists() and TEMPLATE_TYP.is_file()


@new_member.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    if event.group_id not in [793548390, 589034686]:
        return

    headline = str(event.user_id)
    try:
        info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id
        )
        logger.info(info)
        headline = info.get("nickname") or info.get("card") or str(event.user_id)
    except Exception:
        pass

    result = compile(headline)
    if isinstance(result, Ok):
        await welcome.finish(MessageSegment.image(result.png))
    else:
        await welcome.finish(result.stderr)


@welcome.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = args.extract_plain_text()
    match message.strip():
        case "show-template":
            await welcome.finish(TEMPLATE_TYP.read_text(encoding="utf-8"))
            return

    headline = message
    if event.reply:
        sender = event.reply.sender
        headline += sender.nickname or sender.card or str(sender.user_id)

    result = compile(headline)
    if isinstance(result, Ok):
        await welcome.finish(MessageSegment.image(result.png))
    else:
        await welcome.finish(result.stderr)


@dataclass
class Ok:
    png: bytes


@dataclass
class Err:
    stderr: str


def compile(headline: str) -> Ok | Err:
    """Compiles the Typst template with the given headline and returns the result as a PNG.

    Args:
        headline (str): The headline to be injected into the Typst template.

    Returns:
        Ok: If the compilation is successful, containing the PNG output.
        Err: If the compilation fails, containing the processed error message.
    """
    result = run(
        [
            "typst",
            "compile",
            TEMPLATE_TYP,
            "-",
            "--format=png",
            "--input",
            f"headline={headline}",
        ],
        capture_output=True,
    )
    if result.returncode == 0:
        return Ok(png=result.stdout)
    else:
        return Err(
            stderr=re.sub(
                rf"(  ┌─ ).+({TEMPLATE_TYP.name}:)",
                r"\1\2",
                result.stderr.decode(),
            )
        )
