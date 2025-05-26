from nonebot import get_plugin_config, on_command, on_message
from nonebot.adapters import Event, Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from .config import Config
from .handle import handle
from .util import not_cmd, to_me_seriously_if_qq_group

__plugin_meta__ = PluginMetadata(
    name="聊天",
    description="与 Agent.BIT 聊天",
    usage="""
与北京理工大学智能体广场（agent.bit.edu.cn）的“LaTeX-BIThesis帮助”机器人聊天。

用法：
/chat ⟨提问内容⟩
/聊天 ⟨提问内容⟩
⟨提问内容⟩

提问内容可直接写，也可引用之前的消息。
“/…”前缀可省略，即允许直接发送提问内容。

只支持最基本的单轮文本对话；若需多轮对话、推荐问题、渲染格式等功能，请直接使用学校的Web服务：
https://agent.bit.edu.cn/product/llm/chat/d05ee4rha6ps7396rueg

另外，Agent.BIT 并不万能，有些问题询问通用大语言模型更好更快。实例可参考：
https://bithesis.bitnp.net/guide/ask-computer.html

使用示例：
/chat 可参考哪些文档？
/chat 如何配置 VS Code？
""".strip(),
    config=Config,
)

config = get_plugin_config(Config).chat

chat_cmd = on_command("chat", rule=to_me(), aliases={"聊天"}, priority=5, block=True)

chat_all = on_message(
    # 为了避让`block=False`的命令，需要`not_cmd`
    # 为了允许向他人引用机器人的发言而不让机器人回复，需要 seriously
    rule=to_me() & not_cmd & to_me_seriously_if_qq_group,
    # 由于匹配范围太广，必须低优先级
    priority=100,
    block=True,
)


async def handle_chat_general(message: str, /, *, quoted: str | None = None) -> str:
    """处理消息

    Args:
        message: 直接收到的消息
        quoted: 引用的消息，可无

    不同类型的事件用不同方法获取消息内容，故需分别实现。
    """

    blocks = []

    if m := message.strip():
        blocks.append(m)

    # 如果引用了消息，一并附上
    if quoted and (m := quoted.strip()):
        blocks.append("\n".join(f"> {line}" for line in m.splitlines()))

    return await handle("\n\n".join(blocks))


@chat_cmd.handle()
async def handle_chat_cmd(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    reply = await handle_chat_general(
        args.extract_plain_text(),
        quoted=event.reply.message.extract_plain_text() if event.reply else None,
    )
    await chat_cmd.finish(reply)


@chat_all.handle()
async def handle_chat_all(bot: Bot, event: MessageEvent):
    reply = await handle_chat_general(
        event.get_plaintext(),
        quoted=event.reply.message.extract_plain_text() if event.reply else None,
    )
    await chat_all.finish(reply)


try:
    # Dev dependencies
    from nonebot.adapters.console import Bot as ConsoleBot

    # Console 不支持引用消息，简化处理

    @chat_cmd.handle()
    async def handle_chat_cmd_console(bot: ConsoleBot, args: Message = CommandArg()):
        reply = await handle_chat_general(args.extract_plain_text())
        await chat_cmd.finish(reply)

    @chat_all.handle()
    async def handle_chat_all_console(bot: ConsoleBot, event: Event):
        reply = await handle_chat_general(event.get_plaintext())
        await chat_all.finish(reply)

except ImportError:
    pass
