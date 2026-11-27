#!/usr/bin/env python3
"""drift_this_pr.py <head changes.json> <base changes.json>

The `drift` job's verdict on a pull request: which of the changes merging it
would make are the pull request's own. Both files are `repo_settings.py diff
--changes-json` output for one owner, the first planned from the pull
request's `repo-settings/fleet.yml`, the second from the base branch's.

A change the base branch's own fleet.yml would make too (a setting not
applied yet, as on every repo before the adoption kit's first apply) is not
this pull request's: it is listed, and it does not fail the job. A change the
base would not make, or would make differently, is listed, and a drift one
exits 1 (an advisory never fails, as in `diff` itself). Changes are matched
on repo, setting, status and desired value; the current value is the same
live read in both files.

Added by the adoption kit's export (acsi-kit, after its PR #139).

Exit 0: no change of the pull request's own. Exit 1: one or more. Exit 2: a
file could not be read.
"""

import json
import sys


def _key(change):
    return (change.get("repo"), change.get("setting"), change.get("status"),
            json.dumps(change.get("desired"), sort_keys=True, default=repr))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list) or not all(isinstance(c, dict) for c in data):
        raise ValueError(f"{path}: not a list of changes")
    return data


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__.split("\n", 1)[0], file=sys.stderr)
        return 2
    try:
        head, base = _load(argv[0]), _load(argv[1])
    except (OSError, ValueError) as e:
        print(f"drift: could not read the changes ({e})", file=sys.stderr)
        return 2
    pending = {_key(c) for c in base}
    own = [c for c in head if _key(c) not in pending]
    inherited = len(head) - len(own)
    if inherited:
        print(f"drift: {inherited} change(s) the base branch's fleet.yml would make too "
              "(not applied yet); not this pull request's")
    for c in own:
        print(f"drift: this pull request changes {c.get('repo')}: {c.get('setting')} ({c.get('status')})")
    # Only drift fails, as in `diff` itself: an advisory is listed, never fatal.
    failing = [c for c in own if c.get("status") == "drift"]
    if failing:
        print(f"drift: {len(failing)} drift change(s) of this pull request's own")
        return 1
    print("drift: no change of this pull request's own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
