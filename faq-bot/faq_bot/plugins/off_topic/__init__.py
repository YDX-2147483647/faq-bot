import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run

from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="ot",
    description="提示已偏离 typst 主题",
    usage="""
提示已偏离 typst 主题，继续讨论应去隔壁群。

用法：
/ot ⟨名字⟩
/ot show-template
/off-topic ⟨名字⟩
/off-topic show-template

⟨名字⟩可直接写，可省略，也可引用别人。

若⟨名字⟩不含“#”，会作为字符串处理；若⟨名字⟩含“#”，会作为 typst markup 代码处理，但仅在容器 […] 内，不支持 #pagebreak() 等功能。
""".strip(),
)

off_topic = on_command("ot", aliases={"off-topic"}, priority=5, block=True)

TEMPLATE_TYP = Path(__file__).parent / "off-topic.typ"
assert TEMPLATE_TYP.exists() and TEMPLATE_TYP.is_file()


@off_topic.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = args.extract_plain_text()
    match message.strip():
        case "show-template":
            await off_topic.finish(TEMPLATE_TYP.read_text(encoding="utf-8"))
            return
        case "debug":
            await off_topic.finish(debug_info())
            return

    headline = message
    if event.reply:
        sender = event.reply.sender
        headline += sender.nickname or sender.card or str(sender.user_id)

    result = compile(headline)
    if isinstance(result, Ok):
        await off_topic.finish(MessageSegment.image(result.png))
    else:
        await off_topic.finish(result.stderr)


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
    if "#" not in headline:
        # Pass `headline` as `str`
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
    else:
        # Pass `headline` as typst markup codes.
        result = run(
            [
                "typst",
                "compile",
                "-",
                "-",
                "--format=png",
            ],
            capture_output=True,
            input=re.sub(
                r"^  let message = \[.+\]$",
                # Avoid `\1` from parsing as regex.
                lambda _: f"  let message = [\n{headline}\n]",
                TEMPLATE_TYP.read_text(encoding="utf-8"),
                count=1,
                flags=re.MULTILINE,
            ).encode(),
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


def debug_info() -> str:
    """Get debug info."""
    version = run(["typst", "--version"], capture_output=True, text=True).stdout
    fonts = run(["typst", "fonts", "--variants"], capture_output=True, text=True).stdout
    return f"""Version: {version}\n\nFonts:\n{fonts}"""
