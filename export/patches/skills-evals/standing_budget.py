"""DECISIONS C6 for skills-evals: the committed budget is the standing default.

The source's `evals/budget.yml` records its owner's spending decisions: a
weekly cap and an account stop that change from week to week, each with a
comment saying when and why. The kit ships the standing defaults instead,
30 points a week and an 80% account stop, with comments that say only that.
The per-run values (`per_run_cap`, `per_run_overrun`, `points_per_usd`) are
measurements, so they and their comments ship as the source has them.

This patch rewrites the two keys' comment paragraphs and values by key,
rather than by matching their text, so the source can reword them (it does,
most weeks) without breaking the export. The budget test that pins the
source's current numbers gets the matching change: it checks the kit's two
standing values against the test module's LIMITS and leaves the per-run
values to the source's own tests.

Runs on the substituted tree.
"""

from __future__ import annotations

import re
from pathlib import Path

WEEKLY = (
    "# 30 points: all automated evals together, in each allowance week of the\n"
    "# account (Monday 17:00 UTC to the next), so a sanctioned push in one week\n"
    "# is not charged to the next.\n"
    "weekly_cap: 0.30\n"
)

STOP = (
    "# 80 points: once the account's own weekly meter reads this high, a run stops\n"
    "# starting new work, whatever it has spent, so evals never take the last of\n"
    "# the allowance from the owner's own work. It is also the fire limit:\n"
    "# scripts/allowance_guard.py starts no fire past it.\n"
    "stop_when_account_above: 0.80\n"
)

TEST_BODY = (
    "        # C6: the kit ships the standing weekly cap and account stop, the\n"
    "        # values LIMITS uses; the per-run values are the source's measurements.\n"
    "        loaded = budget.load_budget()\n"
    "        self.assertEqual(loaded[\"weekly_cap\"], LIMITS[\"weekly_cap\"])\n"
    "        self.assertEqual(loaded[\"stop_when_account_above\"],\n"
    "                         LIMITS[\"stop_when_account_above\"])\n"
)


def _replace_paragraph(text: str, key: str, block: str) -> str:
    """Replace `key`'s line and the comment lines directly above it."""
    rx = re.compile(r"(?:^#.*\n)*^" + re.escape(key) + r":.*\n", re.M)
    hits = rx.findall(text)
    if len(hits) != 1:
        raise SystemExit(f"standing_budget: expected one `{key}:` in evals/budget.yml, found {len(hits)}")
    return rx.sub(lambda _m: block, text)


def apply(root: Path, ctx) -> None:
    path = root / "evals" / "budget.yml"
    text = path.read_text(encoding="utf-8")
    text = _replace_paragraph(text, "weekly_cap", WEEKLY)
    text = _replace_paragraph(text, "stop_when_account_above", STOP)
    path.write_text(text, encoding="utf-8")

    test = root / "test" / "issues" / "test_issue_68_allowance_guard.py"
    src = test.read_text(encoding="utf-8")
    # The test's comment and its first assertEqual (on load_budget()) are its
    # source-specific part; the lines after it stay.
    rx = re.compile(
        r"(    def test_the_committed_budget_is_the_standing_cap\(self\):\n)"
        r"(?:        #.*\n)*"
        r"        self\.assertEqual\(budget\.load_budget\(\),\n"
        r"(?:                         .*\n)*?"
        r"(?:                         .*\}\)\n)"
    )
    if len(rx.findall(src)) != 1:
        raise SystemExit("standing_budget: the committed-budget test in test_issue_68_allowance_guard.py did not match")
    test.write_text(rx.sub(lambda m: m.group(1) + TEST_BODY, src), encoding="utf-8")
