from nonebot import get_plugin_config, on_command, on_message
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
或者直接发送消息（无需命令前缀）

提问内容可直接写，也可引用之前的消息。

只支持最基本的单轮文本对话；若需多轮对话、推荐问题、渲染格式等功能，请直接使用学校的Web服务：
https://agent.bit.edu.cn/product/llm/chat/d05ee4rha6ps7396rueg

另外，Agent.BIT 并不万能，有些问题询问通用大语言模型更好更快。实例可参考：
https://bithesis.bitnp.net/guide/ask-computer.html

使用示例：
/chat 可参考哪些文档？
直接发送：如何配置 VS Code？
""".strip(),
    config=Config,
)

config = get_plugin_config(Config).chat

# 命令处理器 - 优先级较高（5）
chat_cmd = on_command("chat", rule=to_me(), aliases={"聊天"}, priority=5, block=True)

# 消息处理器 - 优先级较低（10）
chat_msg = on_message(rule=to_me(), priority=10, block=True)

async def process_chat_content(event: MessageEvent, args: Message = None) -> str:
    """处理聊天内容，支持直接消息和引用消息"""
    message = []
    
    # 处理命令参数或直接消息
    if args:
        if m := args.extract_plain_text().strip():
            message.append(m)
    else:
        if m := event.get_plaintext().strip():
            message.append(m)
    
    # 处理引用消息
    if event.reply:
        quoted = event.reply.message.extract_plain_text().strip()
        message.append("\n".join(f"> {line}" for line in quoted.splitlines()))
    
    return "\n\n".join(message) if message else ""

@chat_cmd.handle()
async def handle_chat_command(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    content = await process_chat_content(event, args)
    if not content:
        await chat_cmd.finish("请输入要咨询的问题")
    
    reply = await handle(content)
    await chat_cmd.finish(reply)

@chat_msg.handle()
async def handle_default_chat(bot: Bot, event: MessageEvent):
    # 排除空消息
    if not event.get_plaintext().strip() and not event.reply:
        return
    
    # 检查是否是其他命令（以/开头但不是chat/聊天）
    message = event.get_plaintext().strip()
    if message.startswith("/") and not message.startswith(("/chat", "/聊天")):
        return
    
    content = await process_chat_content(event)
    if not content:
        return
    
    reply = await handle(content)
    await chat_msg.finish(reply)

# Console适配器支持（开发环境）
try:
    from nonebot.adapters.console import Bot as ConsoleBot, MessageEvent as ConsoleEvent

    @chat_cmd.handle()
    async def handle_chat_console(bot: ConsoleBot, event: ConsoleEvent, args: Message = CommandArg()):
        if m := args.extract_plain_text().strip():
            reply = await handle(m)
            await chat_cmd.finish(reply)

    @chat_msg.handle()
    async def handle_default_chat_console(bot: ConsoleBot, event: ConsoleEvent):
        message = event.get_plaintext().strip()
        if message and not message.startswith("/"):
            reply = await handle(message)
            await chat_msg.finish(reply)

except ImportError:
    pass