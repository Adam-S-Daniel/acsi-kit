"""Every script the quick start prints without `bash` is executable in git.

`bootstrap/steps.json` gives each step's command, and `status.sh` prints it
as its "Run:" line (and prints a few hints of its own). A command written as
`bootstrap/regenerate.sh ...`, with no `bash` in front, runs only if git
checked the file out executable: a clone of a 100644 script answers
"Permission denied" with exit 126 (regenerate.sh and apply-settings.sh did).
These tests read each run text's inline code spans with markdown-it-py, take
the ones that start with a `bootstrap/` script, add the `bootstrap/<name>.sh`
tokens status.sh prints without `bash` (a lexical token match), and check
each file's mode in `git ls-files -s`. Outside a git work tree there is no
index to read, and the test skips.

Run: python3 -m pytest export/tests/test_printed_scripts_executable.py -q
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parents[2]
SCRIPT = re.compile(r"bootstrap/[a-z][a-z-]*\.sh")


def code_spans(text: str) -> list[str]:
    tokens = MarkdownIt("commonmark").parseInline(text)
    return [c.content for t in tokens for c in (t.children or []) if c.type == "code_inline"]


def run_text_scripts(steps: dict) -> set[str]:
    """Scripts a step's run text starts a command with (no interpreter in front)."""
    out = set()
    for step in steps["steps"]:
        for span in code_spans(step["run"]):
            words = shlex.split(span, posix=True) if span.strip() else []
            if words and SCRIPT.fullmatch(words[0]):
                out.add(words[0])
    return out


def status_printed_scripts(text: str) -> set[str]:
    """bootstrap/<name>.sh tokens in status.sh not preceded by `bash `."""
    return {m.group(0) for m in SCRIPT.finditer(text) if not text[:m.start()].endswith("bash ")}


def index_modes(root: Path) -> dict[str, str] | None:
    proc = subprocess.run(["git", "-C", str(root), "ls-files", "-s", "--", "bootstrap"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    modes = {}
    for line in proc.stdout.splitlines():
        meta, path = line.split("\t", 1)
        modes[path] = meta.split()[0]
    return modes


def test_every_script_printed_without_bash_is_executable_in_git():
    modes = index_modes(KIT)
    if modes is None:
        pytest.skip("not a git work tree: no index to read")
    steps = json.loads((KIT / "bootstrap/steps.json").read_text(encoding="utf-8"))
    printed = run_text_scripts(steps) | status_printed_scripts(
        (KIT / "bootstrap/status.sh").read_text(encoding="utf-8"))
    # The two that once shipped 100644, and status.sh's own --mark hint: the
    # scan finds at least these, so it cannot pass by finding nothing.
    assert {"bootstrap/regenerate.sh", "bootstrap/apply-settings.sh", "bootstrap/status.sh"} <= printed
    wrong = {p: modes.get(p, "not tracked") for p in sorted(printed) if modes.get(p) != "100755"}
    assert wrong == {}, ("printed without `bash` but not executable in git; run "
                         "git update-index --chmod=+x on each: " + ", ".join(f"{p} ({m})" for p, m in wrong.items()))


def test_a_run_text_and_a_status_hint_are_read_as_commands():
    steps = {"steps": [{"run": "`bootstrap/a.sh --x`, then `bash bootstrap/b.sh` and `python3 bootstrap/c.py`; "
                               "read `bootstrap/d.sh` notes"}]}
    assert run_text_scripts(steps) == {"bootstrap/a.sh", "bootstrap/d.sh"}
    hint = 'log "Run: bootstrap/e.sh$(config_arg) --mark 1"; log "bash bootstrap/f.sh"'
    assert status_printed_scripts(hint) == {"bootstrap/e.sh"}
