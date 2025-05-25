import re

from nonebot.adapters import Event


async def not_cmd(event: Event) -> bool:
    """匹配“非命令”的规则

    `startswith(("!", "/"))`的反面，其中`startswith`源自`nonebot.rule`。
    """
    text = event.get_plaintext()
    return re.match("^[/!]", text) is None
