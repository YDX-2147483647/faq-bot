import re

from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent


async def not_cmd(event: Event) -> bool:
    """匹配规则：非命令

    `startswith(("!", "/"))`的反面，其中`startswith`源自`nonebot.rule`。
    """
    text = event.get_plaintext()
    return re.match("^[/!]", text) is None


async def to_me_seriously_if_qq_group(event: Event) -> bool:
    """匹配规则：不仅与机器人有关，而且要么@了，要么是私聊

    与`to_me`相比，不会匹配“群聊中只回复未@”的情形，且仅限制 OneBot QQ。
    """
    if not isinstance(event, GroupMessageEvent):
        return True

    return any(
        m.type == "at" and m.data.get("qq", event.self_id) == event.self_id
        for m in event.original_message
    )
