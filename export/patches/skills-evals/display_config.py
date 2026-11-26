"""Re-pin round 24: explorer/display.json ships no one's zone or repos.

skills-evals' explorer/display.json (its PR 1176) holds the time zone every
explorer and dashboard page displays and `issue_repos`, the repos the pages
query for issues; the first entry is the data repo the published page reads
(explorer/src/config.js derives DATA_REPO from it). The source's file names
its owner's zone and repos. Here, on the substituted tree:

- `time_zone` becomes the neutral "UTC", the value bootstrap/lib/time_zone.py
  replaces with the adopter's TIME_ZONE in copy-starter.sh (exactly once);
- `issue_repos` keeps, in the source's order, only the entries that name the
  kit's first owner and one of `kit_repos` (export/manifests/_common.yml), so
  a repo the kit does not ship never reaches an adopter's page. The first entry
  must be that owner's skills-evals, the data repo, or the export fails.

The pages are rebuilt from this file by the manifest's regenerate step, which
runs after the patches. Fails, changing nothing, on a file that is not the
source's shape (exactly the two keys, a string zone, a list of owner/repo).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REL = Path("explorer") / "display.json"
NEUTRAL_ZONE = "UTC"
DATA_REPO = "skills-evals"
REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")


def neutral_display(source: dict, owner: str, kit_repos: set) -> dict:
    if set(source) != {"time_zone", "issue_repos"}:
        raise SystemExit(f"display_config: {REL} has keys {sorted(source)}, not exactly time_zone and issue_repos")
    repos = source["issue_repos"]
    if not isinstance(source["time_zone"], str) or not isinstance(repos, list) \
            or not all(isinstance(r, str) and REPO.match(r) for r in repos):
        raise SystemExit(f"display_config: {REL} is not a zone string and a list of owner/repo names")
    kept = [r for r in repos if r.split("/", 1)[0] == owner and r.split("/", 1)[1] in kit_repos]
    if not kept or kept[0] != f"{owner}/{DATA_REPO}":
        raise SystemExit(f"display_config: {REL}'s first kit repo is {kept[:1]}, not {owner}/{DATA_REPO} (the data repo)")
    return {"time_zone": NEUTRAL_ZONE, "issue_repos": kept}


def apply(root: Path, ctx) -> None:
    common = ctx["common"]
    path = root / REL
    source = json.loads(path.read_text(encoding="utf-8"))
    out = neutral_display(source, common["kit_owners"][0], set(common["kit_repos"]))
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
