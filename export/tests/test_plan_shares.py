"""The "which plan" table quotes the model in export/plan_shares.py.

The table's shares went stale once because the model behind them was kept
outside the repo (acsi-kit#43). This fails a change to the eval budget, the
plan sizing, the fleet worker's cadence or the model's inputs until
docs/before-you-start.md follows it.

The rows are found as whole lines of prose (no code shape is read).

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KIT / "export"))
import plan_shares  # noqa: E402

DOC = (KIT / "docs" / "before-you-start.md").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("row", plan_shares.rows(), ids=lambda r: r.split("|")[1].strip())
def test_the_table_carries_each_modeled_row(row):
    assert row in DOC, (
        "docs/before-you-start.md does not carry this row of the model "
        f"(python3 export/plan_shares.py --rows):\n{row}")


def test_the_eval_row_quotes_what_the_cap_lets_through():
    line = next((l for l in DOC if l.startswith("| Evals the weekly cap lets through")), None)
    assert line, "docs/before-you-start.md has no 'Evals the weekly cap lets through' row"
    cells = [c.strip() for c in line.strip("|").split("|")][1:]
    for cell, want in zip(cells, plan_shares.eval_cells(), strict=True):
        assert cell.startswith(want.strip()), f"the eval row says '{cell}', the model '{want}'"


def test_the_docs_quote_the_measured_fleet_size():
    # Lexical: the number in one sentence of prose, not code shape.
    found = re.findall(r"owner's fleet of (\d+) repos", " ".join(DOC))
    assert found, "docs/before-you-start.md no longer names the owner's fleet size"
    want = plan_shares.FLEET_SIZE["measured_repos"]
    assert {int(n) for n in found} == {want}, (
        f"docs/before-you-start.md says the owner's fleet has {found} repos; "
        f"export/plan_shares.py FLEET_SIZE['measured_repos'] is {want}")


def test_the_base_counts_the_fleet_worker_at_its_cadence(monkeypatch):
    monkeypatch.setattr(plan_shares, "fleet_worker_hours", lambda plan: 168)
    after = plan_shares.model()["pro"]["base_usd"]
    assert after == pytest.approx(
        plan_shares.USD_PER_FIRE["fleet_worker"]
        + plan_shares.CHANGELOG_PER_WEEK["pro"] * plan_shares.USD_PER_FIRE["changelog"]
        + plan_shares.USD_PER_FIRE["memory"]
        + plan_shares.SWEEP_PER_WEEK * plan_shares.USD_PER_FIRE["sweep"])
