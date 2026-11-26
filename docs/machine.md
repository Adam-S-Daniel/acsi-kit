# Machines and cloud environments

The repos hold the system, but each machine you work on needs some one-time
setup, and so does each claude.ai cloud environment.

## Install on each durable machine

A durable machine is one you keep, such as a laptop, a desktop, or a WSL
distro. A cloud session, by contrast, starts from a snapshot. On each
durable machine, run:

```bash
bash bootstrap/install-machine.sh             # add --dry-run to see it first
bash bootstrap/install-machine.sh --with-codex  # also wire Codex, if ~/.codex exists
```

It clones your `acsi-agentskills` and `_agent-guidance` into the `REPOS_DIR`
from `fleet.env`, or fast-forwards them when the clone is clean and on its
default branch. It refuses a clone whose `origin` is not your repo, then
runs each repo's installer:

1. `acsi-agentskills`' `setup.sh --owner-machine` registers both
   marketplaces and enables the plugins in `~/.claude/settings.json`. It
   also sets `syncClaudeAiSkills: false` there, so your claude.ai account's
   skills stop loading in terminals, and `disableSkillShellExecution: true`.
   It writes the fleet-guidance owner marker and installs the launcher that
   step 4 registers. On Windows, run the installer in both Git Bash and WSL,
   because each has its own home.
2. `acsi-agentskills`' `scripts/install-agent-hooks.sh` installs the
   config-based git hooks (Git 2.54+) that run `.githooks/agent-checks` on
   every commit and push. They apply only in clones of your two owners'
   repos (one `includeIf` per owner).
3. `_agent-guidance`'s `scripts/register-memory-home-hook.sh` registers the
   user-level `memory-home.sh` hook
   ([memory](guidance.md#memory-that-points-at-its-home)).
4. With `--with-codex`, `_agent-guidance`'s `scripts/register-codex-hook.sh`
   registers the launcher from step 1, and refuses to run without it. Then
   run `codex`, type `/hooks`, and trust the hook once.

Every installer is idempotent, so run it again after a plugin is added or
moved. The fleet guidance itself needs nothing more: step 1 also writes the
owner marker (`~/.config/fleet-guidance/owner`), and with it the
`fleet-memory` hook (delivered by the plugin, not carried by each repo) installs the guidance into
`~/.claude/CLAUDE.md` at the first session in any fleet repo. Without the
marker the hook does nothing on a durable machine
([guidance](guidance.md#the-sync)).

## What every session carries

The fleet guidance and each installed skill's name and description are in
the context of every session, on every turn, whether or not the task uses
them. This is what the kit ships, in bytes (a token is about four bytes of
English):

<!-- generated:always-loaded by export/doc_regions.py; it counts the files, so run it with --write -->
| What | Items | Bytes | Loaded when |
|---|---|---|---|
| Core guidance (`agents-md/base.md` as shipped) | 11 | 13,709 | always |
| Recommended guidance, safety | 4 | 3,420 | your choice in step 1 |
| Recommended guidance, habits | 3 | 2,059 | your choice in step 1 |
| Opinionated guidance: `finding-your-unknowns` | 1 | 1,014 | your choice in step 1 |
| Opinionated guidance: `anything-you-name-gets-its-link` | 1 | 885 | your choice in step 1 |
| Opinionated guidance: `subagent-delegation` | 1 | 2,643 | your choice in step 1 |
| Opinionated guidance: `dependency-updates` | 1 | 536 | your choice in step 1 |
| Core skills (name and description) | 4 | 2,664 | always |
| Recommended skills (name and description) | 2 | 1,170 | your choice in step 1 |
| Opinionated skills (name and description) | 2 | 765 | your choice in step 1 |
<!-- /generated:always-loaded -->

A skill's body loads only when the skill is used. Each repo's `AGENTS.md`
adds its short stub and that repo's own notes on top. Sections and skills
you add later count the same way, and on Pro the context you carry is part
of what each turn costs, so choose the optional content in step 1 with this
table in view ([choosing optional
content](skills.md#choosing-optional-content)).

To turn parts off:

- **The guidance, on one machine:** set `FLEET_GUIDANCE_SKIP=1` in that
  machine's environment. The next session removes the installed block from
  `~/.claude/CLAUDE.md` (and from `~/.codex/AGENTS.md`) and installs
  nothing; unset it to get the guidance back. Your repos' `AGENTS.md` stubs
  still load.
- **An optional section or skill:** don't choose it in step 1, or remove it
  later in a pull request on `_agent-guidance` or `acsi-agentskills`.
- **Your claude.ai account's skills:** `setup.sh --owner-machine` (step 1
  of the installer above) already turns these off in terminals with
  `syncClaudeAiSkills: false`. That includes the document skills Anthropic
  provides on the account, so a terminal session no longer lists them. Set
  it back to `true` in `~/.claude/settings.json` if you want them, at the
  cost of every one of their descriptions.
- **Shell lines in skills:** the installer also sets
  `disableSkillShellExecution: true`, so a `` !`command` `` line in a
  `SKILL.md` is not run when the skill loads. No skill in the kit uses that
  syntax. This one costs no context; it closes a path from a skill's text
  to a command.

## Scheduled jobs (wsl-automation)

**What a base-only machine schedules** (no `skills-evals`, so
`SKILLS_EVALS_URL=none`):

- **Windows:** `register-tasks.ps1` registers every task. The ones that do
  work on the base are the ccstatusline config sync, the WSL memory log, the
  Docker watchdog and memory curation. The session miner and the usage
  census log that they skipped and exit 0. The waiting feed fails each
  minute until you create `waiting-feed` and set `WAITING_FEED_URL`
  (optional).
- **Linux and macOS:** nothing. `scripts/unix/install-schedule.sh` schedules
  the usage census and the session miner, which serve evals, and the
  optional waiting feed. Skip it on the base (mark the quick start's step 22
  done), or schedule `--jobs waiting-feed` if you use the feed.

[`wsl-automation`](../starter/wsl-automation/README.md) schedules the jobs
that must run on your machine because they read its transcripts or use its
login:

| Job | When | What it does |
|---|---|---|
| session miner | daily at 07:17 | turns your transcripts into short, redacted lesson records on `acsi-agentskills-private`'s `persistent/lessons` |
| usage census | daily at 12:37 | publishes which models and skills you ran each week to `skills-evals`' `persistent/eval-results`; the roster picks eval models from it and the planner improves the most used skills first |
| memory curation | weekly, Monday at 13:47 (Windows with WSL only) | curates the memory notes of both homes, WSL's and the Windows profile's ([routines](routines.md#memory-curation)) |
| waiting feed | every minute | publishes the sessions waiting on you to a private `waiting-feed` repo. Optional on Linux and macOS; on Windows the task is always registered, and exits 2 each minute until `WAITING_FEED_URL` is set |

On Windows, `register-tasks.ps1` also registers three housekeeping tasks: a
ccstatusline config sync and a WSL memory log, both every 5 minutes, and a
Docker Desktop WSL integration watchdog. It registers a Codex Cloud
environment sync too, which stays disabled unless you pass
`-EnableCodexTasks`.

**On Windows** (WSL), from the clone, once per machine:

1. Install PowerShell 7.6 or newer from the MSI, not the Microsoft Store
   (`winget install --id Microsoft.PowerShell --scope machine`).
2. From an elevated prompt, run `.\scripts\grant-keeper-batch-logon.ps1`. It
   gives your account the "Log on as a batch job" right the background tasks
   need.
3. From an elevated PowerShell 7 prompt, run `.\scripts\register-tasks.ps1`.
   Add `-WhatIf` to preview the change, or `-DistroName <name>` if your
   distro is not `Ubuntu`.
4. From a normal prompt, run `.\scripts\install-ccstatusline.ps1`.

**On Linux or macOS**, run
`bash scripts/unix/install-schedule.sh <systemd|launchd|cron>`. Add
`--jobs usage-census,session-miner,waiting-feed` to choose jobs, or
`--print` to change nothing. macOS needs `brew install flock coreutils`.
The installer checks the tools (and, for systemd, a user bus) first and, if
any is missing, lists them all with the fix and writes nothing. The waiting
feed is Linux and WSL only (macOS keeps Claude Code's login in the Keychain),
so the installer skips it on a Mac.
systemd needs `loginctl enable-linger "$USER"` so jobs keep running while
you are logged out.

**Every Bash job reads its settings from one file** and has no built-in
repository, so a job whose key is missing exits 2 and names it. Before you
register the jobs, copy the repo's `config/settings.env.example` to
`~/.config/wsl-automation/settings.env`, in the distro or on Linux or macOS.
`copy-starter.sh` has already put your owner in it. It ships
`SKILLS_EVALS_URL=none`: the usage census and the session miner run code
from `skills-evals`, so without it they log that they skipped and exit 0.
When you add evals, set it to your `skills-evals` URL (quick start step 42).
Check `LESSONS_CLONE` (session miner),
`WAITING_FEED_URL` (waiting feed), `AGENT_GUIDANCE_URL` (memory curation),
and `CODEX_CLOUD_GUIDANCE_REPOSITORY` (Codex Cloud sync, as `owner/name`).
The README's "Settings file for the Bash tasks" has the format.

**The session miner refuses to run** until you set it up and run it once by
hand, in the distro. It needs:

- a privacy denylist outside every repo (`~/.config/privacy-denylist.txt`,
  with the same patterns as the `PRIVACY_DENYLIST` secret);
- a clone of `acsi-agentskills-private` (for example at
  `~/repos/acsi-agentskills-private`), with a git credential that works
  without a desktop session (`gh auth setup-git` with a file-stored token);
- `python3-yaml`;
- `LESSONS_CLONE` and `SKILLS_EVALS_URL` in `settings.env`. Both are
  required and have no default, so the wrapper exits 2 and names whichever
  is unset; `SKILLS_EVALS_URL=none` turns the miner off instead.

Then run `bash scripts/run-session-miner.sh --dry-run`. It files no issues
until you set `FILE_ISSUES=on`, so read a sample of its records first. The
README's "Session miner task" has every setting.

**The waiting feed** needs its own private repo:
`bash bootstrap/create-repos.sh --with-optional` creates `waiting-feed`.

## Cloud environments

A claude.ai cloud environment (https://claude.ai/code, the environment
menu) sets the network access and a setup script for every session started
in it. Create one for your fleet work and give it:

- **Network access:** "Custom", with the domains in `_agent-guidance`'s
  [`docs/reference/network-allowlist-claude-environments.txt`](../starter/agent-guidance/docs/reference/network-allowlist-claude-environments.txt).
  Its header says how to change it.
- **Setup script:** the one in `acsi-agentskills`'
  [`docs/multi-repo-delivery.md`](../starter/agent-skills/docs/multi-repo-delivery.md),
  "The wiring (cloud only)", with its project directory set to the one your
  sessions open. A single-repo session doesn't need it, because the repo's
  `skills-bootstrap.sh` hook installs its locked skills. A session opened on
  several repos does, because hooks are read only from the working directory
  and `~`. The script must end with `exit 0`, because a failed setup script
  stops the session from starting.

Each routine names its environment ([routines](routines.md)).
`wsl-automation`'s `scripts/sync-codex-cloud-environments.sh` keeps Codex
Cloud environments in step (see its README, "Codex Cloud environment sync
task"), once you have set [the Codex Cloud
pin](generated-files.md#the-codex-cloud-pin).
