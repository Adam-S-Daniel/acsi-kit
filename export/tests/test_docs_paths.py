"""Every file path a hand-written page names exists in the kit.

The pages (docs/*.md, README.md, bootstrap/README.md) are not generated, but
they name files in starter/, which the daily re-sync changes without touching
them. Pages named `codex-session-start.sh` and `dashboard/tasks/merge-relay.md`
for days after the re-sync dropped them (acsi-kit#73). This fails the re-sync
pull request that removes a file a page still names, and any edit that
introduces a typo.

What is checked (Markdown is parsed with markdown-it-py, never scanned with a
regex; fenced and indented code blocks are NOT checked, they hold commands and
sample output):

* Relative link targets (`[x](../starter/y.md#frag)`, images too): resolved
  against the page's directory, fragment and query dropped; must be a tracked
  file or directory. `http(s):`, `mailto:` and any other scheme, and
  fragment-only links, are skipped.
* Inline code spans that look like a path (see `looks_like_path`): after
  dropping a leading `./`, the span has no whitespace and none of
  `< > * $ \\ | = : ' " , ( ) { }`, does not start with `~`, `/`, `-`, `@`, `..`
  or `http`, is not the placeholder `owner/name`, an upstream repository (`UPSTREAM_REPOS`) or a branch name with a known
  prefix (`BRANCH_PREFIXES`), and either contains a `/` or ends in a known file
  extension (`EXTENSIONS`).

A path-like span resolves when it names a tracked file or directory under one
of the search roots: the kit root; `docs/`; `bootstrap/`; `export/`; the
page's own directory; or any `starter/<name>/` tree (so `evals/budget.yml`
finds `starter/skills-evals/evals/budget.yml`). A bare file name (no `/`)
also resolves when a tracked file of that name exists anywhere in the kit
(`eval.yml` finds `starter/skills-evals/.github/workflows/eval.yml`,
`skills-bootstrap.sh` finds the copy under any `.claude/hooks/`), so does a
bare directory (`bin/`) when any tracked directory has that name, and a bare
`name` resolves when `name.example` is tracked (`fleet.env` is the adopter's
copy of `fleet.env.example`, never committed). "Tracked"
means `git ls-files`, so an untracked local file never hides a miss.

Paths that are real but live outside the kit (the adopter's own machine or
repositories, files created at run time) go in docs_paths_allow.txt; paths
that are genuinely wrong today and await a page fix go in
docs_paths_known_misses.txt. Both use `<page>: <span>  # reason`, and both are
stale-checked: an entry whose span is no longer a miss on that page fails.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parents[2]
ALLOW = KIT / "export" / "tests" / "docs_paths_allow.txt"
KNOWN = KIT / "export" / "tests" / "docs_paths_known_misses.txt"

EXTENSIONS = (".md", ".yml", ".yaml", ".sh", ".py", ".js", ".json", ".ps1", ".txt", ".env", ".html")
# A span starting with one of these is a branch name, not a file.
BRANCH_PREFIXES = (
    "persistent/", "claude/", "agent/", "retire-skill/", "article-lift/",
    "hook-pin-bump/", "regenerate/", "roster/", "origin/",
)
# `owner/name` spans naming upstream GitHub repositories.
UPSTREAM_REPOS = ("anthropics/", "openai/")
FIXED_ROOTS = ("", "docs", "bootstrap", "export")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FORBIDDEN = re.compile(r"[\s<>*$\\|=:'\",(){}]")


# ---------------------------------------------------------------- pure rules


def looks_like_path(span: str) -> bool:
    """True when an inline code span should name a file or directory."""
    s = span[2:] if span.startswith("./") else span
    if not s or FORBIDDEN.search(s):
        return False
    if s.startswith(("~", "/", "-", "@", "..", "http")) or s == "owner/name":
        return False
    if s.startswith(BRANCH_PREFIXES) or s.startswith(UPSTREAM_REPOS):
        return False
    return "/" in s or s.endswith(EXTENSIONS)


class Tree:
    """The set of tracked files and directories, plus a name index."""

    def __init__(self, files):
        self.files = {PurePosixPath(f).as_posix() for f in files}
        self.dirs = {""}
        for f in self.files:
            for parent in PurePosixPath(f).parents:
                self.dirs.add(parent.as_posix() if parent.as_posix() != "." else "")
        self.names = {PurePosixPath(f).name for f in self.files}
        self.dir_names = {PurePosixPath(d).name for d in self.dirs if d}
        self.starters = sorted(
            d for d in self.dirs
            if d.startswith("starter/") and d.count("/") == 1
        )

    def exists(self, path: str) -> bool:
        norm = PurePosixPath(path).as_posix()
        norm = "" if norm == "." else norm
        return norm in self.files or norm in self.dirs

    def roots(self, page_dir: str) -> list[str]:
        return [*FIXED_ROOTS, page_dir, *self.starters]


def resolve_span(span: str, page: str, tree: Tree) -> bool:
    s = span[2:] if span.startswith("./") else span
    s = s.rstrip("/")
    page_dir = PurePosixPath(page).parent.as_posix()
    page_dir = "" if page_dir == "." else page_dir
    for root in tree.roots(page_dir):
        if tree.exists(str(PurePosixPath(root) / s)):
            return True
    if "/" in s:
        return False
    if s in tree.names or f"{s}.example" in tree.names:
        return True  # `fleet.env` is the adopter's copy of tracked `fleet.env.example`
    return span.endswith("/") and s in tree.dir_names


def resolve_link(target: str, page: str, tree: Tree) -> bool:
    """A relative link target, resolved against the page's directory."""
    path = unquote(re.split(r"[#?]", target, maxsplit=1)[0])
    if not path:
        return True
    base = PurePosixPath(page).parent
    parts: list[str] = []
    for part in (base / path).parts:
        if part == "..":
            if not parts:
                return False
            parts.pop()
        elif part != ".":
            parts.append(part)
    return tree.exists("/".join(parts))


def is_relative_link(target: str) -> bool:
    return bool(target) and not target.startswith("#") and not SCHEME.match(target)


def find_refs(text: str):
    """Yield (line, kind, value) for each link target and code span."""
    md = MarkdownIt()

    for tok in md.parse(text):
        if tok.type == "inline" and tok.map:
            line = tok.map[0] + 1
            for child in tok.children or []:
                if child.type in ("softbreak", "hardbreak"):
                    line += 1
                elif child.type == "code_inline":
                    yield line, "span", child.content
                elif child.type in ("link_open", "image"):
                    href = child.attrGet("href") or child.attrGet("src") or ""
                    if is_relative_link(href):
                        yield line, "link", href


def find_misses(text: str, page: str, tree: Tree) -> list[tuple[int, str]]:
    """The (line, value) of each unresolved link or path-like span."""
    out = []
    for line, kind, value in find_refs(text):
        if kind == "link":
            ok = resolve_link(value, page, tree)
        elif looks_like_path(value):
            ok = resolve_span(value, page, tree)
        else:
            continue
        if not ok:
            out.append((line, value))
    return out


def parse_entries(path: Path) -> dict[tuple[str, str], str]:
    """`<page>: <span>  # reason` lines; blank lines and `#` lines skipped."""
    entries: dict[tuple[str, str], str] = {}
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        body, sep, reason = raw.partition("  # ")
        page, colon, span = body.partition(": ")
        if not (colon and sep and page.strip() and span.strip() and reason.strip()):
            raise ValueError(f"{path.name}:{n}: want `<page>: <span>  # reason`, got {raw!r}")
        entries[(page.strip(), span.strip())] = reason.strip()
    return entries


# ------------------------------------------------------------------ the kit


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=KIT, check=True, capture_output=True, text=True
    ).stdout
    return [f for f in out.split("\0") if f]


def page_list() -> list[str]:
    docs = sorted(p.relative_to(KIT).as_posix() for p in (KIT / "docs").glob("*.md"))
    return [*docs, "README.md", "bootstrap/README.md"]


PAGES = page_list()
TREE = Tree(tracked_files())
MISSES = {
    page: find_misses((KIT / page).read_text(encoding="utf-8"), page, TREE)
    for page in PAGES
}
ALLOWED = parse_entries(ALLOW)
KNOWN_MISSES = parse_entries(KNOWN)


@pytest.mark.parametrize("page", PAGES)
def test_page_names_only_existing_paths(page):
    expected = {span for (p, span) in [*ALLOWED, *KNOWN_MISSES] if p == page}
    bad = [(ln, span) for ln, span in MISSES[page] if span not in expected]
    assert not bad, (
        "paths named but not in the kit (fix the page, or if the path is real "
        "but outside the kit add it to export/tests/docs_paths_allow.txt):\n"
        + "\n".join(f"{page}:{ln}: `{span}`" for ln, span in bad)
    )


@pytest.mark.parametrize("name,entries", [("allowlist", ALLOWED), ("known misses", KNOWN_MISSES)])
def test_entries_are_not_stale(name, entries):
    stale = [
        f"{page}: {span}" for (page, span) in entries
        if page not in MISSES or span not in {s for _, s in MISSES[page]}
    ]
    assert not stale, (
        f"{name} entries that no page misses any more (delete them):\n" + "\n".join(stale)
    )


def test_allowlist_and_known_misses_are_disjoint():
    assert not set(ALLOWED) & set(KNOWN_MISSES)


# ------------------------------------------------------------ rule unit tests


@pytest.mark.parametrize("span", [
    "docs/rules.md", "evals/budget.yml", "eval.yml", "scripts/", "./fleet.env",
    "bootstrap/copy-starter.sh", ".githooks/agent-checks", "AGENTS.md",
])
def test_path_like(span):
    assert looks_like_path(span)


@pytest.mark.parametrize("span", [
    "git status", "persistent/eval-results", "claude/eval-*", "<you>/repo-settings",
    "~/.claude/settings.json", "/adopt", "--dry-run", "https://x.example.com/a.md",
    "anthropics/claude-code", "origin/main", "a.md b.md", "$HOME/x.sh", "KEY=a/b",
    "..", "../docs/x.md", "plain", "repo:you/x", "bash x.sh --flag", "weekly_cap",
])
def test_not_path_like(span):
    assert not looks_like_path(span)


def make_tree(tmp_path: Path, files: list[str]) -> Tree:
    for f in files:
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return Tree(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())


def test_resolver_roots_and_names(tmp_path):
    tree = make_tree(tmp_path, [
        "README.md", "docs/a.md", "bootstrap/lib/common.sh",
        "starter/evals/evals/budget.yml", "starter/evals/.github/workflows/eval.yml",
    ])
    page = "docs/a.md"
    assert resolve_span("docs/a.md", page, tree)
    assert resolve_span("lib/common.sh", page, tree)          # bootstrap/ root
    assert resolve_span("evals/budget.yml", page, tree)       # a starter tree
    assert resolve_span("evals/", page, tree)                 # directory
    assert resolve_span("eval.yml", page, tree)               # bare name, anywhere
    assert not resolve_span("lib/missing.sh", page, tree)
    assert not resolve_span("gone.sh", page, tree)
    assert not resolve_span("dashboard/tasks/merge-relay.md", page, tree)


def test_resolve_link(tmp_path):
    tree = make_tree(tmp_path, ["docs/a.md", "docs/b.md", "starter/x/README.md"])
    assert resolve_link("b.md#frag", "docs/a.md", tree)
    assert resolve_link("../starter/x/README.md", "docs/a.md", tree)
    assert resolve_link("../starter/x/", "docs/a.md", tree)
    assert not resolve_link("c.md", "docs/a.md", tree)
    assert not resolve_link("../../outside.md", "docs/a.md", tree)


def test_missing_path_reported_with_line_number(tmp_path):
    tree = make_tree(tmp_path, ["docs/p.md", "docs/real.md"])
    text = (
        "# Title\n\nSee `docs/real.md` and\n`codex-session-start.sh` here.\n\n"
        "```\n`docs/in-a-fence-is-ignored.md`\n```\n\n"
        "A [dead](missing.md#x) link, a [web](https://example.com/a.md), "
        "an [anchor](#top).\n"
    )
    assert find_misses(text, "docs/p.md", tree) == [
        (4, "codex-session-start.sh"),
        (10, "missing.md#x"),
    ]


def test_parse_entries_requires_a_reason(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("# c\n\ndocs/a.md: x.env  # outside the kit\n", encoding="utf-8")
    assert parse_entries(f) == {("docs/a.md", "x.env"): "outside the kit"}
    f.write_text("docs/a.md: x.env\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_entries(f)
    f.write_text("docs/a.md: x.env  #   \n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_entries(f)
