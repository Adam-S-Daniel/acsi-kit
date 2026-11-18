"""Generated regions and held lists in docs/ follow their sources in starter/.

A daily re-sync changes starter/ and the pages drift (docs/routines.md once
quoted the fleet worker's prompt "exactly" after the spec gained a sentence).
Two kinds of drift are mechanical, and this fails until the page follows:

- text a page quotes from a starter file is a generated region, rewritten by
  `python3 export/doc_regions.py --write`;
- a list a page repeats (the agent-checks table, the by-hand variables and
  secrets) must name the same items as its source. The descriptions beside
  each item stay hand-written, so only the sets are compared.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KIT / "export"))
import doc_regions  # noqa: E402


# ── The generator, on fixtures ──────────────────────────────────────────────

SPEC = """\
# A routine

- **Prompt, exactly:**

  > Read and follow `docs/x.md` in
  > `example-adopter/_agent-guidance` (origin/main). Go.

Prose after.
"""

PAGE = """\
# Page

<!-- generated:fleet-worker-prompt by export/doc_regions.py; edit the spec, then run it with --write -->
> old text
<!-- /generated:fleet-worker-prompt -->

Tail.
"""


def spec_path(name="fleet-worker-prompt"):
    return doc_regions.REGIONS[name][1]


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """A kit with one region, the fleet worker's, and the others dropped."""
    name = "fleet-worker-prompt"
    monkeypatch.setattr(doc_regions, "REGIONS", {name: doc_regions.REGIONS[name]})
    # The test spec has one prompt, under the default anchor.
    monkeypatch.setattr(doc_regions, "ANCHORS", {})
    page, spec = doc_regions.REGIONS[name]
    (tmp_path / page).parent.mkdir(parents=True)
    (tmp_path / spec).parent.mkdir(parents=True)
    (tmp_path / page).write_text(PAGE, encoding="utf-8")
    (tmp_path / spec).write_text(SPEC, encoding="utf-8")
    return tmp_path


def test_extracts_the_blockquote_after_the_anchor():
    assert doc_regions.extract_prompt(SPEC, "spec.md") == [
        "Read and follow `docs/x.md` in `example-adopter/_agent-guidance` (origin/main). Go."]


def test_a_spec_with_no_block_fails_naming_it():
    with pytest.raises(doc_regions.RegionError, match=r"spec\.md.*found 0"):
        doc_regions.extract_prompt("# A routine\n\n> a quote, no anchor\n", "spec.md")


def test_a_spec_with_two_blocks_fails_naming_it():
    with pytest.raises(doc_regions.RegionError, match=r"spec\.md.*found 2"):
        doc_regions.extract_prompt(SPEC + "\nPrompt, exactly:\n\n> two\n", "spec.md")


def test_an_anchor_with_no_blockquote_fails():
    with pytest.raises(doc_regions.RegionError, match="no blockquote"):
        doc_regions.extract_prompt("Prompt, exactly: nothing.\n", "spec.md")


def test_the_owner_becomes_the_pages_placeholder():
    lines = doc_regions.render(["see example-adopter/repo and example-adopter/other"])
    assert lines == ["> see <you>/repo and <you>/other"]


def test_wrapping_stays_within_the_width_and_never_breaks_words():
    long_word = "x" * 90
    para = " ".join(["word-with-hyphens"] * 12) + " " + long_word + " tail"
    lines = doc_regions.render([para])
    assert all(l.startswith("> ") for l in lines)
    assert all(len(l) <= doc_regions.WIDTH for l in lines if long_word not in l)
    assert any(l == "> " + long_word for l in lines)
    assert " ".join(l[2:] for l in lines) == para
    assert all("word-with-hyphens" in l or l.endswith(("tail", long_word)) for l in lines)


def test_indentation_counts_toward_the_width_and_prefixes_every_line():
    para = " ".join(["word"] * 40)
    lines = doc_regions.render([para], indent="  ")
    assert len(lines) > 1
    assert all(l.startswith("  > ") and len(l) <= doc_regions.WIDTH for l in lines)


def test_paragraphs_are_separated_by_an_empty_quote_line():
    assert doc_regions.render(["one", "two"], "  ") == ["  > one", "  >", "  > two"]


def test_a_stale_region_fails_check_naming_the_region(kit, capsys):
    assert doc_regions.main(["--check", "--root", str(kit)]) == 1
    out = capsys.readouterr().out
    assert "region 'fleet-worker-prompt'" in out
    assert "\n-> old text\n" in out  # the diff shows the old line
    assert (kit / "docs/routines.md").read_text(encoding="utf-8") == PAGE  # --check never writes


def test_write_fixes_the_region_and_is_idempotent(kit):
    page = kit / "docs" / "routines.md"
    assert doc_regions.main(["--write", "--root", str(kit)]) == 0
    first = page.read_text(encoding="utf-8")
    assert "\n> old text\n" not in first
    assert "(origin/main). Go.\n" in first and "<you>/_agent-guidance" in first
    assert first.startswith("# Page\n\n<!-- generated:") and first.endswith("Tail.\n")
    assert doc_regions.main(["--write", "--root", str(kit)]) == 0
    assert page.read_text(encoding="utf-8") == first
    assert doc_regions.main(["--check", "--root", str(kit)]) == 0


def test_an_indented_region_keeps_its_indentation(kit):
    page = kit / "docs" / "routines.md"
    page.write_text(PAGE.replace("<!--", "  <!--").replace("> old", "  > old"), encoding="utf-8")
    assert doc_regions.main(["--write", "--root", str(kit)]) == 0
    body = page.read_text(encoding="utf-8").split("\n")[3:-4]
    assert body and all(l.startswith("  > ") for l in body), body
    assert doc_regions.main(["--check", "--root", str(kit)]) == 0


def test_a_marker_with_no_source_is_an_error(kit, capsys):
    page = kit / "docs" / "routines.md"
    page.write_text(PAGE + PAGE.replace("fleet-worker-prompt", "mystery"), encoding="utf-8")
    assert doc_regions.main(["--check", "--root", str(kit)]) == 2
    assert "'mystery' has no known source" in capsys.readouterr().err


def test_a_known_region_missing_from_the_page_is_an_error(kit, capsys):
    (kit / "docs" / "routines.md").write_text("# Page\n", encoding="utf-8")
    assert doc_regions.main(["--check", "--root", str(kit)]) == 2
    assert "'fleet-worker-prompt' is missing" in capsys.readouterr().err


def test_a_spec_with_two_blocks_exits_2_naming_the_spec(kit, capsys):
    (kit / spec_path()).write_text(SPEC + "\nPrompt, exactly:\n\n> two\n", encoding="utf-8")
    assert doc_regions.main(["--check", "--root", str(kit)]) == 2
    assert spec_path() in capsys.readouterr().err


def test_an_unclosed_region_is_an_error(kit):
    page = kit / "docs" / "routines.md"
    page.write_text(PAGE.replace("<!-- /generated:fleet-worker-prompt -->\n", ""), encoding="utf-8")
    assert doc_regions.main(["--check", "--root", str(kit)]) == 2


# ── The real pages ──────────────────────────────────────────────────────────

def test_every_generated_region_in_the_docs_follows_its_spec():
    stale = doc_regions.process(KIT, write=False)
    assert not stale, ("a docs region is stale: run `python3 export/doc_regions.py --write`\n\n"
                       + "\n\n".join(stale))


# ── Held lists: the page and its source agree as sets ───────────────────────

def agree(page_name, page, source_name, source, allowed_extra=frozenset()):
    missing, extra = sorted(source - page), sorted(page - source - allowed_extra)
    assert not missing and not extra, (
        f"{page_name} and {source_name} name different items.\n"
        f"  missing from {page_name} (in the source): {missing}\n"
        f"  on {page_name} but not in the source: {extra}")


def md_tokens(path: Path):
    return MarkdownIt("commonmark").enable("table").parse(path.read_text(encoding="utf-8"))


def code_spans(inline) -> list[str]:
    return [c.content for c in inline.children or [] if c.type == "code_inline"]


KEBAB = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
#: Added to a repo's runner from library/git-hooks/rules-dir, which the kit
#: does not export, so the runner script never names it: allowed on the page,
#: not required of the source.
LIBRARY_CHECKS = frozenset({"rules-dir"})
#: The hook for a repo's own checks, which the page describes in prose.
NOT_A_CHECK = frozenset({"repo-local"})


def runner_check_ids() -> set[str]:
    """The ids the runner records: literal `note_ran <id>` tokens, not comments or `note_ran "$id"`."""
    text = (KIT / "starter/agent-guidance/templates/agent-checks/agent-checks").read_text(encoding="utf-8")
    ids = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        ids.update(re.findall(r"\bnote_ran\s+([a-z][a-z0-9-]*)(?=\s|;|$)", line))
    return ids - NOT_A_CHECK


def guidance_page_check_ids() -> set[str]:
    """The first column of the checks table, plus the ids the sentence after it names."""
    toks = md_tokens(KIT / "docs/guidance.md")
    tables = [i for i, t in enumerate(toks) if t.type == "table_open"
              and any(c.content == "Check" for c in toks[i:i + 8] if c.type == "inline")]
    assert len(tables) == 1, "docs/guidance.md should have exactly one table headed 'Check'"
    start = tables[0]
    end = next(i for i in range(start, len(toks)) if toks[i].type == "table_close")
    ids, first = set(), True
    for i in range(start, end):
        if toks[i].type == "tr_open":
            first = True
        elif toks[i].type in ("th_open", "td_open"):
            if first and toks[i].type == "td_open":
                ids.update(code_spans(toks[i + 1]))
            first = False
    after = next(i for i in range(end, len(toks)) if toks[i].type == "inline")
    ids.update(s for s in code_spans(toks[after]) if KEBAB.match(s))
    return ids


def test_the_checks_table_names_the_checks_the_runner_records():
    agree("docs/guidance.md", guidance_page_check_ids(),
          "the agent-checks runner (note_ran)", runner_check_ids(), allowed_extra=LIBRARY_CHECKS)


def test_the_runner_scan_sees_the_known_ids():
    # The scan is lexical; this fails if the runner's shape moves out from under it.
    assert {"skill-shell", "secret-file", "pr-tldr", "dated-phrasing"} <= runner_check_ids()
    assert "repo-local" not in runner_check_ids()


BY_HAND_PREFIXES = ("SITE_", "ARTICLE_WATCH_", "PROMPT_AUDIT_SWEEP_", "FLEET_WORKER_FIRE_")
NAME = re.compile(r"^[A-Z][A-Z0-9_]+$")


def by_hand_names() -> set[str]:
    """The list items "- `NAME`: ..." under bootstrap/README.md's "Variables and secrets set by hand"."""
    toks = md_tokens(KIT / "bootstrap/README.md")
    start = next(i for i, t in enumerate(toks) if t.type == "heading_open" and t.tag == "h2"
                 and toks[i + 1].content == "Variables and secrets set by hand")
    names = set()
    for i in range(start + 1, len(toks)):
        t = toks[i]
        if t.type == "heading_open" and t.tag == "h2":
            break
        if t.type == "list_item_open":
            inline = next(x for x in toks[i:] if x.type == "inline")
            first = inline.children[0] if inline.children else None
            if first is not None and first.type == "code_inline" and NAME.match(first.content):
                names.add(first.content)
    return names


def script_set_names() -> set[str]:
    """Names a bootstrap script sets, from lib/common.sh's registries (as check-refs.py reads them)."""
    def registry(name):
        out = subprocess.run(["bash", "-c", f'. "$1/lib/common.sh"; printf "%s\\n" "${{{name}[@]}}"',
                              "_", str(KIT / "bootstrap")], capture_output=True, text=True, check=True).stdout
        return [line.split("|") for line in out.splitlines() if line]
    names = set()
    for _app, _perms, _inst, _repo, idspec, _env, sec, _key, _opt in registry("APPS"):
        names.update((idspec.split(":", 1)[1], sec))
    names.update(r[3] for r in registry("OTHER_VALUES"))
    names.update(r[1] for r in registry("REPO_VARIABLES"))
    return names


def routines_page_names() -> set[str]:
    names = set()
    for t in md_tokens(KIT / "docs/routines.md"):
        if t.type == "inline":
            names.update(s for s in code_spans(t) if NAME.match(s) and s.startswith(BY_HAND_PREFIXES))
    return names


def test_the_routines_page_names_the_by_hand_variables_and_secrets():
    source = {n for n in by_hand_names() if n.startswith(BY_HAND_PREFIXES)}
    assert source, "bootstrap/README.md lists no by-hand name with a site, article, sweep or worker prefix"
    agree("docs/routines.md", routines_page_names(), "bootstrap/README.md 'set by hand' (or a bootstrap script)",
          source, allowed_extra=script_set_names())


def test_a_spec_with_two_prompts_gives_each_region_its_own():
    spec = (
        "- **Fleet prompt, exactly:**\n\n  > one\n\n"
        "- **Loop prompt, exactly:**\n\n  > two\n"
    )
    assert doc_regions.extract_prompt(spec, "s.md", "Fleet prompt, exactly") == ["one"]
    assert doc_regions.extract_prompt(spec, "s.md", "Loop prompt, exactly") == ["two"]
    assert {"fleet-worker-prompt", "loop-worker-prompt"} <= set(doc_regions.ANCHORS)
