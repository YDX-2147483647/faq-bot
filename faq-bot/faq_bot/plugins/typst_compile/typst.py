import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Final

from nonebot import logger

PREAMBLE_USAGE: Final = """
页面设置取决于命令，每种都支持多页。
- /typtyp 和 /typdev 默认为横向 A8，可用以下代码恢复 typst 默认。
    #set page("a4")
- /typ 默认根据内容自动伸缩，可用以下代码恢复 typst 默认。
    #set page("a4", margin: auto)

默认会设置中文字体为 Noto Serif CJK SC。
- /typtyp 和 /typ 会设置所有场合的中文字体，包括正文、代码、公式。
- /typdev 只会设置正文、代码的中文字体，并不设置公式——开发版 typst 改进了公式字体机制，尚不稳定，暂且保留 typst 默认。
可用字体还有 Noto Sans CJK SC、Noto Serif CJK JP 等，详见`/typtyp fonts`。

默认会设置语言为 zh，但不会设置地区。
""".strip()

PREAMBLE_MINIMAL: Final = """
#set page(width: 74mm, height: 52mm)
#set text(lang: "zh", font: (
  (name: "Libertinus Serif", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
#show raw: set text(font: (
  (name: "DejaVu Sans Mono", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
"""
PREAMBLE_BASIC: Final = f"""
{PREAMBLE_MINIMAL}
#show math.equation: set text(font: (
  // 用 New Computer Modern 修复引号会导致大括号异常，故放弃
  // https://github.com/typst-doc-cn/guide/issues/87
  "New Computer Modern Math",
  "Noto Serif CJK SC",
))
""".strip()
# We do not use `#set page(paper: "a8", flipped: true)` here,
# because it will exchange the meaning of `width` and `height`.

PREAMBLE_FIT_PAGE: Final = f"""
{PREAMBLE_BASIC}
#set page(height: auto, width: auto, margin: 1em)
""".strip()


@dataclass
class Ok:
    pages: list[bytes]
    """A list of PNG pages"""
    stderr: str | None
    """Warnings, if exists"""


@dataclass
class Err:
    stderr: str


def typst_compile(
    document: str,
    /,
    *,
    executable: str | None = None,
    reply: str | None = None,
    preamble="",
) -> Ok | Err:
    """Run typst compile.

    Default executable is `"typst"`.

    Returns:
        Ok: If the compilation is successful, containing the PNG pages.
        Err: If the compilation fails, containing stderr.
    """
    # A temp dir is necessary to restrict read access appropriately.
    with TemporaryDirectory(prefix="typst-") as _cwd:
        cwd = Path(_cwd)
        logger.info(f"Compiling in {cwd}…")

        if reply is not None:
            re_typ = cwd / "re.typ"
            re_typ.write_text(reply, encoding="utf-8")
            logger.info(f"Written reply to {re_typ}.")

        # Compile

        result = run(
            [
                executable or "typst",
                "compile",
                "-",
                "{0p}.png",
                "--root=.",
            ],
            cwd=cwd,
            input="\n".join([preamble, document]),
            capture_output=True,
            text=True,
        )

        stderr = improve_diagnostics(
            result.stderr,
            # Number of lines in the `preamble`
            # Adding one because of `"\n".join`.
            line_number_shift=preamble.count("\n") + 1,
            cwd=cwd,
        )

        # Return the result

        if result.returncode == 0:
            # We can also collect pages from `--make-deps`, but parsing Makefile is fragile.
            pages = sorted(cwd.glob("*.png"))
            return Ok(
                pages=[p.read_bytes() for p in pages],
                stderr=stderr if stderr != "" else None,
            )
        else:
            return Err(stderr=stderr)


def improve_diagnostics(
    stderr: str, *, line_number_shift=0, cwd: Path | None = None
) -> str:
    """Improve diagnostic errors and warnings

    Assuming `stderr` is emitted by `typst compile … --diagnostic-format=human`.
    """

    # Remove sensitive/distractive info
    if cwd is not None:
        stderr = stderr.replace(cwd.as_posix(), "")

    def translate(line: str, *, pad: bool) -> str:
        n = str(int(line) - line_number_shift)
        if not pad:
            return n
        else:
            return " " * (len(line) - len(n)) + n

    def fix_line_number(*, pad: bool):
        def repl(match: re.Match) -> str:
            m = match.groupdict()
            return "".join(
                [
                    m["prefix"],
                    translate(m["line"], pad=pad),
                    m["suffix"],
                ]
            )

        return repl

    stderr = re.sub(
        r"^(?P<prefix>\s{2,}┌─ .*<stdin>:)(?P<line>\d+)(?P<suffix>:)",
        fix_line_number(pad=False),
        stderr,
        flags=re.MULTILINE,
    )
    stderr = re.sub(
        r"^(?P<prefix>\s*)(?P<line>\d+)(?P<suffix> │ )",
        fix_line_number(pad=True),
        stderr,
        flags=re.MULTILINE,
    )
    return stderr


def typst_fonts() -> str:
    """Lists all discovered fonts with their style variants."""
    fonts = run(["typst", "fonts", "--variants"], capture_output=True, text=True).stdout
    return fonts
