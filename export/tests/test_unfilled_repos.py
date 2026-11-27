"""patches/_agent-guidance/unfilled_repos.py: the sync's marker is create-repos.sh's.

The sync skips a repo whose README.md still carries the marker line
create-repos.sh writes (bootstrap/lib/common.sh). If the two drifted apart, the
sync would deliver into unfilled repos again and nothing else would notice.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

EXPORT_DIR = Path(__file__).resolve().parents[1]
KIT = EXPORT_DIR.parent
_spec = importlib.util.spec_from_file_location(
    "kit_patch_unfilled_repos", EXPORT_DIR / "patches" / "_agent-guidance" / "unfilled_repos.py")
unfilled_repos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unfilled_repos)


def common_marker() -> str:
    text = (KIT / "bootstrap" / "lib" / "common.sh").read_text(encoding="utf-8")
    found = re.findall(r"^GENERATED_README_MARKER='([^']*)'$", text, re.M)
    assert len(found) == 1, found
    return found[0]


def test_the_patch_marker_is_create_repos_marker():
    assert unfilled_repos.MARKER == common_marker()


def test_the_committed_sync_skips_on_that_marker():
    sync = (KIT / "starter" / "agent-guidance" / "scripts" / "sync.sh").read_text(encoding="utf-8")
    assert f"KIT_UNFILLED_MARKER='{common_marker()}'\n" in sync
    assert 'grep -qxF -- "$KIT_UNFILLED_MARKER" README.md' in sync
