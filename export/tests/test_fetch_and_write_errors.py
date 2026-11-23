"""A failed fetch and a symlinked output folder end in one clear error, not a traceback.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPORT_DIR))
import export  # noqa: E402
import fetch_sources  # noqa: E402


def test_a_failed_fetch_is_one_line_naming_the_source_and_exit_code(tmp_path, monkeypatch, capsys):
    def fake_git(*args):
        if "fetch" in args:
            raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(fetch_sources, "git", fake_git)
    monkeypatch.setattr(fetch_sources, "plan", lambda manifests, skip=(): {"some-repo": ["0" * 40]})
    rc = fetch_sources.main(["--owner", "example-org", "--dest", str(tmp_path / "src")])
    err = capsys.readouterr().err.strip().splitlines()
    assert rc == 1
    assert err == ["fetch_sources.py: some-repo: git fetch failed (exit 128)"]


def test_write_tree_refuses_a_symlinked_output_folder(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "keep.txt").write_text("mine\n")
    link = tmp_path / "out"
    os.symlink(real, link)
    with pytest.raises(export.ExportError, match="is a symlink"):
        export.write_tree({"a.txt": export.Entry(data=b"a\n")}, link)
    assert (real / "keep.txt").read_text() == "mine\n" and link.is_symlink()


def test_write_tree_refuses_a_dangling_symlink(tmp_path):
    link = tmp_path / "out"
    os.symlink(tmp_path / "missing", link)
    with pytest.raises(export.ExportError, match="is a symlink"):
        export.write_tree({"a.txt": export.Entry(data=b"a\n")}, link)
