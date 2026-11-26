"""Step 3 stores the denylist from the file the machine's own checks read.

The pre-push `privacy` check and the write-marker hook read
`~/.config/privacy-denylist.txt` when `PRIVACY_DENYLIST_FILE` is unset, and
the session miner defaults to it too. A step 3 example that keeps the list
anywhere else leaves those checks without it. These tests read the default
from the shipped checker's AST (`DEFAULT_FILE` in the agent-checks template's
privacy-denylist.py), then hold to it the `--denylist` argument of the
`set-secrets.sh` command in docs/skills.md's code blocks (parsed with
markdown-it-py) and in step 3's run text (an inline code span).

Run: python3 -m pytest export/tests/test_denylist_path.py -q
"""

from __future__ import annotations

import ast
import json
import shlex
from pathlib import Path

from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parents[2]
CHECKER = KIT / "starter/agent-guidance/templates/agent-checks/privacy-denylist.py"


def default_path() -> str:
    """`~/` plus the path parts DEFAULT_FILE joins (Path("a") / "b" / ...)."""
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ["DEFAULT_FILE"]:
            parts, expr = [], node.value
            while isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
                parts.insert(0, expr.right.value)
                expr = expr.left
            assert isinstance(expr, ast.Call) and expr.func.id == "Path", "DEFAULT_FILE is not Path(...) / ..."
            parts.insert(0, expr.args[0].value)
            return "~/" + "/".join(parts)
    raise AssertionError(f"no DEFAULT_FILE in {CHECKER.relative_to(KIT)}")


def denylist_args(commands: list[str]) -> list[str]:
    out = []
    for cmd in commands:
        words = shlex.split(cmd)
        if any(w.endswith("set-secrets.sh") for w in words) and "--denylist" in words:
            out.append(words[words.index("--denylist") + 1])
    return out


def test_the_checker_default_is_the_config_path():
    assert default_path() == "~/.config/privacy-denylist.txt"


def test_the_step_3_example_on_the_page_uses_it():
    tokens = MarkdownIt("commonmark").parse((KIT / "docs/skills.md").read_text(encoding="utf-8"))
    lines = [ln for t in tokens if t.type == "fence" for ln in t.content.splitlines()]
    found = denylist_args(lines)
    assert found, "docs/skills.md has no set-secrets.sh --denylist example"
    assert set(found) == {default_path()}


def test_step_3_run_text_uses_it():
    steps = json.loads((KIT / "bootstrap/steps.json").read_text(encoding="utf-8"))["steps"]
    step = next(s for s in steps if s["id"] == "3")
    inline = MarkdownIt("commonmark").parseInline(step["run"])
    spans = [c.content for t in inline for c in (t.children or []) if c.type == "code_inline"]
    assert denylist_args(spans) == [default_path()]
