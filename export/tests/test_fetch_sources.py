"""fetch_sources.py's plan: what CI fetches for `export.py --check`.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPORT_DIR))
_spec = importlib.util.spec_from_file_location("kit_fetch_sources", EXPORT_DIR / "fetch_sources.py")
fetch_sources = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_sources)
export = fetch_sources.export

SHA_A, SHA_B, SHA_C = "a" * 40, "b" * 40, "c" * 40


def test_the_plan_names_every_source_and_import_at_its_pinned_sha():
    manifests = export.load_manifests()
    got = fetch_sources.plan(manifests)
    for name, m in manifests.items():
        assert m["source_sha"] in got[m.get("source", name)], name
        for imp in m.get("imports") or []:
            assert imp["sha"] in got[imp["repo"]], (name, imp["path"])


def test_skip_leaves_out_only_that_manifests_source():
    manifests = {
        "one": {"repo": "one", "source": "src-one", "source_sha": SHA_A,
                "imports": [{"repo": "lib", "sha": SHA_B, "path": "x"}]},
        "two": {"repo": "two", "source": "src-two", "source_sha": SHA_C},
    }
    assert fetch_sources.plan(manifests) == {"lib": [SHA_B], "src-one": [SHA_A], "src-two": [SHA_C]}
    assert fetch_sources.plan(manifests, ["two"]) == {"lib": [SHA_B], "src-one": [SHA_A]}
    with pytest.raises(export.ExportError, match="no manifest for three"):
        fetch_sources.plan(manifests, ["three"])


def test_the_plan_refuses_a_short_sha_and_an_unsafe_name():
    with pytest.raises(export.ExportError, match="not a full sha"):
        fetch_sources.plan({"one": {"repo": "one", "source_sha": "abc123"}})
    with pytest.raises(export.ExportError, match="unsafe source repo name"):
        fetch_sources.plan({"one": {"repo": "one", "source": "../x", "source_sha": SHA_A}})


def test_export_skip_refuses_a_repo_another_one_needs():
    manifests = {"base": {"repo": "base"}, "top": {"repo": "top", "after": ["base"]}}
    order, wanted = export.order_manifests(manifests, None, ["top"])
    assert wanted == {"base"} and order == ["base"]
    with pytest.raises(export.ExportError, match="another exported repo needs it"):
        export.order_manifests(manifests, None, ["base"])


def test_manifests_at_reads_the_committed_manifests_and_the_union_plan_has_both_pins():
    files = {
        "export/manifests/_common.yml": "protect: []\n",
        "export/manifests/one.yml": f"repo: one\nsource: src-one\nsource_sha: {SHA_A}\n",
    }
    old = fetch_sources.manifests_at("HEAD", show=lambda rev, path: files[path], names=lambda rev: sorted(files))
    assert list(old) == ["one"]
    new = {"one": {"repo": "one", "source": "src-one", "source_sha": SHA_B}}
    merged = fetch_sources.merge_plans(fetch_sources.plan(new), fetch_sources.plan(old))
    assert merged == {"src-one": [SHA_A, SHA_B]}
