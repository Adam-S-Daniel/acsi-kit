#!/usr/bin/env python3
"""resync.py: move each manifest's pinned source commit to its repo's current head.

Usage:
  python3 resync.py --owner OWNER [--manifests DIR] [--skip REPO ...] [--summary FILE]

For every manifest under DIR (default: manifests/ beside this script), except
those --skip names (default: agentskills-private, whose source is private),
the source repo's default-branch head is read with
`git ls-remote https://github.com/OWNER/<source>.git HEAD`, with no
credential, and the manifest's `source_sha` (and the `sha` of every `imports`
entry from that same repo) is rewritten in place. The edit replaces only the
sha text, found from the YAML parser's own positions, so comments and layout
stay as they were. Imports from other repos keep their pins.

Prints one line per source, `<repo>: <old12> -> <new12>` or
`<repo>: unchanged`, and writes a Markdown table (repo, old, new, compare
link) to --summary. Exits 0 when it ran, whether or not anything moved; 2 on
a bad argument or manifest; 1 when a head could not be read.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MANIFESTS = HERE / "manifests"
# The same shapes fetch_sources.py accepts.
OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
NAME = re.compile(r"[A-Za-z0-9._-]{1,100}")
SHA = re.compile(r"[0-9a-f]{40}")


class ResyncError(Exception):
    pass


class HeadError(ResyncError):
    """A source's head could not be read (exit 1, not a usage error)."""


def check_name(repo: str) -> str:
    if not isinstance(repo, str) or not NAME.fullmatch(repo) or repo in (".", ".."):
        raise ResyncError(f"unsafe source repo name {repo!r}")
    return repo


def check_sha(sha, where: str) -> str:
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ResyncError(f"{where}: not a full sha: {sha!r}")
    return sha


def git_ls_remote(owner: str, repo: str) -> str:
    """The head sha of OWNER/REPO's default branch, read with no credential."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")  # a private repo fails, never prompts
    out = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{owner}/{repo}.git", "HEAD"],
        capture_output=True, text=True, env=env, timeout=120)
    if out.returncode != 0:
        raise HeadError(f"{repo}: git ls-remote failed (exit {out.returncode})")
    for line in out.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref == "HEAD":
            return sha
    raise HeadError(f"{repo}: git ls-remote returned no HEAD")


def _value(mapping: yaml.MappingNode, key: str):
    for k, v in mapping.value:
        if isinstance(k, yaml.ScalarNode) and k.value == key:
            return v
    return None


def sha_spans(text: str, name: str):
    """(manifest repo key, source repo, [(start, end, sha)]) for the pins resync owns.

    The spans are the source_sha scalar and the `sha` scalar of each import
    from the same repo, as character offsets into text.
    """
    root = yaml.compose(text)
    if not isinstance(root, yaml.MappingNode):
        raise ResyncError(f"{name}: not a mapping")
    repo_node = _value(root, "repo")
    if not isinstance(repo_node, yaml.ScalarNode):
        raise ResyncError(f"{name}: no `repo:` key")
    source_node = _value(root, "source")
    source = check_name(source_node.value if isinstance(source_node, yaml.ScalarNode) else repo_node.value)
    nodes = [_value(root, "source_sha")]
    imports = _value(root, "imports")
    if isinstance(imports, yaml.SequenceNode):
        for item in imports.value:
            if not isinstance(item, yaml.MappingNode):
                continue
            imp_repo = _value(item, "repo")
            if isinstance(imp_repo, yaml.ScalarNode) and imp_repo.value == source:
                nodes.append(_value(item, "sha"))
    spans = []
    for node in nodes:
        if not isinstance(node, yaml.ScalarNode):
            raise ResyncError(f"{name}: a sha for {source} is missing or not a plain value")
        sha = check_sha(node.value, name)
        start, end = node.start_mark.index, node.end_mark.index
        # A quoted scalar's span includes its quotes; edit only the sha inside.
        at = text.find(sha, start, end)
        if at < 0:
            raise ResyncError(f"{name}: cannot find the sha text for {source}")
        spans.append((at, at + len(sha), sha))
    return repo_node.value, source, spans


def rewrite(text: str, spans, new: str) -> str:
    for start, end, _ in sorted(spans, reverse=True):
        text = text[:start] + new + text[end:]
    return text


def resync(manifests_dir: Path, owner: str, ls_remote=git_ls_remote, skip=("agentskills-private",)):
    """Rewrite the manifests in place; [(source repo, old sha, new sha)], one per manifest."""
    if not OWNER.fullmatch(owner):
        raise ResyncError(f"not a GitHub owner: {owner!r}")
    parsed = []
    for path in sorted(manifests_dir.glob("*.yml")):
        if path.name == "_common.yml":
            continue
        text = path.read_text(encoding="utf-8")
        parsed.append((path, text, *sha_spans(text, path.name)))
    unknown = sorted(set(skip) - {key for _, _, key, _, _ in parsed})
    if unknown:
        raise ResyncError(f"no manifest for {' '.join(unknown)}")
    plans = [p for p in parsed if p[2] not in skip]
    # Read every head before writing anything, so a failed read leaves the
    # manifests as they were.
    heads: dict[str, str] = {}
    for _, _, _, source, _ in plans:
        if source not in heads:
            heads[source] = check_sha(ls_remote(owner, source), f"{source} head")
    results = []
    for path, text, _, source, spans in plans:
        new = heads[source]
        updated = rewrite(text, spans, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
        results.append((source, spans[0][2], new))
    return results


def summary_markdown(owner: str, results) -> str:
    lines = ["| Repo | Old | New | Compare |", "|---|---|---|---|"]
    for repo, old, new in results:
        if old == new:
            lines.append(f"| `{repo}` | `{old[:12]}` | unchanged | |")
        else:
            url = f"https://github.com/{owner}/{repo}/compare/{old}...{new}"
            lines.append(f"| `{repo}` | `{old[:12]}` | `{new[:12]}` | [compare]({url}) |")
    return "\n".join(lines) + "\n"


def main(argv=None, ls_remote=git_ls_remote) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--owner", required=True, help="the GitHub owner the sources live under")
    ap.add_argument("--manifests", type=Path, default=MANIFESTS, help="the manifests folder to rewrite")
    ap.add_argument("--skip", nargs="*", default=["agentskills-private"],
                    help="manifest repo names to leave alone (a private source cannot be read without a credential)")
    ap.add_argument("--summary", type=Path, help="write the Markdown summary table here")
    args = ap.parse_args(argv)
    try:
        results = resync(args.manifests, args.owner, ls_remote, skip=tuple(args.skip))
    except ResyncError as exc:
        print(f"resync.py: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, HeadError) else 2
    for repo, old, new in results:
        print(f"{repo}: unchanged" if old == new else f"{repo}: {old[:12]} -> {new[:12]}")
    if args.summary:
        args.summary.write_text(summary_markdown(args.owner, results), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
