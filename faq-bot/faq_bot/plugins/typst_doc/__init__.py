from nonebot import on_command
from nonebot.plugin import PluginMetadata

from faq_bot.shared.search import (
    add_handler,
    build_handler,
    search_by_mdbook_index,
    search_by_minisearch_index,
)

from .by_official_docs import search as search_by_official_docs

__plugin_meta__ = PluginMetadata(
    name="tyd",
    description="搜索 Typst 中文社区导航、官方文档和 Examples Book",
    usage="""
用法：
/tyd ⟨关键词⟩…
/typdoc ⟨关键词⟩…
/typst-doc ⟨关键词⟩…

1. 先搜索 typst-doc-cn.github.io/guide 的各级标题和 URL。
2. 若无结果，再搜索 typst.app/docs 的标题和类型名。
3. 若无结果，继续搜索 sitandr.github.io/typst-examples-book/book 的各级标题。
目前不会搜索网页内容和标签。

关键词可直接写，也可引用之前的消息。
若提供多个关键词，则按照“或”理解。例如`/tyd A B`的结果是`/tyd A`与`/tyd B`之并。

只支持精确搜索；模糊搜索请直接使用网页上的搜索栏。

为避免刷屏，最多显示五条结果；结果的顺序随机。

使用示例：
/tyd Word
/tyd 圆角表格
/tyd 三线表 table
/tyd hanging
/tyd zip
/tyd catch
""".strip(),
)

tyd = on_command("tyd", aliases={"typdoc", "typst-doc"}, priority=5, block=True)

add_handler(
    tyd,
    build_handler(
        base_url=[
            "https://typst-doc-cn.github.io/guide",
            "https://typst.app",
            "https://sitandr.github.io/typst-examples-book/book",
        ],
        methods=[
            search_by_minisearch_index,
            search_by_official_docs,
            search_by_mdbook_index,
        ],
        if_no_result="未找到结果，建议手动搜索。\n详见`/help tyd`。",
    ),
)
