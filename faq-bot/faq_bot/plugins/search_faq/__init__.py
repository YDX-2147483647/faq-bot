from nonebot import on_command
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from faq_bot.shared.search import (
    add_handler,
    build_handler,
    search_by_minisearch_index,
    search_by_sitemap_html,
)

__plugin_meta__ = PluginMetadata(
    name="搜索",
    description="搜索 BIThesis 网站",
    usage="""
搜索 bithesis.bitnp.net 的各级标题和 URL。目前不会搜索网页内容和标签。

用法：
/search ⟨关键词⟩…
/搜索 ⟨关键词⟩…

关键词可直接写，也可引用之前的消息。
若提供多个关键词，则按照“或”理解。例如`/search A B`的结果是`/search A`与`/search B`之并。

只支持精确搜索；模糊搜索请直接使用网页上的搜索栏。
优先搜索一级标题和 URL；若无结果，才会搜索全部级别的标题。

为避免刷屏，最多显示五条结果；结果的顺序随机。

使用示例：
/search download
/search 生僻字
/search font 字体
""".strip(),
)

search = on_command("search", rule=to_me(), aliases={"搜索"}, priority=5, block=True)

add_handler(
    search,
    build_handler(
        base_url="https://bithesis.bitnp.net",
        methods=[search_by_sitemap_html, search_by_minisearch_index],
        if_no_result="未找到结果，建议手动搜索。\nhttps://bithesis.bitnp.net/guide/ask-computer.html",
    ),
)
