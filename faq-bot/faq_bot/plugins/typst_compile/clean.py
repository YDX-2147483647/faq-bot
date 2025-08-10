import re

from nonebot.adapters.onebot.v11 import (
    Message,
)


def _remove_regex_patterns(string: str, patterns: list[str | re.Pattern]) -> str:
    """Remove patterns (as regular expressions) in order."""
    for p in patterns:
        string = re.sub(p, "", string, count=1)
    return string


def _extract_plain_text(reply: Message) -> str:
    """Extract plain text from a `event.reply.message`.

    The canonical API does not parse at (@) segments correctly. (should be `MessageSegment(type="at")`, but actually `MessageSegment(type="text")`)
    As a result, `message.extract_plain_text()` contains redundant `@…` that will be parsed as `ref` in typst.
    This function mitigates the issue.
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


def clean_reply(reply: Message) -> str:
    """Clean reply into a string."""
    return _remove_regex_patterns(
        _extract_plain_text(reply),
        [
            # This plugin
            r"^/typtyp\s+",
            r"^/typ\s+",
            r"^/typdev\s+",
            # Nana
            r"^typ\s+",
        ],
    )
