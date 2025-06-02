from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .handle import handle

__plugin_meta__ = PluginMetadata(
    name="univ",
    description="预览 Typst Universe 上的包",
    usage="""
用法：
/univ ⟨package⟩
/universe ⟨package⟩
/typst-universe ⟨package⟩

1. 在 typst.app/universe 上查阅包最新版的 README
2. 找到首个包含`#import `的 typst 代码
3. 利用群里的 Nana 机器人编译

使用示例：
/univ cheq
/univ cetz
/univ pointless-size
""".strip(),
)

univ = on_command(
    "univ", aliases={"universe", "typst-universe"}, priority=5, block=True
)


@univ.handle()
async def _(args: Message = CommandArg()) -> None:
    reply = await handle(args.extract_plain_text())
    await univ.finish(reply)
