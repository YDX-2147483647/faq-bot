import json
import re

import httpx


async def handle(message: str) -> str:
    # TODO
    return message


async def get_search_index() -> dict:
    async with httpx.AsyncClient() as client:
        base_url = "https://bithesis.bitnp.net"
        index_html = (await client.get(base_url)).text
        m = re.search(r'href="(/assets/chunks/theme\.\w+\.js)"', index_html)
        assert m is not None
        theme_url = f"{base_url}{m.group(1)}"

        theme_js = (await client.get(theme_url)).text
        m = re.search(r'"(assets/chunks/VPLocalSearchBox\.\w+\.js)"', theme_js)
        assert m is not None
        search_box_url = f"{base_url}/{m.group(1)}"

        search_box_js = (await client.get(search_box_url)).text
        m = re.search(r'import\("\.(/@localSearchIndexroot\.\w+\.js)"\)', search_box_js)
        assert m is not None
        search_index_url = f"{base_url}/assets/chunks{m.group(1)}"

        search_index_js = (await client.get(search_index_url)).text
        search_index = (
            search_index_js.strip()
            .removeprefix("const t=`")
            .removesuffix("`;export{t as default};")
            .replace(R"\`", "`")
        )
    return json.loads(search_index)


if __name__ == "__main__":
    index = await get_search_index()
    from pathlib import Path

    Path("index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
