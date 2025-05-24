"""调用 HiAgent

网信中心老师提供的API文档
https://github.com/Decent898/live2d-project-for-HCI/blob/dbfd27e3198600f84d50cb32aef68142e6f334fa/api_test/llm_api/v1.5.0-chat_api_doc-v4.pdf

参考实现
https://github.com/Decent898/live2d-project-for-HCI/blob/dbfd27e3198600f84d50cb32aef68142e6f334fa/api_test/llm_api/api_test2.py
"""

import json

import httpx
from nonebot import get_plugin_config, logger

from .config import Config

config = get_plugin_config(Config).chat


async def handle(message: str) -> str:
    """回复消息"""

    async with httpx.AsyncClient(
        base_url=config.api_base,
        headers={"ApiKey": config.app_token},
    ) as client:
        # 创建对话
        r = await client.post(
            "/create_conversation",
            json={"UserID": config.user_id},
        )
        conversation = r.json()["Conversation"]["AppConversationID"]
        logger.debug(f"Created the conversation {conversation}")

        # 提问
        r = await client.post(
            "/chat_query_v2",
            json={
                "UserID": config.user_id,
                "Query": message,
                "AppConversationID": conversation,
                "ResponseMode": "streaming",  # 此处若选 blocking，则缺少 TracingJsonStr，而回答来源需要它，故选 streaming
            },
            timeout=60,  # 1 min
        )
        logger.debug(f"Received the chat streaming of conversation {conversation}")

        # 整理 streaming 的消息太复杂，所以我们只提取 message_id，准备重新获取消息
        message_id: str | None = None
        for line in r.text.splitlines():
            if line.startswith("data:"):
                if data := line.removeprefix("data:").strip():
                    data = json.loads(data)
                    if data["event"] == "message":
                        message_id = data["id"]
                        break
        assert message_id is not None
        logger.debug(
            f"Extracted the message id: {message_id} for conversation {conversation}"
        )

        # 重新获取消息
        r = await client.post(
            "/get_message_info",
            json={
                "UserID": config.user_id,
                "MessageID": message_id,
            },
        )
        response = r.json()
        logger.debug(f"Parsed the message {message_id} of conversation {conversation}")

    answer: str = response["MessageInfo"]["AnswerInfo"]["Answer"]

    # 提取回答来源
    tracing: list[dict] = json.loads(
        response["MessageInfo"]["AnswerInfo"]["TracingJsonStr"]
    )
    # docs[n] = (名称, URL或ID)；由于有知识库、问答库等多种类型，这里仅简单处理
    docs: list[tuple[str, str]] = [
        (
            doc["metadata"]["document_name"] or doc["metadata"]["dataset_name"],
            doc["metadata"]["document_url"] or doc["metadata"]["document_id"],
        )
        for doc in tracing[-1]["docs"]["outputList"]
        # `tracing[-1]`即`tracing[1]`，是 knowledge_retrieve_end 事件
    ]

    return "\n\n".join(
        [
            answer,
            "═" * 6,
            "回答来源",
            *(f"{name}\n{url}" for name, url in docs),
        ]
    )
