# Guidance, checks and memory

## What _agent-guidance holds

[`_agent-guidance`](../starter/agent-guidance/README.md) is the guidance
layer: the always-on rules, the machinery that delivers them to every repo
and every session, and the specs the standing routines follow.

- `agents-md/base.md` is the fleet guidance. It ships the core sections,
  copied unchanged from the owner's guidance (their fixtures are in
  `skills-evals`), the recommended and opinionated sections you chose with
  `bootstrap/add-content.sh` ([choosing optional
  content](skills.md#choosing-optional-content)), and an HTML-commented
  template of a section above them (DECISIONS X9; a new
  section also needs a row in `agents-md/eval-coverage.yml`, with its
  `audience`, and an entry in `docs/guidance-impact.md`).
  `agents-md/sections/` holds per-stack sections
  (python, javascript, typescript, go, dotnet, rust, docker), each empty; a
  repo asks for one in its `.agents-sync.yml`.
- `agents-md/stub.md` is the short floor each consumer's `AGENTS.md` gets:
  where the guidance comes from and what to read when it did not load, the
  check value a session's first reply opens with, and one sentence of rules
  that cannot be undone (no push to a default branch, no force-push, no
  secret, no personal data in a CI log).
- `.github/fleet-contributor-rules.md` is the part of `base.md` an outside
  contributor's agent needs, generated from the sections whose
  `eval-coverage.yml` row says `audience: contributor`
  (`scripts/build-contributor-rules.js`; ADR 0043).
- `repos.yml` lists repos excluded from the sync, default sections, the
  skills-bootstrap pin with the repos that receive that hook (each must
  commit its own `skills.lock`), the switches for the agent-checks and
  Dependabot deliveries, and `cron_coverage.fleet`, the repos the routines
  visit.
- `.claude/hooks/` holds the hooks. The sync delivers `fleet-memory.sh` (the
  session-start delivery) with its payload `fleet-guidance.md`,
  `guidance-load-record.sh` (a Stop hook that records whether a session
  loaded the full guidance or only the stub) and `skills-bootstrap.sh`.
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
over every repo of both owners in `SYNC_OWNERS`: it rebuilds each repo's
managed `AGENTS.md` (everything under `## Repo-specific additions` is kept),
writes the `CLAUDE.md` bridge (`@AGENTS.md`) where there is none, delivers
the contributor rules, the hooks and the templates, and pushes straight to
the default branch with a `guidance-sync` token. That push works on a
protected branch because `fleet.yml` names the App as the ruleset's one
bypass actor; where protection still rejects it, the sync opens a pull
request with auto-merge instead. The nightly `drift-report.yml` writes
`drift-report.md` to `persistent/drift-report`.

**Delivered once per session.** A consumer's `AGENTS.md` carries only the
stub. The full guidance arrives through `fleet-memory.sh`, a SessionStart
hook that installs it into user memory (`~/.claude/CLAUDE.md`, and
`~/.codex/AGENTS.md` when `~/.codex` exists) and prints one verdict line:
`installed`, `current`, `DEGRADED` or `skipped`. Inlined in every repo
instead, it once took 332.3k tokens in one multi-repo session.

- **It delivers only to you** (ADR 0042): in a cloud session, or on a
  machine that carries the owner marker `install-machine.sh` writes
  ([machines](machine.md#install-on-each-durable-machine)). In anyone else's
  clone the hook exits before it reads or writes anything, and their agent
  works from the stub and the contributor rules.
- **A session with no fleet repo attached** runs no repo hook, so the
  `acsi-anything-anywhere` plugin's own session-start hook fetches `base.md`
  from `main` and installs it the same way.
- **Proof it loaded** (ADR 0035): the installed guidance ends with a
  `fleet-guidance check value:` line, and the stub tells the agent to open
  its first reply with it, or with `none`.
- **A repo that cannot take the hook** (`.claude/` ignored, or a
  `settings.json` the sync cannot parse) gets `AGENTS_MD_MODE=full`: the
  stub followed by the contributor rules, never `base.md`.

**Changing guidance.** Edit `base.md` (or a section) in a pull request on
`_agent-guidance`. In the same pull request: copy `base.md` byte for byte
to `.claude/hooks/fleet-guidance.md` (CI checks the mirror), give a new
`##` heading a row in `agents-md/eval-coverage.yml` with its `audience`,
add an entry to `docs/guidance-impact.md` for a changed section, and
regenerate the contributor rules and this repo's own `AGENTS.md`. The
repo's `AGENTS.md`, "Repo-specific additions", has the commands; CI fails on
each one you miss. Two gates apply to these pull requests:

- **The eval-protection gate** (`scripts/eval-protected.js`, in required
  CI): a section or skill with eval evidence for its current text may
  change only as a marked correctness fix, because any edit resets that
  evidence (ADR 0033 and 0034).
- **The weekly merge window** (ADR 0039): automation merges a change to
  `base.md` or `agents-md/sections/` only on Monday from 17:00 to 19:00 UTC
  (`scripts/base-md-merge-window.yml`), because every such merge restarts
  each section's eval evidence. You may merge at any time, at that cost.

## Checks before skills, skills before guidance

A rule that a commit can show is broken becomes a check, not text:

- **agent-checks** is one runner, `templates/agent-checks/agent-checks`,
  delivered to every fleet repo as `.githooks/agent-checks` with its CI
  workflow `agent-checks.yml` (added once, never overwritten). Its checks:

  | Check | Refuses |
  |---|---|
  | `skill-shell` | a `SKILL.md` or command file that runs a shell command when it loads |
  | `secret-file` | a committed `.env` or key file |
  | `local-identity` | a changed file that holds this machine's account name in a home path, or its hostname (not run in CI) |
  | `agents-md-size` | a root `AGENTS.md` over the 32 KiB Codex reads |
  | `gha-template-injection` | a workflow expression that zizmor's template-injection audit flags |
  | `pr-tldr` | a pull request whose description does not open with `## TLDR` (CI only) |

  `rules-dir` is added when you choose it, a commented-out template shows
  how to write another, and the `dated-phrasing` pass only warns. A repo's
  own checks go in `.agent-checks/local.sh`, and fleet-wide ones in the
  template. Each refusal says what is wrong, why, and how to fix it, so the
  rule does not need to sit in always-on guidance. Every run is logged
  (`~/.local/state/agent-checks/runs.jsonl`), which is how a check's use is
  measured ([rules](../starter/skills-evals/docs/rules.md)).
- **On your machine** a config-based git hook (Git 2.54+) runs it on every
  commit and push, in clones of your two owners' repos only
  ([machines](machine.md#install-on-each-durable-machine)).
- **In CI** the required `agent-checks` job runs it over a pull request's
  commits. A hook can be skipped with `--no-verify`; the required check
  cannot.
- `templates/agent-checks/agent-checks-guard.sh` is a PreToolUse hook that
  stops an agent from skipping the hooks, repointing or editing them, or
  deleting a remote `persistent/*` branch.

The order of preference for any new rule: a check that a commit can fail;
then a skill; then a line of guidance. The fleet worker turns lessons into
checks this way ([routines](routines.md#fleet-worker)).

## Memory that points at its home

A Claude Code memory note outside a repo must name the repo file that holds
the fact (`metadata.home` as `<owner>/<repo>:<path>`); the note is a pointer
([ADR 0013](../starter/agent-guidance/docs/decisions/0013-a-memory-note-outside-a-repo-names-its-home.md)).
`memory-home.sh`, registered once per machine at user level by
`install-machine.sh`, nudges at session start and blocks a session's stop
while a note it wrote has no home. A weekly routine curates the notes and
promotes facts into issues the fleet worker picks up
([memory curation](routines.md#memory-curation)).

## Where to read more

`_agent-guidance`'s [README](../starter/agent-guidance/README.md) (the
sync, the skills-bootstrap hook, the `CLAUDE.md` bridge, the required
secrets, the drift report, cron coverage), its `AGENTS.md`, and its ADRs.
