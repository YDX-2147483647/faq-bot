from .by.mdbook_index import search as search_by_mdbook_index
from .by.minisearch_index import search as search_by_minisearch_index
from .by.sitemap_html import search as search_by_sitemap_html
from .handle import add_handler, build_handler

__all__ = [
    "search_by_mdbook_index",
    "search_by_minisearch_index",
    "search_by_sitemap_html",
    "add_handler",
    "build_handler",
]
