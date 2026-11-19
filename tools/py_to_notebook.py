#!/usr/bin/env python3
"""
Build a Jupyter notebook from a lesson script.

The lesson .py files are the source of truth. They're split into cells with
"# %%" (code) and "# %% [markdown]" (markdown) markers, the "percent"
format that VS Code, PyCharm and Jupytext understand.

Jupyter already runs an asyncio event loop, so asyncio.run(...) doesn't work
in a notebook. This script rewrites it to top-level await, e.g.
    books = asyncio.run(crawl())   ->   books = await crawl()

Usage:
    # write lessons/04_fast_async_crawling.ipynb
    python tools/py_to_notebook.py lessons/04_fast_async_crawling.py
    # rebuild every lesson and run it so the outputs are saved (needs jupyter)
    python tools/py_to_notebook.py lessons/0*.py --execute

Requires: pip install nbformat (and jupyter for --execute)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import nbformat

ASSIGN_OR_STATEMENT = re.compile(r"^(\s*(?:[\w, ]+=\s*)?)asyncio\.run\((.*)\)\s*$")


def _replace_inline_asyncio_run(line: str) -> str:
    """Replace asyncio.run(X) anywhere in a line with (await X)."""
    marker = "asyncio.run("
    while marker in line:
        start = line.index(marker)
        open_paren = start + len(marker) - 1
        end, depth = open_paren, 0
        while end < len(line):  # find the matching closing parenthesis
            depth += {"(": 1, ")": -1}.get(line[end], 0)
            if depth == 0:
                break
            end += 1
        inner = line[open_paren + 1 : end]
        line = f"{line[:start]}(await {inner}){line[end + 1 :]}"
    return line


def to_notebook_code(code: str) -> str:
    lines = []
    for line in code.splitlines():
        match = ASSIGN_OR_STATEMENT.match(line)
        if match:
            line = f"{match.group(1)}await {match.group(2)}"
        elif "asyncio.run(" in line:
            line = _replace_inline_asyncio_run(line)
        lines.append(line)
    return "\n".join(lines)


def convert(source: Path) -> Path:
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"\A#!.*\n", "", text)  # drop the shebang line

    cells = []
    for chunk in re.split(r"^# %%", text, flags=re.MULTILINE)[1:]:
        header, _, body = chunk.partition("\n")
        body = body.strip("\n")
        if not body:
            continue
        if header.strip() == "[markdown]":
            markdown = "\n".join(re.sub(r"^# ?", "", line) for line in body.splitlines())
            cells.append(nbformat.v4.new_markdown_cell(markdown))
        else:
            cells.append(nbformat.v4.new_code_cell(to_notebook_code(body)))

    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    target = source.with_suffix(".ipynb")
    nbformat.write(notebook, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--execute", action="store_true", help="run the notebook and save outputs")
    args = parser.parse_args()

    for source in args.sources:
        target = convert(source)
        print(f"wrote {target}")
        if args.execute:
            subprocess.run(
                [
                    sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
                    "--execute", "--inplace", "--ExecutePreprocessor.timeout=600", str(target),
                ],
                check=True,
            )  # fmt: skip
            print(f"executed {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
