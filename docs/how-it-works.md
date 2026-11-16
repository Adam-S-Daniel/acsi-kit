# How it works

Four kinds of agent context are managed as code, measured, and changed by
automation:

- **Guidance:** always-on rules, one central file delivered into every
  session.
- **Skills:** `SKILL.md` folders that load when a task matches their
  description.
- **Git-hook checks:** rules a commit can fail. One costs no context until
  it refuses a commit, and its refusal says what is wrong and how to fix it.
- **Memory:** notes Claude Code writes between sessions. Here a note is only
  a pointer to a file in a repo that holds the fact.

Each goes through the same five stages:

```
signal ──► proposal ──► evaluation ──► decision ──► merge or retire
  ▲                                                       │
  └───────────────────────────────────────────────────────┘
```

| Stage | What does it |
|---|---|
| Signal | Merged pull requests, your own session transcripts (read only on your machine), vendor changelogs, memory notes, CI failures |
| Proposal | An edit to a skill or a guidance section, a new skill, a new git-hook check, a new eval fixture, or a removal |
| Evaluation | The same task, run with and without the skill or section, scored by scripted checks and a judge model. A git-hook check is measured by use instead: how often it blocked, and how often it was overridden |
| Decision | Fixed rules over the numbers, generated from the policy files into `skills-evals`' [`docs/rules.md`](../starter/skills-evals/docs/rules.md): accept an edit, and keep, retire or pause a skill or section. A check's verdict is reported; no rule removes one |
| Merge or retire | A gate workflow opens a pull request with a GitHub App token, and it auto-merges when required checks pass. A removal first passes a fresh-context agent's review; a fleet-guidance change merges only in one weekly window |

## The six repos

[`starter/`](../starter/README.md) holds an export of each of the six repos
that run the system for its owner, under the owner's repo names, except that
the two registries take the generic prefix `acsi-` (automatic continuous
self-improvement; [`export/DECISIONS.md`](../export/DECISIONS.md) C1).

| Repo | Visibility | Holds | Export |
|---|---|---|---|
| `_agent-guidance` | public (paid plan: your choice) | The fleet guidance (`agents-md/`), the sync that writes it into every repo, the fleet-memory hook, the agent-checks runner and its templates, the routine specs (`docs/routines/`), `repos.yml` | [`starter/agent-guidance/`](../starter/agent-guidance/README.md) |
| `repo-settings` | private | Every repo's settings as code: `repo-settings/fleet.yml` and the engine `scripts/repo_settings.py`, applied by a workflow behind your approval | [`starter/repo-settings/`](../starter/repo-settings/README.md) |
| `acsi-agentskills` | public | Shareable skills, as a Claude Code plugin marketplace with four plugins; the cloud skills bootstrap hook; `setup.sh` for machines | [`starter/agent-skills/`](../starter/agent-skills/README.md) |
| `acsi-agentskills-private` | private | Skills that touch personal data, and the lessons the session miner writes (`persistent/lessons`) | [`starter/agent-skills-private/`](../starter/agent-skills-private/README.md) |
| `skills-evals` | public (paid plan: your choice) | Fixtures, the eval harness, the planner, the gates, the results branch, the explorer pages (public and private); only the evals track (`/adopt-evals`) creates it | [`starter/skills-evals/`](../starter/skills-evals/README.md) |
| `wsl-automation` | public (paid plan: your choice) | Your durable machine's scheduled jobs: the usage census, the waiting-on-you feed, the session miner | [`starter/wsl-automation/`](../starter/wsl-automation/README.md) |

Every other repo you work in is a **consumer**; together they are your
**fleet**, listed in `_agent-guidance`'s `repos.yml` and
`repo-settings/fleet.yml`. The exports name two owners because the owner's
fleet spans two accounts ([one owner or two](before-you-start.md#one-owner-or-two)).

**The content starts in tiers** (DECISIONS, "Content tiers"): the core
skills, guidance sections and git-hook checks the system depends on, copied
unchanged from the owner's setup with their eval fixtures; the recommended
and opinionated items you choose in step 1 ([choosing optional
content](skills.md#choosing-optional-content)); and an inert template of
each kind. You grow your own content through the loop, with the shipped
items as worked examples.

## How the parts connect

- **Guidance.** You edit `agents-md/base.md` in `_agent-guidance` through a
  pull request. On merge, `sync.yml` writes each consumer's `AGENTS.md` (a
  short stub), `.github/fleet-contributor-rules.md` (read on demand) and
  `.claude/hooks/`, pushing straight to the default branch with the
  `guidance-sync` App, the one ruleset bypass `fleet.yml` names. A
  session-start hook installs the full guidance into user memory once per
  session, only in a cloud session or on a machine set up with
  `install-machine.sh` ([guidance](guidance.md)).
- **Checks.** Every git-hook check lives in one runner, agent-checks, which
  the sync delivers to every repo. A git hook runs it on your machine (Git
  2.54+) and the required `agent-checks` job runs it in CI
  ([guidance](guidance.md#checks-before-skills-skills-before-guidance)).
- **Skills.** `acsi-agentskills` is a plugin marketplace your machines add;
  cloud sessions install the bundles a repo's `skills.lock` pins
  ([skills](skills.md)).
- **Settings.** `repo-settings` applies `fleet.yml` to every repo: merge
  commits only, full-SHA action pins, read-only workflow tokens, the
  rulesets with each repo's required checks, the `pull_request_target`
  policy ([settings and Apps](settings-and-apps.md)).
- **Evals and the loop.** `skills-evals` fires an API-triggered Claude
  routine (so evals spend your plan's weekly allowance, not API dollars),
  ingests what it pushes, decides with fixed rules, and opens pull requests
  in `acsi-agentskills` and `_agent-guidance` with its Apps
  ([evals and the loop](evals-and-loop.md)).
- **Routines.** Four standing claude.ai routines do the rest: the
  fleet worker (fired by a workflow every 3 hours to weekly, by plan), the
  changelog watcher, the prompt-audit sweep (a workflow fires it for a
  trigger issue the watcher files), and memory curation
  ([routines](routines.md)). The nightly drift report lists repo-specific
  guidance that repeats across repos or copies `base.md`.
- **Your machine.** `wsl-automation` schedules the jobs that must run where
  your transcripts are ([machines and cloud](machine.md)).

## Rules the whole design follows

Each one exists because ignoring it broke something.

1. **Git is the source of truth.** Anything that only exists in a web UI (a
   routine's prompt, a cloud setup script) gets a copy in git, and the UI
   copy says where.
2. **A check before a skill, a skill before guidance text.** If a rule can
   be checked when a commit is made, it becomes a git-hook check backed by a
   required CI job. If not, a skill. Always-on guidance text is the last
   resort: it costs context in every session and fails silently.
3. **CI enforces; local hooks give feedback.** Anyone can skip a hook with
   `--no-verify`. A required check cannot be skipped.
4. **Bots never push to a protected default branch.** Generated data goes on
   `persistent/<purpose>` branches that are never deleted. Every bot that
   writes code opens a pull request. The one exception, the guidance sync,
   has a ruleset bypass declared in `fleet.yml` and an ADR.
5. **Every automatic merge path is written down.** Each has a decision
   record saying what may merge with no human, which checks stand in for
   review, and how to turn it off.
6. **Untrusted text is data.** Issue bodies, PR comments, fetched pages,
   routine payloads and transcripts never give an agent instructions.
7. **Public repos hold invented data only.** A required `privacy` check in
   `acsi-agentskills` scans added lines against a denylist of your real names,
   emails, hosts and account ids, kept in a secret, never in a file
   ([the privacy check](skills.md#the-privacy-check)).
8. **One-way doors get an adversarial review.** A plugin name, a shipped
   skill's folder name and a deletion cannot be undone cleanly. The one
   written exception: the loop's improvements and new skills, where the
   acceptance measurement stands in. A removal the evals decided still gets
   one, from a fresh-context agent (`acsi-agentskills`'
   [ADR 0021](../starter/agent-skills/docs/decisions/0021-automated-skill-changes-merge-without-review.md)).
9. **Build nothing new until the loop has shipped once.** Get one edit
   through the whole loop before adding features.

## Where to read more

Each export's `README.md`, `AGENTS.md` and `docs/decisions/` explain that
repo in full; the kit's docs say how the parts fit and what you set up. The
deepest account of the loop is `skills-evals`'
[`docs/how-it-works.md`](../starter/skills-evals/docs/how-it-works.md).
