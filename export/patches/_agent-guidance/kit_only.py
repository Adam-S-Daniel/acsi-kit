"""DECISIONS C11 and "Kit-only blocks": the kit's own re-sync merge rule and `kit_resync` key do not ship.

The source's fleet-worker spec may carry blocks that tell the owner's fleet
worker it may merge the kit's re-sync pull requests (heads `resync/auto` and
`resync-fix/*`), and `repos.yml` may carry a top-level `kit_resync` key. An
adopter's fleet has no kit, so neither belongs in what the kit ships:

* in every Markdown file under `docs/routines/`, each region from a line that is
  exactly `<!-- kit-only:begin -->` through the matching line that is exactly
  `<!-- kit-only:end -->` is cut, plus one blank line after the end marker, so
  the paragraphs around it stay one blank line apart;
* in `repos.yml`, the top-level `kit_resync` key, its body and the comment
  block directly above it are cut, plus one blank line after it.

The patch landed before the source change, so it is tolerant: a file without
markers, or a `repos.yml` without the key, is left byte for byte as it is. A
marker that is unbalanced, nested or out of order stops the export, naming the
file, rather than shipping half a block. Runs on the substituted tree, before
the other patches, so the marker text is intact.
"""

from __future__ import annotations

from pathlib import Path

BEGIN = "<!-- kit-only:begin -->"
END = "<!-- kit-only:end -->"
KEY = "kit_resync:"


def strip_blocks(text: str, where: str) -> str:
    """Cut every begin..end region (and one blank line after it)."""
    out: list[str] = []
    inside = False
    skip_blank = False
    for line in text.splitlines(keepends=True):
        mark = line.strip()
        if mark == BEGIN:
            if inside:
                raise SystemExit(f"kit_only: {where}: nested {BEGIN}")
            inside = True
        elif mark == END:
            if not inside:
                raise SystemExit(f"kit_only: {where}: {END} without {BEGIN}")
            inside = False
            skip_blank = True
        elif inside:
            pass
        elif skip_blank and not mark:
            skip_blank = False
        else:
            skip_blank = False
            out.append(line)
    if inside:
        raise SystemExit(f"kit_only: {where}: {BEGIN} without {END}")
    return "".join(out)


def strip_key(text: str, where: str) -> str:
    """Cut the top-level `kit_resync` key, its body and the comment above it."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(KEY)]
    if not starts:
        return text
    if len(starts) > 1:
        raise SystemExit(f"kit_only: {where}: {KEY} appears {len(starts)} times")
    first = starts[0]
    while first > 0 and lines[first - 1].startswith("#"):
        first -= 1
    last = starts[0] + 1
    # The body is every following indented or blank line up to the next
    # top-level line; trailing blanks are handled below.
    while last < len(lines) and (lines[last][:1] in (" ", "\t") or not lines[last].strip()):
        last += 1
    while last > starts[0] + 1 and not lines[last - 1].strip():
        last -= 1
    if last < len(lines) and not lines[last].strip():
        last += 1
    elif last == len(lines) and first > 0 and not lines[first - 1].strip():
        first -= 1  # the key ended the file: drop the blank line before it
    return "".join(lines[:first] + lines[last:])


def apply(root: Path, ctx) -> None:
    routines = root / "docs" / "routines"
    for path in sorted(routines.glob("*.md")) if routines.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        new = strip_blocks(text, path.relative_to(root).as_posix())
        if new != text:
            path.write_text(new, encoding="utf-8")
    path = root / "repos.yml"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        new = strip_key(text, "repos.yml")
        if new != text:
            path.write_text(new, encoding="utf-8")
