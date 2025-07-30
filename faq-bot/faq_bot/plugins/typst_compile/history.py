from collections import OrderedDict
from typing import Final

_history: OrderedDict[int, int] = OrderedDict()
"""An ordered map from human_message_id to bot_reply_id.

Later replies come at last. Recalled messages will be removed.

Only works for single-threading.
"""
_MAX_HISTORY: Final = 10


def push_history(human_message_id: int, bot_reply_id: int) -> None:
    """Push a record to history.

    And drop old records automatically.
    """

    # Update history
    while len(_history) >= _MAX_HISTORY:
        _history.popitem(last=False)
    _history[human_message_id] = bot_reply_id
    _history.move_to_end(human_message_id, last=True)


def pop_history(human_message_id: int) -> int | None:
    """Pop a record to history, and get bot_reply_id.

    It the record does not exist, return `None`.
    """
    return _history.pop(human_message_id, default=None)
