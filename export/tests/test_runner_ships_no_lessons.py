"""The exported agent-checks runner carries none of the source owner's lesson checks.

The source's lesson-check lane adds `case` arms to `check_lessons` and ids to
`lesson_checks`. The kit ships the empty slot: agent-skills' own
test_agent_checks.py splices its fixture lesson into exactly that text and fails
when it is not there (acsi-kit#74).
"""

from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
RUNNERS = sorted(KIT_ROOT.glob("starter/*/.githooks/agent-checks")) + [
    KIT_ROOT / "starter/agent-guidance/templates/agent-checks/agent-checks"]
EMPTY_BODY = "check_lessons() {\n  :\n}\n"


def test_every_runner_has_the_empty_lesson_slot():
    assert RUNNERS, "no runner found"
    for runner in RUNNERS:
        text = runner.read_text(encoding="utf-8")
        rel = runner.relative_to(KIT_ROOT)
        assert text.count('\nlesson_checks=""\n') == 1, rel
        assert text.count(EMPTY_BODY) == 1, rel
