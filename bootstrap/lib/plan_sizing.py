#!/usr/bin/env python3
"""plan_sizing.py <starter tree> --plan pro|max5x|max20x

Sizes a staged skills-evals tree for the adopter's Claude plan, before
copy-starter.sh commits it (acsi-kit#28). The exported budget and roster
policy are the owner's, on Max 20x; a smaller plan has a smaller weekly
allowance, so the same dollars are more points of it.

- evals/budget.yml: `points_per_usd` is set for the plan (Max 20x keeps the
  exported value), and on Pro and Max 5x `stop_when_session_above: 0.90` is
  added, so a sweep cannot use up a whole 5-hour window (skills-evals#921).
- evals/roster-policy.yml: on Pro, `judge_exclude_tiers: [fable, mythos]`,
  because Pro bills Fable as usage credits from the first call
  (skills-evals#920).

The 25% weekly cap and the 80% account stop are left as exported. A tree
without evals/budget.yml (every starter but skills-evals) is left alone.
Each edit is checked by parsing the result with the YAML parser, and a file
that already carries the key is refused rather than edited twice. Prints one
line per file changed. Exits 2 on a bad argument or file.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

#: Allowance fraction per dollar of API-equivalent spend: the exported Max 20x
#: rate (0.0015, about $6.70 per point, measured 2026-11-10), scaled by the
#: plan multipliers (Max 5x a quarter of Max 20x, Pro a twentieth).
#: docs/before-you-start.md#which-plan.
POINTS_PER_USD = {"pro": 0.03, "max5x": 0.006, "max20x": None}
SESSION_STOP = {"pro": 0.90, "max5x": 0.90, "max20x": None}
JUDGE_EXCLUDE = {"pro": ["fable", "mythos"], "max5x": None, "max20x": None}
PPU_LINE = re.compile(r"^points_per_usd:[ \t]*[0-9.eE+-]+[ \t]*$", re.MULTILINE)


class SizingError(Exception):
    pass


def size_budget(text: str, plan: str) -> str:
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or "points_per_usd" not in doc:
        raise SizingError("evals/budget.yml has no points_per_usd")
    if "stop_when_session_above" in doc:
        raise SizingError("evals/budget.yml already sets stop_when_session_above")
    rate = POINTS_PER_USD[plan]
    if rate is not None:
        if len(PPU_LINE.findall(text)) != 1:
            raise SizingError("evals/budget.yml's points_per_usd is not one plain line")
        text = PPU_LINE.sub(f"points_per_usd: {rate}  # sized for CLAUDE_PLAN={plan}", text)
    stop = SESSION_STOP[plan]
    if stop is not None:
        text = text.rstrip("\n") + (
            "\n\n# Added by copy-starter.sh for CLAUDE_PLAN=" + plan + ": stop starting eval\n"
            "# work once the 5-hour window reads this (docs/how-it-works.md).\n"
            f"stop_when_session_above: {stop}\n")
    sized = yaml.safe_load(text)
    if sized.get("points_per_usd") != (rate if rate is not None else doc["points_per_usd"]) \
            or sized.get("stop_when_session_above") != stop:
        raise SizingError("evals/budget.yml did not parse back as sized")
    return text


def size_policy(text: str, plan: str) -> str:
    words = JUDGE_EXCLUDE[plan]
    if words is None:
        return text
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or "judge_exclude_tiers" in doc:
        raise SizingError("evals/roster-policy.yml is not a mapping or already sets judge_exclude_tiers")
    text = text.rstrip("\n") + (
        "\n\n# Added by copy-starter.sh for CLAUDE_PLAN=" + plan + ": Pro bills Fable as\n"
        "# usage credits, so the judge comes from another tier.\n"
        f"judge_exclude_tiers: [{', '.join(words)}]\n")
    if yaml.safe_load(text).get("judge_exclude_tiers") != words:
        raise SizingError("evals/roster-policy.yml did not parse back as sized")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path)
    parser.add_argument("--plan", required=True, choices=sorted(POINTS_PER_USD))
    args = parser.parse_args(argv)
    budget = args.tree / "evals" / "budget.yml"
    if not budget.is_file():
        return 0
    try:
        for path, size in ((budget, size_budget),
                           (args.tree / "evals" / "roster-policy.yml", size_policy)):
            if not path.is_file():
                raise SizingError(f"{path.name} is missing beside evals/budget.yml")
            before = path.read_text(encoding="utf-8")
            after = size(before, args.plan)
            if after != before:
                path.write_text(after, encoding="utf-8")
                print(f"sized: evals/{path.name} for CLAUDE_PLAN={args.plan}")
    except (SizingError, yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
        print(f"plan_sizing: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
