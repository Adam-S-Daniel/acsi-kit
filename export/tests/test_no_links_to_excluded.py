"""No exported Markdown file links to a file its manifest left out.

A manifest's `exclude` drops a source file from `starter/`, but text that
links to it ships unchanged, so the adopter gets a dead link and a promise
nothing in their copy keeps. The 2026-11-09 re-sync shipped the drift
report's guidance overlap section with a README link to the excluded
`docs/routines/fleet-health-audit.md`, the routine meant to judge each
entry, and no test noticed. This test resolves every relative Markdown link
in each repo's `starter/<kit_name>/` tree and fails when it lands on an
excluded file (directory excludes are not checked: they cover fixture trees
that design notes cite by design). Fix a hit with an `edits` entry that
rewrites or drops the link, never by un-excluding the file blindly.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
MANIFESTS = KIT / "export" / "manifests"
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)")


def excluded_files() -> list[tuple[str, set[str]]]:
    out = []
    for f in sorted(MANIFESTS.glob("*.yml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        kit_name = doc.get("kit_name")
        paths = {
            e["path"] for e in doc.get("exclude") or []
            if isinstance(e, dict) and not str(e["path"]).endswith("/")
        }
        if kit_name and paths:
            out.append((kit_name, paths))
    return out


def dead_links(root: Path, excluded: set[str]) -> list[str]:
    hits = []
    for md in sorted(root.rglob("*.md")):
        rel_dir = PurePosixPath(md.relative_to(root).parent.as_posix())
        for n, line in enumerate(md.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in LINK.finditer(line):
                target = m.group(1)
                if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("/"):
                    continue
                parts: list[str] = []
                for p in (rel_dir / target).parts:
                    if p == "..":
                        if parts:
                            parts.pop()
                    elif p not in (".", ""):
                        parts.append(p)
                if "/".join(parts) in excluded:
                    hits.append(f"{md.relative_to(root)}:{n} links {target}")
    return hits


@pytest.mark.parametrize("kit_name,excluded", excluded_files(), ids=lambda v: v if isinstance(v, str) else "")
def test_no_starter_link_lands_on_an_excluded_file(kit_name, excluded):
    root = KIT / "starter" / kit_name
    if not root.is_dir():
        pytest.skip(f"starter/{kit_name} not exported")
    assert dead_links(root, excluded) == []


def test_the_check_sees_a_link_to_an_excluded_file(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("See [it](../routines/gone.md#x) and [ok](kept.md).\n")
    assert dead_links(tmp_path, {"routines/gone.md"}) == ["docs/a.md:1 links ../routines/gone.md"]
