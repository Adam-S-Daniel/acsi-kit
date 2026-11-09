"""The kit's hand-written docs quote the eval budget the starter ships.

docs/before-you-start.md and docs/evals-and-loop.md are not generated, but
they quote numbers from starter/skills-evals/evals/budget.yml, which the
daily re-sync moves with the source. They went stale once (30% and 0.035
quoted while 25% and 0.0105 shipped, acsi-kit#28); this fails the re-sync
pull request that changes the budget until the docs follow it.

The quotes are found as lexical tokens in prose (no code shape is read).

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parent.parent.parent
BUDGET = yaml.safe_load((KIT / "starter/skills-evals/evals/budget.yml").read_text(encoding="utf-8"))
DOCS = {name: (KIT / "docs" / name).read_text(encoding="utf-8")
        for name in ("before-you-start.md", "evals-and-loop.md")}
TEXT = "\n".join(DOCS.values())


def pct(fraction: float) -> str:
    return f"{fraction * 100:g}"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# (what, pattern with one group, the value it must quote, how many at least)
QUOTES = [
    ("weekly cap as a key", r"`weekly_cap: ([0-9.]+)`", str(BUDGET["weekly_cap"]), 1),
    ("weekly cap as a share", r"(\d+)% (?:of the weekly allowance|cap\b)", pct(BUDGET["weekly_cap"]), 2),
    ("weekly cap in the plan table", r"weekly cap \((\d+)%\)", pct(BUDGET["weekly_cap"]), 1),
    ("account stop", r"meter reads (\d+)%", pct(BUDGET["stop_when_account_above"]), 2),
    ("account stop in the plan table", r"(\d+)% account stop", pct(BUDGET["stop_when_account_above"]), 1),
    ("per-run reservation", r"reserves ([0-9.]+) for one eval fire",
     f"{BUDGET['per_run_cap'] + BUDGET['per_run_overrun']:g}", 1),
    ("per-run cap", r"one run at ([0-9.]+) plus", f"{BUDGET['per_run_cap']:g}", 1),
    ("per-run overrun", r"plus a ([0-9.]+) overrun", f"{BUDGET['per_run_overrun']:g}", 1),
    ("exported points_per_usd", r"`([0-9.]+)` \(as exported\)", f"{BUDGET['points_per_usd']:g}", 1),
]


@pytest.mark.parametrize("what, pattern, want, least", QUOTES, ids=[q[0] for q in QUOTES])
def test_every_quote_matches_the_shipped_budget(what, pattern, want, least):
    found = re.findall(pattern, flat(TEXT))
    assert len(found) >= least, f"{what}: expected at least {least} quote(s) in docs/, found {len(found)}"
    wrong = sorted({f for f in found if abs(float(f) - float(want)) > 1e-12})
    assert not wrong, (f"{what}: docs/ quotes {wrong}, but starter/skills-evals/evals/budget.yml "
                       f"ships {want}; update docs/before-you-start.md and docs/evals-and-loop.md")
