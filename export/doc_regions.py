#!/usr/bin/env python3
"""doc_regions.py [--check | --write]

Keeps the text a docs page quotes "exactly" from a starter file in step with
that file. A page marks each such passage as a generated region:

    <!-- generated:NAME by export/doc_regions.py; edit the spec, then run it with --write -->
    > the text, as a Markdown blockquote
    <!-- /generated:NAME -->

REGIONS below names each region's page and its source: the blockquote that
follows the "Prompt, exactly" paragraph or list item in a spec. The source is
read by parsing the spec with markdown-it-py. The page gets that text with
the kit's invented owner replaced by `<you>`, wrapped to 78 columns.

A second kind of region is computed from the kit's files instead of quoted:
COMPUTED names each one's page and the function that returns its lines. The
one such region is the table in docs/machine.md of what every session loads
(the fleet guidance and the skill descriptions, in bytes, by content tier),
read from bootstrap/content-catalog.json and the files it names, so the
numbers are never counted by hand and follow a re-sync.

--check exits 1 and prints a diff for each stale region; --write rewrites
the stale ones in place (a second run changes nothing). Exit 2: a spec or
page the tool cannot read (no block or more than one in a spec, a marker
with no source, a known region missing from its page).
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import textwrap
from pathlib import Path

from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parent.parent
GUIDANCE = "starter/agent-guidance/"
OWNER = "example-adopter"
PLACEHOLDER = "<you>"
WIDTH = 78
ANCHOR = "Prompt, exactly"

#: region name -> (page, spec)
REGIONS = {
    "fleet-worker-prompt": ("docs/routines.md", GUIDANCE + "docs/routines/fleet-worker.md"),
    "loop-worker-prompt": ("docs/routines.md", GUIDANCE + "docs/routines/fleet-worker.md"),
    "prompt-audit-sweep-prompt": ("docs/routines.md", GUIDANCE + "docs/routines/prompt-audit-sweep.md"),
    "changelog-watcher-prompt": ("docs/routines.md", GUIDANCE + "docs/reference/agent-changelog-routine.md"),
    "memory-curation-prompt": ("docs/routines.md", GUIDANCE + "docs/routines/memory-curation.md"),
}

#: A spec that holds more than one prompt names which one a region quotes by
#: the text that introduces it (default: ANCHOR).
ANCHORS = {
    "fleet-worker-prompt": "Fleet worker prompt (maintenance role), exactly",
    "loop-worker-prompt": "Loop worker prompt (loop role), exactly",
}

CATALOG = "bootstrap/content-catalog.json"
BASE_MD = GUIDANCE + "agents-md/base.md"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def skill_listing_bytes(text: str, where: str) -> int:
    """The bytes of a skill's name and description, the part of a SKILL.md
    that every session's skill list carries (the body loads only on use)."""
    import yaml
    m = FRONTMATTER.match(text)
    meta = yaml.safe_load(m.group(1)) if m else None
    if not isinstance(meta, dict) or not isinstance(meta.get("name"), str) or not isinstance(meta.get("description"), str):
        raise RegionError(f"{where}: no frontmatter with a name and a description")
    return len(meta["name"].encode("utf-8")) + len(meta["description"].encode("utf-8"))


def always_loaded(root: Path) -> list[str]:
    """The docs/machine.md table: bytes every session loads, by content tier."""
    try:
        items = json.loads((root / CATALOG).read_text(encoding="utf-8"))["items"]
    except (OSError, ValueError, KeyError) as exc:
        raise RegionError(f"{CATALOG}: cannot be read ({type(exc).__name__})") from None

    def size(item) -> int:
        path = root / item["source_link"]
        if not path.is_file():
            raise RegionError(f"{item['source_link']}: named by {CATALOG} for '{item['id']}', does not exist")
        if item["kind"] == "skill":
            return skill_listing_bytes(path.read_text(encoding="utf-8"), item["source_link"])
        return len(path.read_bytes())

    def pick(kind, tier, group=None):
        return [i for i in items if i["kind"] == kind and i["tier"] == tier and (group is None or i.get("group") == group)]

    def row(label, chosen, where, total=None):
        if not chosen:
            raise RegionError(f"{CATALOG}: no item for the row '{label}'")
        total = sum(size(i) for i in chosen) if total is None else total
        return f"| {label} | {len(chosen)} | {total:,} | {where} |"

    core = pick("guidance", "core")
    if {i["source_link"] for i in core} != {BASE_MD}:
        raise RegionError(f"{CATALOG}: a core guidance item is not a section of {BASE_MD}")
    step1 = "your choice in step 1"
    lines = ["| What | Items | Bytes | Loaded when |", "|---|---|---|---|",
             row("Core guidance (`agents-md/base.md` as shipped)", core, "always", len((root / BASE_MD).read_bytes())),
             row("Recommended guidance, safety", pick("guidance", "recommended", "safety"), step1),
             row("Recommended guidance, habits", pick("guidance", "recommended", "habits"), step1)]
    for item in pick("guidance", "opinionated"):
        lines.append(row(f"Opinionated guidance: `{item['id']}`", [item], step1))
    lines += [row("Core skills (name and description)", pick("skill", "core"), "always"),
              row("Recommended skills (name and description)", pick("skill", "recommended"), step1),
              row("Opinionated skills (name and description)", pick("skill", "opinionated"), step1)]
    return lines


#: region name -> (page, function(root) -> the region's lines, before indentation)
COMPUTED = {
    "always-loaded": ("docs/machine.md", always_loaded),
}

# The markers are lexical tokens on a line of their own.
OPEN = re.compile(r"^(?P<indent>[ ]*)<!-- generated:(?P<name>[a-z0-9-]+) by export/doc_regions\.py;[^>]*-->[ ]*$")
CLOSE = re.compile(r"^(?P<indent>[ ]*)<!-- /generated:(?P<name>[a-z0-9-]+) -->[ ]*$")
ANY_OPEN = re.compile(r"<!--\s*generated:")


class RegionError(Exception):
    """Something the tool cannot decide (exit 2), as opposed to a stale region (exit 1)."""


def extract_prompt(spec_text: str, spec_name: str, anchor: str = ANCHOR) -> list[str]:
    """The paragraphs of the one blockquote after the "Prompt, exactly" text."""
    tokens = MarkdownIt("commonmark").parse(spec_text)
    anchors = [i for i, t in enumerate(tokens) if t.type == "inline" and anchor in t.content]
    if len(anchors) != 1:
        raise RegionError(f"{spec_name}: expected exactly one '{anchor}' block, found {len(anchors)}")
    start = next((i for i in range(anchors[0], len(tokens)) if tokens[i].type == "blockquote_open"), None)
    if start is None:
        raise RegionError(f"{spec_name}: no blockquote follows '{anchor}'")
    depth, paragraphs = 0, []
    for t in tokens[start:]:
        if t.type == "blockquote_open":
            depth += 1
        elif t.type == "blockquote_close":
            depth -= 1
            if depth == 0:
                break
        elif t.type == "inline":
            paragraphs.append(" ".join(t.content.split()))
    if not paragraphs:
        raise RegionError(f"{spec_name}: the blockquote after '{anchor}' is empty")
    return paragraphs


def render(paragraphs: list[str], indent: str = "") -> list[str]:
    """The page's lines for a prompt: owner replaced, wrapped, as a blockquote."""
    prefix = f"{indent}> "
    out: list[str] = []
    for n, para in enumerate(paragraphs):
        if n:
            out.append(f"{indent}>")
        para = para.replace(OWNER, PLACEHOLDER)
        out += textwrap.wrap(para, width=WIDTH, initial_indent=prefix, subsequent_indent=prefix,
                             break_long_words=False, break_on_hyphens=False)
    return out


def find_regions(page_text: str, page_name: str) -> dict[str, tuple[int, int, str]]:
    """name -> (index of its first body line, index of its closing marker, indent)."""
    lines = page_text.split("\n")
    found: dict[str, tuple[int, int, str]] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = OPEN.match(line)
        if not m:
            if ANY_OPEN.search(line):
                raise RegionError(f"{page_name}:{i + 1}: a generated-region marker this tool cannot read")
            i += 1
            continue
        name = m["name"]
        if name in found:
            raise RegionError(f"{page_name}:{i + 1}: region '{name}' appears twice")
        end = next((j for j in range(i + 1, len(lines))
                    if (c := CLOSE.match(lines[j])) and c["name"] == name), None)
        if end is None:
            raise RegionError(f"{page_name}:{i + 1}: region '{name}' is never closed")
        found[name] = (i + 1, end, m["indent"])
        i = end + 1
    return found


def process(root: Path, write: bool) -> list[str]:
    """Check or rewrite every page; returns one diff per stale region."""
    stale: list[str] = []
    pages: dict[str, list[str]] = {}
    known = {**REGIONS, **COMPUTED}
    for page in sorted({p for p, _ in known.values()}):
        pages[page] = [n for n, (p, _) in known.items() if p == page]
    for page, names in pages.items():
        path = root / page
        text = path.read_text(encoding="utf-8")
        regions = find_regions(text, page)
        for name in regions:
            if name not in known or known[name][0] != page:
                raise RegionError(f"{page}: region '{name}' has no known source (REGIONS in export/doc_regions.py)")
        for name in names:
            if name not in regions:
                raise RegionError(f"{page}: region '{name}' is missing from the page")
        lines = text.split("\n")
        # Bottom up, so a rewrite does not move the regions above it.
        for name in sorted(names, key=lambda n: -regions[n][0]):
            first, end, indent = regions[name]
            if name in COMPUTED:
                spec = "the kit's files"
                want = [indent + line for line in COMPUTED[name][1](root)]
            else:
                spec = REGIONS[name][1]
                spec_path = root / spec
                if not spec_path.is_file():
                    raise RegionError(f"{spec}: the source of region '{name}' does not exist")
                want = render(extract_prompt(spec_path.read_text(encoding="utf-8"), spec, ANCHORS.get(name, ANCHOR)), indent)
            have = lines[first:end]
            if have == want:
                continue
            diff = "\n".join(difflib.unified_diff(have, want, f"{page} region {name} (page)",
                                                  f"{page} region {name} (from {spec})", lineterm=""))
            stale.append(f"region '{name}' in {page} is stale (source {spec}):\n{diff}")
            lines[first:end] = want
        if write:
            new = "\n".join(lines)
            if new != text:
                path.write_text(new, encoding="utf-8")
    return stale


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1], formatter_class=argparse.RawTextHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="exit 1 listing each stale region")
    mode.add_argument("--write", action="store_true", help="rewrite stale regions in place")
    ap.add_argument("--root", type=Path, default=KIT, help="the kit root (default: this kit)")
    args = ap.parse_args(argv)
    try:
        stale = process(args.root, write=args.write)
    except RegionError as exc:
        print(f"doc_regions: {exc}", file=sys.stderr)
        return 2
    for s in stale:
        print(s)
    if args.write:
        print(f"rewrote {len(stale)} region(s)" if stale else "every region is current")
        return 0
    if stale:
        print("\nRun: python3 export/doc_regions.py --write", file=sys.stderr)
        return 1
    print("every region is current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
