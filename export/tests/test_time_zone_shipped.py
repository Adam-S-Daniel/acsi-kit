"""The kit ships no one's time zone as the adopter's setting.

The merge window's zone is the adopter's own (`TIME_ZONE` in fleet.env;
DECISIONS, "The adopter's own time zone"). No tracked file under `starter/` or
`bootstrap/` may name `America/New_York`, the kit owner's zone, unless it is
on the allowlist below. Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
ZONE = "America/New_York"

# Each pattern is a fnmatch glob over the kit-relative path ("*" crosses "/").
ALLOWED = [
    # Documentation and decision records: they cite the owner's own schedule or
    # use the zone as the worked example of an IANA name.
    "starter/*/docs/*",
    # Tests: fixtures that pin US Eastern date arithmetic or a valid zone name.
    "starter/*/test/*",
    # Error messages and a comment that give "America/New_York" as the example
    # of what a valid IANA zone looks like. They set nothing.
    "starter/agent-guidance/scripts/base-md-merge-window.js",
    "starter/skills-evals/scripts/guidance_merge_window.py",
    "starter/skills-evals/harness/budget.py",
    "starter/skills-evals/evals/budget.yml",
]


def allowed(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, g) for g in ALLOWED)


def tracked_hits() -> list[str]:
    ls = subprocess.run(["git", "-C", str(KIT), "ls-files", "-z", "--", "starter", "bootstrap"],
                        capture_output=True)
    if ls.returncode != 0:
        pytest.skip("not a git work tree")
    hits = []
    for rel in ls.stdout.decode().split("\0"):
        p = KIT / rel
        if rel and p.is_file() and not p.is_symlink() and ZONE.encode() in p.read_bytes():
            hits.append(rel)
    return hits


def test_no_shipped_file_names_the_owners_zone_outside_the_allowlist():
    bad = [h for h in tracked_hits() if not allowed(h)]
    assert not bad, f"{ZONE} shipped outside the allowlist (use TIME_ZONE; see this file): {bad}"


def test_the_shipped_window_file_carries_the_neutral_zone():
    text = (KIT / "starter/agent-guidance/scripts/base-md-merge-window.yml").read_text(encoding="utf-8")
    assert text.count("\ntimezone: UTC\n") == 1


def test_every_allowlist_entry_still_matches_a_file():
    # A stale entry would hide a future leak under the same pattern.
    files = tracked_hits()
    stale = [g for g in ALLOWED if not any(fnmatch.fnmatchcase(f, g) for f in files)]
    assert not stale, f"allowlist entries that match no file naming the zone: {stale}"


def test_the_explorer_display_config_is_neutral():
    # Re-pin round 24 (export/patches/skills-evals/display_config.py): the zone
    # copy-starter.sh replaces, and only the kit's own repos, data repo first.
    import json
    import yaml
    d = json.loads((KIT / "starter/skills-evals/explorer/display.json").read_text(encoding="utf-8"))
    assert d["time_zone"] == "UTC"
    common = yaml.safe_load((KIT / "export/manifests/_common.yml").read_text(encoding="utf-8"))
    owner = common["kit_owners"][0]
    assert d["issue_repos"][0] == f"{owner}/skills-evals"
    assert all(r.split("/", 1)[0] == owner and r.split("/", 1)[1] in common["kit_repos"] for r in d["issue_repos"]), d
