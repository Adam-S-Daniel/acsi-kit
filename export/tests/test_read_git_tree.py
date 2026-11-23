"""read_git_tree returns the committed blobs exactly, whatever .gitattributes says.

`git archive` honors export-ignore (drops the file), export-subst (rewrites
`$Format:...$`) and eol/text conversion, so a source repo's attributes would
silently drop or change files in the starter tree.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

EXPORT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPORT_DIR))
import export  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
               GIT_AUTHOR_DATE="2000-01-01T00:00:00Z", GIT_COMMITTER_DATE="2000-01-01T00:00:00Z",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env=env).stdout.strip()


def test_attributes_do_not_drop_or_rewrite_files(tmp_path):
    repo = tmp_path / "src"
    repo.mkdir()
    _git(repo, "init", "-q")
    files = {
        ".gitattributes": b"ignored.txt export-ignore\nsubst.txt export-subst\n*.crlf text eol=crlf\n",
        "ignored.txt": b"kept\n",
        "subst.txt": b"version $Format:%H$\n",
        "dir name/a.crlf": b"one\ntwo\n",
        "run.sh": b"#!/bin/sh\n",
    }
    for rel, data in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_bytes(data)
    os.chmod(repo / "run.sh", 0o755)
    os.symlink("dir name/a.crlf", repo / "link")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    sha = _git(repo, "rev-parse", "HEAD")

    tree = export.read_git_tree(repo, sha)

    assert sorted(tree) == sorted([*files, "link"])
    for rel, data in files.items():
        assert tree[rel].data == data, rel
    assert tree["run.sh"].executable and not tree["subst.txt"].executable
    assert tree["link"].link == "dir name/a.crlf"
