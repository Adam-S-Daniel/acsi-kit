#!/usr/bin/env python3
"""coverage_fleet.py <check|add> <repos.yml> <label> <repo name>

`_agent-guidance`'s repos.yml lists, under `cron_coverage.fleet`, the repos
the audits expect to find: the daily Dependabot health check fails on a name
neither owner has, the fleet worker attaches each one, and the prompt-audit
sweep reads each one. The starter's list leaves `skills-evals` out, because a
base-only setup has no such repo (export/DECISIONS.md, "Pro plan values and
small fixes"). regenerate.sh's evals-fleet task puts it there once the evals
track has created the repo:

  check   exit 0 when the list names <repo name>; exit 1 with one
          "NOT DONE: ..." line when it does not.
  add     put `- <repo name>` in the list; a list that already names it is
          left as it is. The starter's list holds the repo's place with a
          comment ("# <repo name> is not listed while ..."): the name
          replaces that comment, so the file does not go on saying the repo
          is not listed. A list without the comment gets the name after its
          last element. The result is parsed again, and nothing is written
          unless the list is the old one plus that name, in that place, and
          the rest of the document is unchanged.

The list is found by parsing the file with PyYAML (`cron_coverage` must be a
mapping whose `fleet` is a block sequence of plain names); the edit is made
at the line the parser gives for the last element, so comments stay where
they are (but for the one the name replaces). <label> is how messages name the file. A file of another shape is
an error (exit 2, one "ERROR: <label>: ..." line), never a skip.
"""
import copy
import re
import sys

NAME = re.compile(r"[A-Za-z0-9._-]{1,100}")
#: How the comment that holds a repo's place begins, after "# <name> ".
#: export/patches/_agent-guidance/kit_repos.py writes it into the starter.
MARKER = "is not listed while"


class ShapeError(Exception):
    """The file does not hold the list this looks for."""


def _fleet_node(text):
    import yaml
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as e:
        raise ShapeError(f"is not valid YAML ({type(e).__name__})") from None

    def child(node, key):
        if not isinstance(node, yaml.MappingNode):
            return None
        return next((v for k, v in node.value if isinstance(k, yaml.ScalarNode) and k.value == key), None)

    fleet = child(child(root, "cron_coverage"), "fleet")
    if not isinstance(fleet, yaml.SequenceNode) or fleet.flow_style or not fleet.value:
        raise ShapeError("has no cron_coverage.fleet block list with at least one name")
    if not all(isinstance(v, yaml.ScalarNode) and NAME.fullmatch(v.value) for v in fleet.value):
        raise ShapeError("has a cron_coverage.fleet element that is not a plain repo name")
    return fleet


def names(text):
    """The repo names under cron_coverage.fleet, in order."""
    return [v.value for v in _fleet_node(text).value]


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _marker(lines, fleet, name):
    """(first, last) line indexes of the comment that holds `name`'s place in
    the list, or None. The starter writes it where the source lists the repo:
    a run of comment lines among the elements (or right under the last) whose first begins
    "# <name> is not listed while ...". A comment indented less than the
    elements' `-` is not the list's: it belongs to what follows (the next
    key's comment, with no blank line before it), and is never taken."""
    first, last = fleet.value[0].start_mark.line, fleet.value[-1].start_mark.line
    dash = _indent(lines[last])
    while (last + 1 < len(lines) and lines[last + 1].strip().startswith("#")
           and _indent(lines[last + 1]) >= dash):
        last += 1                       # comments right under the last element belong to the list too
    for n in range(first, last + 1):
        if lines[n].strip().startswith(f"# {name} {MARKER}"):
            end = n
            while (end + 1 <= last and lines[end + 1].strip().startswith("#")
                   and _indent(lines[end + 1]) >= _indent(lines[n])):
                end += 1
            return n, end
    return None


def add(text, name):
    """The text with `name` in cron_coverage.fleet (unchanged when it is
    there): in place of the comment that marks its place when the list has
    one, else after the last element. Every other line, comments included,
    stays as it is."""
    import yaml
    fleet = _fleet_node(text)
    have = [v.value for v in fleet.value]
    if name in have:
        return text
    last = fleet.value[-1]
    lines = text.split("\n")
    line = lines[last.start_mark.line]
    m = re.fullmatch(r"(\s*)- " + re.escape(last.value) + r"\s*(#.*)?", line)
    if not m:
        raise ShapeError(f"writes the last cron_coverage.fleet element in a form this cannot extend: {line.strip()[:60]!r}")
    entry = f"{m.group(1)}- {name}"
    mark = _marker(lines, fleet, name)
    if mark:
        at = sum(v.start_mark.line < mark[0] for v in fleet.value)   # the elements above the comment
        lines[mark[0]:mark[1] + 1] = [entry]
    else:
        at = len(have)
        lines.insert(last.start_mark.line + 1, entry)
    new = "\n".join(lines)
    want = copy.deepcopy(yaml.safe_load(text))
    want["cron_coverage"]["fleet"] = have[:at] + [name] + have[at:]
    if yaml.safe_load(new) != want:
        raise ShapeError("the edit would change something other than the list, so nothing was written")
    return new


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 4 or argv[0] not in ("check", "add") or not NAME.fullmatch(argv[3]):
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    cmd, path, label, name = argv
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR: {label}: cannot be read ({type(e).__name__})", file=sys.stderr)
        return 2
    try:
        if cmd == "check":
            if name in names(text):
                return 0
            print(f"NOT DONE: {label} cron_coverage.fleet does not name {name}")
            return 1
        new = add(text, name)
        if new != text:
            with open(path, "wb") as f:   # in place: the file keeps its mode
                f.write(new.encode("utf-8"))
    except ShapeError as e:
        print(f"ERROR: {label}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
