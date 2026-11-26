# How it works

Four kinds of agent context are managed as code, measured, and changed by
automation:

- **Guidance:** always-on rules, one central file delivered into every
  session.
- **Skills:** `SKILL.md` folders that load when a task matches their
  description.
- **Git-hook checks:** rules a commit can fail. A check costs no context
  until it refuses a commit, and the refusal says what is wrong and how to
  fix it.
- **Memory:** notes Claude Code writes between sessions. Here, each note
  just points to the repo file that holds the fact.

Each goes through the same five stages:

```
signal ──► proposal ──► evaluation ──► decision ──► merge or retire
  ▲                                                       │
  └───────────────────────────────────────────────────────┘
```

| Stage | What does it |
|---|---|
| Signal | Merged pull requests, your own session transcripts (read only on your machine), the weekly count of which skills and models you used, vendor changelogs, memory notes, CI failures |
| Proposal | An edit to a skill or a guidance section, a new skill, a new git-hook check, a new eval fixture, or a removal |
| Evaluation | The same task, run with and without the skill or section, scored by scripted checks and a judge model. A git-hook check is measured by use instead: how often it blocked, and how often it was overridden |
| Decision | Fixed rules over the numbers, generated from the policy files into `skills-evals`' [`docs/rules.md`](../starter/skills-evals/docs/rules.md): accept an edit, keep or retire a skill or section, or pause evals for a skill nobody uses. Check verdicts are reported, but no rule removes a check |
| Merge or retire | A gate workflow opens a pull request with a GitHub App token, and it auto-merges when required checks pass. A removal must first pass review by a fresh-context agent. A fleet-guidance change merges only during a weekly window. Anything that needs your approval, such as a plugin that runs code, becomes an issue for you instead |

## The six repos

[`starter/`](../starter/README.md) holds an export of each of the six repos
that run the owner's system. They keep the owner's repo names, except that
the two registries use the generic prefix `acsi-` (automatic continuous
self-improvement; [`export/DECISIONS.md`](../export/DECISIONS.md) C1).

| Repo | Visibility | Holds | Export |
|---|---|---|---|
| `_agent-guidance` | public (paid plan: your choice) | The fleet guidance (`agents-md/`), the sync that writes it into every repo, the fleet-memory hook, the agent-checks runner and its templates, the routine specs (`docs/routines/`), `repos.yml` | [`starter/agent-guidance/`](../starter/agent-guidance/README.md) |
| `repo-settings` | private | Every repo's settings as code: `repo-settings/fleet.yml` and the engine `scripts/repo_settings.py`, applied by a workflow behind your approval | [`starter/repo-settings/`](../starter/repo-settings/README.md) |
| `acsi-agentskills` | public | Shareable skills, as a Claude Code plugin marketplace with four plugins; the cloud skills bootstrap hook; `setup.sh` for machines | [`starter/agent-skills/`](../starter/agent-skills/README.md) |
| `acsi-agentskills-private` | private | Skills that touch personal data, and the lessons the session miner writes (`persistent/lessons`) | [`starter/agent-skills-private/`](../starter/agent-skills-private/README.md) |
| `skills-evals` | public (paid plan: your choice) | Fixtures, the eval harness, the planner, the gates, the results branch, the explorer pages (public and private); only the evals track (`/adopt-evals`) creates it | [`starter/skills-evals/`](../starter/skills-evals/README.md) |
| `wsl-automation` | public (paid plan: your choice) | Your durable machine's scheduled jobs: the usage census, the session miner, memory curation, the waiting-on-you feed | [`starter/wsl-automation/`](../starter/wsl-automation/README.md) |

Every other repo you work in is a **consumer**. Together they make up your
**fleet**, which `_agent-guidance`'s `repos.yml` and
`repo-settings/fleet.yml` list. The exports name two owners because the
owner's fleet spans two accounts ([one owner or
two](before-you-start.md#one-owner-or-two)).

**The content comes in tiers** (DECISIONS, "Content tiers"). The core
skills, guidance sections, and git-hook checks the system depends on are
copied unchanged from the owner's setup, with their eval fixtures. You
choose the recommended and opinionated items in step 1 ([choosing optional
content](skills.md#choosing-optional-content)), and each kind also has an
inert template. You grow your own content through the loop, using the
shipped items as worked examples.

## How the parts connect

- **Guidance.** You edit `agents-md/base.md` in `_agent-guidance` through a
  pull request. On merge, `sync.yml` writes each consumer's `AGENTS.md` (a
  short stub), `.github/fleet-contributor-rules.md` (read on demand), and
  `.claude/hooks/`. It pushes straight to the default branch as the
  `guidance-sync` App, the only ruleset bypass in `fleet.yml`. A
  session-start hook then installs the full guidance into user memory once
  per session, but only in a cloud session or on a machine set up with
  `install-machine.sh` ([guidance](guidance.md)).
- **Checks.** Every git-hook check lives in a single runner, agent-checks,
  which the sync delivers to every repo. A git hook runs it on your machine
  (Git 2.54+), and the required `agent-checks` job runs it in CI
  ([guidance](guidance.md#checks-before-skills-skills-before-guidance)).
- **Skills.** `acsi-agentskills` is a plugin marketplace your machines add;
  cloud sessions install the bundles a repo's `skills.lock` pins
  ([skills](skills.md)).
- **Settings.** `repo-settings` applies `fleet.yml` to every repo: merge
  commits only, pinned actions (a full SHA, or a tag an `actions.lock`
  pins), read-only workflow tokens, secret scanning, the rulesets with each
  repo's required checks, the `pull_request_target` policy
  ([settings and Apps](settings-and-apps.md)).
- **Evals and the loop.** `skills-evals` fires an API-triggered Claude
  routine, so evals spend your plan's weekly allowance rather than API
  dollars. It ingests what the routine pushes, decides with fixed rules, and
  uses its Apps to open pull requests in `acsi-agentskills` and
  `_agent-guidance` ([evals and the loop](evals-and-loop.md)).
- **Routines.** Four standing claude.ai routines do the rest: the fleet
  worker (a workflow fires it every 3 hours to weekly, depending on your
  plan), the changelog watcher, the prompt-audit sweep (a workflow fires it
  for each trigger issue the watcher files), and memory curation, which also
  runs on your machine ([routines](routines.md)). An article-lift routine is
  optional. The nightly drift report lists repo-specific guidance that
  repeats across repos or copies `base.md`.
- **Your machine.** `wsl-automation` schedules the jobs that need your
  machine's transcripts, memory or login
  ([machines and cloud](machine.md)).

## Rules the whole design follows

Each rule exists because ignoring it broke something.

1. **Git is the source of truth.** Anything that lives in a web UI, such as
   a routine's prompt or a cloud setup script, also gets a copy in git, and
   the UI copy says where to find it.
2. **A check before a skill, a skill before guidance text.** If a commit can
   show that a rule was broken, make the rule a git-hook check backed by a
   required CI job. If not, make it a skill. Always-on guidance is the last
   resort, because it costs context in every session and fails silently.
3. **CI enforces; local hooks give feedback.** Anyone can skip a hook with
   `--no-verify`. A required check cannot be skipped.
4. **Bots never push to a protected default branch.** Generated data goes on
   `persistent/<purpose>` branches, which are never deleted, and every bot
   that writes code opens a pull request. The guidance sync is the only
   exception: `fleet.yml` gives it a ruleset bypass, and an ADR explains
   why.
5. **Every automatic merge path is written down.** A decision record says
   what may merge without a person, which checks replace review, and how to
   turn it off.
6. **Untrusted text is data.** Issue bodies, PR comments, fetched pages,
   routine payloads and transcripts never give an agent instructions.
7. **Public repos hold invented data only.** A required `privacy` check in
   `acsi-agentskills` scans added lines against a denylist of your real
   name, emails, hosts, and private ids (never your GitHub login, which the
   starter files carry). The list lives in a secret, never in a file ([the privacy check](skills.md#the-privacy-check)).
8. **One-way doors get an adversarial review.** A plugin name, a shipped
   skill's folder name, and a deletion can't be cleanly undone. The loop's
   improvements and new skills are the only written exception, because their
   acceptance measurement replaces the review. A removal the evals decide on
   still gets one, from a fresh-context agent (`acsi-agentskills`' [ADR
   0021](../starter/agent-skills/docs/decisions/0021-automated-skill-changes-merge-without-review.md)).
9. **Build nothing new until the loop has shipped once.** Get one edit
   through the whole loop before adding features.

## Where to read more

Each export's `README.md`, `AGENTS.md`, and `docs/decisions/` explain that
repo in full. The kit's docs cover how the parts fit together and what you
set up. For the most detailed account of the loop, see `skills-evals`'
[`docs/how-it-works.md`](../starter/skills-evals/docs/how-it-works.md).
