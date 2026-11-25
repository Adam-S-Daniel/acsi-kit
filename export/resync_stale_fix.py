#!/usr/bin/env python3
"""resync_stale_fix.py: which held sources have moved past an open fix pull request's pins.

Usage:
  python3 resync_stale_fix.py HELD_HEADS_JSON PR_MANIFESTS_DIR

HELD_HEADS_JSON is what `resync_holdback.py --held-heads` wrote: an object of
each held source repo to the head sha it could not take. PR_MANIFESTS_DIR holds
the fix pull request's head copy of `export/manifests/*.yml`. A held source is
stale when the `source_sha` of the manifest whose `source` is that repo differs
from its held head (a pin in another source's manifest never counts).

Prints the stale sources on one line, space-separated and sorted; empty output
means the pull request still follows every held head. Exits 0 on a decision,
and 2 with one line on stderr naming what is unreadable (never its contents).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("kit_resync", HERE / "resync.py")
resync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resync)


def read_held(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise resync.ResyncError(f"cannot read the held heads file {path.name}") from None
    if not isinstance(data, dict) or not data:
        raise resync.ResyncError(f"the held heads file {path.name} is not a non-empty object")
    for source, sha in data.items():
        resync.check_name(source)
        resync.check_sha(sha, f"held head of {source}")
    return data


def pr_pins(manifests: Path) -> dict:
    """source repo -> the set of source_sha values the PR's manifests carry for it."""
    pins: dict[str, set] = {}
    for path in sorted(manifests.glob("*.yml")):
        if path.name == "_common.yml":
            continue
        try:
            text = path.read_text(encoding="utf-8")
            _, source, spans = resync.sha_spans(text, path.name)
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            raise resync.ResyncError(f"cannot parse the pull request's manifest {path.name}") from None
        pins.setdefault(source, set()).add(spans[0][2])
    return pins


def stale_sources(held: dict, manifests: Path) -> list:
    pins = pr_pins(manifests)
    stale = []
    for source in sorted(held):
        if source not in pins:
            raise resync.ResyncError(f"the pull request has no manifest for {source}")
        if pins[source] != {held[source]}:
            stale.append(source)
    return stale


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("resync_stale_fix.py: usage: HELD_HEADS_JSON PR_MANIFESTS_DIR", file=sys.stderr)
        return 2
    try:
        print(" ".join(stale_sources(read_held(Path(argv[0])), Path(argv[1]))))
    except resync.ResyncError as exc:
        print(f"resync_stale_fix.py: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
