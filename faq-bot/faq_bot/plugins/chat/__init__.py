from nonebot import get_plugin_config, on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from .config import Config
from .handle import handle

__plugin_meta__ = PluginMetadata(
    name="聊天",
    description="与 Agent.BIT 聊天",
    usage="""
与北京理工大学智能体广场（agent.bit.edu.cn）的“LaTeX-BIThesis帮助”机器人聊天。

用法：
/chat ⟨提问内容⟩
/聊天 ⟨提问内容⟩

提问内容可直接写，也可引用之前的消息。

只支持最基本的单轮文本对话；若需多轮对话、推荐问题、回答来源等功能，请直接使用学校的Web服务：
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

chat = on_command("chat", rule=to_me(), aliases={"聊天"}, priority=5, block=True)


@chat.handle()
async def handle_chat(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    message = []

    if m := args.extract_plain_text().strip():
        message.append(m)

    # 如果引用了消息，一并附上
    if event.reply:
        quoted = event.reply.message.extract_plain_text().strip()
        message.append("\n".join(f"> {line}" for line in quoted.splitlines()))

    reply = await handle("\n\n".join(message))

    await chat.finish(reply)


try:
    # Dev dependencies
    from nonebot.adapters.console import Bot as ConsoleBot

    @chat.handle()
    async def handle_chat_console(bot: ConsoleBot, args: Message = CommandArg()):
        # Console 不支持引用消息，简化处理

        message = []

        if m := args.extract_plain_text().strip():
            message.append(m)

        reply = await handle("\n\n".join(message))

        await chat.finish(reply)

except ImportError:
    pass
