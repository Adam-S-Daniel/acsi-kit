#!/usr/bin/env python3
"""List the hand-written pages a re-sync may have made stale.

The daily re-sync (.github/workflows/resync.yml) moves the pins and
regenerates starter/. Nothing told the reviewer which docs/*.md pages
describe a source that changed. This script reads export/doc-sources.yml (a
map from each page to the starter paths it describes) and the list of
starter paths that changed, and writes a "Pages to review" section for the
pull request.

    python3 export/doc_review.py --base <git-ref> [--head <git-ref>]
        [--map export/doc-sources.yml] [--summary FILE]

With no --head the changes are those of the working tree against --base,
untracked files included (that is the tree right after regeneration, before
the commit). --summary appends the section to FILE; without it the section
goes to stdout. The output names repo paths only, never file contents: the
repository is public.

A map that does not validate exits 2 with a message naming the entry.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

KIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = Path("export") / "doc-sources.yml"

TOP_LEVEL_KEYS = {"required", "pages", "not_documented"}
LINE_CAP = 15

# Status letters git prints, mapped to the words the section uses.
STATUS_WORDS = {"A": "added", "D": "deleted", "M": "modified", "R": "renamed",
                "C": "added", "T": "modified", "U": "modified"}
# Added and deleted first: they are the changes most likely to make a page wrong.
STATUS_ORDER = {"added": 0, "deleted": 1, "modified": 2, "renamed": 3}

# Files a re-sync adds that deserve a page decision (new ADRs, routine specs,
# workflows), whether or not a page maps them.
NEW_SOURCE_GLOBS = (
    "starter/*/docs/decisions/**",
    "starter/*/docs/routines/**",
    "starter/*/docs/routine/**",
    "starter/*/.github/workflows/**",
)

# Coverage: routine specs, and scheduled workflows, that no page names.
ROUTINE_SPEC_GLOBS = ("starter/*/docs/routines/*.md", "starter/*/docs/routine/*.md")
WORKFLOW_GLOB = "starter/*/.github/workflows/*.yml"
NAMING_FILES = ("README.md", "bootstrap/README.md")


class MapError(Exception):
    """The map does not validate; the message names the entry."""


# -- glob matching ------------------------------------------------------------

def glob_to_regex(glob: str) -> "re.Pattern[str]":
    """Translate a path glob to a regex with `**` semantics.

    `*` and `?` stay inside one path segment; `**` as a whole segment crosses
    segments (`a/**` is everything under `a`, `a/**/b` has zero or more
    segments between); `[...]` is a character class.
    """
    out = []
    i, n = 0, len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if glob.startswith("**", i):
                at_start = i == 0 or glob[i - 1] == "/"
                j = i + 2
                if at_start and j < n and glob[j] == "/":
                    out.append("(?:.*/)?")
                    i = j + 1
                    continue
                out.append(".*")
                i = j
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            end = glob.find("]", i + 2)
            if end == -1:
                out.append(re.escape(c))
            else:
                body = glob[i + 1:end]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                i = end
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out) + r"\Z")


def match_glob(path: str, glob: str) -> bool:
    return glob_to_regex(glob).match(path) is not None


# -- the map ------------------------------------------------------------------

def load_map(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        raise MapError(f"{path}: cannot read the map ({type(exc).__name__})") from exc
    return data


def tree_files(kit_root: Path) -> list[str]:
    """Every file under starter/, as repo-relative posix paths."""
    root = Path(kit_root)
    out = []
    for dirpath, _dirs, files in os.walk(root / "starter"):
        for name in files:
            out.append((Path(dirpath) / name).relative_to(root).as_posix())
    return sorted(out)


def validate_map(doc, kit_root: Path, files: list[str] | None = None) -> dict:
    """Check the map's shape against the tree; return it with defaults filled in."""
    kit_root = Path(kit_root)
    if not isinstance(doc, dict):
        raise MapError("the map must be a mapping with `required`, `pages` and `not_documented`")
    unknown = sorted(str(k) for k in doc if k not in TOP_LEVEL_KEYS)
    if unknown:
        raise MapError(f"unknown top-level key: {', '.join(unknown)}")
    required = doc.get("required", False)
    if not isinstance(required, bool):
        raise MapError("`required` must be true or false")
    pages = doc.get("pages")
    if not isinstance(pages, dict) or not pages:
        raise MapError("`pages` must be a non-empty mapping of page to a list of starter paths")
    if files is None:
        files = tree_files(kit_root)
    for page, globs in pages.items():
        if not isinstance(page, str) or not (kit_root / page).is_file():
            raise MapError(f"pages: {page}: the page does not exist")
        if not isinstance(globs, list) or not globs or not all(isinstance(g, str) for g in globs):
            raise MapError(f"pages: {page}: must be a non-empty list of starter paths")
        for glob in globs:
            if not glob.startswith("starter/"):
                raise MapError(f"pages: {page}: {glob}: a mapped path must start with starter/")
            if not any(match_glob(f, glob) for f in files):
                raise MapError(f"pages: {page}: {glob}: matches nothing in the tree")
    not_documented = doc.get("not_documented") or []
    if not isinstance(not_documented, list):
        raise MapError("`not_documented` must be a list of {path, reason} entries")
    for entry in not_documented:
        label = entry.get("path") if isinstance(entry, dict) else entry
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise MapError(f"not_documented: {label}: needs a `path`")
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise MapError(f"not_documented: {label}: needs a non-empty `reason`")
        if not (kit_root / entry["path"]).is_file():
            raise MapError(f"not_documented: {label}: the path does not exist")
    return {"required": required, "pages": pages, "not_documented": not_documented}


# -- changes ------------------------------------------------------------------

def parse_name_status(text: str) -> list[tuple[str, str, str | None]]:
    """Parse `git diff --name-status -z` output into (status, path, old_path)."""
    parts = text.split("\0")
    changes = []
    i = 0
    while i < len(parts) and parts[i]:
        code = parts[i]
        word = STATUS_WORDS.get(code[0], "modified")
        if code[0] in "RC":
            if i + 2 >= len(parts):
                break
            changes.append((word, parts[i + 2], parts[i + 1] if code[0] == "R" else None))
            i += 3
        else:
            if i + 1 >= len(parts):
                break
            changes.append((word, parts[i + 1], None))
            i += 2
    return changes


def git_changes(kit_root: Path, base: str, head: str | None = None) -> list[tuple[str, str, str | None]]:
    """The starter/ changes from base to head, or to the working tree."""
    cmd = ["git", "-C", str(kit_root), "diff", "--name-status", "-z", base]
    if head:
        cmd.append(head)
    cmd += ["--", "starter/"]
    changes = parse_name_status(_git(cmd))
    if not head:
        # A re-sync's new files are untracked until the commit: diff skips them.
        out = _git(["git", "-C", str(kit_root), "ls-files", "--others",
                    "--exclude-standard", "-z", "--", "starter/"])
        seen = {p for _s, p, _o in changes}
        changes += [("added", p, None) for p in out.split("\0") if p and p not in seen]
    return changes


def _git(cmd: list[str]) -> str:
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        # Name the command's failure, never its output beyond git's own message.
        raise SystemExit(f"doc_review: git failed (exit {done.returncode}): {done.stderr.strip()}")
    return done.stdout


# -- coverage -----------------------------------------------------------------

def _workflow_is_scheduled(path: Path) -> bool:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return False
    if not isinstance(doc, dict):
        return False
    # PyYAML reads the key `on` as the boolean True.
    triggers = doc["on"] if "on" in doc else doc.get(True)
    return isinstance(triggers, dict) and "schedule" in triggers


def undocumented(kit_root: Path, doc: dict) -> list[str]:
    """Routine specs and scheduled workflows that no page names.

    "Named" means the file's base name appears in the text of a docs/*.md
    page, README.md or bootstrap/README.md. Files in `not_documented` are
    left out.
    """
    kit_root = Path(kit_root)
    texts = []
    for page in sorted((kit_root / "docs").glob("*.md")):
        texts.append(page.read_text(encoding="utf-8"))
    for name in NAMING_FILES:
        f = kit_root / name
        if f.is_file():
            texts.append(f.read_text(encoding="utf-8"))
    corpus = "\n".join(texts)
    skip = {e["path"] for e in (doc.get("not_documented") or [])}
    found = []
    for path in tree_files(kit_root):
        if path in skip:
            continue
        is_spec = any(match_glob(path, g) for g in ROUTINE_SPEC_GLOBS)
        is_sched = match_glob(path, WORKFLOW_GLOB) and _workflow_is_scheduled(kit_root / path)
        if (is_spec or is_sched) and Path(path).name not in corpus:
            found.append(path)
    return sorted(found)


# -- rendering ----------------------------------------------------------------

def pages_hit(changes, doc: dict) -> dict[str, list[tuple[str, str, str | None]]]:
    hits: dict[str, list] = {}
    for page, globs in doc["pages"].items():
        mine = [c for c in changes
                if any(match_glob(c[1], g) or (c[2] and match_glob(c[2], g)) for g in globs)]
        if mine:
            hits[page] = mine
    return hits


def new_on_no_page(changes) -> list[str]:
    return sorted(p for s, p, _o in changes
                  if s == "added" and any(match_glob(p, g) for g in NEW_SOURCE_GLOBS))


def _bullets(lines: list[str]) -> list[str]:
    if len(lines) <= LINE_CAP:
        return lines
    return lines[:LINE_CAP] + [f"- and {len(lines) - LINE_CAP} more"]


def _change_line(change) -> str:
    status, path, old = change
    if status == "renamed" and old:
        return f"- `{path}` (renamed from `{old}`)"
    return f"- `{path}` ({status})"


def render(changes, doc: dict, findings: list[str]) -> str:
    """The "Pages to review" section, as Markdown."""
    out = ["## Pages to review", ""]
    hits = pages_hit(changes, doc)
    if not hits:
        out += ["No mapped source changed, so no page needs a look.", ""]
    for page in sorted(hits):
        ordered = sorted(hits[page], key=lambda c: (STATUS_ORDER[c[0]], c[1]))
        out += [f"### {page}", ""] + _bullets([_change_line(c) for c in ordered]) + [""]
    new = new_on_no_page(changes)
    out += ["### New, on no page yet", ""]
    out += _bullets([f"- `{p}`" for p in new]) if new else ["None."]
    out += ["", "### Coverage (advisory)", ""]
    if findings:
        out += ["Routine specs and scheduled workflows that no page, `README.md` or "
                "`bootstrap/README.md` names:", ""]
        out += _bullets([f"- `{p}`" for p in findings])
    else:
        out += ["None."]
    return "\n".join(out) + "\n"


# -- command line -------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="git ref to compare starter/ against")
    ap.add_argument("--head", help="git ref to compare to; default is the working tree")
    ap.add_argument("--map", default=str(DEFAULT_MAP), help="the page-to-source map")
    ap.add_argument("--summary", help="append the section to this file instead of printing it")
    ap.add_argument("--root", default=str(KIT_ROOT), help="the kit's root (default: this checkout)")
    args = ap.parse_args(argv)
    root = Path(args.root)
    map_path = Path(args.map)
    if not map_path.is_absolute():
        map_path = root / map_path
    try:
        doc = validate_map(load_map(map_path), root)
    except MapError as exc:
        print(f"doc_review: {exc}", file=sys.stderr)
        return 2
    text = render(git_changes(root, args.base, args.head), doc, undocumented(root, doc))
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("\n" + text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
