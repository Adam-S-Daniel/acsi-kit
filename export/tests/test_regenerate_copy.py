"""regenerate `copy` and `copy_from_kit` give a NEW destination the source's exec bit.

A copied hook (`.githooks/agent-checks`) must stay executable even when the
destination is not already in the tree, and a new destination folder is made.
An existing destination keeps its own mode.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

EXPORT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPORT_DIR))
import export  # noqa: E402


def _exec(p: Path) -> bool:
    return bool(p.stat().st_mode & 0o111)


def test_copy_steps_keep_the_exec_bit_and_make_folders(tmp_path):
    other = tmp_path / "other"
    (other / "templates").mkdir(parents=True)
    (other / "templates" / "hook").write_bytes(b"#!/bin/sh\n")
    os.chmod(other / "templates" / "hook", 0o755)
    root = tmp_path / "root"
    root.mkdir()
    (root / "run.sh").write_bytes(b"#!/bin/sh\n")
    os.chmod(root / "run.sh", 0o755)
    steps = [
        {"copy_from_kit": {"repo": "other", "from": "templates/hook", "to": ".githooks/hook"}, "why": "t"},
        {"copy": {"from": "run.sh", "to": "bin/run.sh"}, "why": "t"},
    ]
    export._regenerate("x", steps, root, {"other": other}, {}, tmp_path)
    assert (root / ".githooks" / "hook").read_bytes() == b"#!/bin/sh\n"
    assert _exec(root / ".githooks" / "hook")
    assert _exec(root / "bin" / "run.sh")


def test_copy_onto_an_existing_file_keeps_its_mode(tmp_path):
    # The committed starters rely on this: a hook copied from a 644 template
    # stays 755 where the source tree already ships it executable.
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.sh").write_bytes(b"a\n")
    os.chmod(root / "a.sh", 0o644)
    (root / "b.sh").write_bytes(b"old\n")
    os.chmod(root / "b.sh", 0o755)
    export._regenerate("x", [{"copy": {"from": "a.sh", "to": "b.sh"}, "why": "t"}], root, {}, {}, tmp_path)
    assert (root / "b.sh").read_bytes() == b"a\n"
    assert _exec(root / "b.sh")
