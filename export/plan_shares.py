#!/usr/bin/env python3
"""plan_shares.py [--rows]

The model behind the "which plan" table in docs/before-you-start.md: what
the kit's base routines and evals cost in a week of each Claude plan.

The first model (2026-11-09) is a simulation in the owner's project files,
not in any repo: it drew each fire's cost from an assumed range (the fleet
worker $0.60 to $1.10) and $20 to $35 a point, so the table could not be
re-run from the kit when the eval budget's rate moved (acsi-kit#43). This
one is arithmetic over measured inputs, below, and
export/tests/test_plan_shares.py fails when the table and the model part.

Read from the kit, so the model follows them:
- each plan's `points_per_usd` (starter budget and bootstrap/lib/plan_sizing.py)
  and the weekly cap;
- how often the fleet worker fires on each plan (`fleet_worker_hours` in
  bootstrap/lib/common.sh);
- how many core fixtures the starter schedules.

Measured or assumed, below: dollars per fire, fires a week, and the two
unknowns that give every share a range (dollars per meter point, and how
the plans' weeks compare).

Prints the per-plan figures; --rows prints the table's modeled rows as
markdown. Keeps full precision until it prints.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "bootstrap" / "lib"))
import plan_sizing  # noqa: E402

PLANS = ("pro", "max5x", "max20x")

#: Dollars per fire, API-equivalent at list prices: each session's own
#: `total_cost_usd`, one fire of each on the owner's Max 20x account and
#: 13-repo fleet, 2026-11-13. One fire is a thin sample.
USD_PER_FIRE = {
    "fleet_worker": 1.85,   # a fire that took an issue; an idle fire costs less
    "changelog": 2.68,      # a fire that stopped at its first step
    "memory": 4.54,         # ran on Opus
    "sweep": 2.03,          # the parent session only; see FLEET_SIZE
}
#: An eval fire: the mean of 304 routine fires from 2026-11-09 to 2026-11-12
#: ($0.75) plus the runner session that starts it ($0.12).
USD_PER_EVAL_FIRE = 0.87

#: Fires a week that do not come from the kit's code. The changelog watcher's
#: schedule is set by hand (docs/routines.md: weekly on Pro); the sweep fires
#: when the changelog watcher asks, taken as weekly, as the first model did
#: (the owner's record held two fires by 2026-11-13).
CHANGELOG_PER_WEEK = {"pro": 1, "max5x": 7, "max20x": 7}
MEMORY_PER_WEEK = 1
SWEEP_PER_WEEK = 1

#: Dollars per point of the Max 20x weekly meter. The cautious end is the
#: exported `points_per_usd`. Middle: eval calls cost $8.80 a point over the
#: 20 points that ticked in overnight windows, 2026-10-26 to 2026-11-11, and
#: $10.20 by regression. Favorable: three whole weeks of the account's known
#: spend came to at least $14, $17 and $20 a point.
USD_PER_POINT_MIDDLE = 10.0
USD_PER_POINT_FAVORABLE = 17.0

#: A plan's week as a fraction of Max 20x's. The cautious end is the kit's
#: own sizing (the plan multipliers); the favorable end is the weekly hours
#: Anthropic gave in 2025 (40-80, 140-280, 240-480). Neither is published as
#: a weekly ratio.
WEEK_RATIO_FAVORABLE = {"pro": 1 / 6, "max5x": 0.58, "max20x": 1.0}

#: How two routines grow with the number of repos in the fleet. Bounds read
#: from one fire's tool calls and context sizes, not a measured slope: the
#: fleet worker's fire was on 15 repos, and one small repo's sweep child
#: session cost $0.46.
FLEET_SIZE = {"measured_repos": 15, "fleet_worker_usd_per_repo": (0.02, 0.09),
              "sweep_child_usd_per_repo": 0.46}


def fleet_worker_hours(plan: str) -> int:
    out = subprocess.run(
        ["bash", "-c", '. "$1"; fleet_worker_hours "$2"', "_",
         str(KIT / "bootstrap" / "lib" / "common.sh"), plan],
        check=True, capture_output=True, text=True).stdout
    return int(out)


def model() -> dict[str, dict[str, float]]:
    budget = yaml.safe_load(
        (KIT / "starter/skills-evals/evals/budget.yml").read_text(encoding="utf-8"))
    scheduled = yaml.safe_load(
        (KIT / "starter/skills-evals/evals/scheduled.yml").read_text(encoding="utf-8"))
    exported = budget["points_per_usd"]
    out = {}
    for plan in PLANS:
        rate = plan_sizing.POINTS_PER_USD[plan] or exported
        ratio = exported / rate
        fires = 168 / fleet_worker_hours(plan)
        base = (fires * USD_PER_FIRE["fleet_worker"]
                + CHANGELOG_PER_WEEK[plan] * USD_PER_FIRE["changelog"]
                + MEMORY_PER_WEEK * USD_PER_FIRE["memory"]
                + SWEEP_PER_WEEK * USD_PER_FIRE["sweep"])
        week = {"cautious": 1 / rate,
                "middle": 100 * USD_PER_POINT_MIDDLE * ratio,
                "favorable": 100 * USD_PER_POINT_FAVORABLE * WEEK_RATIO_FAVORABLE[plan]}
        capped = budget["weekly_cap"] / rate
        out[plan] = {
            "fleet_worker_fires": fires, "base_usd": base,
            **{f"week_usd_{k}": v for k, v in week.items()},
            **{f"base_share_{k}": base / v for k, v in week.items()},
            "eval_cap_usd": capped,
            "eval_passes": capped / (len(scheduled["fixtures"]) * USD_PER_EVAL_FIRE),
        }
    return out


def usd(value: float) -> str:
    """Two significant figures, as the table prints a modeled dollar figure."""
    digits = len(str(int(value)))
    return f"${round(value, 2 - digits):,.0f}"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def rows() -> list[str]:
    m = model()
    def row(label, cell):
        return f"| {label} | " + " | ".join(cell(m[p]) for p in PLANS) + " |"
    return [
        row("One week of the plan, in API-equivalent dollars (model)",
            lambda r: f"about {usd(r['week_usd_middle'])} ({usd(r['week_usd_cautious'])} to "
                      f"{usd(r['week_usd_favorable'])})"),
        row("Base routines, a week", lambda r: f"about ${r['base_usd']:.0f}"),
        row("Base routines, share of the week (model)",
            lambda r: f"~{pct(r['base_share_middle'])} ({pct(r['base_share_favorable'])} to "
                      f"{pct(r['base_share_cautious'])})"),
    ]


def eval_cells() -> list[str]:
    """How each cell of the eval row starts; the words after it are prose."""
    m = model()
    return [f"about {usd(m[p]['eval_cap_usd'])}: " for p in PLANS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", action="store_true", help="print the table's modeled rows")
    args = parser.parse_args(argv)
    if args.rows:
        print("\n".join(rows()))
        return 0
    for plan, r in model().items():
        print(plan)
        for key, value in r.items():
            print(f"  {key}: {value:.4g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
