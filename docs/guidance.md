# Guidance, checks and memory

## What _agent-guidance holds

[`_agent-guidance`](../starter/agent-guidance/README.md) holds the always-on
rules, the machinery that delivers them to every repo and session, and the
specs the standing routines follow.

- `agents-md/base.md` is the fleet guidance. It ships the core sections,
  copied unchanged from the owner's guidance (their fixtures are in
  `skills-evals`), plus the recommended and opinionated sections you chose
  with `bootstrap/add-content.sh` ([choosing optional
  content](skills.md#choosing-optional-content)). An HTML-commented section
  template sits above them (DECISIONS X9). A new section also needs a row in
  `agents-md/eval-coverage.yml`, with its `audience`, and an entry in
  `docs/guidance-impact.md`. `agents-md/sections/` holds empty per-stack
  sections (python, javascript, typescript, go, dotnet, rust, docker), and a
  repo requests one in its `.agents-sync.yml`.
- `agents-md/stub.md` is the short minimum each consumer's `AGENTS.md` gets.
  It says where the guidance comes from, what to read if it didn't load, and
  which check value to open a session's first reply with. It also gives one
  sentence of rules that protect against what can't be undone: no push to a
  default branch, no force-push, no secrets, and no personal data in a CI
  log.
- `.github/fleet-contributor-rules.md` is the part of `base.md` an outside
  contributor's agent needs. It is generated from the sections marked
  `audience: contributor` in `eval-coverage.yml`
  (`scripts/build-contributor-rules.js`; ADR 0043).
- `repos.yml` lists the repos excluded from the sync, the default sections,
  the skills-bootstrap pin and the repos that receive that hook (each must
  commit its own `skills.lock`), the switches for agent-checks and
  Dependabot delivery, and `cron_coverage.fleet`, the repos the routines
  visit.
- `.claude/hooks/` holds the hooks. The sync delivers `skills-bootstrap.sh`;
  `fleet-memory.sh` (the session-start delivery), its payload
  `fleet-guidance.md` and `guidance-load-record.sh` (a Stop hook that records
  whether a session loaded the full guidance or only the stub) stay in
  `_agent-guidance`, which the owner's own routes download, and the sync
  removes any leftover copy from a consumer (ADR 0043).
  `memory-home.sh` is registered per machine instead, and
  `github-write-marker.sh` reaches sessions through the `acsi-anything-anywhere`
  plugin.
- `templates/` holds the other files the sync delivers: the agent-checks
  runner, its guard hook, its warning-only `dated-phrasing` pass and its CI
  workflow, and the Dependabot auto-merge sweep.
- `docs/routines/` and `docs/reference/` hold the routine specs
  ([routines](routines.md)), `docs/decisions/` the ADRs.

## The sync

On every merge that changes the guidance, `sync.yml` runs `scripts/sync.sh`
over every repo of both owners in `SYNC_OWNERS`. It rebuilds each repo's
managed `AGENTS.md`, keeping everything under `## Repo-specific additions`.
It writes the `CLAUDE.md` bridge (`@AGENTS.md`) where none exists, delivers
the contributor rules, hooks, and templates, and pushes straight to the
default branch with a `guidance-sync` token. The push works on a protected
branch because `fleet.yml` lists that App as the ruleset's only bypass
actor. Where protection still rejects the push, the sync opens a pull
request with auto-merge instead. The nightly `drift-report.yml` writes
`drift-report.md` to `persistent/drift-report`.

**Delivered once per session.** A consumer's `AGENTS.md` carries only the
stub. The full guidance arrives through `fleet-memory.sh`, a SessionStart
hook that no consumer repo carries (ADR 0043): the plugin's SessionStart hook
and the Codex Cloud setup script download it from `_agent-guidance`. It installs it into user memory (`~/.claude/CLAUDE.md`, and
`~/.codex/AGENTS.md` when `~/.codex` exists) and prints one verdict line:
`installed`, `current`, `DEGRADED` or `skipped`. Inlined in every repo
instead, it once took 332.3k tokens in one multi-repo session.

- **It delivers only to you** (ADR 0042): in a cloud session, or on a
  machine with the owner marker that `install-machine.sh` writes
  ([machines](machine.md#install-on-each-durable-machine)). In anyone else's
  clone, the hook exits before reading or writing anything, and their agent
  works from the stub and the contributor rules.
- **A session with no fleet repo attached** runs no repo hook, so the
  `acsi-anything-anywhere` plugin's own session-start hook fetches `base.md`
  from `main` and installs it the same way.
- **Proof it loaded** (ADR 0035): the installed guidance ends with a
  `fleet-guidance check value:` line, and the stub tells the agent to open
  its first reply with it, or with `none`.
- **A repo that can't take the hook** (`.claude/` is ignored, or the sync
  can't parse its `settings.json`) gets `AGENTS_MD_MODE=full`: the stub plus
  the contributor rules, never `base.md`.

**Changing guidance.** Edit `base.md` or a section in a pull request on
`_agent-guidance`. In the same pull request, copy `base.md` byte for byte to
`.claude/hooks/fleet-guidance.md` (CI checks the mirror), give any new `##`
heading a row in `agents-md/eval-coverage.yml` with its `audience`, add a
`docs/guidance-impact.md` entry for a changed section, and regenerate the
contributor rules and this repo's `AGENTS.md`. The commands are in that
`AGENTS.md`, under "Repo-specific additions", and CI fails on anything you
miss. Two gates apply:

- **The eval-protection gate** (`scripts/eval-protected.js`, in required
  CI): any edit resets a section's or skill's eval evidence, so one with
  evidence for its current text can change only through a marked correctness
  fix (ADR 0033 and 0034).
- **The weekly merge window** (ADR 0039): every merge to `base.md` or
  `agents-md/sections/` restarts each section's eval evidence, so automation
  merges those changes only on Monday from 17:00 to 19:00 UTC
  (`scripts/base-md-merge-window.yml`). You can merge at any time, at that
  cost.

## Checks before skills, skills before guidance

If a commit can show that a rule was broken, the rule becomes a check
instead of text:

- **agent-checks** is a single runner,
  `templates/agent-checks/agent-checks`, delivered to every fleet repo as
  `.githooks/agent-checks`, along with its CI workflow `agent-checks.yml`
  (added once, never overwritten). Its checks:

  | Check | Refuses |
  |---|---|
  | `skill-shell` | a `SKILL.md` or command file that runs a shell command when it loads |
  | `secret-file` | a committed `.env` or key file |
  | `privacy` | on push, a ref name or commit message that holds this machine's account name or hostname, or a term in your privacy denylist (a file outside any repo; without one only the machine's own names are checked) |
  | `local-identity` | a changed file that holds this machine's account name in a home path, or its hostname (not run in CI) |
  | `agents-md-size` | a root `AGENTS.md` over the 32 KiB Codex reads |
  | `gha-template-injection` | a workflow expression that zizmor's template-injection audit flags |
  | `pr-tldr` | a pull request whose description does not open with `## TLDR` (CI only) |

  `rules-dir` is added if you choose it, a commented-out template shows how
  to write another check, and the `dated-phrasing` pass only warns. A repo's
  own checks go in `.agent-checks/local.sh`, and fleet-wide ones go in the
  template. Each refusal says what is wrong, why, and how to fix it, so the
  rule doesn't need to sit in always-on guidance. Every run is logged to
  `~/.local/state/agent-checks/runs.jsonl`, which is how a check's use is
  measured ([rules](../starter/skills-evals/docs/rules.md)).
- **On your machine**, a config-based git hook (Git 2.54+) runs it on every
  commit and push, but only in clones of your two owners' repos
  ([machines](machine.md#install-on-each-durable-machine)).
- **In CI**, the required `agent-checks` job runs it over a pull request's
  commits. `--no-verify` can skip a hook, but not the required check.
- `templates/agent-checks/agent-checks-guard.sh` is a PreToolUse hook that
  stops an agent from skipping the hooks, repointing or editing them, or
  deleting a remote `persistent/*` branch.

For any new rule, prefer a check that a commit can fail, then a skill, then
a line of guidance. The fleet worker follows the same order when it turns
lessons into checks ([routines](routines.md#fleet-worker)).

## Memory that points at its home

A Claude Code memory note outside a repo is only a pointer, so it must name
the repo file that holds the fact (`metadata.home` as
`<owner>/<repo>:<path>`; [ADR
0013](../starter/agent-guidance/docs/decisions/0013-a-memory-note-outside-a-repo-names-its-home.md)).
`install-machine.sh` registers `memory-home.sh` once per machine at user
level. The hook nudges at session start and blocks a session from stopping
while a note it wrote has no home. A weekly routine curates the notes and
promotes facts into issues the fleet worker picks up ([memory
curation](routines.md#memory-curation)).

## Where to read more

`_agent-guidance`'s [README](../starter/agent-guidance/README.md) (the
sync, the skills-bootstrap hook, the `CLAUDE.md` bridge, the required
secrets, the drift report, cron coverage), its `AGENTS.md`, and its ADRs.
