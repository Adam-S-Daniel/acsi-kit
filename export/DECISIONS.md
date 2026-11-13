# Kit export: what is left out or changed, and why

The owner, 2026-10-29: copy the real setup into the adoption kit; leave nothing
out without a compelling reason, and record every such decision here so it
can be reversed. Each entry says what was decided, why, and how to reverse it.
The per-file detail is in the manifests beside this file.

## Principles

- **P1. Copy, then substitute.** Each repo is exported from a pinned commit.
  Owner-specific literals become placeholders that the adopter's setup fills
  in. Everything else is byte-for-byte.
- **P2. Historical citations stay pointed at the source.** A link to a
  specific issue, pull request, commit or file-at-a-commit in the owner's repos
  records where a lesson came from. Rewriting it to the adopter's owner would
  point at something that doesn't exist. These links stay unchanged. Live
  references (a repo the code reads, an owner it scans, a branch it pushes)
  are substituted.
  Reverse: substitute them too and accept dead links.
- **P3. Generated files are regenerated, never substituted.** Lockfiles
  (`skills.lock`, `actions.lock`), digests in `repos.yml`, the generated
  `AGENTS.md`, `fleet-guidance.md` and the byte counts in `eval-coverage.yml`
  are rebuilt by the export with each repo's own tooling, because they hold
  hashes and numeric GitHub ids.

## Left out

| # | What | Kind | Why | Reverse by |
|---|---|---|---|---|
| X1 | Fastmail skills (`add-from-address`, `add-received-from-addresses`, `fastmail`) | personal | They drive the owner's own mail account through the owner's mail-automation repo. | Include them; an adopter would also need that repo. |
| X2 | The owner's writing-style skill and its eval fixtures | personal | It describes the owner's voice. | None sensible. |
| X3 | `docs/credential-runbook.md` (private registry) | private | It names the owner's real credentials and where they live. | None. |
| X4 | The source platform repo's eval fixtures and the four `evals/real-work/` seeds taken from it (about 1,800 files) | platform | They are copies of the owner's sites and test skills that only apply to that platform repo. | Include them along with the platform repo's skills. |
| X5 | `evals/real-work/_agent-guidance-196` | runtime-data | Its seed and checker pin real commit SHAs and byte-equal checks, so they can't be substituted. An adopter's fixture-supply job mines its own real-work cases. Tests that read these fixtures are pointed at a small invented seed instead. | Ship it unsubstituted as a read-only example. |
| X6 | Eval results branches (`persistent/eval-results`, `persistent/orchestration-state`) | runtime-data | They are the owner's measurements of the owner's skills; an adopter's own runs produce theirs. | Copy them as a baseline. |
| X7 | `docs/evidence/2026-10-07-workstation-retirement-117.md` | personal | It is a checkpoint on retiring the owner's own workstation (its machine and task names); nothing links to it. | Include it with the hostnames replaced. |
| X9 | **Content starts with one real item of each kind and a template** (owner, 2026-10-29 12:29 UTC; it replaces the same day's 02:02 UTC decision that content start fully blank). Skills, guidance sections and agent-checks checks each keep ONE real item copied unchanged (apart from substitution) from the owner's setup, plus a commented-out or inert template beside it: the skill `workflow-path-audit` (with the four eval fixtures under `evals/workflow-path-audit/` and a template in `templates/skill/`), the guidance section "A successful `git push` does not mean your commit exists" (with its fixture `evals/guidance/git-push-does-not-mean-commit-exists/` and an HTML-commented section template in `agents-md/base.md`), and the agent-checks check `skill-shell` (with a commented-out `.orig`/`.rej` example beside it). Every other skill, section and check, and the eval fixtures that test them, is left out. The machinery that delivers, measures, improves and retires them all comes along. Tests that only lock a left-out skill, section or check are removed and listed in the export's record; tests of the machinery use test-only fixtures. | owner choice | An adopter grows their own content through the loop, with a worked example of each kind to copy from instead of a blank page. | Delete the three real items and their fixtures (the first, blank form of X9: re-add the manifest excludes for them, restore the patches' blanking of `blank_content.py`, `blank_registry.py` and `empty_config.py`, and move the restored tests back into `removed_tests.txt` and the patches), or copy more chosen items in, one at a time (drop that item's `exclude` and add its tests back). |
| X10 | From `wsl-automation`: the restic backup, and the Remote Control session keeper. The waiting-on-you feed is **included** (owner, 2026-10-29: the dashboard's waiting list keeps all its plumbing, renamed from "Waiting on" the owner's name to "waiting on you"), and so is the usage census task (wrapper, Task Scheduler registration, checkout updater, tests), with a cron equivalent for Linux and macOS; the session miner is scheduled the same way. | personal | They maintain the owner's machine and dashboard; the census feeds the loop's value score. | Include them. |
| X8 | Scheduled tasks: Morning brief, Heartbeat, Watch for Work locally, Lockfile upstream daily check, Dashboard Hub refresh, Token sprint heartbeat, Rotate-keys reminder, one-shot eval-cap reminders, Watch reaper rejects, Cross-post watcher | personal or platform | They serve the owner's day, other projects or the platform repo, not the loop. | Add their prompts to the kit's routine list. |

## Changed

| # | What | Why | Reverse by |
|---|---|---|---|
| C1 | The two registry repos, whose names start with the owner's first name, become `acsi-agentskills` and `acsi-agentskills-private`: the owner's prefix is replaced by the generic `acsi-` (automatic continuous self-improvement). Plugin names take the same prefix (`acsi-anything-anywhere`, `acsi-coding-anywhere`, `acsi-coding-local`, `acsi-non-coding-local`, `acsi-private-anything-anywhere`), and so does the marketplace, which is named for its repo. The bare owner-name bundle label in fixtures becomes `acsi` (`acsi-writing-style`). | They carry the owner's name. A generic prefix keeps the names distinct from the source owner's and the set still reads as one set, which dropping the prefix would not. Plugin names are one-way once enabled, so an adopter must start with names they will keep. `_agent-guidance`, `skills-evals` and `repo-settings` keep their names. | Drop the prefix instead of replacing it (the first form of C1), or keep the `acsi-` names; an adopter could rename before first enabling. |
| C2 | Owners: the source owner's login → the adopter's owner (`example-adopter`); the second source owner → an optional second owner (`example-adopter-two`), in every case and separator form (`GH_TOKEN_<OWNER>`, `token_<owner>`, ...); a third account's examples → an invented third owner. A one-owner fleet sets the second owner to the first, and `bootstrap/lib/substitute.py` then drops the second owner's legs (One-owner fleets, below). | Owner names. | n/a |
| C3 | Code paths specific to the source platform repo are **kept**, with the repo names replaced by an invented example platform (`example-site-platform` and its consumers): the label-only allowlist in repo-settings (ADR 0016), the federated marketplace entry, the `platform.lock` branch in `sync.sh`, the release-tag carve-out in guidance and scorers. | They are generic mechanisms (a shared platform repo with consumer sites) that an adopter may grow into, and deleting them touches many tests. | Delete them and their tests. |
| C4 | The `scheduled-run-health` reusable workflow is copied from the source platform repo into the kit's `_agent-guidance`, and the four callers point at that copy. | `_agent-guidance`'s cron-coverage gate requires it, and the platform repo is not part of the kit. | Drop the callers and the gate. |
| C5 | The source owner's `verify-actions-lock` action stays as is: adopters use the owner's published, Apache-2.0 action. | It is a public action meant for reuse, and substituting the owner breaks the lockfile. | Fork it and substitute. |
| C6 | `evals/budget.yml` is reset to the standing defaults (weekly 30%, per run 3 points, stop at 80%), keeping the comments that explain the design and dropping the dated, week-by-week cap changes. | Those were the owner's spending decisions for particular weeks. | Copy the file as is. |
| C7 | Claude.ai ids (trigger, artifact, session, environment, project ids) become placeholders. Where a workflow hardcodes a routine trigger id, it reads a repo variable instead. | They are the owner's account objects. | n/a |
| C8 | Tests that read excluded fixtures (about 40 in skills-evals) are pointed at a small invented seed, and their expected values are updated; no test is deleted unless what it tests was itself left out. | Keep the tests' lessons without the excluded data. | n/a |
| C9 | The repo-settings workflow's two hardcoded owner steps (one per source owner) become the adopter's owner and the optional second owner. | Owner names. | n/a |
| C10 | Text that tells a story about the owner by name (for example "<name>'s standing rule", "<name>'s decision on 2026-10-06") says "the owner" instead, capitalized only where a sentence starts. Dates and measurements stay. | Names. | n/a |
| C11 | **Live registries list only the kit's repos.** `repos.yml`, `fleet.yml`, `dependabot.yml` entries, workflow repo lists and any other config the code acts on name only the kit's own repos (and, in `repo-settings`' `fleet.yml` and `_agent-guidance`'s `repos.yml` only, the invented example repos of C3, which steps 9 and 11 trim; skills-evals' workflows and `harness/registries.yml` do not name them, see "Cold-start fixes"). The owner's other repos (personal tools, sites, scratch repos) are dropped from config, and tests that pin those lists are updated. Mentions of those repos in history (ADRs, evidence, changelog analysis, routine findings) stay, like P2 citations. | Config that names repos an adopter doesn't have would sync into, or report on, repos that don't exist. History mentions are what lessons were learned on. | Keep the full list; the adopter trims it. |
| C12 | **Account-specific numbers become config.** GitHub App ids (the source's two bypass Apps' and any others), installation ids and similar numbers that differ per account are read from a variable or a single config file the bootstrap fills, never hardcoded in the kit. | They are the owner's App ids; an adopter's Apps have different ones. | n/a |
| C13 | **`repo-settings/fleet.yml` declares the base repos only; `skills-evals`' element ships in `repo-settings/fleet.evals.yml`** (owner, 2026-11-03, issue #12). The patch `patches/repo-settings/evals_fragment.py` finds the element by its parsed name (a PyYAML node tree, never a text anchor; exactly one, or the export fails) and moves its lines, comments included, under the fragment's header. `/adopt-evals` merges it back (`bootstrap/regenerate.sh evals-fleet`, step 40). The shipped tests read `fleet.yml` plus the fragment while it exists. | With the element in `fleet.yml`, a base-only setup had a `fleet.yml` naming a repo it did not have and a roster App id it did not need, so `repo-settings.yml`'s own `plan` job failed until evals were added, and `apply-settings.sh` had to hand the engine a filtered copy. | Drop the patch: `fleet.yml` declares `skills-evals` again, the base-only `plan` job fails until `/adopt-evals`, and `apply-settings.sh` again needs to leave a declared but absent `skills-evals` out of a filtered copy (its form before #12). |

## Kept on purpose (questions an inventory raised)

- **Agent changelogs, run logs and the routine findings** (`agent-claude-code.CHANGELOG.md`, `agent-codex.CHANGELOG.md`, `agent-changelog-runs.md`, `prompt-audit-runs.md`, the measured tail of `docs/routines/guidance-centralization.md`): they are analysis of the same vendors an adopter uses and the measured lessons the routines rely on.
- **ADRs and evidence files**, school bell-schedule ADR mentions, the Fastmail entries in `docs/skill-impact.md`: history, with names substituted.
- **Stub and full guidance modes**, the helper scripts and the full `repos.yml` schema.

## Scheduled tasks in the kit

Included: Fleet worker, agent changelog watcher, prompt-audit sweep, Memory
curation, the eval runner, Guidance centralization audit. Optional: Daily
security alert triage (needs a `security-alerts` repo the kit does not yet
include), Workflow health sweep and the "Dashboard refresh: every 2 hours" task plus its three merge-triggered refreshes, which keep the project dashboard (a claude.ai artifact in the owner's account that shows the loop, eval results and real-work impact) current (both run
scripts from the owner's project files, not a repo). Prompts that live only in
claude.ai are committed to the kit as files.

## Export record: `_agent-guidance` and `repo-settings`

How `export.py` carries out the entries above for these two repos. The
manifests (`manifests/_agent-guidance.yml`, `manifests/repo-settings.yml`)
hold every edit with its `why`; this section records the ones that are more
than a substitution, and every test the X9 blanking changed or removed.

### Substitution details

- **The retired registry.** The source owner's retired `agentskills` registry
  would become `example-adopter/agentskills` under C2 alone. It becomes
  `example-adopter/retired-agentskills` instead, which stays distinct from the
  live `example-adopter/acsi-agentskills` and reads as what it is, so history
  about the retired repo never reads as the live one.
- **C5 is narrowed to uses and links.** The source owner's `verify-actions-lock`
  is kept where it is used (`uses: ...@`), named in backticks, or linked
  (`github.com/...`). The same string as an element of a fleet registry
  (`repo-settings/fleet.yml`) is the owner's own repo list, so it is
  substituted like every other entry.
- **P2 exceptions.** `test/test-routine-merge-gate.js` and
  `docs/reference/agent-changelog-issue-map.txt` hold `owner/repo#N`
  strings that are test data, not citations; they are substituted so the
  fixture and its expected values agree (`protect_except`).

### C4 in practice

The reusable is imported from the source platform repo at a pinned commit to
`.github/workflows/scheduled-run-health-reusable.yml`, with the two scripts
it checks out (`scripts/audit-scheduled-runs.js`,
`scripts/check-platform-currency.js`). Its two legacy SHA pins become the
tags `actions.lock` already maps to the same commits (`actions/checkout@v7.0.1`,
`actions/setup-node@v7.0.0`), and `actions.lock` gets its entry. The
`_agent-guidance` caller uses the local path; the `repo-settings` caller uses
`example-adopter/_agent-guidance/...@<forty zeros>`, a placeholder the
adopter replaces (`REGENERATE.md`). The cron-coverage test that deletes the
caller's `uses:` line matches the key now, not the owner name.

### X9 in practice

- `agents-md/base.md` keeps its preamble, a template section, and one real
  section, "A successful `git push` does not mean your commit exists",
  copied byte for byte from the source (after substitution).
  `scripts/check-guidance-coverage.js` refuses a payload with no `##`
  heading (exit 2), so one real section is also the minimum the tooling
  accepts. The template is an HTML comment placed between the preamble and
  the real section, so no section's byte extent counts it. It shows the
  heading indented, never at the start of a line, so a line-regex reader
  cannot take it for a heading (the checker's markdown parse reads the
  comment as one html block either way). It departs from the manifest's own
  note, "do not put these ids into base.md itself", only by being a comment
  with no ids; the owner chose it.
- `agents-md/sections/*.md` keep their `##` heading and a one-line "None
  yet" body: the sync tests check that a requested section's heading arrives
  in the built `AGENTS.md`.
- `agents-md/eval-coverage.yml` keeps its header, the real section's row as
  the source has it (`covered`, fixture
  `evals/guidance/git-push-does-not-mean-commit-exists/` in `skills-evals`)
  and one `gap` row per empty section file (eight rows: the real section and
  seven sections); byte counts are regenerated.
- `docs/guidance-impact.md` keeps its header and entry format;
  `docs/agent-checks-lessons.md` keeps its header and table head.
- The agent-checks runner (`templates/agent-checks/agent-checks`, and the
  repo's own `.githooks/agent-checks`) keeps its events, the run log, the
  empty lesson slot (`check_lessons`) and `.agent-checks/local.sh`, and the
  `skill-shell` check exactly as the source has it (it refuses a `SKILL.md`
  or command file with a shell-command line, so it also guards the kit's
  own skill and skill template). Beside it is a commented-out example check
  (`.orig`/`.rej` leftovers). Removed checks: `rules-dir`, `secret-file`
  (path checks) and `staged-index`, `push-to-default`, `persistent-delete`
  (pre-push). The machinery's own ids remain: `repo-local`, `runner-error`,
  `tree-rev`.
  The PreToolUse guard (`agent-checks-guard.sh`) is machinery and is kept
  whole.

### X9: tests changed or removed

Moved to a test-only fixture (the test still exercises the same machinery;
the check it uses lives in the test):

- `test/test_agent_check_lane.py` (these use the template with the file's
  own `PATH_ARM` example lesson in place of the removed `secret-file` check,
  and they leave the real `skill-shell` check alone, so a run's `checks`
  list now starts with `skill-shell`): `test_wrong_expectation_is_reported`,
  `test_refusal_without_the_message_is_reported`,
  `test_tree_checks_every_path_of_a_revision`,
  `test_local_check_exiting_0_cannot_suppress_a_fleet_refusal`, and the
  run-log tests `test_passing_pre_commit_writes_one_line`,
  `test_refused_pre_commit_lists_the_check_and_keeps_the_message`,
  `test_repo_local_check_is_logged`, `test_ci_tree_and_unknown_events_write_nothing`,
  `test_unwritable_log_changes_nothing` use a fixture runner (the template
  with the file's own `PATH_ARM` example lesson) in place of the removed
  `secret-file` check.
- `test_case_that_already_refuses_under_base_fails` and the fleet-scan
  fixture's "already refused" repo use a repo-local `.agent-checks/local.sh`
  draft check for the base runner's own refusal.
- `test_pre_push_to_default_lists_push_to_default` becomes
  `test_refused_pre_push_is_logged_as_pre_push`: the run log's pre-push
  entry, from a fixture refusal on a feature branch.
- `CheckIdTests`: the core ids are the machinery's three and `skill-shell`,
  and the minimum `problem` call count is four, not seven.
- `test/fixtures/agent-checks-cases.jsonl` (the lane's case table):
  `ci-earlier-commit-caught` and `tree-refuses-committed-key` (renamed
  `tree-refuses-committed-draft`) keep their range and tree shape with the
  repo-local draft check standing in.
- `test/run-tests.sh`: "the delivered runner's ci mode refuses a committed
  .env" becomes "the delivered runner's ci mode runs the repo's own check",
  with a `.agent-checks/local.sh` committed in the test clone.
- `test/test-on-hold-label.js`: "fleet rule protects issues and PRs..."
  becomes "fleet payload stays under budget and matches its mirror", keeping
  the budget and mirror assertions; the test count stays nine.

Removed, because each locked only content the kit does not ship:

- Lane case table: `rules-dir-refused`, `claude-dir-other-file-passes`,
  `env-refused`, `env-local-refused`, `env-example-passes`, `pem-refused`
  and `ssh-key-refused` (the removed `rules-dir` and `secret-file` checks).

Restored for the one real check (owner, 2026-10-29 12:29 UTC): the six
`skill-shell-*` cases of the lane's case table
(`skill-shell-inline-refused`, `-fenced-refused`, `-command-file-refused`,
`-plugin-command-refused`, `-code-span-passes`, `-in-readme-passes`), which
the first blanking had removed with the check. The tests that asserted a
`checks` list or the set of check ids (`test_passing_pre_commit_writes_one_line`,
`test_refused_pre_push_is_logged_as_pre_push`, `test_repo_local_check_is_logged`,
`CheckIdTests`) name `skill-shell` again.
- `test/run-tests.sh`: "agent-checks persistent: deleting persistent/results
  is refused" (the removed `persistent-delete` check). The two cases beside
  it, a branch delete and a push to `persistent/*` passing, stay.
- `test/test-on-hold-label.js`: the `ON_HOLD_MUTATION=policy` branch, which
  mutated the removed on-hold rule's wording in `base.md`.

The skills registries ship one skill under the same entry (below).

### C11 in practice

`kit_repos` and `kit_owners` in `manifests/_common.yml` are the list; the
patches read it, and `tests/test_no_leaks.py::test_config_names_only_kit_repos`
fails on any other repo in a starter tree's `repos.yml`, `fleet.yml`,
workflows or `dependabot.yml` (parsed YAML, so comments, which are history,
are not checked).

- `_agent-guidance/repos.yml` (`patches/_agent-guidance/kit_repos.py`):
  `skills_bootstrap.repos` drops ai-usage-dashboard, claude-memory-map,
  fastmail-actions, scratch-claude-002 and verify-actions-lock;
  `skills_bootstrap.out_of_scope` drops scratch-claude-001, 4A, jc,
  rss-inator, scratch-jules-001, squarespacetemp and waiting-feed;
  `cron_coverage.fleet` drops ai-usage-dashboard, claude-memory-map,
  fastmail-actions and rss-inator; `cron_coverage.out_of_scope` becomes `[]`
  (every entry was a scratch repo, a fork or the third owner). Each entry
  goes with the comment that explained it. One `_agent-guidance` test pinned
  the list's size: `test/test-prompt-audit-sweep.js` ("sweep covers the
  declared fleet across both owners") now asks for at least 6 fleet repos,
  not 10.
- `repo-settings/fleet.yml` (`patches/repo-settings/kit_config.py`): drops
  retired-agentskills, claude-memory-map, squarespacetemp, fastmail-actions,
  ai-usage-dashboard, verify-actions-lock (the repo element; C5's `uses:`
  pins of the action are untouched), GHA-bench, rss-inator, jc, 4A,
  waiting-feed, security-alerts, the three scratch repos and the two forks.
- History mentions stay: script and workflow comments, ADRs, evidence, and
  `test/test-dependabot-config-health.js`, whose mocked fleet is the
  measured 2026-09 one (test data, not config).

Tests changed (`tests/test_repo_settings.py`):
- `RequiredStatusChecksFleetConfigTests.EXPECTED` and `PRE_EXISTING` lose
  the dropped repos' rows.
- `test_only_known_repos_declare_extras` expects skills-evals and
  `_agent-guidance` only.
- `test_other_repos_render_the_pre_migration_bypass` counts 8 repos, not 22.
- `test_the_mapping_is_one_for_one`: no repo is `manage: []` any more
  (`WERE_FALSE` is empty) and 6 repos are `manage: ["all"]`, not 19.
- `test_an_excluded_repo_is_given_no_labels` adds its own `manage: []`
  fixture element, since the kit's fleet excludes no repo.

Tests removed, because each locked a dropped repo's element:
`test_gha_bench_declares_deletion_only_persistent_ruleset` and
`test_security_alerts_declares_deletion_only_persistent_ruleset`.

### C12 in practice

`fleet.yml` writes the guidance sync App's id (default-branch bypass) as
`actor_id: "${GUIDANCE_SYNC_APP_ID}"` and the roster App's (skills-evals'
`roster/proposal` ruleset) as `"${ROSTER_WRITER_APP_ID}"`, the bootstrap's
names. The engine (`scripts/repo_settings.py`, `_actor_id`) reads that
environment variable when it renders a ruleset and refuses one that is unset,
empty or not a positive integer, so a missing id fails the plan instead of
dropping or inventing a bypass; a literal id still works. The
`repo-settings.yml` workflow maps both from repository variables in a
top-level `env:`; `schema.md` documents the form. The tests set invented ids
(900001, 900003) in `setUpModule`, and five new tests (`EnvAppIdTests`)
cover the variable, unset, empty and non-integer values, a literal id, and
the shipped fleet using both variables. The five ADRs that gave the
source's App ids beside the substituted App slugs now say `<roster App id>`
and `<guidance sync App id>` (`patches/repo-settings/app_ids.py`, which finds
the ids from the ADRs' "App id N" text, so the kit spells neither). This
reverses an earlier choice to keep them as history: paired with the
adopter's App names, the source's ids read as the adopter's.

### Changes to `export.py`

- Patches get `ctx["common"]`, the parsed `_common.yml` (an added key; every
  existing key is unchanged).

## Export record: wsl-automation

How `export.py` carries out X10 and the scheduling additions for
`wsl-automation` at 1c6893002aea500d43dcd25534a5fd7059c87b25. The manifest
(`manifests/wsl-automation.yml`) holds every exclusion and edit with its
`why`; the three patches (`patches/wsl-automation/`) say what they change in
their docstrings. This section records what is more than a substitution.
No change to `export.py` was needed.

### What X10 leaves out, and what stays

- **Left out** (37 files): the restic backup (`wsl-restic-backup.{ps1,sh}`,
  its excludes file, `Invoke-WslResticBackup`, `ConvertTo-WslMountPath`,
  `Invoke-RobocopyExe`, their tests); the session keeper and both launchers
  (`ensure-claude-session.ps1`, `Invoke-ClaudeSessionKeeper`, the session
  start/test/restore/snapshot helpers, `Test-CodexRemoteControl`,
  `Repair-WslUserRuntime`, the Windows Terminal argument builders, their
  tests); and, with no caller left, the backup lock functions. The manual
  `wsl --export` backup (`wsl-ubuntu-backup.ps1`, `Invoke-WslBackup`,
  `Test-WslActivity`, `Get-LastWakeTime`, their tests) goes too (notes Q2):
  it is the same backup feature, and it cannot run without the keeper's
  snapshot and the lock.
- **Kept** (notes Q1, the owner's decision): the usage census, the waiting
  feed, the ccstatusline sync, the Codex Cloud environment sync, the
  agent-trust scripts and `pull-repo.ps1`, with the checkout updater both
  sides share. `grant-keeper-batch-logon.ps1` keeps its name (the README and
  AGENTS.md cite it) and is reworded for the S4U tasks.
- **"Waiting on" the owner's name is "waiting on you"** in the feed script's header; its
  README section already said "waiting on you".

### Edits beyond substitution

- `Set-WslAutomationScheduledTasks` and `register-tasks.ps1`
  (`tasks_installer.py`): the backup, keeper and launcher tasks and their
  parameters go, including the two mandatory ones (`-BackupDir`,
  `-ResticRepoDir`, notes Q5), so `.\scripts\register-tasks.ps1` now needs no
  arguments. The Store-pwsh warning stays (it protects the two pwsh-based S4U
  tasks), and the explanation of the indefinite-repetition trigger moves to
  the ccstatusline trigger. The module manifest and loader drop the ten
  exported functions that are left out, and the `Backup` tag.
- Comments in kept code that named the keeper or the backup are reworded
  (notes Q3): `Get-WslAutomationDefaultPwshPath.ps1`,
  `New-WslAutomationRepoMutex.ps1`, `Update-CcstatuslineConfig.ps1`,
  `tests/CcstatuslineConfig.Tests.ps1`. `Register-WslScheduledTask.ps1`'s
  "interactive session launcher" and `Write-WslAutomationLog.ps1`'s example
  string stay; both read as general statements.
- `README.md` and `AGENTS.md` (`docs.py`): the sections about left-out code
  go (README: "Why staging", "Lock protocol", install step 3, five task
  sections, "Keeper semantics"; AGENTS.md: seven sections, notes Q4). The
  at-logon measurement is folded into "There is no WSL lifecycle event", and
  the transition-window lesson keeps its measurements without the backup's
  functions. The README gains "Session miner task" and "Linux and macOS"
  sections; AGENTS.md gains "Linux and macOS: one runner, three schedulers",
  which keeps the user-manager lesson (linger restarts a dead user manager)
  without the keeper's repair function or its incident link.
- **C12.** The waiting feed's fallback commit identity named the owner and
  carried a numeric GitHub user id; it is `Example Adopter` /
  `0+example-adopter@users.noreply.github.com`, and REGENERATE.md says to put
  the adopter's own there. The id itself is replaced by the common C12
  noreply rule (any `<digits>+<source login>@users.noreply.github.com`
  becomes `0+`), so the manifest no longer spells it.
- **Notes Q6.** The Codex Cloud bootstrap pin (a commit and a sha256 of the
  source registry's hook) becomes zeros that fail closed, with a comment;
  the README's link to that commit is reworded; REGENERATE.md gives the
  command.
- **Notes Q7.** The source owner's Windows repos folder, on another drive,
  becomes `C:\repos` (a repo rule ahead of the common `<drive>:` rule), because the agent-trust tests assert the default
  owner roots by value.
- `.gitattributes` drops the restic stanza; `.gitignore` gains the kit's
  junk lines; `ci.yml`'s `shell` job drops the restic ShellCheck targets and
  test step and gains the two new tests and their ShellCheck targets.

### Pester tests changed or removed

Removed with their subject (X10), as `patches/wsl-automation/pester_tests.py`
lists them: whole files `InvokeWslBackup`, `InvokeWslResticBackup`, `Keeper`,
`KeeperRestore`, `RepairWslUserRuntime` and `WslActivity` (`.Tests.ps1`) and
`wsl-restic-backup.test.sh`; in `Tasks.Tests.ps1`, 20 `It` blocks (backup,
keeper and launcher registration) and two `Context` blocks; in
`Helpers.Tests.ps1`, five `Describe` blocks (the backup lock and the launcher
argument builders); in `RepoUpdate.Tests.ps1`, the keeper and manual-backup
rows and the keeper's dirty-branch `It`.

Changed: every remaining `Set-WslAutomationScheduledTasks` call loses the two
removed arguments (32 calls); the S4U count is five, not six; the
no-interactive-principal check expects none; the history-failure check names
the census and ccstatusline tasks; the AST bootstrap test discovers every
`--exec /bin/bash ./<entry>.sh` action instead of naming two, so it covers
the session miner and any later Bash task. Added: three session miner `It`
blocks and its "already exists" `Context`.

**The Pester suite was not run.** No `pwsh` is installed where the export
was built, so neither Pester nor PSScriptAnalyzer ran against the exported
tree; `ci.yml`'s `test` and `test-linux` jobs are the first run. The bash
suite, ShellCheck over `ci.yml`'s list, and the ASCII check of every
`.ps1`/`.psm1`/`.psd1` did run.

### Added by the kit

- **The session miner task** (`Session Miner`, daily 07:17, S4U, 30 minute
  limit, `IgnoreNew`, no catch-up) runs `scripts/run-session-miner.sh`, a
  wrapper modeled on the census: the checkout bootstrap (interval 0), a
  shallow clone of skills-evals `main` whose `run_session_miner.sh` it runs,
  and one log line. The nine needs in the inventory notes map to: a
  KEY=value settings file read as data (needs 2, 3 and 5, because a
  `wsl.exe` action has no environment); fixed defaults for the denylist and
  the private registry clone (2, 3); preflight checks that exit before
  mining (denylist 2, clone origin 3 and 4, PyYAML 6); a refusal in CI or a
  cloud session (8); a scheduled run that refuses with exit 3 until a dry
  run by hand has succeeded (8); `--file-issues` refused unless
  `FILE_ISSUES=on` (8); in WSL without `WIN_HOME`, only the WSL transcripts,
  noted in the log line, rather than the untested `cmd.exe` lookup from a
  session 0 logon (5); a note when no state file exists yet (7); and a log
  that keeps only the miner's `session miner: ` lines and counts the rest,
  so a traceback's path never reaches it. Need 9 belongs to the skills-evals
  manifest: the miner's default registry paths and the marker string in
  `mine_sessions.py` are substituted there. The wrapper clones skills-evals
  to get the reviewed runner, which clones it again for the miner; the
  second shallow clone is the price of never running a local branch's
  runner.
- **Linux and macOS scheduling**: `scripts/unix/run-task.sh` (the per-run
  guard: PATH for a profile-less scheduler, `flock -n` overlap guard taken
  before the checkout update and held across the re-exec, coreutils
  `timeout` with the Windows task's limit, a native fast-forward-only
  checkout update that fails open, one log line) and
  `scripts/unix/install-schedule.sh` (systemd user service and timer with
  `Persistent=true` and an outer `TimeoutStartSec`; a launchd LaunchAgent;
  an idempotent crontab block). The census is the default job; the waiting
  feed and the session miner are opt-in with `--jobs`.
- **Tests**: `tests/run-session-miner.test.sh` (71 assertions) and
  `tests/unix-schedule.test.sh` (122 assertions since the second review's crontab fixes), both in `ci.yml`'s `shell`
  job and the manifest's suite. Each was checked to fail on a mutation of
  what it guards (the CI refusal, output withholding, the lock, the kill
  grace, `Persistent=true`). Neither ran on macOS: launchd output is checked
  by parsing the plists with `plistlib`, and bash 3.2 compatibility of the
  runner is by inspection only.
- `NOTICE` names the source repository and commit.

## Export record: agentskills

How `export.py` carries out the entries above for the source registry
(pinned d2d81b00c51388baf51c3922a540ae27839adcde, kit tree
`starter/agent-skills/`, repo name `acsi-agentskills`) and its private twin
(pinned c4bf812e4703e7b9fdd3f5408ed9198cba9df9be,
kit tree `starter/agent-skills-private/`, repo name `acsi-agentskills-private`).
Every edit, with its `why`, is in `manifests/agentskills.yml`,
`manifests/agentskills-private.yml` and `patches/agentskills/` (each
manifest's `source:` names the source repo).

### Left out

- **X9:** every skill of the public registry's four `plugins/*/skills/`
  folders (21, including the X1 Fastmail ones) but one, and the private
  registry's one skill (X2). The kept skill is `workflow-path-audit`
  (`acsi-coding-anywhere`), the single file `SKILL.md`: the source has no
  `PURPOSE.md` for it, and adding one would move its digest, so the kit does
  not (the registry's own rule is no mass backfill). The tests inside the
  skills that went went with them (`skills-doctor`,
  `launch-top-level-claude-session`, `migrate-claude-memory`,
  `sync-cc-settings-between-wsl-and-windows`, `rename-pdfs`). The template for
  your own skill is `templates/skill/` (`SKILL.md`, `PURPOSE.md`, and a
  `templates/README.md` saying how to adopt it), an overlay: it sits outside
  `plugins/*/skills/`, which every registry check, the lock generator and the
  README table read, so none of them sees it (checked by the registry's own
  suite).
- **X3:** `docs/credential-runbook.md` of the private registry. Never read
  into the kit.
- The plugins keep their manifests and machinery: `acsi-coding-local` keeps its
  clone-sync and credit-lane hooks and `bin/claude-credit`, which are not
  skills.

### Substitution details

- **The retired registry, bare.** In these two repos a bare `agentskills`
  (`acsi@agentskills`, the checkout `../agentskills`, `agentskills#55`, the
  marketplace key `"agentskills"`) names the retired predecessor. A manifest
  rule renames the bare word to `retired-agentskills` (and `-private`), as
  the common rule already does for the source owner's retired `agentskills`,
  so setup.sh sees the retired registry under a name of its own, distinct
  from the live `acsi-agentskills`, which reads as what it is.
  `agentskills.io` and `AGENTSKILLS_*` are
  untouched. The concatenated slug in `check_consistency.py`
  (`"<owner>/" + "agentskills"`) is caught by the same rule.
- Two hyphenated owner-name bundle labels the common rule's word boundary
  misses (a probe name and a test id) become `acsi`.
- The sync-delivered files (`fleet-guidance.md`, `.githooks/agent-checks`,
  `agent-checks-guard.sh`, `fleet-memory.sh`, `skills-bootstrap.sh`) are
  copied from the exported `_agent-guidance`, so they carry its X9 blanking
  and stay byte-identical to the copy its `repos.yml` pins. The managed half
  of each `AGENTS.md` is that tree's `build-agents-md.sh` output.
- Manifest owner and author names are the kit's `<your name>` placeholder;
  plugin descriptions and keywords describe each plugin's audience, not the
  skills the source shipped.

### C3, C4, C11 in practice

- C3: the federated `example-site-platform` marketplace entry, the
  dependabot cooldown `exclude` and the tests' `example-site-platform/`
  reusable carve-out are kept with the invented name.
- C4: `scheduled-run-health.yml` is kept (the inventory proposed dropping
  it) and calls `_agent-guidance`'s reusable at a forty-zero placeholder sha,
  as in `repo-settings`.
- C11: CI's census step cloned the platform repo and a consumer site; the
  clones and their two `scripts/skills_registries.yml` entries are removed
  (a clone of a missing repo fails the job), with the how-to left as a
  comment. The census keeps this registry and the optional private one.

### X9: machinery changed to accept an empty plugin

Three of the four plugins still start empty, so this stays (the owner's
2026-10-29 12:29 UTC decision added one skill to the fourth).

- `setup.sh` (public) refused a registry with no skills (`ERROR: no skills
  found`); it now prints that and goes on, since it links nothing any more
  (ADR 0017) and its settings and owner-machine steps still apply.
- `scripts/plugin_layout.json` keeps the four plugins and their
  `defaultEnabled`; `acsi-coding-anywhere` lists `workflow-path-audit`, the
  other three have `skills: []`.
- `generate_readme_table.py` refused a plugin with no skills ("renders no
  table rows"). It now renders one row, `none yet — add skills under
  plugins/<plugin>/skills/`, so the rule the refusal protected (every
  published bundle is named in the README) still holds.
- `ci.yml`'s two pytest steps, the AGENTS.md command and the pull request
  template prefix `shopt -s nullglob;`: with no skill tests the two plugin
  globs match nothing and pytest exits 4 on the literal. The kit's `suite:`
  command does the same.
- `skills.lock` is regenerated with the repo's generator (it lists the one
  skill); its ref is forty zeros until the adopter's first commit
  (REGENERATE.md).

### X9: tests changed or removed

Changed (the machinery is still tested):

- `test_check_consistency.py`: `test_the_layout_file_is_in_canonical_form`
  accepts an empty skill list (it asserted each list non-empty);
  `test_the_shipped_plugins_match_the_adr_0013_layout` treats a missing
  `skills/` folder (git keeps no empty folder) as no skills.
- `test_generate_readme_table.py`: `test_a_bundle_that_renders_no_rows_is_a_problem`
  becomes `test_a_bundle_with_no_skills_still_renders_one_row`;
  `test_problems_from_several_bundles_accumulate` and
  `test_build_rows_exits_nonzero_when_a_bundle_renders_nothing` use an
  unclassifiable (`gitlab`) entry as the bundle that renders nothing.
- `test_generate_skills_lock.py`: `test_the_source_limits_are_the_hooks_own`
  (cited by the vendored hook, defined in the left-out skills-doctor skill)
  is declared in
  `_TESTS_IN_ANOTHER_REPO`. (`test_this_repos_committed_lock_passes_check_format`
  had been changed to skip while the shipped lock listed no skills, since
  `--check-format` refuses an empty lock by design. The lock lists one skill
  now, so the test is the source's again and runs.)
- `test_setup_owner_machine.py`:
  `test_a_whole_directory_home_link_is_removed_only_when_it_is_ours` links
  the legacy home to `plugins/acsi-coding-local/hooks/` (a shipped folder under
  `plugins/`) instead of the absent `skills/`.
- `test_agent_checks.py`: each scratch repo gets a test-only copy of the
  runner (which ships `skill-shell`) with a lesson in its slot that refuses
  the paths the source's `secret-file` and `rules-dir` checks refused, so the
  pre-commit, pre-push, ci, installer and real-git tests run unchanged
  against it.

Removed, because each locked only a check the kit does not ship:

- `test_agent_checks.py`: `test_pre_push_refuses_the_default_branch` (two
  cases) and `test_pre_push_uses_the_remotes_recorded_default_branch`
  (`push-to-default`), and
  `test_pre_push_refuses_while_changes_are_staged_but_uncommitted`
  (`staged-index`).

### The private registry's suite

It has no tests; its one CI job runs the agent-checks runner over the
change. The kit's `suite:` runs that (`ci "" HEAD` and `tree HEAD`) and
`setup.sh` with a scratch HOME, which must succeed with no skills.

### Environment note

Two hook tests (`test_every_unsearchable_child_is_named_not_just_the_last`,
`test_an_unsearchable_child_with_an_unsafe_name_is_still_reported`) run
the hook as `nobody` through `setpriv` when the suite is root, so they need
the checkout's parent folders searchable. They fail the same way on the
unmodified source in a 0700 temp folder. The suite's `setup:` opens the
checkout and its parent (`chmod o+rx`) when run as root.

## Export record: skills-evals

How `export.py` carries out X4, X5, X6, X9, C4, C6, C7, C8, C11 and C12 for
`skills-evals` at 99c667f93c67a3ddd0630bf7aadbcb43e506d43c (which adds
`dashboard/`). The manifest (`manifests/skills-evals.yml`) holds every
exclusion, substitution and edit with its `why`; the patches
(`patches/skills-evals/`) say what they change in their docstrings. This
section records what is more than a substitution.

### What X4, X5, X6 and X9 leave out, and what stays

- Every skill fixture directory under `evals/` but one (24 of 25 skills;
  `evals/workflow-path-audit/`, with its four fixtures, stays), every
  guidance fixture but one (28 of 30; `evals/guidance/_delivery/` and
  `evals/guidance/git-push-does-not-mean-commit-exists/` stay), all five
  `evals/real-work/` seeds and `badges/workflow-path-audit.json` (a
  generated result, the owner's measurement). No results branch is copied
  (X6). The kept fixtures are byte copies after substitution. The guidance
  ones are excluded one directory at a time, so a new source section's
  fixture is not copied by accident.
- Kept as machinery: `evals/orchestrator-scenarios/` (the orchestrator's
  own scenarios, no skill), `evals/guidance/_delivery/`,
  `evals/guidance-bridge-canary/` and `evals/propagation/` (probes of the
  delivery path), the config files (`roster.yml`, `roster-policy.yml`,
  `gate-policy.yml`, `improve-policy.yml`, `budget.yml`), `harness/`,
  `scripts/`, every workflow and `dashboard/` with `config.example/` and
  `inputs.example/` (the private `config/` is not in the source tree).
- `evals/scheduled.yml` keeps the rows of the two kept fixtures, as the
  source has them (the skill's `required-check-routing` and the section's
  `hook-refused-commit`, readiness notes and all), so the weekly planner has
  something to run on day one; the other 30 rows are dropped.
  `evals/non-coverage.yml` ships `skips: []`. Each keeps its header
  (`patches/skills-evals/empty_config.py`). `scripts/plan_scheduled_evals.py`
  refused an empty schedule; it still accepts 0 to 256 entries, so an
  adopter who replaces the two sample rows with their own can pass through
  an empty list (the tests of that, `test_issue_scheduled_fixtures.py`, keep
  their X9 edit).
- `evals/real-work/README.md` (overlay) says the directory ships empty and
  how the fixture supply routine fills it.
- Symlinks: the source has 22. The 14 inside left-out fixture seeds went
  with them; the 5 `evals/orchestrator-scenarios/*/seed/bin/gh` links and the
  3 in the kept `evals/workflow-path-audit/*/seed/bin/` stay, and the
  invented `test/fixtures/fake-gh/seed/bin/gh` adds one (9 in all, each
  resolving to `harness/fakes/gh`).

### C8: the invented test-only fixtures

`overlay/skills-evals/test/fixtures/` holds small invented fixtures, laid out
as they would sit in a checkout, named after source skills only as test data
(four `writing-adrs`, four
`guidance/anything-you-name-gets-its-link` and one
`guidance/finding-your-unknowns` fixture, three pairwise `acsi-writing-style`
fixtures, two `github-actions-repo-settings` fixtures, one
`real-work/example-real-work-1` whose seed holds only an npm and a bundler
lockfile, example `non-coverage.yml` rows, and `fake-gh/`, a seed of invented
`gh` payloads for the shared fake). `test/example_evals.py` builds a scratch
git checkout (the repo's tracked files plus those fixtures in `evals/`, and a
four-fixture schedule) for the tests whose machinery reads a checkout's
committed fixtures: dispatch validation, the weekly planner, the improve and
guidance-improve fire checks, the skill census allowlist, `dev_setup.sh`'s
directory lists.

The test edits are 84 exact old/new pairs in
`patches/skills-evals/retargets.txt`, one section per file with its `why`
(24 files; the earlier "85 pairs, 22 files" had drifted). Edits that are more
than a path change:

- `test_issue_scheduled_fixtures.py`: the empty schedule moved from the
  bad-schema list to an assertion that it is valid.
- `test_issue_local_eval.py`: the left-out `ci-watcher-loops` checks are
  inlined.
- `test_issue_97.py`: four lines checking the left-out windows-elevation
  fixture's env block are dropped. (Two harness tests that read the scheduled
  workflow-path-audit fixture had been pointed at an invented copy; the real
  fixture ships now, so they are the source's again.)
- `run_tests.py`: the fake `gh` tests (`TestIssue84*`) drive
  `test/fixtures/fake-gh`; three expected payload strings are the invented
  seed's, the in-world allowlist is empty, and the fixture-wide scans (env
  blocks, `.git` globs) also cover test fixtures and nested `evals/`.
  `TestIssue81` reads the invented pairwise fixtures; its judge-call pin no
  longer reads the left-out README, and its end-to-end rank uses an
  invented candidate.
- `test_issue_followups.py`: follow-ups reaching both arms is checked on a
  fixture the test writes.
- `test_issue_64.py`: the committed non-coverage file must still load; the
  example rows are held to its rules.
- `test_issue_70_retirement.py`: `FIXTURE_ALIASES` is checked only for the
  skills the example checkout has (one).
- `test_issue_real_work_fixtures.py`, `test_issue_dev_setup.py`,
  `test_issue_board_feed.py`: read the invented real-work fixture; the
  floors are its counts (4 manifests, 7 classification cases).
- `test_issue_closed_loop_planner.py`: fire-check is pointed at the example
  checkout's `evals/`, since a module imported earlier in the same worker
  keeps the repository's.

`patches/skills-evals/machinery_tests.py` also prunes `test/shard_weights.json`
to the tests that still exist (40 keys to 17), keeping its serialization.

### Tests removed

Each locks content the kit leaves out. Single tests and classes are listed in
`patches/skills-evals/removed_tests.txt` (673 entries, each group commented):
581 in `test/run_tests.py` (the fixture-hardening classes of the left-out
skill fixtures, `TestIssue74`-`TestIssue92`, the vendor-release check, the
windows-elevation fixture and its stand-in `powershell.exe`, 74 tests of the
cms-stuck-pr-triage fixture's checks and rubric, 12 tests of the
owner's writing-style fixtures' own avoid list, facts and rubrics, which had
passed vacuously over an empty directory),
34 in `test_issue_124_guidance_gates.py`, 35 in `test_issue_89_fixture.py`,
13 in `test_issue_94.py`, 5 in `test_issue_real_work_fixtures.py` (the
committed fixtures' seeds, prompts and red/green runs), 2 in
`test_issue_371_scheduled_fixtures.py` (the source schedule's size and
measured bytes) and one each in `test_issue_64.py` (the test-canary row) and
`test_issue_followups.py` (rename-pdfs' follow-up text), and the whole
`TestIssue80Supersede` class, whose module stays as a helper (below).

**Restored after review (2026-10-29).** Seven tests the first pass removed
test machinery, not left-out content, and are back:
`TestIssue81::test_normalisation_leaves_a_sign_off_on_its_own_line`,
`test_every_committed_shape_keeps_the_sign_off_it_was_written_with` and
`test_the_signoff_survives_the_new_width` (sign-off normalisation, on
invented names: the one-word sign-off is `Alex`, so its expected tail is
`the meantime.\nAlex`); `RealWorkFixtureTests::test_each_fixture_loads_as_a_subject_agnostic_draft_or_promoted`
and `test_each_checker_is_the_pull_requests_own_test_file` (the invented
`example-real-work-1` gains `strip_agent_context`, a `repo_tests` check and a
`checker/` test file to satisfy them); `CommittedFixturesTests::test_the_committed_fixtures_pass_the_static_check`
(its floor of three committed fixtures is dropped: it checks whatever the
adopter's scaffolds commit); and `JudgeDiffTests::test_build_judge_diff_on_the_real_disarm_fixture_hides_prod_internals`
(it builds the invented `test/fixtures/evals/nested-repo-diff` seed, a bare
`prod.git` and a clone, instead of the left-out disarm fixture). The two
fixture-shape tests were checked to fail on a broken input (a fixture
without `strip_agent_context` or `checker/`). The 581 `run_tests.py` entries left were then re-audited
class by class: an AST walk of each removed test, its class, its base
classes and the helpers it calls finds the left-out fixture it reads in
every one. The verdicts, per class, are at the top of `removed_tests.txt`. The manifest leaves out 24 whole modules that test nothing else
(`test_issue_71_trigger_set`, `_75`, `_75_onboarding`, `_76` and its three
siblings, `_78`, `_80_why`, `_87`, `_88_fixture`, `_90`, `_91`, `_93`, the
three `bash_ci_*`, `ci_job_performance_browser_cache`, the three
`skills_doctor_*` and the three `vendor_release_*`) and their helper
(`test/vendor_release_fixtures.py`).

**Restored for the kit's two real fixtures (owner, 2026-10-29 12:29 UTC).**
The first pass left these out with the fixtures they read; the fixtures ship
now, so the tests are back as the source has them:

- The three `wpa_*` modules (`test_issue_wpa_companion_skip_pair`,
  `_moved_test_dir`, `_workflow_doc_in_step`) and their helper
  `test/workflow_path_audit_case.py`, which test the workflow-path-audit
  skill's other three fixtures. `_workflow_doc_in_step` imports the
  pattern-anchoring helpers of `test_issue_80_supersede`, so that module stays
  as a helper: its one test class, which locks the left-out
  `writing-adrs/supersede` fixture, is removed and its docstring says so. The
  runner requires every discovered module to contribute a test, so the helper
  gains `AnchoringHelperTests` (3 tests of `anchoring_problems` itself, added by
  `retargets.txt`).
- `ObjectiveAsymmetryTests` (3 tests, `test/run_tests.py`), which read the
  source `required-check-routing` fixture's seed anchors and eight checks.
- `PushFixtureTests` (3 tests, `test_issue_124_guidance_gates.py`), which run
  the `git push` section's `hook-refused-commit` fixture's trap, its bypass
  and its fix through the scorer. `FixtureLayoutTests::test_each_covered_section_has_fixtures_and_one_has_four`
  stays removed: it pins the source's thirty-section set.
- Retargets undone because the real fixture exists: the invented
  `test/fixtures/evals/workflow-path-audit/required-check-routing` is gone
  from the overlay, and `test_issue_202_harness.py`, `test_issue_66.py`,
  `test_issue_97.py` (two harness tests), `test_issue_71.py` (one
  copy of the fixture) and the `EVAL_DIR` and `FLAT_SOURCE` constants of
  `run_tests.py` and `test_issue_local_eval.py` read `evals/workflow-path-audit/`
  again. The example checkout (`test/example_evals.py`) now gets that
  fixture from the repository's tracked files and names it in its schedule.

Left as they were, because they test machinery on a fixture set the kit does
not have: `test_issue_scheduled_fixtures.py`, `test_issue_371_scheduled_fixtures.py`
(they read the example checkout and its schedule; the source schedule's size
and measured bytes are not the kit's), `test_issue_70_retirement.py` (the
`FIXTURE_ALIASES` loop runs for the skills the checkout has) and the dispatch
validation tests, which still run in the example checkout.

### C4, C6, C7, C12 in practice

- C4: `scheduled-run-health.yml` calls `_agent-guidance`'s
  `scheduled-run-health-reusable.yml` at a placeholder sha
  (REGENERATE.md).
- C6: `evals/budget.yml` drops the temporary-raise comment and sets
  `weekly_cap: 0.30`; the allowance-guard test asserts the loaded budget
  equals the standing limits.
- C7: `routine-eval-fire.yml` reads `ROUTINE_TRIGGER_ID` from the
  `routine-fire` environment (the job now names it), beside the bearer
  secret, as `bootstrap/set-secrets.sh` stores them; the C7 row says "repo
  variable", and an environment variable is the stricter scope the kit's
  bootstrap already uses. The step refuses a value that is not
  `trig_[A-Za-z0-9]{1,64}` before curl runs. Three tests were added
  (URL built from the variable, malformed values stop before curl, the job
  reads the environment) and three were updated. The routine prompt is
  committed as `docs/routine-prompt.md` (`inputs/skills-evals/`).
- C12: ADR 0003's App id is `<roster App id>`.
- `.gitignore` adds `.pytest_cache/`, `node_modules/` and `.DS_Store`, the
  paths `copy-starter.sh` skips that it did not already name.

### protect_except

Three files get their citation-shaped spans substituted because tests
compare them with substituted code: `test/issues/test_issue_70_retire.py`,
`scripts/improve_gate.py` and `test/issues/test_issue_real_work_miner.py`.

### Changes to `export.py`

- `inputs:` (additive): files kept under `export/inputs/<repo>/` are
  substituted and written into the tree.
- `_SENTENCE_PREFIX` is written without nested quantifiers that backtracked
  catastrophically on long comment runs; it matches the same prefixes.

### Suite result

Both runs used the same container, `bash scripts/dev_setup.sh`, then
`python3 test/run_tests.py --jobs auto` in a PID namespace, in a fresh git
repository. The unmodified source archive: 67 failed, 5835 passed, 73
skipped. The export: 67 failed, 4441 passed, 60 skipped. The 67 failing test
ids are the same set in both (`test_issue_202.py`, `test_issue_370.py`,
`test_issue_88.py`, `test_issue_eval_on_merged_roster.py`), so they come from
the source at this commit in this environment, not from the export. (An
earlier version of this record said they "fail the same way with `env -i`";
that was not what was measured.) Their causes were traced afterwards and are
in `starter/known-failures.txt`: this container's `/etc/gitconfig` has an
`includeIf` path starting with `~/` that git cannot expand under the tests'
HOME-less environment (202, eval_on_merged_roster); the container sets
`CLAUDE_CODE_REMOTE_SESSION_ID` (370); Python 3.13's `Path.resolve()` no
longer raises on a symlink loop (88; CI uses 3.12). With the gitconfig masked
and the variable unset, 202, eval_on_merged_roster and 370 pass. None is a
source defect; the first two are tests not hermetic against the machine. `bwrap` is present (`/usr/bin/bwrap`), so
no workspace-executing scorer test failed closed.

## Review fixes (2026-10-29)

Decisions taken, and departures from the entries above, while fixing a
review of the first export. Each is carried out by a manifest rule, a patch
or an overlay, never by editing a starter tree.

### The leak scan reads the whole kit, and private details stay outside it

- `export/tests/test_no_leaks.py` scans every file of the kit (`export/`,
  `docs/`, `bootstrap/`, `.claude/`, `README.md` and `starter/`), paths
  included, for the public tokens listed under `leak_scan:` in
  `manifests/_common.yml`: the source owners' logins and first name (also
  in the possessive form a file name may carry), the sites, the machine names, the Windows repos path, claude.ai
  trigger, session, environment, artifact, project and chat ids (the short
  artifact form too), Anthropic federation ids, numeric noreply ids other
  than `0+`, the left-out platform repo's name and email addresses. Only
  P2 citation spans, `export/manifests/` (the substitution rules must spell
  what they replace) and two counted per-file allowances are exempt.
- Private details (personal details that appear in no source repo) are not
  in the kit at all, so they cannot be in the test either. The test reads
  them at run time from `PRIVACY_DENYLIST` or `PRIVACY_DENYLIST_FILE`
  (outside the kit), the registry's `check_privacy_denylist.py` format, and
  reports hits as `path:line: pattern #N` only. With no list it fails when
  `CI=true` and is skipped locally; a planted-token test proves it can fail
  and that it never prints the match.
- C12 gains three common substitution rules: a numeric noreply id before a
  source login becomes `0+`; the numeric id written beside the source
  owner's login becomes `<user id>`; and the short claude.ai artifact form
  (`claude.ai/artifact/<id>`) becomes `.../EXAMPLE`.

### `actions.lock` keeps its publisher ids

`actions.lock` records each action owner's numeric id. The kept C5 action
is published by the source owner, so its entry carries that account's id.
An earlier fix set it to `owner_id: 0` with a common patch; a second review
reverted that (2026-10-29): the id belongs to the publisher of a shared,
public action, GitHub shows it to anyone, and `gh actions-lock --no-narrow`
writes it back on every regeneration, so a zero only made the lockfile
disagree with its own tool. The patch (`patches/_common/lock_owner_ids.py`)
and `export.py`'s `common.patches` hook that ran it are gone, and the id is
not on the private denylist's list of what the kit must not hold (above).

### Account ids are read from variables

- **Anthropic workload identity federation (C12).** `eval.yml`'s two token
  exchanges named the source's federation rule, organization, service
  account and workspace. They read four `skills-evals` repository
  variables (`ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`,
  `ANTHROPIC_SERVICE_ACCOUNT_ID`, `ANTHROPIC_WORKSPACE_ID`), checked by
  shape and passed to `jq --arg` (`patches/skills-evals/federation_vars.py`).
  A failed exchange logs the HTTP status and the error type only; it used
  to print the whole response body. The bootstrap registers the four as
  optional `fleet.env` keys and `REPO_VARIABLES` in a new `federation`
  group (create-environments.sh sets them when filled in; verify.sh checks
  them only with `--only federation`); `docs/evals-and-loop.md` has the
  set-up ("Workload identity federation"), and the quick start gains an
  optional step 25 (later steps renumbered 26 to 31). Two roster App
  confinement tests forbid any `vars.` reference outside `roster-pr`
  (`test_issue_202.py` `TestRosterAppTokenIsConfined`,
  `test_issue_eval_on_merged_roster.py` `TestRosterPrStillHoldsTheAppTokenAlone`);
  a retarget drops exactly the four federation references before that
  check, so any other `vars.` in the `eval` or `roster` job still fails it.
- **Other per-account ids found by a sweep of every tree:** a handoff
  note's ruleset id and two fixtures' real Claude Code session id in
  `_agent-guidance` (`patches/_agent-guidance/account_ids.py`), and the App
  ids in repo-settings' ADRs (C12 in practice, above).

### skills-evals' HANDOFF.md ships as a blank template

The source's `HANDOFF.md` is that repo's operating record: dated sessions,
the owner's decisions, links to the owner's issues and the owner's numeric
id. The kit ships an overlay with its headings and a one-line purpose
each. `AGENTS.md` keeps its pointer to it, and the pointer and
`docs/how-it-works.md` no longer link the source owner's status-board
issue: the adopter keeps their own, linked from HANDOFF.md.

### Live output links the adopter's own records

Text the adopter's bots publish (pull request bodies, impact entries, a
scaffold's tracking.json) linked issues in the source owner's repos, or
built links on the adopter's repo with the source's issue numbers.
`patches/_agent-guidance/owner_links.py` and
`patches/skills-evals/owner_links.py` point each at the decision record
in the adopter's own repo that holds the same rule (sync.sh: the README's
"The CLAUDE.md bridge"; the improvement loop: skills-evals ADR 0005;
removals: ADR 0014), or drop a "Part of ..." line, and set the scaffold's
tracking issues to null; the tests that pinned the old text assert that no
issue link is left. Left as they are: `harness/run_eval.py`'s and
`bump-consumer-locks.sh`'s citations in messages a person reads at the
terminal, and `scaffold_skill_gaps.py`'s links on the adopter's own repo,
whose body format `test_issue_60` parses.

### Routine specs fit an adopter

`patches/_agent-guidance/routine_specs.py` edits the guidance
centralization Routine (its stored-prompt snapshot and its source): the
fork control is "the forks your enumeration finds", the attached
repositories are the kit's six, counts are computed from the run's own
enumeration rather than carried from the source, the trigger id is the
adopter's Routine's own, and the source's measured history stays under
headings marked "(source system history)". The stored prompt's byte count
and sha256 are recomputed. The prompt-audit sweep's private-repo list is
the kit's. A new test, `test_routine_prompts_name_only_kit_repos`, extends
C11 to every routine prompt file: any `<owner>/<repo>` outside a marked
history section must be a kit repo.

### One-owner fleets

When `OWNER_TWO` equals `OWNER`, `bootstrap/lib/substitute.py` parses every
YAML file that names the second owner and drops the second owner's legs
that would otherwise duplicate the owner's (keys, step items, flow-list
elements, words in an owner list), checking that the result loads to
exactly the original's data minus those nodes. Before this, a one-owner
fleet got workflows with duplicate keys (`GH_TOKEN_<OWNER>` twice), which
a YAML loader rejects. `bootstrap/tests/check-one-owner.py` substitutes
every starter YAML file with one owner and loads each with a
duplicate-key-rejecting loader; with the collapse turned off it fails.

### Smaller fixes

- **Sentence case.** `export.py`'s `_at_sentence_start` capitalized "the
  owner" at the start of every wrapped line. A line that only wraps the
  sentence before it (same comment marker, no list bullet, previous line
  ending without sentence punctuation) is no longer a sentence start.
  `export/tests/test_sentence_case.py` covers it.
- **Names.** The wrapping scorer's sign-off example and the surname-only
  bio test data use the invented `Alex Rivera`. skills-evals ADR 0015's file
  name no longer carries the owner's name.
- **The federated marketplace example** describes an invented platform,
  not the source platform repo's stack.
- **Manifest names.** The two registry manifests are `agentskills.yml` and
  `agentskills-private.yml` (with their overlay and patch folders). Those are
  manifest keys, the names `--only` and `--skip` take, not the exported repo
  names (`acsi-agentskills`, `acsi-agentskills-private`); each keeps the
  source repo's name in `source:`.
- **macOS.** `copy-starter.sh` and `regenerate.sh` use no GNU-only flag
  (`realpath -m`, `sed -i` without a suffix, `sha256sum`); the kit's own
  test suites assume GNU tools (`docs/before-you-start.md`).

## Second review fixes (2026-10-29)

What a second, independent review found, and how each is carried out
(manifests, patches and overlays only; the starter trees are re-exported).
Departures from the entries above are marked **Departure**.

### The kit is committed whole, and `--check` reads git

- The repo-root `.gitignore`'s `**/[Bb]in/*` and `*.log` kept ten exported
  files out of git: `bin/claude-credit`, the five orchestrator scenarios'
  `seed/bin/gh` links, and the fake-gh seed's `bin/gh` and replay `.log`, in
  the starter and the overlay. A clone failed agent-skills' credit-lane
  tests and skills-evals' `TestIssue84*` and `test_issue_65`. Two scoped
  negations at the end of the root `.gitignore` re-include them under the
  kit; each tree's own `.gitignore` still applies inside it.
- `export.py --check` compares a fresh export with the tree git tracks (the
  index's paths, modes and blobs: `git ls-files -s` and `git cat-file
  --batch`), not with the disk, so an ignored or unstaged file fails it.
  Outside a git work tree it compares the disk and says so. The two labels
  in `diff_trees` were reversed and are swapped back ("only in the fresh
  export", "only in the committed tree").
- `export/tests/test_kit_tracked.py` fails on any file under the kit that
  git does not track (test-run junk aside), and proves on a scratch repo
  that an ignored `bin/` file and `.log` are caught and that the negations
  clear them.
- `export.py` gains `--skip REPO ...` (refused when another exported repo
  needs the skipped one), for CI below.

### The kit's tests run in CI

- `run-all-tests.sh` also runs `export/tests` and `export.py --check`.
  **Departure:** the check needs the source checkouts beside the kit's
  repo; where they are missing (any copy of the kit) it prints SKIP, not
  PASS or FAIL.
- `_agent-guidance`'s `ci.yml` `checks` job (no new job, so no ruleset
  change) gains a kit-changed detection step (the kit, the root
  `.gitignore`, `ci.yml`; it runs when it cannot tell), `actions/setup-python`
  (`v7.0.0`, locked in `actions.lock` beside the tags it already held) and
  one step that runs the kit's tests and `export.py --check`. The denylist
  reaches it through `env:` from the `PRIVACY_DENYLIST` repository secret;
  unset or blank, the step fails when the kit changed. `test/run-tests.sh`'s
  `test_ci_adoption_kit_step` (group `self_hosted`) locks the step's shape,
  runs the detection step on scratch git ranges and the check step with a
  blank and a set secret.
- `export/fetch_sources.py` fetches each manifest's source and import at
  its pinned commit (`git fetch --depth 1`, no credential) for that step.
  **Departure:** the private registry's source is private, so CI checks
  every tree but `agent-skills-private` (`--skip agentskills-private`, the manifest key); that
  tree is still leak-scanned and checked as tracked there, and fully
  checked by `run-all-tests.sh` where its source is.
- **Departure (the private scan):** the denylist scan skips exactly one
  line shape, `owner_id: <digits>` in a `.github/workflows/actions.lock`
  (see "`actions.lock` keeps its publisher ids" above): the owner's list
  holds the owner's numeric id, which is that public field's value.
- The leak scan decodes base64 (standard and URL-safe) and hex runs and
  searches the printable ones for the public tokens and the private list
  (a hit reads `<token> (encoded)`). skills-evals' fixture-scan test listed
  a Basic credential that decoded to the source owner's first name; it is
  `alex:hunter2` now (`patches/skills-evals/invented_credential.py`, which
  finds it by decoding and spells neither).

### Federation is optional for the weekly roster refresh

`roster-refresh.yml` dispatches `eval.yml` with `roster_only` weekly, and
the `roster` job minted an Anthropic token on every dispatch, so with the
four federation variables unset it failed every week.
`patches/skills-evals/federation_vars.py` gives the roster job's mint
`id: federation`: all four empty exits 0 with a `::notice::` and
`federation=off`, and "Refresh the model roster" then publishes no roster
and says so in the step summary. One set without the others, or a
malformed value, still fails, and so does the `eval` job's mint, which an
eval leg needs. `test/issues/test_issue_federation_optional.py` (overlay)
runs both steps' scripts under `bash -e` with a fake `curl`.
`docs/evals-and-loop.md` says what happens with the variables unset.

### Setup scripts

- `create-apps.sh --dry-run` writes no manifest file (it prints the two
  paths it would write); `install-machine.sh --dry-run` no longer fetches
  in an existing clone (a fetch writes its refs and `FETCH_HEAD`); it prints
  the fetch and the fast-forward it would do.
- wsl-automation `install-schedule.sh cron` refuses when `crontab -l` fails
  for any reason but "no crontab for <user>", and when the crontab has an
  unpaired, doubled or reversed BEGIN/END marker, changing nothing.
- `bootstrap/lib/common.sh` refuses bash older than 4.4 (`bash_version_ok`),
  before anything runs.
- `set-secrets.sh` reads the denylist's mode with `os.stat`, not GNU
  `find -perm /077`, which BSD find rejects.
- Each has tests: `bootstrap/tests/test-bootstrap.sh` (the dry runs write
  and fetch nothing, the guard, the mode warning both ways) and
  wsl-automation's `tests/unix-schedule.test.sh` (15 new assertions).

### `/adopt` runs from a copy of the kit

Claude Code loads `CLAUDE.md` (and `AGENTS.md` through its import) from
the starting folder and every folder above it, and the enclosing git
repository's root `.claude/settings.local.json`; the shared
`.claude/settings.json` is read from the starting folder only (Claude Code
memory and settings docs; checked with Claude Code 2.1.312 on a scratch
parent repo: the parent's `CLAUDE.md` and `settings.local.json` hook
applied in a subfolder, its `settings.json` hooks did not). So run from
inside the clone, `/adopt` carried the source owner's guidance, and run
from the clone's root, its `fleet-memory` and `skills-bootstrap` hooks.
The README's "Start here" and the quick start now say to copy the kit out
of the clone first, and the skill checks `git rev-parse --show-toplevel`
and stops inside a repository. The kit carries a copy of the repo's
`LICENSE` (the README linked `../../../LICENSE`, outside the kit);
`test_kit_tracked.py` holds it equal to the repo's.

The skill told Claude to `--mark` every browser step, but `status.sh`
accepts `--mark` only for `ask` steps; it now marks only those and re-runs
`status.sh` for the rest (steps 5, 6 and 25 are browser `verify` steps).
A bootstrap test holds the skill's `--mark` paragraphs to `ask` steps.

### Smaller fixes

- `docs/routines.md` names example environments, not the owner's.
- skills-evals: the judge-mode refusal's report cell and the propagation
  Routine's retirement plan no longer link the source owner's issues
  (manifest edits; the history header keeps its citation).
- acsi-agentskills: `install-agent-hooks.sh`'s owner list named the first owner
  twice (the source's two letter cases, folded by C2); one entry now, and
  `test_agent_checks.py` holds the list unique.
- `starter/known-failures.txt` lists the three `codex_cloud` unittest
  failures by id instead of `group:codex_cloud`. `run_suites.py` reads
  unittest failure headers and their `FAILED (failures=N, errors=M)`
  totals, and names a failed group only when the runner's table shows a
  failed assertion of its own; a group that "exited N without reporting a
  failed assertion" is named by its unittest ids, so a new failure there
  is a new id.

### Not changed

- The source owner's environment name (`My Whitelist`) still appears in
  `agent-guidance`'s routine specs (`docs/routines/fleet-worker.md`,
  `prompt-audit-sweep.md`) and its allowlist notes; the review named only
  `docs/routines.md`.

- The starter suites assume a PID namespace only (`unshare --pid --fork
  --mount-proc`), run as root or as an ordinary user. Two kinds of test
  drop to `nobody` when run as root: agent-guidance's `test_codex_cloud`
  preexec and agent-skills' `_run_hook_unprivileged`. Under `unshare --user
  --map-current-user`, `nobody` is unmapped. The three known codex_cloud
  ids then report as `ERROR` (a raised preexec) rather than `FAIL`, so the
  exact list does not excuse them. Two `test_generate_skills_lock`
  unsearchable-child tests fail as well. The second also fails when the
  clone sits under a directory `nobody` cannot traverse, such as a 0700
  temp dir. Neither is a kit defect, so neither is excused.

## Third review fixes (2026-10-29)

What a third review found, and how each is carried out. Departures from
the entries above are marked **Departure**.

### A copy of the kit in a shallow folder works

`export.py` computed `DEFAULT_SOURCES = KIT.parents[3]` at import, which
raised `IndexError` in a copy with fewer than four ancestors (`~/adopt-kit`
is `/home/u/adopt-kit`), and `run_suites.py` imports it, so every suite
failed in the README's own copy-out path. `fetch_sources.py` (`parents[2]`)
and `test_kit_tracked.py` had the same flaw. Now `DEFAULT_SOURCES` is
`None` when the ancestor is missing; `export.py` with no `--sources` and no
`KIT_EXPORT_SOURCES` exits 2 with a message saying so, and `fetch_sources.py`
asks for `--self`. `run-all-tests.sh`'s export check still reports SKIP in a
copy (it looks for the source checkouts itself). The LICENSE comparison runs
only when the repo root is a git work tree holding the kit at
`docs/reference/adopt-the-whole-system`, so a copy two folders below an
unrelated `LICENSE` no longer compares against it.
`test_a_copy_in_a_shallow_folder_still_imports` copies the entry points
under `/tmp` and imports `export`, runs `export.py --check` (exit 2, the
message) and `--help` of the other two scripts; it fails on the old code
(`IndexError: 3`).

### CI: a missing secret only fails when kit files changed

GitHub passes no Actions secrets to a Dependabot- or fork-triggered
`pull_request` run, and Dependabot's weekly github-actions bumps edit
`ci.yml`, a salient path, so the step that failed closed on a blank
`PRIVACY_DENYLIST` turned every such bump red. The detection step now also
outputs `kit_changed` (files under the kit changed; true when it cannot
tell). The check step, with the secret unset or blank:

- fails closed when `kit_changed` is true (a leak scan over kit files that
  checked nothing must not read as green), unless
- the pull request's author is `dependabot[bot]` (read from
  `$GITHUB_EVENT_PATH` with `jq`, never interpolated), which cannot add
  personal data: warn;
- when only `ci.yml` or `.gitignore` changed, warn.

In both warning cases the public scan, the other export tests and
`--check` still run; only the private half is skipped (`CI=false` for that
run makes its test skip, as it does locally). `kit_changed` reaches the step
through `env:`. **Departure:** a fork pull request that changes kit files
still fails (it cannot be told from a maintainer's by anything but its
secret), and is fixed by a maintainer pushing the branch. `test_ci_adoption_kit_step`
locks the new output, the `env:` entry and each case on scratch event files.

### No App id literal in the kit

C12 says the kit spells neither of the source owner's App ids, but
`patches/repo-settings/kit_config.py` and `manifests/skills-evals.yml` did.
The patch now finds both from `fleet.yml`'s own comments by shape
(`agents-md-sync GitHub App (App id N)`, `(App id N). GitHub checks
--match-head-commit`) and puts them into its old texts at run time; the
skills-evals ADR's id is a substitution rule matched by its context
("-roster`, App id N) and"). The exported trees are byte-identical
(`export.py --check`).

### The App manifest redirects to this machine

`create-apps.sh` used `https://example.com/` as `redirect_url`, which sends
the one-time manifest `code` (convertible into the App's private key) to a
host the adopter does not control. It is `http://127.0.0.1/` now: nothing
listens, the browser shows a connection error, and the adopter copies the
URL from the address bar. The prompt, the script header and
`docs/settings-and-apps.md` say so; a bootstrap test holds the manifest's
`redirect_url`.

### Running the tests as root

The README gave only the `--user --map-current-user` form, which as root
leaves `nobody` unmapped (see "Not changed" above). It and the starter
README give both forms and say `known-failures.txt` is calibrated for the
root form (measured as root).

### `OWNER_NAME` takes no apostrophe

The name lands in single-quoted shell
(`publish-waiting-feed.sh`) and PowerShell (`WslAutomation.psd1`) strings.
`bootstrap/lib/common.sh` and `bootstrap/lib/substitute.py` now refuse
`'`, with a message; bootstrap tests check both.

### The root `.gitignore` clears the whole kit

The two negations (`bin/*`, `*.log`) left the VisualStudio rules'
`[Ll]ogs/`, `out/`, `artifacts/`, `x64/`, `Debug/` and others still
dropping exported files. One negation, `!/docs/reference/adopt-the-whole-system/**`,
re-includes everything (it matches the excluded directories themselves, so
git looks inside them); four rules after it put the junk back
(`__pycache__/`, `*.py[cod]`, `node_modules/`, `.pytest_cache/`). Each tree's
own `.gitignore` still applies inside it. `test_the_real_root_gitignore_clears_everything_under_the_kit`
runs the repo's real file on a scratch repo (it fails on the old one).

### Smaller

- agentskills' `skills.lock` step used GNU `sed -i`; it is a `python3 -I -c`
  replacement now (BSD `sed -i` takes a suffix argument).
- The line above listing the owner's private details was cut to a generic
  sentence, and its pointer to a public test dropped.

## Cold-start fixes (2026-10-29)

Five findings from running the exported system against an empty account. Each
departure is made through the export (a manifest edit or a patch), so
`export.py --check` reproduces it.

### The `persistent/eval-results` branch is created by `create-repos.sh`

Nothing created skills-evals' `persistent/eval-results` branch, which the
coverage census, the ingest and the publishers read and write, so the first
scheduled run failed on a missing ref. `bootstrap/create-repos.sh` now creates
it, idempotently, as an orphan commit holding one `README.md` (git data API:
tree, parentless commit, ref), through `gh_write_api`, so `--dry-run` prints
and writes nothing. `verify.sh` has a `branches` group (on by default) and
`status.sh` keeps step 2 as next while the branch is missing. No other
`persistent/*` branch needed this: the code creates the rest on first write.
Not an export departure (the bootstrap scripts are kit files). Reverse: drop
`ensure_results_branch` and the `branches` group.

### A registry may be declared empty (`may_be_empty: true`)

The census refused a registry that matched no skill, so the kit's empty
private registry failed it every day. `harness/registries.yml` entries take an
optional boolean `may_be_empty`; `run_eval._load_registries_config` validates
it, `resolve_registries` carries it, and `eval_coverage.enumerate_skills`
returns 0 skills for a declared registry. It is set for
`acsi-agentskills-private` only; every other registry keeps the refusal.
Patch `cold_start_registries.py`; tests in the overlay file
`test_issue_cold_start_registries.py`. Reverse: drop the patch's registry
and census parts, and seed one skill in the private registry before the first
census.

### The invented example sites are not live config in skills-evals

C3's `example-site-platform` and `example-site-a` were checked out by four live
workflows (`routine-eval-weekly`, `skill-coverage`, `propagation`, `eval`),
passed as `--registry` flags, and listed in `harness/registries.yml`. Repos an
adopter does not have: a checkout of a missing repo fails the job, and a
registry with no flag is unresolved. Their checkouts, flags and registry
entries are dropped, as is the matching federated checkout in
`_agent-guidance`'s `skills-lock-bump.yml` (manifest edits). The code that
handles a platform repo stays (C3), and `fleet.yml` and `repos.yml` keep the
example entries for steps 9 and 11 to trim. Tests that used the sites as a
second public registry move to `acsi-agentskills` or
`acsi-agentskills-private` (patch `cold_start_tests.py`: test_issue_60, 64,
70_retire, adr0012_delivery and TestIssue63) with counts that follow the new
denominator. Lost with them: the census-level checks that a flat and a dot-dir
registry resolve; TestIssue63 still resolves both layouts, passing the layout
directly. Reverse: drop both patches and the `skills-lock-bump.yml` edits.

### The dashboard builds from empty inputs

`dashboard/build.py` required `loop_status.json`, so a build with no inputs
failed, and the `threads` and `loop_gaps` datasets had no placeholder row. It now defaults
`loop_status.json` to `{"gaps": []}` and gives `threads` and `loop_gaps` a
placeholder row, as the other datasets have (key field `none`, hidden by the
page's placeholder map). New test
`test_builds_from_fully_empty_inputs`. Manifest edits on `dashboard/`.
Reverse: drop those edits.

### Improve fires are refused at first (docs only)

`docs/evals-and-loop.md` says so: the allowance guard reserves an improve fire
at 12 times the average ingested run, 42 points on day one against the
30-point cap, until ingested runs average 2.5 points or less. No code changed.

## Content tiers (2026-10-29)

The owner's decision of 2026-10-29 replaces X9's "one real item of each
kind" with four tiers. X9's machinery (the blanking patches, the template
skill and section, the moved tests) stays; what it keeps changes.

| Tier | Where it ships | Skills | Guidance sections | agent-checks checks |
|---|---|---|---|---|
| Core | `starter/`, always | `workflow-path-audit`, `skills-doctor`, `github-actions-repo-settings`, `vendor-release-impact-issues` | "A successful `git push`...", "The watch finished...", "Automation vs branch protection", "Agent-made GitHub contributions carry a marker", "Pinning GitHub Actions", "Data exposure in CI and public repos", "Skills ecosystem", "Two setup gaps...", and the core parts of "Working in these repos" and "Git practices" | `skill-shell`, `secret-file` |
| Recommended | `library/`, optional | `review-bash-ci-reliability`, `debug-github-workflows`, `disarm-inherited-reach` | "Security", "A GitHub 404 means...", "A test that can signal...", "A name you choose...", "Working habits", "Git habits" | none |
| Opinionated | `library/`, optional | `writing-adrs`, `finding-unknowns` | "Finding your unknowns", "Anything you name gets its link", "Subagent delegation (model routing)", "Dependency updates" | `rules-dir` |
| Not shipped | nowhere | every other skill | "Workstation layout", "Two GitHub connectors...", "Read before you start", "The fleet spans TWO owners..."; the American English bullet; the writing-style bullet; the squash exception for the CMS repos | the pre-push checks (`staged-index`, `push-to-default`, `persistent-delete`) |

`bootstrap/content-catalog.json` is the one list of every item, with its
tier and the text the `/adopt` skill shows. `bootstrap/tests/check-catalog.py`
holds it to `library/` and `starter/` (every optional item has its library
folder and every folder an item; every core item is in `starter/`; the
retirement list below equals the core items; no question the skill asks has
more than four choices).

### 4cab855's text, as an edit

The owner asked for "Automation vs branch protection" as of
`_agent-guidance` commit 4cab855, which rewrote one bullet ("PR + auto-merge
is a sanctioned bot-write path only where a repo-settings ADR declares the
exception..."). The `_agent-guidance` manifest applies that bullet as a
stage-source edit, word for word, and keeps `source_sha` at 9404fe7.
Re-pinning was the larger change: between the two commits the range also
changes the repo's `ci.yml`, `actions.lock`, `.gitignore` and
`test/run-tests.sh` (the kit's own CI), which would have entered the
exported tree. `git diff 9404fe7 4cab855 -- agents-md/base.md` is that one
bullet; the eval-coverage bytes and the mirror are regenerated as usual.

### The two split sections

Each keeps its core part under the source heading, and its other bullets,
byte for byte and in source order, move to a recommended section with a new
heading:

| Section | Part | Bullets | Coverage row |
|---|---|---|---|
| "Working in these repos" (core) | the `on-hold` bullet | 1 | `working-in-these-repos`, covered by `evals/guidance/working-in-these-repos/on-hold-pull-request` |
| "Working habits" (recommended) | fix what was asked; interface changes update tests; deterministic tests; full precision; AST for code shape; text to paste | 6 | `working-habits`, `gap` (no fixture tests these bullets) |
| "Git practices" (core) | the merge-commit bullet, its squash exception dropped | 1 | `git-practices`, covered by `evals/guidance/git-practices/merge-method-and-closing-keyword` |
| "Git habits" (recommended) | concise commits, never amend or force-push; the closing-keyword trap; `git log origin/<base>..HEAD` before a PR; one worktree per session | 4 | `git-habits`, `gap` |

The `merge-method-and-closing-keyword` fixture also tests the closing-keyword
trap, which now sits in "Git habits"; it stays on the core row because its
merge-method half is the core rule, and a fixture can serve only one row.
The "American English spelling" and writing-style bullets of "Working in
these repos" are not shipped. The merge-commit bullet drops its clause excepting
the three CMS-managed repos, kept for Decap publishing, and keeps the
rest, ending "Squash strands commits a lockfile pins by sha
(2026-08-15: `cannot resolve ref`)".

### The library

`export.py` writes `library/` beside the starter trees: one folder per
optional item, `library/<skills|guidance|git-hooks>/<id>/<tree>/` with
`files/` (copied as they are), `fragments/` (text an op inserts) and
`ops.json` (edits to files already in the tree). The patches that used to
delete an item now move it there (`export.py`'s `Library`, passed to every
patch as `ctx["library"]`). `--check` compares `library/` with a fresh
export like a starter tree, so it now prints seven `OK` lines; the library
is written or checked only when every repo is exported.
`library/README.md` (from `export/library-README.md`) lists the ops.

- Each guidance item carries its section, its eval-coverage row and its
  `docs/guidance-impact.md` entry. Its `insert-section` op names the
  sections that precede it in the source, nearest first, so an installed
  section lands where the source has it.
- Each skill item carries its folder, its `scripts/plugin_layout.json`
  entry and a `docs/skill-impact.md` entry.
- Each item carries its eval fixtures, its `evals/scheduled.yml` rows, and
  its tests: whole test modules, or (for tests inside shared modules) the
  classes and methods, found by AST, that `removed_tests.txt` takes out of
  the starter. `test_issue_71_trigger_set.py` tests two items' fixtures
  (`writing-adrs`, `review-bash-ci-reliability`) and is copied only once
  both are installed (`copy-if`). The `writing-adrs` copy of `TestIssue80`
  reads the real fixture folders, not the invented ones its starter
  retargets point at (a NAME-token rename, never inside strings).
- The rules-dir item carries its runner arm, its `note_ran` line, its run-log
  example, its two lane cases and the three assertions of
  `test_agent_check_lane.py` that list it.

The impact entries are dated 2026-10-29, the day of the decision, not the
day of an install: an install must be reproducible, and the date says when
the item entered the kit. Their `Eval:` line reads "not run at install
(n=0)", which the touch gate's result pattern accepts and which is true.

### Installing

`bootstrap/add-content.sh --items <ids|recommended|none> [--dry-run]`
(through `bootstrap/lib/content.py`) applies the chosen items to the kit
copy's `starter/` in a scratch copy, rebuilds the generated files the
export's `regenerate` steps build (the base.md mirror and agent-checks
runner in every tree, each `AGENTS.md`, the section bytes, the registry's
README table, `skills.lock` with the forty-zero ref and its private copy),
then writes back what differs. Before any change it rebuilds the unchanged
starter with the same recipes and stops if they do not reproduce it, so a
recipe that drifts from the export cannot install silently. The byte counts
are recomputed in Python (the extent rule of
`scripts/lib/markdown-sections.js`, outside code fences) because an adopter
need not have `node_modules`; the self-test checks them against the
exported values. It refuses an unknown id and a kit inside a git work tree,
and records the installed items in `<state file>.content-choices.json`,
beside `status.sh`'s state file. Once the repos exist it lists the repos
that need a pull request instead of suggesting `copy-starter.sh --force`,
which would overwrite the pins `regenerate.sh` set on the default branch.

- **Quick start.** A new ask step, 1, "Choose optional skills, guidance and
  git hooks", comes after the config and before the repos are created, so
  every starter pull request already carries the choices. Its check carries
  `"record": "content"`: `status.sh` reads it as done once the record
  exists (or once marked). The later steps are renumbered 2 to 32, and every
  reference to a step number (the quick start, `settings-and-apps.md`,
  `/adopt`, `test-bootstrap.sh`, C11 above) follows; the dated entries
  above keep the numbers of their day. A state file written before this
  change names the old numbers: mark the ask steps again.
- **verify.sh** gains a `content` group (run when named, or by default once
  a record exists): the record is readable, and each installed item is on
  its repo's default branch (a file it adds, or the line it adds to
  `base.md` or the runner, read through the contents API).
- **The `/adopt` skill** asks the questions with AskUserQuestion. Its limits,
  read 2026-10-29 at <https://code.claude.com/docs/en/agent-sdk/user-input>
  (and <https://code.claude.com/docs/en/tools-reference>): 1 to 4 questions
  per call, 2 to 4 options each (a `label` and a `description`), a `header`
  of at most 12 characters, `multiSelect`, no preselection, an "Other"
  answer always available, not available in subagents. The owner's layout
  fits: the largest list has four items, and the one-item list (opinionated
  git hooks) gets a second option, "No git hook".
- **Catalog texts.** The owner gave the rules-dir short and details and the
  finding-unknowns details word for word. The rules-dir text is stored
  split: `details` up to "...the loop can measure." and `clashes` from
  "Clashes if your repos...", printed one after the other, so it reads as
  given. finding-unknowns' `short` is the first sentence of the given text;
  its `clashes` and every other item's texts are new, in the same style.

### Retirement never removes a core item

`evals/retirement-exempt.yml` in `skills-evals`, written from the catalog
(`patches/skills-evals/retirement_exempt.py`), names the core skills and
guidance sections. `compute_gates.py`'s `finalize()` turns a core item's
`retire` verdict into `retire-exempt` (keeping `raw_verdict`) before it
picks the one retirement per evaluation, so a core item never takes the
slot of an item that may retire; `retire_skill.py`'s `plan()` and
`guidance_plan()` open nothing for a core item, as a second guard. A
guidance section's shorten-or-merge proposal, an issue, is unchanged.
`test/issues/test_issue_retirement_exempt.py` (overlay, 9 tests) shows a
core skill and a core section with a `retire` verdict open nothing while a
non-core one still files its issue.

### Tests

- `skills-evals`: the core items' tests are no longer removed (66 lines out
  of `removed_tests.txt`, among them `TestVendorReleaseImpactPublishTimesCheck`
  and the core sections' `test_issue_124` methods; 607 entries remain), and
  their fixtures and module excludes are gone from the manifest.
  `empty_config.py` keeps the 12 core rows of `scheduled.yml`.
  `skills-doctor`'s `bucketed-account-store` fixture stores two account
  copies with CRLF line endings on purpose (its `fixture.yaml`), so
  `starter/.gitattributes` marks that folder `-text` and git keeps the bytes.
- `skills-evals`' `TestIssue84Round5::test_no_objective_check_anywhere_globs_into_the_git_directory`
  scanned every nested fixture in the kit (an X9 retarget, so it had
  something to scan). Installing `debug-github-workflows` made it fail: that
  item's `wrong-branch` fixture reads `.git/trace.log` on purpose, and the
  source's test never sees it because it scans only `evals/*/fixture.yaml`.
  The retarget keeps its recursive scan (the core starter has too few
  top-level fixtures for the test's `checked > 20`) and passes over that one
  fixture by path, with a comment saying why.
- `agentskills`: `test_generate_skills_lock.py` is no longer patched (its
  `skills-doctor` citation exists again).
- `_agent-guidance`: `secret-file` returns with its cases. The rules-dir
  cases and assertions move to its library item. The pre-push test, whose
  check (`push-to-default`) is not shipped, becomes
  `test_refused_pre_push_is_logged_as_pre_push`: a feature-branch push whose
  commit `secret-file` refuses, which still shows the `pre-push` event in the
  run log. `run-tests.sh` keeps only the two `persistent-delete` hunks. The
  on-hold test is the source's again.
- `bootstrap/tests/test-bootstrap.sh` tests the installer (refusals, the dry
  run, a real run, idempotence, the joint module, the record, `verify.sh`'s
  `content` group before and after a merge, `status.sh`'s step 1) and
  `check-catalog.py`, including one run that must fail.

## Re-pin (2026-10-30)

Every manifest's `source_sha` moved to its source's current `main`, and the
export was rerun.

| Repo | Old | New |
|---|---|---|
| `_agent-guidance` | `9404fe7d648eb916a65128818fb58c4ca5f998aa` | `0082194ce1dcb122e802886e48f62eadb6db9b99` |
| `agentskills` (the public registry) | `d2d81b00c51388baf51c3922a540ae27839adcde` | `0e81a5e9989c5f92a2af774f9d714e137a7262f9` |
| `agentskills-private` (the private registry) | `c4bf812e4703e7b9fdd3f5408ed9198cba9df9be` | `c5b1bc9dfaaec3651ad9cb35f8d04192a126319b` |
| `repo-settings` | `db44cee233bfd6c23aa34b1e2822df97c32df5bb` | `075636253c63a91e84d32fd331ca80e0174737ac` |
| `skills-evals` | `99c667f93c67a3ddd0630bf7aadbcb43e506d43c` | `d965ccf6aeb0c3f5e2d744063405923525620b94` |
| `wsl-automation` | `1c6893002aea500d43dcd25534a5fd7059c87b25` | `305090ad7e62dc773462508909d947fbaa13ca56` |
| platform `imports:` (C4) | `06c89431ff513057e97bd5e5711522be586f6a12` | `fe15bb1cad82e3ee6934063b6ce6ae130096c433` |

The C4 imports follow the platform release that `_agent-guidance`'s own
`scheduled-run-health.yml` caller pins at its new `main` (`v0.1.164`, a
lightweight tag on `fe15bb1`). The three imported files are byte-identical at
both commits. The `_agent-guidance` source at its new `main` contains the kit
itself; the manifest's `docs/reference/adopt-the-whole-system/` exclude keeps
it out of the export. Each overlay `NOTICE` names the new commit.

Edits and patches changed or dropped:

- `_agent-guidance`, the `agents-md/base.md` edit that applied the
  "Automation vs branch protection" bullet as of 4cab855: **dropped**. The
  source now has that text.
- `_agent-guidance`, `patches/_agent-guidance/blank_content.py`
  `MERGE_CLAUSE`: the source dropped the date from "(2026-08-15: `cannot
  resolve ref`)"; old and new follow it, and the cut clause is the same.
- `_agent-guidance`, the reusable's `actions/setup-node` edit and its
  `actions.lock` entry: `v7.0.0` becomes `v7.1.0`. The source moved every
  workflow to `v7.1.0`, `v7.0.0` is no longer locked, and `v7.1.0` is the
  commit the imported reusable pins.
- `agentskills`, the `scheduled-run-health.yml` caller edit: `old` follows
  the source's bump of the platform ref to `v0.1.167`. The edit still points
  the caller at `_agent-guidance`'s copy.
- `skills-evals`, the `dashboard/page/index.html` placeholder-key edit: the
  source renamed the `usage_sources` key field from `file` to `key`; `old`
  and `new` follow it, and the edit still adds the `threads` and `loop_gaps`
  keys.
- New (C11), `patches/_agent-guidance/kit_repos.py`: the agent-checks
  dated-phrasing allowlist, new in the source, matches its entries by repo.
  The one entry for a repo outside the kit (the source owner's usage
  dashboard) is removed from the template and from `_agent-guidance`'s
  `.githooks` copy, and the patch fails if any other entry names a repo
  outside `kit_repos`. The other five repos copy the template
  (`copy_from_kit`), as the sync delivers it.
- New, `patches/_agent-guidance/kit_ci.py`: the source's CI now runs the
  adoption kit's own tests (three steps in `ci.yml`'s `checks` job, the
  `actions/setup-python` entry they add to `actions.lock`, the root
  `.gitignore` block that keeps every kit file tracked, and
  `test_ci_adoption_kit_step` in `test/run-tests.sh`). The exported repo has
  no kit (the manifest excludes it), so the patch cuts each whole.
- `patches/_agent-guidance/machinery_tests.py`: the source's new
  dated-phrasing run-log assertion in `test/run-tests.sh` lists `rules-dir`
  among the checks that ran. The kit's runner has no `rules-dir` (Content
  tiers), so the assertion drops it, and the `rules-dir` library item puts it
  back on install, as it does for the other run-log assertions.

skills-evals' `harness/scorers/objective.py` carries `<!--|--!?>` at the
source (skills-evals#480), so the kit copy has it with no edit.

The dated-phrasing warning pass (`.githooks/dated-phrasing.js`, its allowlist
and its pinned `markdown-it`) arrives with the source's agent-checks runner.
It is machinery that only warns, and is shipped as the source has it. It is
not listed in `bootstrap/content-catalog.json`, so it has no content tier yet.

## Own repo (2026-10-30)

The kit moved out of `_agent-guidance` (`docs/reference/adopt-the-whole-system/`,
as of `_agent-guidance` commit 0a51ed7) into its own public repo, at the
root, so outside feedback and contributions never touch the repo that feeds
guidance to the source owner's fleet. What changed with the move:

- **It runs in its own clone.** The repo carries no `CLAUDE.md`, `AGENTS.md`
  or `.claude/settings.json`, and the source owner's guidance sync excludes
  it, so cloning it and running `claude` there loads only the `/adopt` skill
  and the adopter's own `~/.claude/`. The README's "Start here" and the
  quick start say to clone it outside every other repository instead of
  copying a folder out of a clone. The skill checks the folder above the kit
  (`git -C .. rev-parse --show-toplevel`), and `add-content.sh` refuses a kit
  inside another repository but runs in its own clone.
- **Sources sit beside the clone.** `export.py`'s default `--sources` and
  `run-all-tests.sh`'s export check read the folder holding the clone, not
  four folders up. `fetch_sources.py` lost `--self`: `_agent-guidance` is
  fetched at its pin like every other source. Its pinned commit still holds
  the kit folder, which its manifest excludes; the `kit_ci.py` patch and that
  exclusion stay until the next re-pin past the move.
- **Repo machinery.** `.github/workflows/ci.yml` (`test`: the kit's tests,
  `export.py --check`, the bootstrap tests) and `agent-checks.yml`, with
  `.githooks/` copied from the kit's own `starter/agent-guidance/.githooks/`
  (the exported runner, free of owner names). The leak scan covers them
  like every other file. A new `keep` rule in `manifests/_common.yml`
  protects the kit's own clone URL, the one place the repo names its owner.
- **Tests.** `test_kit_tracked.py` checks the kit as its own clone (the root
  `.gitignore` is the repo's), and the license test only checks that
  `LICENSE` exists. `test-bootstrap.sh` adds the clone and nested-repo cases
  for `add-content.sh`.

## Re-pin (2026-11-03)

Every public manifest's `source_sha` moved to its source's current `main`,
and the export was rerun. `agentskills-private` was not re-exported (see the
end of this section).

| Repo | Old | New |
|---|---|---|
| `_agent-guidance` | `0082194ce1dcb122e802886e48f62eadb6db9b99` | `2e2045a0870db995547d0e79d8a5148f89e94b0b` |
| `agentskills` (the public registry) | `0e81a5e9989c5f92a2af774f9d714e137a7262f9` | `151d20ca550905bfdad78709460b880b5150ae75` |
| `repo-settings` | `075636253c63a91e84d32fd331ca80e0174737ac` | `4308b61cd0a482b38c9c683094f85ed96132958e` |
| `skills-evals` | `d965ccf6aeb0c3f5e2d744063405923525620b94` | `8f6351af9677c042c104f20bc09bd104706ed16e` |
| `wsl-automation` | `305090ad7e62dc773462508909d947fbaa13ca56` | `913a417181edc26fcd84f32e01e2105dcc2bc125` |
| platform `imports:` (C4) | `fe15bb1cad82e3ee6934063b6ce6ae130096c433` | `e0d772c22312cc6585d0b4f70de8bc22d0f18368` |

Each overlay `NOTICE` names the new commit. The `_agent-guidance` source is
now past the kit's move to its own repo: it no longer carries the kit folder,
only a pointer page (`docs/reference/adopt-the-whole-system.md`), which the
manifest excludes instead.

### C4: the source's own reusable, with the script copied in

The source moved the scheduled-run-health reusable into `_agent-guidance`
itself (`scheduled-run-health-reusable.yml`). It checks the audit scripts out
of the platform repo at the release named in `.github/health-audit-platform-ref`,
and three more files keep that copy in step with the platform's
(`health-reusable-parity.yml`, `scripts/check-health-reusable-parity.js` and
its test). Every other repo's caller now calls it at a full `_agent-guidance`
commit (`7254006`).

- **The kit ships the source's reusable**, with edits instead of importing
  the platform's copy. The checkout that fetched the platform release now
  sparse-checks out `scripts/audit-scheduled-runs.js` from this repo's
  default branch (`.self`), and the step that ran it reads it from there.
  The platform-release resolution, the platform currency check and its
  inputs (`currency_scan`, `behind_days`) are cut: the kit has no platform
  repo.
- **One import is left:** `scripts/audit-scheduled-runs.js`, from the
  platform at `e0d772c` (`v0.1.170`, the release the source's pin file
  names). The reusable and `check-platform-currency.js` are no longer
  imported.
- **Excluded:** `.github/health-audit-platform-ref`, the parity workflow,
  script and test. The output stage removes the parity workflow's
  `actions.lock` entry, and the edits to `test/run-tests.sh` remove its call
  and function. The edits that put the caller and the `actions.lock` entry in
  place are dropped: the source has them.
- **Callers:** the `agentskills`, `repo-settings`, `skills-evals` and (new)
  `wsl-automation` manifests share one three-edit block. It replaces the
  source owner's `_agent-guidance` commit with the forty-zero placeholder
  (REGENERATE.md), and it rewords the two comments that name the platform.

### `kit_ci.py` is removed

The source's CI no longer runs the kit's tests, since it no longer has the
kit. This is the re-pin past the move that "Own repo (2026-10-30)" waited
for, so the patch is deleted.

### `_agent-guidance`: content and config

- **New guidance section "PR descriptions open with a TLDR"**
  (`blank_content.py` SECTIONS, id `pr-tldr`), tiered **core,
  provisionally**. The owner should confirm the tier. Its agent-checks check
  (`pr-tldr`) ships as the source has it, and `machinery_tests.py` adds it to
  the core check ids. The core-row check now accepts a `skipped` coverage row
  that gives a reason, as well as a `covered` row with a fixture.
  **Caution:** the PR bodies in `bootstrap/lib/pr.sh` and
  `bootstrap/lib/copy-starter.sh` have no `## TLDR` heading, so an adopter's
  starter pull requests opened after the check's cutoff (2026-11-03) would
  fail `pr-tldr`. They are not changed here.
- **The runner edits** in `blank_content.py` follow the source's new
  `"runner"` line (`"failed":["secret-file"],` is the anchor now).
- **C11, `kit_repos.py`:** cuts the new `cron_coverage.fleet` entry for the
  source owner's security-alerts snapshot repo, with its comment, and the
  sync's new exclusion of the kit's own repo (`exclude: [acsi-kit]` becomes
  `exclude: []`, with its comment). The kit is the adopter's setup tool, not
  a repo of the adopter's fleet.
- **Excluded:** `docs/routines/fleet-health-audit.md`. It is the owner's
  weekly audit of their own fleet: its first run seeds from the owner's hand
  audit, and it reads the task health snapshot that the kit's
  `wsl-automation` does not publish (below). Nothing links to it.
- **Shipped as the source has it:** the session-start usage record
  (`.claude/hooks/guidance-load-record.sh`, ADRs 0035 to 0037). It records
  to the private registry's `persistent/usage-events` branch, or to an S3
  bucket only when its environment variables name one. Also shipped: the
  eval-protection gate (`scripts/eval-protected.js`, ADRs 0033 and 0034), the CI
  scope step (`scripts/ci-scope.sh`) and ADRs 0030 to 0037.

### `agentskills`

- **New skills, not shipped:** `fan-out-triage` (untiered, so not shipped
  until the owner tiers it) and the red-CI skill named for the source owner's site (it diagnoses CI on the
  source owner's own platform site, like X4's platform skills). The new
  `tool-powershell` skill sits under the excluded `coding-local` skills.
- **The anything-anywhere plugin's new SessionStart hook** (ADR 0023)
  installs the fleet guidance from a bundled copy when its fetch is off or
  fails. Two new `copy_from_kit` steps regenerate that copy from the kit's
  `_agent-guidance` (`agents-md/base.md` and `.claude/hooks/fleet-memory.sh`).
  Without them the bundle would carry the source owner's full guidance. The
  README plugin-table edit and `blank_registry.py`'s plugin description
  follow the source's new wording.

### `repo-settings`

`kit_config.py`'s cut of the test row includes the source's new
`acsi-kit` entry (C11). The two counts the cut no longer changes follow the
source: the checked-repo count is 23 (was 22) and the all-repos rule count is
20 (was 19). Both are still replaced by the kit's 8 and 6.

### `skills-evals`

- **The schedule:** the source took some fixtures off the schedule into a
  new `evals/unscheduled.yml`. `empty_config.py` no longer keeps a fixed
  list (`KEEP_SCHEDULED`). It keeps a row of either file when that row's
  fixture folder ships (has a `fixture.yaml`), and it fails if no scheduled
  row is kept. `unscheduled.yml` is written as `fixtures: []` when nothing is
  kept. `library_fixtures.py` carries a library item's `unscheduled.yml`
  rows too (`unscheduled-rows.yml`, appended on install).
- **C6, the budget:** the source raised the weekly cap and the stop
  threshold for the week ending 2026-11-09, and planned 0.25 as its steady
  state. The edits are source-stage now and keep the kit's standing defaults
  (`weekly_cap: 0.30`, `stop_when_account_above: 0.80`). The dropped comments
  recorded the source owner's spending decisions. The kit does not adopt
  the 0.25 steady state, which is the source owner's plan, not yet a
  standing default. The owner may want to revisit that.
- **Retargets and renames follow the source:** `test_issue_70` reads
  `unscheduled.yml`, the scheduled-fixtures REVIEWED list follows the
  source's new list, `test_issue_dev_setup`'s import hunk is dropped (the
  source imports `sys` itself), and `removed_tests.txt` names the renamed
  schedule-count test.
- **New substitutions** rename two test methods and a constant that carried
  the owner's first name, which the leak scan caught.
- **`cold_start_registries.py`:** the site-entry pattern allows the
  source's new `private: false` line, and the comment anchor and eval.yml's
  checkout count ("All five checkouts") follow the source.
- **Smaller:** the browser-testing `ci.yml` edit uses `setup-node@v7.1.0`.
  The routine-eval-fire environment edit includes the job's new `outputs:`
  block. The dashboard placeholder-key edit follows the source's new keys
  and still appends `threads` and `loop_gaps`.

### The eval runner's prompt is the source's stub

The kit carried the eval runner routine's prompt as an input
(`inputs/skills-evals/docs/routine-prompt.md`), because the source kept the
prompt only in claude.ai. The source now commits it: a short stub
(`docs/routine/eval-runner-prompt.md`) that reads the routine's real
instructions (`docs/routine/eval-runner-instructions.md`) from `main` at the
start of each run. The kit's copy, as of 2026-10-29, also lacked the new
improve-cost lane (`claude/eval-cost-*`, `routine-eval-cost-pushed.yml`).
The input is removed. `docs/routines.md`, `docs/quick-start.md`,
`bootstrap/steps.json`, `bootstrap/set-secrets.sh`, REGENERATE.md and the
`routine-eval-fire.yml` header edit now name the stub.
`docs/evals-and-loop.md` gains the cost lane. `check-branch-prefixes.py`
reads the lanes the instructions push to, scans `docs/` recursively, and
expects six lanes.

### `wsl-automation`

The source added a session miner, a weekly memory curation and a daily task
health publish, each with a scheduled task. It also added local-time triggers
(`ConvertTo-WslLocalTimeTrigger`) and a stub `.git` guard in the keeper
(`Test-ClaudeStubGitDir`).

- **Session miner:** the source now ships its own wrapper and test. The
  kit's overlay copies, which generalize them for an adopter, replace them,
  and the task keeps the kit's 07:17 time and 30 minute limit.
  `tasks_installer.py` and `pester_tests.py` now edit the source's miner
  task, parameters and tests instead of adding their own, and `docs.py`
  replaces the source's README section with the kit's.
- **Memory curation ships** as the source has it. Its routine ships in the
  kit's `_agent-guidance`. The only edit replaces the owner's clone drive in
  its fallback clone root (`/mnt/d/repos` becomes `/mnt/c/repos`), as the
  repo's substitution for the owner's Windows clone drive does. Its test joins the manifest's suite
  command.
- **Task health is left out**, with its script and test, as part of X10:
  it reads the left-out restic repository and keeper log, and it feeds the
  source owner's fleet health audit (excluded above). The installer, the
  wrapper, the Pester tests, `ci.yml` and both docs lose it.
- **The stub `.git` guard is left out** (X10): its only caller is the
  keeper. `ci.yml`'s Linux Pester step loses its test, and AGENTS.md loses
  its section.
- **Local-time triggers ship.** They apply to every kept task.
- **The scheduled-run-health caller is new here.** It takes the shared C4
  edit block, and `bootstrap/regenerate.sh run-health-sha` now pins it too
  (`docs/generated-files.md`, `docs/quick-start.md` and `steps.json` say four
  pull requests).

### Not re-exported: `agentskills-private`

Its `copy_from_kit` files are now behind the re-pinned public starters.
These are the fleet guidance payload, the agent-checks runner with
`pr-tldr`, the dated-phrasing allowlist, and the `guidance-load-record.sh`
hook its siblings now carry. Its NOTICE and pin are unchanged until it is
re-exported. Every overlay `NOTICE` also still cites the export as
`docs/reference/adopt-the-whole-system/export/export.py in _agent-guidance`,
a path from before the move.

The same day, skills-evals moved again to 341f4bd (skills-evals#720: only `skill-coverage.yml` writes `coverage/latest.json` and `badges/coverage.json`; `propagation.yml`'s census writes `fixture-census/`, guarded by `test_issue_660_single_writer.py`). The manifest needed no other change.

### Round 2 (2026-11-03)

The daily re-sync failed the same day
([run 41722628098](https://github.com/Adam-S-Daniel/acsi-kit/actions/runs/41722628098)):
the `agentskills` README plugin-table edit no longer matched its source.
`export/resync.py` moved the public pins again; `repo-settings`,
`wsl-automation` and the platform `imports:` were unchanged, and
`agentskills-private` stays at `c5b1bc9` (not re-exported, as above).

| Repo | Old | New |
|---|---|---|
| `_agent-guidance` | `2e2045a0870db995547d0e79d8a5148f89e94b0b` | `7c5a3a9c6bee4c65ea873daa8aa4c4e76246b9e7` |
| `agentskills` (the public registry) | `151d20ca550905bfdad78709460b880b5150ae75` | `13075c83be711d134d7e39e3d00584dea736b933` |
| `skills-evals` | `341f4bd5717e171a21cfe362d510536dc6d37709` | `73d9c4c5ad5d81c1e612756af8fc0c489e208ccc` |

- **`agentskills`, the write-marker hook ships.** The anything-anywhere
  plugin gained a `PreToolUse` hook
  (`hooks/github-write-marker/github-write-marker.sh`) that blocks a GitHub
  write without the agent marker. It is a verbatim copy of
  `_agent-guidance`'s `.claude/hooks/github-write-marker.sh`, which the kit
  already ships, and it enforces the core section "Agent-made GitHub
  contributions carry a marker", so it is machinery, not new content: a new
  `copy_from_kit` step regenerates it from the kit's `_agent-guidance` (the
  two are byte-identical in the sources). The README plugin-table edit
  (`X9`) and `blank_registry.py`'s anything-anywhere description follow the
  source's new wording, which names the hook.
- **`agentskills`, the skill freshness lint ships, trimmed (C11).** New in the
  source: `scripts/check_skill_freshness.py`, its test, its config
  `scripts/skills_freshness.yml` and the scheduled `skill-freshness.yml`
  workflow, which files one issue when the lint fails. It is generic
  machinery and ships. New patch `kit_freshness.py` cuts the config's two
  platform and site registries (the kit's `skills_registries.yml` no longer
  declares them), every waiver (each is for a skill of one of those
  registries; the shipped test requires a waiver to name a declared
  registry) and the source owner's personal tool repo from `repos:`, then
  checks that every repo left is in `kit_repos`. Two output edits replace the
  workflow's clone of the platform repo and a site with a comment, as
  `ci.yml`'s census edit does, and drop the platform from its header.
- **`agentskills`, not shipped:** the `launch-top-level-claude-session` edit
  sits under the excluded `coding-local` skills.
- **`skills-evals`, `retirement_exempt.py`:** the source's `guidance_plan()`
  now lowers an `auto` removal to a proposal when the verdict allows only one
  (`proposal_only`), right after `kind = "retire"`. The patch's anchor
  follows that line; the core-item guard still comes first. The rest of the
  source's gate rewrite (the betting bound, parked cells, the new gate
  tests, the removed stratified-pooling simulator) is machinery and ships
  as the source has it.
- **`_agent-guidance`:** `sync.sh`, `bump-consumer-locks.sh`, the fleet-worker
  routine and `test/run-tests.sh` changed with no manifest change.
  `package-lock.json` is unchanged, so the Node install is the same.

### Round 3 (2026-11-03)

The re-sync's failure issue (#14) caught skills-evals' dashboard gaining a `ci_red_runs` placeholder key, which broke the cold-start edit on `dashboard/page/index.html`. The edit's old and new text now carry that key; its intent (hide the two cold-start placeholder rows like the others) is unchanged. _agent-guidance → ba30b6f and skills-evals → c6b38e1 needed nothing else.

### Round 4 (2026-11-04)

The daily re-sync failed in "Regenerate starter/"
([run 41847534882](https://github.com/Adam-S-Daniel/acsi-kit/actions/runs/41847534882),
issue [#18](https://github.com/Adam-S-Daniel/acsi-kit/issues/18)):
`_agent-guidance` commit 2133d52 added an `AGENTS.md` size check to
`templates/agent-checks/agent-checks`, and `blank_content.py`'s
`check_paths` anchor no longer matched. `export/resync.py` moved every
public pin to its source's `main`; the platform `imports:` are unchanged,
and `agentskills-private` stays at `c5b1bc9` (not re-exported, as above).

| Repo | Old | New |
|---|---|---|
| `_agent-guidance` | `ba30b6f61437e84bbe8696d11d2a5818d4b12bba` | `a406262b2a726ccb84e892e513b2b51c28d6a002` |
| `agentskills` (the public registry) | `13075c83be711d134d7e39e3d00584dea736b933` | `126e8e0f7cd48be1ff280dd6eaa0f64d9b28408d` |
| `repo-settings` | `4308b61cd0a482b38c9c683094f85ed96132958e` | `9db16b62932a351fb4d6a903ffe132f9cd594ba1` |
| `skills-evals` | `50daafcaf5535612491dd758b3f0c05012f31e4b` | `f3196c3fcfafb2f801e860bf1c700fe2bacc8cc3` |
| `wsl-automation` | `913a417181edc26fcd84f32e01e2105dcc2bc125` | `1ea339739dd60ac86e7a5f37e912a31d525c0609` |

Neither Node lockfile moved (`_agent-guidance`'s root, `skills-evals`'
`explorer/`), so the installs are the same.

- **`_agent-guidance`, the runner edits are anchored on code.** The
  rules-dir arm is removed by its own text (`RULES_DIR_ARM`, the same text
  the library item puts back), the kit's "a check of your own" note is
  added on its own lines just above `check_paths() {`, after the source's
  comment whatever it says, and the commented example check goes just
  before the per-path `check_lessons` call. None of the three anchors
  includes the source's comment or the checks beside the arm, so a new
  fleet check no longer breaks them. The new `agents-md-size` check ships
  as the source has it: it enforces the floor's "keep this file under
  32 KiB" rule, which the kit's `AGENTS.md` carries, so it is machinery
  like `pr-tldr`.
- **`_agent-guidance`, the new section "Turn lessons into checks, skills
  and guidance"** (`turn-lessons-into-checks`) ships as core, as the owner
  asked. The kit refuses a core section whose coverage row is neither
  covered by a fixture nor skipped with a reason; the row turned `covered`
  in `_agent-guidance` [#452](https://github.com/Adam-S-Daniel/_agent-guidance/pull/452),
  which is why the pin is `a406262` (past #452's merge, `2e53728`) rather
  than the `37c073e` this round first took. Its fixture,
  `evals/guidance/turn-lessons-into-checks/`, ships with it, and
  `bootstrap/content-catalog.json` lists it as a core guidance item, which
  also puts it in `retirement-exempt.yml`. The same pin brings
  `_agent-guidance` #453, which makes the runner's `problem()` print an
  `::error` annotation in CI; it ships as the source has it, and no kit
  edit is anchored on either changed line.
- **`_agent-guidance`, the prompt-audit sweep is fired by a workflow.**
  The new `prompt-audit-fire.yml` fires the sweep for each trigger issue
  the changelog watcher files, with the bearer in an Actions secret instead
  of the watcher's environment. It ships (the sweep and the watcher are
  kit routines). `docs/routines.md`, steps 28 and 29 and
  `bootstrap/README.md`'s by-hand list now put `PROMPT_AUDIT_SWEEP_FIRE_URL`
  (variable) and `PROMPT_AUDIT_SWEEP_FIRE_BEARER` (secret) on
  `_agent-guidance`, and the watcher's environment holds no variables.
- **`skills-evals`, no `SITE_REPO` fallback.** This round first kept
  `|| 'none'` in the site workflows; kit
  [#19](https://github.com/Adam-S-Daniel/acsi-kit/pull/19), merged first,
  follows the owner's no-fallback rule instead (`SITE_REPO` is set in
  `fleet.env`, `none` by default), so the merge takes #19's side and the
  workflows and their tests ship as the source has them.
- **`skills-evals`, smaller:** `removed_tests.txt` names the renamed
  schedule-count test (`..._twenty_three_guidance_fixtures`), and the
  REVIEWED list retarget carries the new turn-lessons fixture, as the
  source's list does. The new `evals/add-from-address/` (a trigger set for
  the source owner's personal mail skill) is excluded, like the PDF
  skills' folders. The new `scripts/agent_made.py` (counts the
  `Captures:` commit trailers) and its test ship as machinery.
- **`agentskills`, `repo-settings`, `wsl-automation`:** only the delivered
  hooks and runner changed; no manifest change.

## Evals fragment (2026-11-03)

Issue [#12](https://github.com/Adam-S-Daniel/acsi-kit/issues/12): the
starter `repo-settings/fleet.yml` no longer declares `skills-evals` (C13).

- **The patch.** `patches/repo-settings/evals_fragment.py` runs after
  `kit_config.py`, which edits that element's comments and actor id. It
  composes `fleet.yml` with PyYAML, finds the one `repos:` element whose
  `name` is `<owner>/skills-evals`, and takes its lines from its `- name:`
  line to the end of its last value (the deepest scalar's or flow list's end
  mark). Those lines go, byte for byte, under `repos:` in
  `repo-settings/fleet.evals.yml`, after a header that says what the file is
  and how it is merged. It then parses both files again: `fleet.yml` must
  hold its other elements and keys unchanged and the fragment exactly that
  element. No element, or two, fails the export; so does an element that
  does not start its line with `- `. `export/tests/test_evals_fragment.py`
  runs it on invented fleets, the missing and doubled element among them.
- **What stays in `fleet.yml`.** The comment block above the element (the
  required-check preconditions of several repos) stays where it was. Two
  later comments still point at it as "the cms-platform#437 comment above
  example-adopter/skills-evals"; it is still above where that element was.
- **Tests.** In `tests/test_repo_settings.py`, `setUpModule` also patches
  `rs.load_config`: loading the shipped `fleet.yml` appends the fragment's
  elements while the fragment exists, and refuses a repo declared in both.
  Every shipped test about `skills-evals` (its approval switch, label,
  roster ruleset, required checks, the counts) therefore runs unchanged,
  before and after the merge. `test_the_real_fleet_names_both_app_ids_by_variable`
  reads both files' text. New `EvalsFragmentTests`: `fleet.yml` alone
  declares no `skills-evals` and resolves with only `GUIDANCE_SYNC_APP_ID`
  set (what the `plan` job has on a base-only setup), the fragment holds only
  `skills-evals`, the merged fleet does not resolve without
  `ROSTER_WRITER_APP_ID` (the negative control), and a repo in both files is
  refused. The fragment-only tests skip once the fragment is merged.
- **The bootstrap.** `regenerate.sh evals-fleet` (evals track, step 40;
  `lib/common.sh`'s `regen_track` puts it there although it edits the base
  repo `repo-settings`) runs `lib/fleet_fragment.py merge` on a clone: it
  appends each fragment element `fleet.yml` does not declare to the end of
  its `repos:` list, re-indented to that list, checks the result parses to
  the old list plus those elements, deletes the fragment and proposes both
  files on `regenerate/evals-fleet`. `--check` (`verify.sh
  --only regen:evals-fleet`) passes once `fleet.yml` declares
  `<owner>/skills-evals` once and no fragment is left. `apply-settings.sh`
  no longer leaves a declared but absent `skills-evals` out: `fleet.yml`
  declares it only after step 40, so an absent one is reported like any
  missing repo, with the `create-repos.sh` hint. The filtered copy stays for
  `--track base` and `--track evals` once `fleet.yml` declares it.

## Unified explorer (2026-11-04)

`skills-evals` now builds both of its pages, the public Evals Explorer
(`tool/index.html`) and the private dashboard (`dashboard/page/index.html`),
with esbuild from one source tree, `explorer/` (`src/`, `build.js`,
`package.json`, `package-lock.json`, `template/`, `test/`, `schema.json`).
The manifest moves `skills-evals` from `c6b38e18c441888d8458979f75d020bce2253655`
to `22f9adafc05a6d3b18e0660a5d17d7b40e3fd628`, the head of the source's then open
pull request skills-evals#754 (the private build of the same app). That
commit contains the source's `main` at the time. Re-run the export once that
pull request merges, and pin the merge commit. The other manifests keep their
pins.

The tree is exported whole, so everything new since the old pin comes along
too: `explorer/`, `scripts/eval_facts.py`, `scripts/explorer_public.py`,
`scripts/site_freshness.py`, `evals/hook-policy.yml`,
`evals/public-export.yml`, `.github/workflows/site-freshness.yml`,
`docs/routines/site-freshness-fixer.md` and their tests. No file the kit
exported before went away in the source.

### The pages are rebuilt, not substituted

The two pages are build output now. A new `regenerate` step runs
`node build.js` in the staged `explorer/` after substitution, so each page is
a fresh build of the substituted source, and the exported tree's own
`npm run check` (the source's CI drift step) passes. The owner name reaches
the public page in one place, `DATA_REPO` in `explorer/src/config.js`,
which the ordinary C2 rule rewrites. No rule or edit names `tool/index.html`.
Before this, the substitution ran over the committed page like any other
file. `bootstrap/lib/substitute.py` keeps the pages in step too: it rewrites
the owner in the source and in the built pages the same way. Checked with an
invented login: `node build.js --check` still passes.

The step takes esbuild from the source checkout's `explorer/node_modules`.
`ci.yml` and `resync.yml` install it from the source's own lockfile at the
pinned commit, as they already did for `_agent-guidance`. By hand, run
`npm ci` in the source's `explorer/` first. Without it the step fails and
names the folder.

### Moved edits

- **Cold start:** the placeholder-key edit that hid the `threads` and
  `loop_gaps` placeholder rows targeted `dashboard/page/index.html`. It now
  edits `PLACEHOLDER_KEY` in `explorer/src/private/datasets.js`, and the
  rebuild carries it into the page. `test_builds_from_fully_empty_inputs`
  reads the source file, because esbuild rewrites the quotes in the bundle.
- **X9:** the `scripts/dev_setup.sh` edits keep the source's new
  `explorer` npm folder and drop only `evals/browser-testing/seed`.
- **Content tiers:** the guidance half of `retirement_exempt.py` follows the
  source's rename of `proposal_only` to `guidance_proposal_only`.

### What the new source needed

- **Cold start:** `loop-pr-refresh.yml` gained a `withdraw` job that
  computes the verdicts as `skill-coverage.yml` does, and a test compares the
  two steps. `cold_start_registries.py` drops its two example-site checkouts
  and `--registry` flags too.
- **Citation-shaped test data** (`protect_except`):
  `test_issue_fixture_pr_gate.py` (a pull request body's `owner/repo#N`),
  `test_issue_explorer_lessons.py`, `test_issue_dashboard_build.py` and
  `test_issue_public_data_contract.py` (expected URLs and keys that the code
  builds from the substituted owner). Both sides are substituted together.
- **Substitution side effects:** the explorer test's and the dashboard
  test's check that the page names no person look for the kit's invented
  person, "Example Adopter" (which `substitute.py` turns into the adopter's
  name), not "the owner", which the page says on purpose. A lesson record's
  subject follows the invented site name, which has no dot.
- **Retargets** (machinery tests on library fixtures): the in-situ refusal
  test reads `test/fixtures/evals/writing-adrs/bootstrap`, and the trigger-set
  gate's "the repository's own set passes" check reads the core skill
  `skills-doctor`'s committed set.
- **The empty-inputs build** writes a minimal explorer document first:
  `build.py` now refuses to build without `explorer/latest.json`, and a test
  in the source locks that.

### Adopter defaults

- **`evals/public-export.yml`** ships `include_spend: false`; the source
  owner publishes spend, and an adopter chooses to. The test that read the
  committed value as true reads it as false and still checks both values.
- **`SITE_REPO`:** `site-sync.yml` and `site-freshness.yml` fell back to the
  source owner's site when the variable was unset, and a site sync with no
  App on that site fails red. In the kit the fallback is `none`, the source's
  own clean skip: every step after the first is skipped. The two tests that
  pin the fallback follow. `site-freshness.yml` stays: with `none` it does
  nothing but skip.
- **Docs:** `docs/routines.md` ("Dashboard refresh"), step 32 and
  `/adopt-evals` describe the two claude.ai artifacts: the private build as
  the Dashboard artifact, with its datasets including `explorer`, and the
  public build as an artifact with the data beside it. Both start private.
  An artifact's content security policy allows only `'self'`, so the data
  travels with the artifact.

### Second pin (2026-11-04)

skills-evals#754, #755 and #757 merged, and the manifest moves on to the
source's `main`, `50daafcaf5535612491dd758b3f0c05012f31e4b`. Its #755 adds a
third build, `explorer/dist/artifact/index.html` (entry
`src/entries/artifact.js`; `build.js` swaps `adapters/web.js` for
`adapters/artifact.js`, which reads a `latest.json` beside the page). The
same `regenerate` step builds it, and the exported tree's `npm run check`
covers all three pages. The docs, step 32 and `/adopt-evals` now publish
that page as the public artifact, with the results branch's
`explorer/latest.json` beside it as a file named `latest.json`. Both start
private; a public link is the adopter's, from the artifact's Share menu.
Refreshing the page means republishing `latest.json`. No edit, patch or
retarget needed changing for this pin. The source's #757 adds a seventh push
lane, `claude/spend-*` (`spend-pushed.yml`), which the private dashboard's
refresh pushes rather than the eval runner routine, so
`bootstrap/tests/check-branch-prefixes.py` expects it without requiring the
routine's instructions to name it, and `docs/evals-and-loop.md` lists it.

Reverse: pin the old commit and drop the edits and the `regenerate` step
named above.

### Third pin: site variables have no fallback (2026-11-04)

The manifest moves on to the source's `main`,
`cdedb7e1e1523647a11cac30f560e17a6b733e0a`. Its #771 removes every
`vars.X || '<literal>'` fallback from `site-sync.yml`, `site-preview.yml` and
`site-freshness.yml`, and the `DEFAULT_*` constants from
`scripts/site_freshness.py`: `SITE_REPO`, `SITE_PAGE_URL`, `SITE_ASSET_URL`
and `SITE_FRESHNESS_ROUTINE_ID` are required repository variables, `none`
skips, and unset fails naming the variable. That is the owner's rule for
values that name an owner's resources (`_agent-guidance`
`docs/reference/settings-schema-design.md`, rule 4): no in-code fallback,
set in one place, fail descriptively, and an opt-out set explicitly.

- **The `SITE_REPO` edits are gone.** The seven edits above that turned the
  fallback into `none` (two workflows, their comments, three tests) no longer
  had a target, and the kit adds no fallback of its own, `none` included.
- **The one place is `fleet.env`.** `SITE_REPO` is a `fleet.env` key
  (`none` or `owner/name`, validated as `site-sync.yml` validates it), and
  `create-environments.sh` makes it a `skills-evals` repository variable
  (`REPO_VARIABLES`, verify group `variables`). `fleet.env.example` ships
  `SITE_REPO=none`, so a default setup says "no website" explicitly rather
  than by omission; an empty key is skipped with a message naming it, and
  `verify.sh` fails on it. The other three, and the fixer routine's bearer,
  are needed only with a site and stay on the README's by-hand list.

Reverse: pin `50daafc`, restore the seven edits, and drop the `SITE_REPO`
key, its `REPO_VARIABLES` row and the doc changes.

### Fourth pin, and the session miner's repository settings (2026-11-04)

The manifest moves on to the source's `main`,
`af2163e9302b2f0e7954c52cddef2c3352f54432` (the site freshness check's
iframe fix and a glossary entry). No edit, patch or retarget needed changing.

The kit's own session miner wrapper
(`overlay/wsl-automation/scripts/run-session-miner.sh`) fell back to
`~/repos/acsi-agentskills-private` for `LESSONS_CLONE` and to the adopter's
`skills-evals` URL for `SKILLS_EVALS_URL`. Both name the adopter's own
repositories, so under settings-schema-design rule 4 neither has a default
now: each comes from the environment or `session-miner.env`, and unset the
wrapper exits 2 naming the key and where to set it. A new
`config/session-miner.env.example` carries both keys, and the README's
"Session miner task" and `docs/machine.md` say to copy it.
`PRIVACY_DENYLIST_FILE` keeps its `~/.config` default: it names a path on
the machine, not a repository. `tests/run-session-miner.test.sh` covers both
missing keys.

Reverse: pin `cdedb7e1`, restore the two fallbacks, and drop the example and
its tests.

## Re-pin (2026-11-04): wsl-automation

Only `wsl-automation` moved; every other manifest keeps its Round 4 pin.
This section **supersedes Round 4's `wsl-automation` row** (above, which
moved it to `1ea3397`): the two were made in parallel, and the merge takes
`29344b2`, which contains `1ea3397`.

| Repo | Old | New |
|---|---|---|
| `wsl-automation` | `1ea339739dd60ac86e7a5f37e912a31d525c0609` (Round 4; `913a417` before it) | `29344b2e7d23ab3d82917a494b457d0ace844602` |

The overlay `NOTICE` names the new commit.

### Task settings have no fallback (wsl-automation#92)

The source's Bash task entries no longer fall back to the source owner's
repositories. `publish-usage-census.sh` (`SKILLS_EVALS_URL`),
`publish-waiting-feed.sh` (`WAITING_FEED_URL`), `run-memory-curation.sh`
(`AGENT_GUIDANCE_URL`) and `sync-codex-cloud-environments.sh`
(`CODEX_CLOUD_GUIDANCE_REPOSITORY`) source the new `scripts/task-settings.sh`,
which takes each key from the environment, then from
`~/.config/wsl-automation/settings.env` (read as data), and exits 2 naming
the key when it is missing. This is settings-schema-design rule 4, the rule
the third and fourth skills-evals pins above applied to the site variables
and the kit's own session miner. All of it ships as the source has it:
`task-settings.sh`, its test, `config/settings.env.example`, the `ci.yml`
changes (`config/*` as a salient path, the resolver's test step, ShellCheck)
and the README section.

- **`config/settings.env.example`**, three edits: the task health key goes
  (X10: its task is left out); the census comment no longer says the session
  miner reads the file; and its `example-owner` placeholders become the kit's
  `example-adopter`, as in `config/session-miner.env.example`, so
  `copy-starter.sh` fills in the adopter's login.
- **`docs.py`**: the README settings table loses the task health row and its
  census row no longer names the session miner, a bullet says the miner has
  its own file, and the kit's Install steps gain one for `settings.env`
  (the session miner becomes step 6). The leftover check also refuses
  `TASK_HEALTH` in README.md or AGENTS.md.
- **The waiting feed header edit** said "(default ... waiting-feed)"; with no
  default left it says the repository is `WAITING_FEED_URL`.
- **The kit's `tests/unix-schedule.test.sh`** (overlay) copies
  `task-settings.sh` beside the census entry in its "real entries" case; the
  census sources it now, and the case failed without it. The value comes from
  the environment there, so the case is otherwise unchanged.
- **The suite command** runs `tests/task-settings.test.sh`, as the source's
  `ci.yml` does.

**Two config files.** An adopter now keeps two settings files on the
machine: `settings.env` for the source's Bash tasks and `session-miner.env`
for the kit's own session miner wrapper (overlay; Fourth pin above), which
keeps its own reader and does not read `settings.env`. `SKILLS_EVALS_URL`
belongs in both. Merging them (the overlay sourcing `task-settings.sh` and
dropping `session-miner.env`) is a possible follow-up, not done here: the
overlay accepts keys `settings.env`'s example does not carry
(`LESSONS_CLONE`, `PRIVACY_DENYLIST_FILE`, `FILE_ISSUES` and more), and its
tests pin its own file. The bootstrap writes neither file (`install-machine.sh`
writes nothing of its own), so the docs say to copy both:
REGENERATE.md's wsl-automation section (the waiting feed's repository has no
default now), `docs/machine.md`, step 22 in `steps.json` (and the quick start
table rendered from it) and `/adopt`'s "Steps with a catch".

### Task health's nonzero count (wsl-automation#93)

`publish-task-health.sh` stops counting `0x41301` (running) and `0x41303`
(has not run yet). The script and its test stay excluded (X10). Its README
section is dropped whole by `docs.py`, so the reworded sentence never reaches
the kit, and the `ci.yml` edits that drop its ShellCheck entry and test step
still match.

### Sync-delivered files

The range from `913a417` has four `chore: deliver ...` commits from the
source owner's guidance sync; Round 4's `1ea3397` already includes three of
them, so only `32e257a` (the agent-checks runner) is new past it. Each
delivered file is treated as it already was at the old pin, the same way the
sibling manifests treat it:

- **`.claude/hooks/fleet-guidance.md` and `.githooks/agent-checks`** are
  `copy_from_kit` steps, rebuilt from the exported `_agent-guidance`, so the
  source's new bytes never reach the kit; this pin leaves them as Round 4
  regenerated them.
- **`.claude/hooks/guidance-load-record.sh`** ships as the source has it
  (substituted), as in every sibling tree ("Re-pin (2026-11-03)",
  `_agent-guidance`). At this pin and Round 4's, every starter that carries
  it has the same bytes.
- **`.claude/hooks/skills-bootstrap.sh`**: the "deliver" commit left it
  byte-identical to the old pin; nothing changed.

Reverse: pin `1ea3397` (Round 4), drop the three `config/settings.env.example` edits,
restore the waiting feed header's "(default ...)" wording, and revert the
`docs.py`, overlay test, suite command and doc changes.

## One machine config file (2026-11-04)

This closes the follow-up "Re-pin (2026-11-04): wsl-automation" named: an
adopter now keeps one settings file on the machine,
`~/.config/wsl-automation/settings.env` (`WSL_AUTOMATION_SETTINGS`), the
file the source's `scripts/task-settings.sh` reads. The kit's session miner
wrapper (`overlay/wsl-automation/scripts/run-session-miner.sh`) reads it
instead of its own `session-miner.env`.

- **The wrapper keeps its own reader**, not `wsl_automation_require_setting`.
  The resolver takes one key per call and only for required keys; the miner
  also takes seven optional keys, and its exit paths log through its own
  `finish`. Its reader is the smaller correct change. It still reads the file
  as data, takes only its allowlisted keys, expands a leading `~/`, and lets
  the environment win. Because the file now holds every task's keys, a key
  outside the allowlist is **ignored**, where it used to exit 2. A line that is
  not `KEY=value`, a comment or blank still exits 2 naming its line number,
  never the path. Its key pattern and CR stripping now match
  `task-settings.sh`. The required `LESSONS_CLONE` and `SKILLS_EVALS_URL` exit
  2 naming the key and pointing at `settings.env` and
  `config/settings.env.example`.
- **Removed:** `SESSION_MINER_CONFIG` and `config/session-miner.env.example`.
  Their keys and comments move into `config/settings.env.example` through a
  manifest edit: `LESSONS_CLONE` (required) after `SKILLS_EVALS_URL`, and the
  optional `PRIVACY_DENYLIST_FILE`, `WIN_HOME` and `FILE_ISSUES` commented out.
  The source's census comment, which names both the census and the session
  miner, ships unedited again. The README's settings table gains a
  `LESSONS_CLONE` row.
- **No back-compat read of `session-miner.env`.** The kit has no adopters on
  that file yet, so nothing reads it.
- **Tests:** `tests/run-session-miner.test.sh` (overlay) points
  `WSL_AUTOMATION_SETTINGS` at its files. It checks that another task's key
  (`WAITING_FEED_URL`) in the file is ignored while the miner's own keys still
  apply, and that a malformed line exits 2 named by number, with no path and
  no miner run. Each new assertion was shown to fail against the old behavior:
  rejecting unknown keys fails "another task's key ... is ignored", and
  skipping malformed lines fails "a malformed line exits 2".
- **Docs:** the README (`docs.py`: Install steps 5 and 6, the settings
  section, "Session miner task" step 4, the Linux and macOS note),
  `docs/machine.md`, REGENERATE.md, step 22 (and the quick start rendered
  from it) and `/adopt` name the one file.

Reverse: restore the overlay's `config/session-miner.env.example`,
`SESSION_MINER_CONFIG` and reject-unknown-keys reader, drop the
`LESSONS_CLONE` edit, and revert the test and doc changes.

## Re-pin round 5 (2026-11-09)

The daily re-sync failed from 2026-11-05 to 2026-11-09 in "Regenerate
starter/" ([run 42645286648](https://github.com/Adam-S-Daniel/acsi-kit/actions/runs/42645286648)).
`export/resync.py` moved every public pin to its source's `main`;
`agentskills-private` stays at `c5b1bc9`.

| Repo | Old | New |
|---|---|---|
| `_agent-guidance` | `a406262b2a726ccb84e892e513b2b51c28d6a002` | `4e3f70c7a88f3a5dfd1d22b961e153f789b62399` |
| `agentskills` (the public registry) | `126e8e0f7cd48be1ff280dd6eaa0f64d9b28408d` | `13029c6c4de08428515aeb47c1c8fa50faef1364` |
| `repo-settings` | `9db16b62932a351fb4d6a903ffe132f9cd594ba1` | `c3574f28da69f607e964929662cd96a08cc24ed5` |
| `skills-evals` | `f3196c3fcfafb2f801e860bf1c700fe2bacc8cc3` | `508181f9da3b28e38c8a912c9a5c0a48503f24fc` |
| `wsl-automation` | `29344b2e7d23ab3d82917a494b457d0ace844602` | `3f973eec89b52198e17dae7628adc7f3b6a7a31f` |

- **`agentskills`, the AGENTS.md test-command edit** follows the source's
  new wording ("the one CI runs, minus its flags", with CI's `-rfEs -n auto`
  explained); the kit's change is the same: no rename-pdfs test named, and
  `shopt -s nullglob` on the command.
- **`skills-evals`, the committed budget is set by key** (C6,
  `standing_budget.py`). The source rewrites `evals/budget.yml`'s weekly cap
  and account stop, and their comments, most weeks, and two exact-text edits
  broke on each rewrite. The patch replaces each key's comment paragraph and
  value (30 points, 80%) wherever it sits, and the committed-budget test now
  checks those two values against its own `LIMITS`, leaving the per-run
  values, which are measurements, to the source's tests.
- **`skills-evals`, a removed test can be named by pattern.** The schedule
  count test's name spells its counts and changes with them, so
  `removed_tests.txt` names it `test_the_schedule_names_*_skill_and_*_guidance_fixtures`;
  `machinery_tests.py` requires a pattern to match exactly one test.
- **`skills-evals`, smaller:** the `REVIEWED` list retarget in
  `test_issue_scheduled_fixtures.py` gains the five "harder fixtures, set A"
  rows; `empty_config.py` drops `evals/scope-auto.yml` rows (fixtures the
  source's eval scope pass paused) whose fixture the kit does not ship, as it
  does for the two schedule files, because the source's tests now read those
  rows as scheduled ones.
- **`wsl-automation`, the Docker WSL integration watchdog ships.** It is a
  new background task (`ensure-docker-wsl-integration.ps1`,
  `Invoke-DockerWslIntegrationWatchdog`) that restarts Docker Desktop when
  its WSL integration with the distro breaks, which is not the backup or the
  keeper (X10), so it is kept like the other tasks. `pester_tests.py`
  follows: the backup trigger test is dropped by its new name's prefix, 49
  argument lines (five new) lose `-BackupDir`/`-ResticRepoDir`, the
  principal test says the watchdog is the one interactive task, and the
  action-coverage test counts seven script actions; `docs.py`'s two README
  edits name the watchdog. Its alert's email channel defaults to a
  `fastmail-actions` workflow repository the kit does not ship; when that
  fails it logs one line and the toast still shows. That default is the
  source's to remove (a setting naming the owner's resources has no
  fallback in code).
- **`_agent-guidance`, two new scheduled workflows ship, set by hand.**
  `fleet-worker-fire.yml` now fires the fleet worker every 3 hours (the
  routine keeps only its API trigger), so `docs/routines.md`, step 27 and
  the quick start say so, and `bootstrap/README.md` lists
  `FLEET_WORKER_FIRE_URL` and `FLEET_WORKER_FIRE_BEARER`. `article-watch.yml`
  (an hourly Anthropic-articles feed watch that fires an article-lift
  routine) ships as the source has it, its tests being in the source's
  suite; the README lists its three values and says to disable it if
  unused, since each run fails naming a missing value. `skills-evals`'
  `site-preview.yml` reads a new `SITE_PREVIEW_URL`, listed the same way.
- **`bootstrap/tests/check-branch-prefixes.py`** reads the eval runner's
  per-mode instructions (`docs/routine/modes/*.md`) as well as
  `eval-runner-instructions.md`: the source split the instructions per
  mode, and each mode's file names its own branch.

Reverse: restore round 4's pins and the edits named above, and remove
`standing_budget.py` and the pattern support in `machinery_tests.py`.

## Re-pin round 6 (2026-11-09)

Two sources moved between round 5's pin and the first re-sync after it:

| Source | Round 5 | Round 6 |
|---|---|---|
| skills-evals | `508181f9da3b` | `f6f16f835d4e` |
| wsl-automation | `3f973eec89b5` | `5118c58b887e` |

- skills-evals' `AGENTS.md` now says the live operational state is
  `HANDOFF.md`'s "Current state" section and that the old status board issue
  is closed. `owner_links.py`'s edit follows the new text and keeps only its
  first sentence, since the kit has no such issue.
- Two new guidance fixtures (skills-ecosystem `lockless-repo`,
  watch-finished-is-not-ci-passed `grep-q-pipe-race`) ship with their
  `scheduled.yml` rows, because both sections ship.

Reverse: restore round 5's pins and the old `owner_links.py` edit.

## Re-pin round 7 (2026-11-09)

The daily re-sync failed at "Regenerate starter/"
([acsi-kit#34](https://github.com/Adam-S-Daniel/acsi-kit/issues/34)):
`_agent-guidance`'s `repos.yml` now lists `acsi-kit` in
`cron_coverage.fleet`, so the source fleet's health audit watches the kit's
own re-sync (`_agent-guidance#492`). An adopter's fleet holds no copy of the
kit, so `kit_repos.py` cuts that entry with its comment, as it already cuts the
sync's `exclude` entry for the kit (C11).

| Source | Round 6 | Round 7 |
|---|---|---|
| _agent-guidance | `4e3f70c7a88f` | `1e72504f1fd5` |
| acsi-agentskills | `bf7aa5a022a6` | `24f7a7b63b47` |
| skills-evals | `c77f08cdedec` | `3482456d9f26` |

The skills-evals pin brings `judge_exclude_tiers` and
`stop_when_session_above` (skills-evals#920, #921), and the _agent-guidance pin
brings `FLEET_WORKER_EVERY_HOURS` (_agent-guidance#494), which
`bootstrap/lib/plan_sizing.py` and `create-environments.sh` set from
`CLAUDE_PLAN`.

- skills-evals' `skill-coverage.yml` gained a token exchange for the
  removal review (skills-evals#917) that names the source's own federation
  rule, organization, service account and workspace ids. `federation_vars.py`
  (C12) now gives it the same four repository variables and shape checks as
  `eval.yml`; the step is under `continue-on-error`, so an adopter without
  federation gets no review bearer and no auto removal, as before.

Reverse: restore round 6's pins and drop the `cron_coverage.fleet` cut and
the `skill-coverage.yml` part of `federation_vars.py`.

## Re-pin round 8 (2026-11-12)

The daily re-sync failed at "Regenerate starter/" from 2026-11-10
([acsi-kit#41](https://github.com/Adam-S-Daniel/acsi-kit/issues/41)). Three
source changes needed the kit to follow them:

- `_agent-guidance`'s `repos.yml` moved `verify-actions-lock` from
  `cron_coverage.out_of_scope` into `cron_coverage.fleet` once it had a
  weekly cron. The kit's workflows use the public action, and an adopter's
  fleet holds no copy of its repo, so `kit_repos.py` cuts that entry with its
  comment, as it cuts the kit's own (C11).
- `_agent-guidance`'s `test/run-tests.sh` now matches the dated-phrasing run
  log with `grep -qE` and lets lesson check ids sit between `skill-shell` and
  `dated-phrasing`. `machinery_tests.py` drops `rules-dir` from the new
  pattern, and the rules-dir library item's op puts it back, as before.
- skills-evals' `evals/budget.yml` ships `points_per_usd: 0.0015` (about
  $6.70 per point, measured 2026-11-10) in place of 0.0005. The plan table in
  `docs/before-you-start.md` quotes it, and `bootstrap/lib/plan_sizing.py`
  scales the Pro and Max 5x rates by the same plan multipliers (0.03 and
  0.006). The table's weekly shares were modeled at the old rate and are
  flagged for re-modeling
  ([acsi-kit#43](https://github.com/Adam-S-Daniel/acsi-kit/issues/43)).

| Source | Before (`4e6aaeb`) | Round 8 |
|---|---|---|
| _agent-guidance | `9f42f9e69b1b` | `6026fa78be2c` |
| acsi-agentskills | `e4a64b9f0bb9` | `60d805ca926c` |
| repo-settings | `c3574f28da69` | `a890dbc58797` |
| skills-evals | `5e50a24020ab` | `a50f114e26b9` |
| wsl-automation | `0a438429236f` | `460f6c77fe5e` |

`agentskills-private` keeps its pin; its starter and `library/` were
re-exported by hand (MAINTAINING.md, Re-pin). acsi-agentskills is pinned at
`60d805ca926c`, past `84aa6ef`, which removed
`scripts/test_dependabot_auto_merge.py`: at `42a971565b30` (the sync of the
shared Dependabot merge workflow) that test still read the old two-copy
allowlist and failed in the starter. Later
wsl-automation commits (two new scheduled tasks, the WSL memory log and the
Claude settings sync) break `tasks_installer.py`'s keeper check, so
wsl-automation stays at `460f6c77fe5e` here and follows in the next round.

Reverse: restore the previous pins, the two patch edits and the three plan
rates.

## Re-pin round 9 (2026-11-12): wsl-automation

Round 8 held `wsl-automation` at `460f6c77fe5e` because its newer commits
broke `tasks_installer.py`'s keeper check. This round follows them. Upstream
added two scheduled tasks and some supporting changes:

- **The WSL memory log ships.** `log-wsl-memory.ps1`,
  `Write-WslMemorySample`, its tests, its task in
  `Set-WslAutomationScheduledTasks` and `register-tasks.ps1`
  (`-MemoryLogTaskName`, `-MemoryLogIntervalMinutes`, `-MemoryLogDir`) and its
  README section are generic, so they stay. The patched help, task counts,
  the S4U lists and the Pester counts are reworded for the kit's eight tasks
  (seven S4U, plus the Interactive Docker watchdog), with no mention of the
  keeper, the backup, the launchers or task health.
- **The Claude settings sync is left out** (X9, with X10's treatment of the
  files). It runs the `sync-cc-settings-between-wsl-and-windows` skill from the
  owner's registry, which the kit already leaves out, so the task would have
  nothing to run. The manifest excludes `Invoke-ClaudeSettingsSync`, its
  private helper, `sync-claude-settings.ps1` and its tests, and two `edits`
  drop its exports from `WslAutomation.psd1` and `.psm1`. The three patches
  remove its task, its three parameters (`-ClaudeSettingsSyncTaskName`,
  `-ClaudeSettingsSyncIntervalMinutes`, `-ClaudeSettingsSyncLive`), its help,
  summary line, Pester tests and README section, and each now fails if
  `ClaudeSettingsSync` or `sync-claude-settings` reappears.
- **Catch-up settings ship.** The usage census and the session miner now set
  `StartWhenAvailable` with `RestartCount 3` and `RestartInterval 10 min`
  (the source's task health publish, which the kit leaves out, shared them).
  The kit's miner keeps its 30 minute limit on top of them. `docs.py` rewrites
  the source's new AGENTS.md section for the two tasks and says in the
  post-wake window section which tasks catch up.
- **`-EnableCodexTasks` ships for the Codex Cloud sync alone.** The source
  registers both Codex tasks disabled unless the switch is given, and
  `Set-WslScheduledTaskEnabled` is the new private seam. The launcher and the
  keeper's `-NoCodexRemoteControl` are left out with the keeper (X10), so the
  patched function disables or enables the Codex Cloud sync only, and the
  source's Pester Context for it is replaced by a Context written for that one
  task.
- **Two small source changes ship unchanged:** `run-memory-curation.sh` adds
  `~/.local/bin` to `PATH` (with its test), and `publish-task-health.sh`
  changed, which stays excluded.
- **The Docker watchdog task is registered again.** `tasks_installer.py`'s
  block removal for the task health publish ran on to the archive anchor and
  took the Docker watchdog's task block with it (its help and the wrapper's
  call too). Its summary line stayed and read the unassigned
  `$dockerWatchdogArguments`, so under the module's strict mode the installer
  most likely threw at the summary, after registering the other tasks. The
  removal now stops at the watchdog's block, and the help, summary and wrapper
  call keep it.
- **`Private/Get-LastWakeTime.ps1` ships.** X10 left it out with the backups,
  but the watchdog's wake guard calls it, so the shipped watchdog threw
  `CommandNotFoundException` and 34 of its Pester tests failed. One `edits`
  entry rewords its help, which named only the backup.
- Pester 5.7.1 on Windows (pwsh 7.6), run on the generated starter: 307
  tests, 300 passed, 7 skipped (the Linux-only trust cases, as in the source)
  once the wake guard shipped. Before that fix, the 34 watchdog failures above
  were the only ones.

| Source | Before | After |
|---|---|---|
| wsl-automation | `460f6c77fe5e` | `155123c1fbde` |

The Pester suite needs pwsh 7.6, which the cloud container lacks, so the
patched `Tasks.Tests.ps1` counts (seven S4U principals, eight script actions,
the shared settings) were derived by reading the patched installer, not run.

Reverse: restore the previous pin, drop the four exclusions and the three
export edits, exclude `Get-LastWakeTime.ps1` again, and revert the three
patches.

## Re-pin round 10 (2026-11-12)

`export/resync.py` moved all five public pins to their sources' current heads.
The export then failed, and the kit follows the source in each case:

- **`debug-github-workflows` leaves the library.** The owner retired the skill
  in the agentskills registry (PR #147, `3795a5e`), so `library_skills.py` could not
  find `plugins/acsi-coding-anywhere/skills/debug-github-workflows/SKILL.md`.
  skills-evals keeps the skill's fixtures under `evals/debug-github-workflows/`
  (the owner's policy keeps fixtures on removal), but the kit ships no fixture
  for a skill it does not ship (X9), as for `ci-job-performance`. So the item
  goes whole: its `OPTIONAL` row in `library_skills.py` and its `ITEMS` row in
  `library_fixtures.py`; its catalog entry in `bootstrap/content-catalog.json`
  (the recommended tier is now eight items: two skills, four safety sections
  and two habits sections, and `test-bootstrap.sh` expects eight and greps the
  dry run for `would install disarm-inherited-reach`); the manifest comments
  and `docs/skills.md`. The manifest now excludes `evals/debug-github-workflows/`
  and the four `test/issues/test_issue_76*.py` modules that only lock those
  fixtures. The retarget that skipped the `wrong-branch` fixture in the
  `.git/` scan test is gone with its reason (the note in Content tiers
  stays as history). The `REVIEWED` list in `retargets.txt` still names the
  four fixtures, because it is the source text that patch anchors on, and the
  kit replaces the whole list.
- **The source removes unused skills.** `retire_skill.py`'s `plan()` now
  calls `unused_plan()` when no skill has a `retire` verdict, which removes a
  skill that `removal_policy.unused_removal` calls unused, except those in
  `evals/usage-unknown.yml`. The retirement-exempt patch's anchor moved with
  the new `if skill is None:` branch (updated, same guard). The kit's rule is
  that the automatic retirement never removes a core item, so the patch also
  adds the core skills to the exempt set `unused_inputs()` returns, which
  covers `unused_plan()` and `unused_checker()` alike. A test in
  `test_issue_retirement_exempt.py` locks it. The unused removal itself
  ships as the source has it.
- skills-evals' new `test_issue_unused_removal.py` compares the removal's pull
  request URL with a literal `https://github.com/<owner>/<registry>/pull/999`.
  As one literal after `github.com/` it was protected as a citation (P2) and
  kept the source owner's name, so the test failed in the kit. A manifest
  edit splits the literal so the C1 renames reach it.

| Source | Before | After |
|---|---|---|
| _agent-guidance | `6026fa78be2c` | `458b958ad310` |
| acsi-agentskills | `60d805ca926c` | `3795a5e5eef8` |
| repo-settings | `a890dbc58797` | `0ae5a7ed1d3b` |
| skills-evals | `a50f114e26b9` | `b345ff7506c3` |
| wsl-automation | `155123c1fbde` | `aa78623ef6e9` |

Reverse: restore the previous pins, the `debug-github-workflows` rows,
catalog entry, test expectations and docs wording, drop the two manifest
exclusions, put back the `.git/` scan exception, and revert the two
retirement-exempt edits, the new test and the URL edit.

## Re-pin round 11 (2026-11-12)

`export/resync.py` moved all five public pins to their sources' current heads.
The export then failed in two places, and the kit follows the source in both:

- **skills-evals removed the dashboard's Loop tab.** `dashboard/build.py` no
  longer has `loop()`, `loop_gaps` or the `loop_status.json` input (the loop's
  gap list, and the stages, grid and lanes built from it), so the two `build.py`
  cold-start edits that gave those a placeholder row or an optional input had
  nothing to anchor on, and the README row for `loop_status.json` is gone from
  the source. Those three edits are dropped with the feature. What stays: the thread
  placeholder row (`threads()` still returns an empty list for a project with no
  threads), so the `datasets.js` edit now adds only `threads: 'id'` and the
  empty-inputs regression test checks the thread row alone. The source also
  dropped `ci_red_runs`, the cleanup, gate and decisions datasets and the
  decisions column in the cost weeks, and added `refresh` and the
  "since reset" allowance figures; none of that touches a kit edit.
- **The usage census now dispatches the Evals Explorer data workflow.**
  wsl-automation's `publish-usage-census.sh` runs `gh workflow run
  explorer-data.yml` in its clone after a real publish, so the explorer
  rebuilds the same day. The kit ships that workflow (the Evals fragment), so
  the dispatch ships as the source has it. Its README paragraph and the script
  header said a failed dispatch "shows in Task Health", which the kit leaves
  out (X10), so the README patch and a manifest edit on the script say "the
  task's last result shows it" instead. The patch's guard against the words
  "Task Health" is unchanged and now passes.
- **Two test literals follow the renames.** skills-evals' explorer test builds
  live pull request URLs as one `https://github.com/<owner>/<registry>/pull/N`
  literal, which kept the source owner's name (P2) while the document's row was
  renamed, so the "once each" test saw two rows. A manifest edit splits each
  literal, as in round 10. The Summary page's "names no person" check in
  `tool/test/run.js` looked for "the owner", which C10 puts on the page on
  purpose; it now looks for the kit's invented person, as the dashboard build
  test already does.
- The other three sources changed without a break.
  `fleet-memory.sh` gains the hosted-session git hooks and
  `guidance-load-record.sh` grows (both ship unchanged, in every starter that
  carries them).

| Source | Before | After |
|---|---|---|
| _agent-guidance | `458b958ad310` | `5c6b3aebb001` |
| acsi-agentskills | `3795a5e5eef8` | `27994ee9c516` |
| repo-settings | `0ae5a7ed1d3b` | `970e1c54aa94` |
| skills-evals | `b345ff7506c3` | `194edfb4bf0f` |
| wsl-automation | `aa78623ef6e9` | `6987040ddf99` |

Reverse: restore the previous pins, put back the two loop cold-start edits in
`build.py` and the `loop_status.json` README edit, the `loop_gaps` key in the
`datasets.js` edit and the gap lines of the empty-inputs test, and drop the
census README patch step, the script header edit and the three test edits
above.

## Re-pin round 12 (2026-11-13)

`export/resync.py` moved all five public pins to their sources' current heads.
The export failed in one place, and the kit follows the source:

- **_agent-guidance added a `local-identity` check to the agent-checks
  runner.** It refuses a changed file that holds the committing machine's own
  account name in a home path, or its hostname; the names come from the
  machine at run time, so the runner carries none, and it never runs under
  GitHub Actions. The source's `test_core_check_ids` now lists the id, so the
  `machinery_tests.py` anchor on that assertion matched nothing. The anchor and
  its replacement carry the new id, and so does the inverse replacement the
  `rules-dir` library item makes (`library/git-hooks/rules-dir/agent-guidance/ops.json`).
  The check ships in the kit's runner as the source has it, beside
  `secret-file` and `skill-shell`: it names nobody and holds no opinion about
  how a repo is laid out, so it is treated as core, not as a library item.
  Its tests ship unchanged. Every starter's `.githooks/agent-checks` copy
  follows, the private registry's included (a `copy_from_kit` of the exported
  template, written by hand because the fix routine cannot read the private
  source).
- **skills-evals added a second fixture to the `subagent-delegation`
  guidance item** (`routing-four-tasks`) and its weekly row. The library item
  carries both; `library/` was rewritten from the five public sources (the
  private registry puts nothing in it).
- The other sources changed without a break. skills-evals also gains the
  `docs-only-required-check` fixture and explorer and dashboard changes;
  wsl-automation changes `tests/CcstatuslineConfig.Tests.ps1`.

| Source | Before | After |
|---|---|---|
| _agent-guidance | `5c6b3aebb001` | `30ba3821c6e7` |
| acsi-agentskills | `27994ee9c516` | `e2069029fb3f` |
| repo-settings | `970e1c54aa94` | `b1423a5eee85` |
| skills-evals | `194edfb4bf0f` | `685ab6bcb979` |
| wsl-automation | `6987040ddf99` | `72c5a0c3165f` |

Reverse: restore the previous pins and drop `"local-identity"` from the
`test_core_check_ids` anchor, its replacement and the library item's inverse
replacement in `machinery_tests.py`. To ship the kit without the check
instead, move it to a library item as `rules-dir` is (`blank_content.py`).

## The guidance overlap judgment (2026-11-10)

`_agent-guidance#495` added a warn-only "Repo-specific guidance overlap"
section to the nightly drift report and gave the judgment on each entry
(make it a check, a skill or a `base.md` section, or delete the local copy)
to item 8 of the source owner's weekly Fleet health audit. The kit excludes
that audit (Re-pin 2026-11-03), so round 7 shipped the detector with a dead
README link and nothing in an adopter's setup that acted on its entries.

- Five `edits` in `_agent-guidance.yml` move item 8's rules into the
  README's "Repeated guidance across repos", worded for the adopter, and
  point the workflow comment, the script's header and report line, and the
  retirement note there.
- `docs/week-to-week.md` gives the weekly review a row.
- `export/tests/test_no_links_to_excluded.py` fails when an exported
  Markdown file links to a file its manifest excludes, so the next excluded
  target of a live link is caught at re-sync, not by an adopter.

Reverse: drop the five edits, the row and the test.

## The shipped-names ledger (2026-11-10)

adam-agentskills#133 added `scripts/shipped_names.json`, the append-only
record of every name that has shipped, and two checks read it as retired:
`check_one_way_doors.py` fails a pull request that adds a listed skill
basename, and skills-evals' `draft_new_skill.py` refuses a drafted skill with
a listed name. The kit shipped the source's ledger, which names about twenty
skills the adopter's registry never had, the five library skills among them.
Adding a library skill with `add-content.sh` once the repos existed would fail
the required `pytest` check, and the draft lane could not use those names.

- `export/patches/agentskills/shipped_ledger.py` keeps the skills on disk,
  the removals the exported `docs/skill-impact.md` records (the starter's own
  test requires them), the marketplace's plugins and its name.
- `export/tests/test_shipped_ledger.py` fails when the ledger lists a library
  skill, or misses a skill the registry ships.

Reverse: drop the patch, its manifest entry and the test.

## Prompt-audit sweep (2026-11-13, issue 37)

The 2026-11-10 prompt audit filed seven findings. One was confirmed and fixed:
`skills-doctor` named the flat `synced/manifest.json` in its description and
channel table while its own trap section and commands use
`synced/<bucket>/manifest.json`. Three manifest `edits` on `agentskills`
change those lines; the source registry carries the same wording, so fix it
there too and drop the edits when a re-pin brings it.

Not fixed, with the reason:

- Issue and pull request numbers in the `repo-settings` and `agent-skills`
  `AGENTS.md` (findings 1, 3, 4) are P2 citations: history kept on purpose, and
  the export already substitutes owners, not numbers.
- The "from 2026-11-02" date (finding 5) is not verifiable from the repo.
- "the backup the adoption kit leaves out" (finding 6) is true of the kit and
  reads correctly to an adopter (X10).
- The `debug-github-workflows` skill (finding 7) is not in this kit; the
  `jodidaniel.com#264` text is in the starter's `skill-impact.md`, an ADR-style
  record (P2), and the registry skill is not shipped.

Reverse: drop the three edits.

## Local username rule (2026-11-13, issue 47)

`leak_scan` gains two rules for a local username: one in a home-directory path
(a Linux, macOS, WSL-share or Windows-drive home folder followed by the user component) and one in a
Claude-encoded project directory (the encoded form of such a path). Neither spells a name:
each matches the SHAPE and passes only the invented placeholder users the
starters use (`example`, `user`, `runner`, `fixtureuser*`, `fictional-dev`,
and a few one-word fixtures). A bare-substring rule would also hit ordinary
identifiers that contain the name. A new invented user a fixture needs is added
to the list in both patterns; `test_scanner_flags_a_username_in_a_home_path_but_not_a_placeholder`
pins both sides. The private `PRIVACY_DENYLIST` stays the place for the exact
name.

Reverse: drop the two `leak_scan` entries and the test.

## Re-pin round 13 (2026-11-13): follow three source changes

All five public pins move to their heads; `agentskills-private` keeps its pin and its lockfile follows the new public registry. Three source changes needed a follow-up in the `_agent-guidance` patches, and each had held that source back since 2026-11-10:

- `_agent-guidance` rewrote the `acsi-kit` bullet in `repos.yml` (it no longer ends "as for verify-actions-lock") and added a bullet about `verify-actions-lock` before `exclude:`. `patches/_agent-guidance/kit_repos.py` matches the new text and still drops both bullets and the exclusion (the kit is not in an adopter fleet).
- A case in `test/fixtures/agent-checks-cases.jsonl` carries Unicode whitespace inside a JSON string, so `machinery_tests.py` splitting the file with `str.splitlines()` cut a line in two. It now splits on newline only.
- ADR 0043 gave every row of `agents-md/eval-coverage.yml` an `audience`. The rows `blank_content.py` writes for empty section files and gap rows say `contributor`, as the source does for its own section files.

The prompt-file count floor in `test_routine_prompts_name_only_kit_repos` drops from 8 to 7: the sources dropped another routine prompt.

After merging main (which brought the prompt-audit sweep), the pins moved again to the heads of 2026-11-13: all five public sources exported at their new heads with no further patch change, so none is held back. The three `skills-doctor` edits from the sweep still apply: the source has not yet fixed the wording.

Reverse: re-pin the old shas and revert the three patch edits.

## Re-pin round 14 (2026-11-13): follow the eval-rules changes

All five public pins move to their heads; `agentskills-private` keeps its pin. The 2026-11-13 re-sync held `skills-evals` back, and `_agent-guidance` broke too once it moved past its new section:

- `_agent-guidance` added the base.md section "Eval rules" (`_agent-guidance#558`), which points at `skills-evals`' generated `docs/rules.md`. `blank_content.py` lists it with tier `none`: only the evals track ships `skills-evals`, so a base-only adopter would get a pointer to a repo it does not have. The kit's own docs link the starter copy of `docs/rules.md` instead.
- `skills-evals` deleted the `debug-github-workflows` fixtures and the four `test_issue_76*` tests that locked them. The manifest drops their five excludes, and `retargets.txt` drops the four fixture paths from `test_issue_scheduled_fixtures.py`'s `REVIEWED` anchor.
- `_agent-guidance` rewrote the stub's first section (ADR 0043). `starter/agent-skills-private/AGENTS.md` takes the rebuilt managed block, written by hand from `bootstrap/lib/content.py`'s recipe because the private source is not exported here.
- `library/` was rewritten from the five public sources (the private registry puts nothing in it): two library items follow `skills-evals`' schedule changes.

| Source | Before | After |
|---|---|---|
| _agent-guidance | `35c62e01891c` | `0ef732fdbd82` |
| agentskills | `c25ca77a9c8a` | `bc0b75555d52` |
| repo-settings | `e64fc208cdce` | `bcd342771667` |
| skills-evals | `8b578f31ce49` | `b93d1d9a79f6` |
| wsl-automation | `19c8232e6d67` | `4aa4768aadb6` |

Reverse: re-pin the old shas, put back the five excludes and the four `REVIEWED` lines, and drop the "Eval rules" row from `blank_content.py`.
