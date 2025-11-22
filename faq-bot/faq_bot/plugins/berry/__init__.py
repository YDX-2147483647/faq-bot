import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="berry",
    description="树莓娘",
    usage="""
用法：
/berry ⟨文字⟩
/berry show-template
""".strip(),
)

berry = on_command("berry", priority=5, block=True)

TEMPLATE_TYP = Path(__file__).parent / "main.typ"
assert TEMPLATE_TYP.exists() and TEMPLATE_TYP.is_file()


@berry.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    # Determine command
    received = args.extract_plain_text()
    match received.strip():
        case "show-template":
            await berry.finish(TEMPLATE_TYP.read_text(encoding="utf-8"))
            return

    # Compile
    headline = received or "哈！"

    result = compile(headline)
    if isinstance(result, Ok):
        message = Message(MessageSegment.image(result.png))
    else:
        message = Message(result.stderr)

    await berry.finish(message)


@dataclass
class Ok:
    png: bytes


@dataclass
class Err:
    stderr: str


def compile(body: str) -> Ok | Err:
    """Compiles the Typst template with the given body and returns the result as a PNG.

    Args:
        body (str): The body to be injected into the Typst template.

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
            "--ppi=20",
            "--input",
            f"body={body}",
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
