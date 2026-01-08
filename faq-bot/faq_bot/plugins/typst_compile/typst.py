import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Final, Literal

from nonebot import logger

PREAMBLE_USAGE: Final = """
页面设置取决于命令，每种都支持多页。
- /typtyp 和 /typdev 默认为横向 A8，可用以下代码恢复 typst 默认。
    #set page("a4")
- /typ 默认根据内容自动伸缩，可用以下代码恢复 typst 默认。
    #set page("a4", margin: auto)

默认会设置中文字体为 Noto Serif CJK SC，包括正文、代码、公式。
可用字体还有 Noto Sans CJK SC、Noto Serif CJK JP 等，详见`/typtyp fonts`或`/typtyp fonts variants`。

默认会设置语言为 zh，但不会设置地区。
""".strip()

PREAMBLE_BASIC: Final = """
#set page(width: 74mm, height: 52mm)
#set text(lang: "zh", font: (
  (name: "Libertinus Serif", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
#show raw: set text(font: (
  (name: "DejaVu Sans Mono", covers: "latin-in-cjk"),
  "Noto Serif CJK SC",
))
#show math.equation: set text(font: (
  (name: "Noto Serif CJK SC", covers: regex("[–—‘’“”‥‧⸺]")),
  "New Computer Modern Math",
  "Noto Serif CJK SC",
))
""".strip()
# We do not use `#set page(paper: "a8", flipped: true)` here,
# because it will exchange the meaning of `width` and `height`.
# https://github.com/typst/typst/issues/7179

PREAMBLE_FIT_PAGE: Final = f"""
{PREAMBLE_BASIC}
#set page(height: auto, width: auto, margin: 1em)
""".strip()


@dataclass
class OkCompile:
    pages: list[bytes]
    """A list of PNG pages"""
    stderr: str | None
    """Warnings, if exists"""


@dataclass
class OkEval:
    stdout: str
    """YAML output"""
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
    command: Literal["compile", "eval"] = "compile",
) -> OkCompile | OkEval | Err:
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

        match command:
            case "compile":
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
            case "eval":
                assert not preamble, "preamble is not supported with eval"
                result = run(
                    [
                        executable or "typst",
                        "eval",
                        document,
                        "--format=yaml",
                        *([] if reply is None else ["--in", str(re_typ)]),
                    ],
                    cwd=cwd,
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
            match command:
                case "compile":
                    # We can also collect pages from `--make-deps`, but parsing Makefile is fragile.
                    pages = sorted(cwd.glob("*.png"))
                    return OkCompile(
                        pages=[p.read_bytes() for p in pages],
                        stderr=stderr if stderr != "" else None,
                    )
                case "eval":
                    return OkEval(
                        stdout=result.stdout,
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


def typst_fonts(*, list_variants=False) -> str:
    """Lists all discovered fonts with their style variants."""
    fonts = run(
        ["typst", "fonts", "--variants"] if list_variants else ["typst", "fonts"],
        capture_output=True,
        text=True,
    ).stdout
    return fonts
