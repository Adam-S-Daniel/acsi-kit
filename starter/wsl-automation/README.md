# wsl-automation

PowerShell automation for a WSL2 Ubuntu distro on Windows, with the same
scheduled jobs available natively on Linux and macOS:

- A daily usage census publish (see "Usage census task" below).
- An every-minute feed of the Claude Code cloud sessions waiting on you (see
  "Waiting feed task" below).
- A daily session miner run that turns this machine's Claude Code transcripts
  into short, redacted lesson records (see "Session miner task" below).
- A weekly memory curation run that tidies Claude Code's private memory notes
  in both Claude homes on this machine (see "Memory curation task" below).
- A sync of the WSL ccstatusline layout to Windows, and a twice-daily sync of
  Codex Cloud environments.
- A scheduled-task installer that wires all of the above into Windows Task
  Scheduler, and scripts that pre-trust your workspaces for Claude Code and
  Codex.

## What this is

`wsl-automation` is a small PowerShell 7.6+ module (`WslAutomation`) plus a
handful of thin wrapper scripts meant to be run directly or from Windows
Task Scheduler. `scripts\register-tasks.ps1` creates or updates the scheduled
tasks idempotently, and archives any legacy ad-hoc scripts they replace. The
jobs that run inside the distro are Bash, so on Linux or macOS
`scripts/unix/install-schedule.sh` schedules them with systemd, launchd or cron
instead (see "Linux and macOS" below).

## Install

1. Clone this repository anywhere on the machine, for example:

   ```
   C:\Users\<you>\repos\wsl-automation
   ```

2. **Background-task prerequisites (once per machine).** Every task runs as a
   background (S4U, session 0) task, so a run never flashes a window on the
   desktop. That imposes two one-time requirements:

   - **PowerShell 7 installed via MSI** (not the Microsoft Store build). A
     Store-packaged pwsh cannot be activated in session 0, so the pwsh-based
     tasks need a non-packaged pwsh at `C:\Program Files\PowerShell\7\`.
     Install it with `winget install --id Microsoft.PowerShell --scope
     machine` or the MSI from the PowerShell releases page. `register-tasks`
     prefers this path automatically and warns if only a Store pwsh is found.
   - **The "Log on as a batch job" right** for your account, which a
     background (S4U) task needs. On a machine where you are a local admin
     this is *not* covered by the default Administrators grant (an S4U logon
     gets a UAC-filtered token in which Administrators is deny-only). Grant
     it to your own account from an elevated prompt:

     ```powershell
     .\scripts\grant-keeper-batch-logon.ps1
     ```

3. Open an elevated PowerShell 7.6+ prompt (scheduled task registration
   needs administrator rights) and run the task installer:

   ```powershell
   cd C:\Users\<you>\repos\wsl-automation
   .\scripts\register-tasks.ps1
   ```

   This creates/updates the scheduled tasks described below. Re-running it is
   safe and idempotent - it will update the existing tasks in place rather
   than duplicating them. `-WhatIf` shows what it would change.

4. **Windows ccstatusline runtime (once per machine).** Run
   `.\scripts\install-ccstatusline.ps1` from a normal PowerShell 7 prompt; see
   [Windows runtime (one-time)](#windows-runtime-one-time).

5. **Settings for the Bash tasks (once per machine, in the distro).** Copy
   `config/settings.env.example` to `~/.config/wsl-automation/settings.env`
   and set each key to your own repository. The census, waiting feed, session
   miner, memory curation and Codex Cloud sync have no built-in repository: a
   task whose key is missing exits 2 naming it. See
   [Settings file for the Bash tasks](#settings-file-for-the-bash-tasks-settingsenv).

6. **Session miner (once per machine).** The session miner task refuses to
   mine until you have set it up and run it by hand once; see
   [Session miner task](#session-miner-task-default-name-session-miner). Its
   settings go in the same `settings.env`.

## Task descriptions

### Checkout update before every scripted task

Every task action runs a repo script (ccstatusline sync, Codex Cloud sync,
usage census, session miner, memory curation, waiting feed, and the Docker watchdog), and first updates that same
checkout through one updater, `Update-WslAutomationRepo`, before it loads any
task code. All six run from the one Windows checkout; the Bash
tasks reach it through its `/mnt` path, so there is no second clone to keep
current. Whatever lands on `main` runs with the Claude login and the git
credential in reach, so keep `main` protected.

There are two entry shapes and one bootstrap for each, both calling the same
updater:

| Entry | Bootstrap | Tries | Bounded by |
| --- | --- | --- | --- |
| PowerShell (ccstatusline, Codex Cloud, Docker watchdog) | `scripts/update-task-checkout.ps1` (`Initialize-WslAutomationTask`) | every run | 30 s per Git call |
| Bash in WSL: usage census (daily) | `scripts/update-task-checkout.sh` | every run | 300 s overall |
| Bash in WSL: session miner (daily) | `scripts/update-task-checkout.sh` | every run | 300 s overall |
| Bash in WSL: memory curation (weekly) | `scripts/update-task-checkout.sh` | every run | 300 s overall |
| Bash in WSL: waiting feed (every minute) | `scripts/update-task-checkout.sh` | at most every 5 minutes | 120 s overall |

The task actions themselves are unchanged, so **no re-registration is needed**
when the bootstrap changes; the next run of any task picks it up from the
checkout. A Pester test reads the installer's registered actions and fails if
any script action skips its bootstrap, so a new task cannot be added without it.

Each run fetches `origin`, switches to `main` if necessary and the working tree
is clean, then runs `git merge --ff-only origin/main`. The old 12-hour update
interval is removed. A per-checkout named mutex serializes updates across
Windows sessions, with a 5-second lock wait. Every Git call has a 30-second
timeout and authentication prompts are disabled. Changed HEADs and warnings go to
`%LOCALAPPDATA%\wsl-automation\repo-update.log` without raw Git output or
credential-bearing URLs. Unchanged successful updates are silent, so their short
intervals do not grow the log with no-op messages.

- Dirty tracked or untracked files: warn and leave the working tree and branch
  untouched; run the task using the current code.
- A clean checkout on another branch (or detached HEAD): switch to `main`.
- Local commits on `main`, including a checkout ahead of or diverged from the
  remote: warn and skip the fast-forward. No merge commit, reset, stash, clean,
  or force operation is used.
- Offline, failed or timed-out Git, or lock contention: warn and continue the
  task using the current code. The next run retries.

When HEAD changes, PowerShell entries run themselves once in a fresh
PowerShell host before loading task code, preserving parameters and exit status.
The Bash entries source `update-task-checkout.sh`, which calls the same updater
through PowerShell 7 (`pwsh.exe` on PATH, falling back to the standard MSI
install) as `update-task-checkout.ps1 -UpdateOnly`, then re-execs the entry from
disk once with its arguments (Bash reads a script as it runs, so the old copy
must not carry on). Coreutils `timeout` bounds that Windows update to the
entry's deadline, with a 5-second kill grace period; a timeout or a missing
utility warns and lets the task continue. The waiting feed's 5-minute throttle
is by attempt, recorded in `~/.local/state/wsl-automation/checkout-update.stamp`:
starting a Windows PowerShell host and fetching every minute would cost more
than the publish itself, and an offline machine then retries once per interval
rather than every minute. Its 120-second deadline leaves room inside the task's
5-minute limit. Environment guards keep every entry from looping.
`pull-repo.ps1` remains a separate, manual general-purpose pull tool; scheduled
self-updates do not call it.

**Trust:** tasks execute whatever code is on `main`. The default branch is
PR-only through the [repo-settings rulesets](https://github.com/example-adopter/repo-settings/blob/main/fleet.yml).
Reviewing and merging a change therefore also authorizes it to run on the next
task invocation. Dirty, divergent, or unavailable checkouts can continue to run
older or local code until their warning is resolved.

### Settings file for the Bash tasks (`settings.env`)

A value that names one of your own resources (a repository or URL) is set in
one place and has **no fallback in code**. The Bash tasks start through
`wsl.exe` from Task Scheduler with no environment of their own, so those values
live in `~/.config/wsl-automation/settings.env` inside the distro. Copy
[`config/settings.env.example`](config/settings.env.example) there and replace
its placeholder values with yours.

| Key | Task that uses it |
| --- | --- |
| `SKILLS_EVALS_URL` | Usage census and Session miner (the skills-evals repository to clone) |
| `AGENT_GUIDANCE_URL` | Memory curation (the `_agent-guidance` repository to clone) |
| `WAITING_FEED_URL` | Waiting feed (the feed repository it pushes to) |
| `LESSONS_CLONE` | Session miner (the private registry clone that receives lesson records) |
| `CODEX_CLOUD_GUIDANCE_REPOSITORY` | Codex Cloud environment sync (the guidance repository as `owner/name`) |

- **The file is read as data, never sourced.** One `KEY=VALUE` per line; blank
  lines and `#` comments are skipped, only the key a task asks for is taken
  (the last occurrence wins), a value starting with `~/` expands to your home
  directory, and nothing else is expanded: no quotes are stripped and no
  variable is substituted. A line that is neither a comment nor `KEY=VALUE`
  is an error that names its line number (never the path, which holds your
  user name).
- **The environment wins.** A key already set and non-empty in the task's
  environment is used as is, and the file is not read for it.
  `WSL_AUTOMATION_SETTINGS` points at a different file (tests use this).
- **Missing means exit 2.** When a key is unset or empty everywhere, the task
  exits 2 with `<KEY> is not set; set it in ~/.config/wsl-automation/settings.env
  (WSL_AUTOMATION_SETTINGS; see config/settings.env.example) or the
  environment`. The tasks that keep a log also write a line naming the key
  (`... setting <KEY> is missing or invalid`, with `exit=2`); no path goes into
  it. The resolver is `scripts/task-settings.sh`
  (`wsl_automation_require_setting KEY`).
- **The session miner reads this file too**, with its own reader: it
  takes `LESSONS_CLONE` (required) and its optional keys from here and
  ignores the other tasks' keys (see
  [Session miner task](#session-miner-task-default-name-session-miner)).

### ccstatusline config sync task (default name: `ccstatusline Config Sync`)

- Runs `scripts\sync-ccstatusline-config.ps1` every 5 minutes as a background
  S4U task for the current Windows user (the MSI PowerShell and batch-logon
  prerequisites of Install step 2).
- Copies the WSL `~/.config/ccstatusline/settings.json` to
  `%USERPROFILE%\.config\ccstatusline\settings.json`. WSL is the source of
  truth: the Windows copy is kept read-only, and the task never writes back
  into WSL.
- A shut-down distro (or a source file that is not there) is a no-op that
  keeps the existing Windows copy rather than treating it as deleted.
- Logs outcomes to `%LOCALAPPDATA%\wsl-automation\ccstatusline-sync.log`. A run
  that finds the copy already in sync logs nothing.

#### Windows runtime (one-time)

The task copies only the layout. Windows Claude Code also needs its own
runtime (Bun plus the `ccstatusline` npm package) and its own `statusLine`
entry in `%USERPROFILE%\.claude\settings.json`, because `statusLine` is a
per-OS command: the WSL entry points at a Linux path, and the settings sync
skill deliberately never copies it. From a normal (non-elevated) PowerShell 7
prompt:

```powershell
.\scripts\install-ccstatusline.ps1
```

It is idempotent, installs Bun with winget when needed, pins the Bun and
ccstatusline versions, backs up `settings.json` before editing it, and refuses
to replace a different existing `statusLine` unless you pass `-Force`. Restart
Windows Terminal (and any Windows Claude Code sessions) afterwards so they pick
up the new PATH.

### Codex Cloud environment sync task (default name: `Codex Cloud Environment Sync`)

- Runs `scripts\sync-codex-cloud-environments.ps1` at exactly 00:00 and 12:00.
  A missed time remains missed; it does not use `-StartWhenAvailable` or wake
  the computer.
- Runs as a background S4U task for the current Windows user, is allowed on
  battery, has a 15 minute execution limit, and ignores a second overlapping
  instance. It uses the MSI PowerShell and batch-logon prerequisites of
  Install step 2.
- First checks that the selected WSL distro is already running. A stopped
  distro is skipped without invoking a distro command. When it is running, the
  task refreshes the authenticated Codex CLI state, pages through the Code
  Review repository inventory, and maps each repository to a connected GitHub
  connector by an exact repository-name lookup. It uses authenticated GitHub CLI
  metadata to skip forks, so only connected non-forks receive environments. Each
  environment has only its target repository selected, including the guidance
  repository's own environment. Automatic setup is disabled. Setup and
  maintenance use the same generated script, starting in the selected
  repository's checkout:

  ```bash
  set -euo pipefail
  cd /workspace/<target-repository>
  if [[ -f package-lock.json ]]; then npm ci; fi
  CODEX_HOME="${CODEX_HOME:-/opt/codex}" bash .claude/hooks/fleet-memory.sh --codex-cloud
  ```

  A repository without `skills.lock` reports a healthy skills skip. An enrolled repository
  must also contain its delivered `.claude/hooks/skills-bootstrap.sh`; a missing
  or invalid lock or hook fails setup. For an enrolled repository, the script
  downloads your registry's `.claude/hooks/skills-bootstrap.sh` at one
  reviewed, immutable commit, checks its SHA-256 digest (both pinned at the
  top of `scripts/sync-codex-cloud-environments.sh`, and all zeros until you
  set them, which fails closed: setup reports skills DEGRADED), and runs it with `CLAUDE_PROJECT_DIR` set to that repository and
  `--codex-cloud`. The bootstrap reads from `/dev/null` because Cloud keeps
  setup stdin open. The repository's own lock controls which skills install.
  The reconciler updates only setup, maintenance, the selected repository,
  and automatic setup when those fields drift; unrelated environment settings
  remain in place.

  The reconciler requires `codex`, `curl`, `jq`, `flock`, and `mktemp` inside
  the distro. Its status output is aggregate-only and excludes account,
  repository, environment, and response-body data.
- The synchronizer calls Codex's private ChatGPT web API. That contract is not
  a public stability guarantee, so this script may need an update if Codex
  changes the environment or repository-discovery endpoints.
- Logs outcomes, without response data, to
  `%LOCALAPPDATA%\wsl-automation\codex-cloud-sync.log`.

### Usage census task (default name: `Usage Census Publish`)

- Runs `scripts/publish-usage-census.sh` inside the distro once a day at
  12:37 (`-UsageCensusTime`). The wrapper shallow-clones skills-evals `main`
  and runs that copy's `scripts/publish_usage_census.sh`, which reads
  `~/.claude/projects` and pushes `usage/latest.json` to skills-evals'
  `persistent/eval-results` branch. It clones `main` rather than using a local checkout
  because the local checkout may be on any feature branch. See
  [CENSUS.md](https://github.com/example-adopter/skills-evals/blob/main/evals/usage/CENSUS.md)
  for what the census records.
- The action is `wsl.exe` directly, with no pwsh in between:

  ```
  C:\Windows\System32\wsl.exe --distribution Ubuntu --cd "<scripts dir>" --exec /bin/bash ./publish-usage-census.sh
  ```

- Runs as a background S4U task for the current Windows user (session 0), so
  no console window ever appears. The WSL git authenticates through
  `gh auth git-credential` with a file-stored token, which works in an S4U
  logon.
- Allowed on battery, 15 minute execution limit, ignores a second overlapping
  instance. There is no `-StartWhenAvailable`: a missed day stays missed (the
  census's 14-day freshness window and 6-day re-publish absorb it), and a
  catch-up at wake would land in WSL's post-wake transition window. 12:37 keeps
  it off the hour.
- Appends one line per run (UTC time, exit code, totals-only summary) to
  `~/.cache/usage-census.log` inside the distro.
- Run it now: `Start-ScheduledTask -TaskName 'Usage Census Publish'`.
- Check it:
  - `(Get-ScheduledTaskInfo -TaskName 'Usage Census Publish').LastTaskResult`
    is `0`.
  - In WSL, `tail ~/.cache/usage-census.log`.
  - `git ls-remote https://github.com/example-adopter/skills-evals persistent/eval-results`
    shows the branch head moving after a publish.

### Session miner task (default name: `Session Miner`)

- Runs `scripts/run-session-miner.sh` inside the distro once a day at 07:17
  (`-SessionMinerTime`). Like the census, the wrapper shallow-clones
  skills-evals `main` and runs that copy's `scripts/run_session_miner.sh`
  (skills-evals ADR 0015), so a scheduled run always executes the reviewed
  `main` version.
- It reads this machine's real Claude Code transcripts. What leaves the
  machine is short, redacted, hashed lesson records, pushed to the
  `persistent/lessons` branch of your private skills registry. The wrapper never
  copies a transcript anywhere, and it refuses to run in CI or in a cloud
  session (`CI`, `GITHUB_ACTIONS`, `CLAUDE_CODE_REMOTE` or
  `CLAUDE_CODE_REMOTE_SESSION_ID` set).
- The action is `wsl.exe` directly, as for the census:

  ```
  C:\Windows\System32\wsl.exe --distribution Ubuntu --cd "<scripts dir>" --exec /bin/bash ./run-session-miner.sh
  ```

- Runs as a background S4U task for the current Windows user (session 0).
  Allowed on battery, 30 minute execution limit, ignores a second overlapping
  instance, no `-StartWhenAvailable` (a missed day stays missed; the next run
  reads what it missed).
- **One-time setup, in the distro.** Until a dry run has succeeded, a
  scheduled run exits 3 ("not set up yet") and mines nothing.
  1. A privacy denylist, one pattern per line, kept **outside every
     repository**: `~/.config/privacy-denylist.txt` (`PRIVACY_DENYLIST_FILE`).
     Without a readable one the wrapper exits 2 and nothing is mined.
  2. A clone of your private skills registry whose `origin` receives
     `persistent/lessons`, for example `~/repos/acsi-agentskills-private`.
     Its git credential must work with no desktop session: `gh auth setup-git`
     with a file-stored token, as for the census.
  3. python3 with PyYAML (`sudo apt install python3-yaml`).
  4. Settings in the Bash tasks' one settings file,
     `~/.config/wsl-automation/settings.env` (`WSL_AUTOMATION_SETTINGS`; see
     [Settings file for the Bash tasks](#settings-file-for-the-bash-tasks-settingsenv)),
     copied from `config/settings.env.example`. `LESSONS_CLONE` (that clone)
     and `SKILLS_EVALS_URL` (your skills-evals) are required and have no
     default, because they name your own repositories; unset, the wrapper
     exits 2 naming the key. A scheduled action has no environment of its own,
     so this is where settings go. The file is read as data, never sourced;
     the wrapper takes only `PRIVACY_DENYLIST_FILE`, `LESSONS_CLONE`,
     `GUIDANCE_MANIFEST`, `MINER_REGISTRIES`, `WIN_HOME`, `MINER_STATE`,
     `SKILLS_EVALS_URL`, `PYTHON` and `FILE_ISSUES` from it and ignores the
     other tasks' keys, a leading `~/` is expanded, a line that is not
     `KEY=value`, a comment or blank exits 2, and a variable already in the
     environment wins.
  5. One run by hand: `bash scripts/run-session-miner.sh --dry-run`. It mines
     and reports without pushing, and on success records
     `~/.local/state/session-miner/dry-run-ok`, which arms the scheduled run.
- **`WIN_HOME`** (the Windows profile as a WSL path, for example
  `/mnt/c/Users/<you>`) adds the Windows transcripts and the desktop app's
  metadata, which lets the miner drop scheduled-task sessions as noise.
  Without it the wrapper reads only `~/.claude/projects` in WSL, rather than
  have the miner ask `cmd.exe` from a session 0 logon, and says so in its log
  line.
- **Filing issues stays off.** `--file-issues` exits 2 unless `FILE_ISSUES=on`
  is set; turn it on only after you have rated a sample of records for
  usefulness and privacy.
- Appends one line per run to `~/.cache/session-miner.log`: UTC time, exit
  code, and the miner's own `session miner: ...` count lines. Any other output
  (a Python traceback, for example) could carry a path or an excerpt, so it is
  counted, not copied. Exit codes: 0 success; 1 a missing prerequisite (the
  registry clone, PyYAML) or a failed clone of skills-evals; 2 a refusal (CI or
  cloud, no denylist, a bad settings line, an unset `LESSONS_CLONE` or
  `SKILLS_EVALS_URL`, `--file-issues` while off); 3 not
  set up yet; anything else is the miner's own exit code.
- Run it now: `Start-ScheduledTask -TaskName 'Session Miner'`; check
  `(Get-ScheduledTaskInfo -TaskName 'Session Miner').LastTaskResult` is `0`
  and `tail ~/.cache/session-miner.log` in WSL.

### Memory curation task (default name: `Memory Curation`)

- Runs `scripts/run-memory-curation.sh` inside the distro once a week, on
  Monday at 13:47 (`-MemoryCurationTime`). It
  is the machine half of the routine in
  [_agent-guidance's `docs/routines/memory-curation.md`](https://github.com/example-adopter/_agent-guidance/blob/main/docs/routines/memory-curation.md):
  the wrapper shallow-clones `_agent-guidance` `main` and starts a headless
  Claude session in that copy, with a short prompt that points at the doc.
- **It covers both Claude homes on this machine.** Claude Code keeps memory in
  the WSL home (`${CLAUDE_CONFIG_DIR:-~/.claude}`) and in the Windows home
  (`%USERPROFILE%\.claude`). The wrapper resolves the Windows home at run time
  (`cmd.exe` through WSL interop, then `wslpath`; override it with
  `WINDOWS_CLAUDE_HOME`), passes every `projects/*/memory/` directory of both
  homes to the session, and runs on the WSL home alone, with
  `windows_home=unresolved` in the log, if the Windows one cannot be resolved.
- **Memory is private.** Claude's final summary is written to
  `~/.cache/memory-curation/last-summary.md` (mode 600) and printed to stdout.
  The log, `~/.cache/memory-curation.log`, gets one line per run (UTC time, exit
  code, mode, and counts of homes, memory directories, notes and archived
  notes before and after) and never a path, note name, note text, or Claude
  output.
- The action is `wsl.exe` directly, as for the session miner:

  ```
  C:\Windows\System32\wsl.exe --distribution Ubuntu --cd "<scripts dir>" --exec /bin/bash ./run-memory-curation.sh
  ```

- Runs as a background S4U task for the current Windows user (session 0), with
  the session miner's settings except for a 3 hour execution limit: allowed on
  battery, ignores a second overlapping instance, no `-StartWhenAvailable`. The
  wrapper stops Claude itself after 2 hours (`MEMORY_CURATION_TIMEOUT`).
- Run it now: `Start-ScheduledTask -TaskName 'Memory Curation'`. To try it
  without starting Claude, run `bash scripts/run-memory-curation.sh --dry-run`
  in WSL: it runs the routine's `memory_audit.py` over every memory directory
  and exits `1` if any audit fails.
- Check it:
  - `(Get-ScheduledTaskInfo -TaskName 'Memory Curation').LastTaskResult` is `0`.
  - In WSL, `tail ~/.cache/memory-curation.log`.

### Waiting feed task (default name: `Claude Waiting Feed Publish`)

- Runs `scripts/publish-waiting-feed.sh` inside the distro every minute,
  indefinitely. It lists your Claude Code cloud sessions from
  `GET https://api.anthropic.com/v1/code/sessions` (up to three pages of 100,
  plus one call for the `hearth-thread`, `cowork-local` and `cowork-remote`
  tags), keeps the ones waiting on you, and pushes `feed.json` to the
  `persistent/waiting-feed` branch of the private
  [waiting-feed](https://github.com/example-adopter/waiting-feed) repository.
  It never writes `main`: waiting-feed is a fleet repo, its `main` takes
  changes only through pull requests, and the agent-checks pre-push hook
  refuses a direct push there.
- The action is `wsl.exe` directly, as for the census:

  ```
  C:\Windows\System32\wsl.exe --distribution Ubuntu --cd "<scripts dir>" --exec /bin/bash ./publish-waiting-feed.sh
  ```

- Runs as a background S4U task for the current Windows user (session 0).
  Allowed on battery, 5 minute execution limit, ignores a second overlapping
  instance, no `-StartWhenAvailable` (a missed minute is just skipped). Like
  every task it updates its checkout from `main` first, but at most every 5
  minutes and within 120 seconds (see
  [Checkout update before every scripted task](#checkout-update-before-every-scripted-task)).
  `wsl.exe --exec` starts a non-login shell, so the script
  appends `~/.local/bin` to `PATH` itself to find a user-installed `jq`.
- **It never refreshes the login.** The token comes from
  `.claudeAiOauth.accessToken` in `~/.claude/.credentials.json` (the
  organization from `~/.claude.json`) and is passed to curl through a private
  headers file, never on a command line; the file is deleted as soon as the
  API calls finish, and lives under `$XDG_RUNTIME_DIR` (else `/run/user/<uid>`,
  else `/tmp`). curl runs with `-q` (no `~/.curlrc`) and `--proto =https`, and
  identifies itself as `waiting-feed-publisher/1`. When the token has expired,
  the feed says so until Claude Code itself renews it.
- **The endpoint is undocumented.** It is the one the Claude Code CLI uses; it
  can change or be refused without notice.
- **What is kept.** Sessions whose `status_bucket` is `blocked` (bucket
  `wait`) or `review_ready` (bucket `review`); archived sessions and anything
  tagged `hearth-overview` are dropped; items are deduplicated by id and sorted
  newest first. Items whose id is not of the `cse_` form are dropped.
- **`feed.json`**:

  ```json
  {
    "generated_at": "2026-10-24T15:04:05Z",
    "ok": true,
    "error": null,
    "items": [
      {
        "id": "cse_...",
        "link": "https://claude.ai/code/session_...",
        "title": "...",
        "bucket": "wait",
        "kind": "Claude Code",
        "updated_at": "2026-10-24T15:00:00Z",
        "ask": "What the session is waiting for, or null",
        "unread": true
      }
    ]
  }
  ```

  `kind` is `Project thread` (tag `hearth-thread`, or origin `claude-in-hearth`),
  `Cowork` (tags `cowork-local` or `cowork-remote`), or from the origin
  `Claude Code`, `Desktop`, `iPhone`, `Android`, `Web`, else `Session`. `ask`
  is the session's `needs_action`, else its `status_detail`, capped at 400
  characters; `title` is capped at 200. Both are session text copied to
  GitHub, so obvious credential shapes in them (`sk-`, `ghp_`, `github_pat_`,
  `AKIA`, Slack tokens, `Bearer ...`) are replaced with `[redacted]` first. The API exposes no project or thread ids, so `link` is always the
  plain session page.
- **Failures** keep the previous items and set `ok` to `false` with an `error`
  code, and the script exits nonzero: `no_credentials` (credentials file
  missing or unreadable), `login_expired` (token past `expiresAt`, or any HTTP
  401), `http_<code>` (any other HTTP status), `network` (curl failed),
  `bad_response` (the body was not the expected JSON).
- **Publishing.** The clone is `~/.cache/waiting-feed` (`WAITING_FEED_DIR`),
  cloned from `WAITING_FEED_URL` (a [required setting](#settings-file-for-the-bash-tasks-settingsenv), no default) when missing; a clone whose `origin` is any
  other repository is refused. Each run first fetches (with `--prune`) and
  resets the clone to `origin/main`, which keeps the hooks it carries current;
  the previous feed is read from `origin/persistent/waiting-feed`, so a commit
  made there by hand can't block later pushes. Nothing is committed while
  `ok`, `error` and `items` equal the committed ones and the last commit is
  under 15 minutes old; after that an unchanged feed is committed anyway as a
  heartbeat so a reader can tell the publisher is alive. The feed branch keeps
  exactly one commit, whose tree holds only `feed.json`: each publish pushes a
  new parentless commit with `--force-with-lease`, built with `hash-object` and
  `mktree` rather than the clone's index, so the clone stays clean and fleet
  files on `main` never ride along. Earlier titles and asks are not kept in its history
  (GitHub may still hold replaced commits by hash for a while). Commits use the
  noreply identity and a UTC date. Clone, fetch and push each time out after 60
  seconds and never prompt for credentials. A failed push is logged and exits
  nonzero, and the next run tries again.
- Output is one aggregate line per run, for example
  `waiting feed: ok=true wait=2 review=5 published=yes`, never titles, ids or
  tokens. The same line with a UTC time and exit code is appended to
  `~/.cache/waiting-feed.log` (`WAITING_FEED_LOG`) only when a run published or
  failed; past 2,000 lines the log is cut to its newest 1,000.
- Dry run (fetch and report, but no write, commit or push) from inside the
  distro: `bash scripts/publish-waiting-feed.sh --dry-run`.
- Run it now: `Start-ScheduledTask -TaskName 'Claude Waiting Feed Publish'`;
  check `(Get-ScheduledTaskInfo -TaskName 'Claude Waiting Feed Publish').LastTaskResult`
  is `0` and `tail ~/.cache/waiting-feed.log` in WSL.

### Docker WSL integration watchdog task (default name: `Docker WSL Integration Watchdog`)

- Runs `scripts\ensure-docker-wsl-integration.ps1` (`Invoke-DockerWslIntegrationWatchdog`) 12
  minutes after you log on and then every 30 minutes, indefinitely. It never
  boots a stopped distro and never prompts. The logon delay (and the function's
  own check that the machine booted or resumed at least 10 minutes ago) keeps it
  clear of WSL's post-boot init window and Docker Desktop's own start at login.
- **Why it exists.** After a reboot, Docker Desktop's WSL integration with the
  distro intermittently fails. Docker's pre-bootstrap force-unmounts its
  shared-socket mounts under `/mnt/wsl` (a mount peer group shared across
  distros), the distro can power off moments later, and its shutdown unmounts
  `/mnt/wsl/docker-desktop/shared-sockets/host-services`, so integration fails
  with `connect: no such file or directory` on `backend.sock`. Clicking "Skip WSL
  distro integration" in Docker's error dialog then removes the distro from
  Docker's integration list. A Docker Desktop restart re-creates the mounts and
  recovers the first case. See the AGENTS.md section on this and
  [docker/desktop-feedback#678](https://github.com/docker/desktop-feedback/issues/678).
- **What it checks, in order**, with one log line per step:
  1. Wake guard: less than 10 minutes since boot or resume is `DeferredRecentWake`.
  2. Docker Desktop must report `running` (`docker desktop status --format json`);
     otherwise `DockerNotRunning`, with no alert and no restart.
  3. `IntegratedWslDistros` in `%APPDATA%\Docker\settings-store.json` must include
     the distro (case-insensitive). If it does not, that is `IntegrationNotConfigured`:
     an alert telling you to turn it back on under Docker Desktop > Settings >
     Resources > WSL integration and Apply & restart. A restart cannot fix it, so
     Docker is **not** restarted. An unreadable settings file is `SettingsUnreadable`
     (log only).
  4. The distro must already be running; otherwise `DistroNotRunning`.
  5. A probe inside the distro: the shared socket exists and `docker version` answers.
     Passing is `Healthy`.
  6. Otherwise up to 2 `docker desktop restart` attempts (`-MaxRestarts`), each waiting
     up to 180 s for the engine and then up to 120 s for the probe. Passing is
     `Recovered`.
  7. Still broken is `Unrecovered`: an alert suggesting Quit Docker Desktop,
     `wsl --shutdown`, start Docker Desktop again.
- **Alerts** are a Windows toast plus an email through the
  [`send-self-alert.yml`](https://github.com/example-adopter/fastmail-actions) workflow of
  `example-adopter/fastmail-actions`, dispatched with `gh workflow run`. The email needs
  `gh` authenticated for your user and the repository secrets `SELF_ALERT_FROM` and
  `SELF_ALERT_TO` in that repository. That repository is public, so subjects and bodies are
  fixed text plus the distro name, never a host name, user name or log text, and the
  `gh` output is never logged. Each email subject ends with
  `, via "Docker WSL Integration Watchdog" <link to the script>`. An alert is sent
  once per status: the state file remembers the last alerted status and a repeat sends
  nothing until a `Healthy` or `Recovered` run clears it.
- **Logs and state**, under `%LOCALAPPDATA%\wsl-automation\`: `docker-wsl-watchdog.log`
  (outcomes only; no user name, host name or profile path) and
  `docker-wsl-watchdog-state.json` (`{ "lastAlert": "<Status>", "at": "<ISO 8601>" }`;
  a corrupt file counts as no state).
- Exit code: `0` for `Healthy`, `Recovered`, `DockerNotRunning`, `DistroNotRunning`,
  `DeferredRecentWake` and `SettingsUnreadable`; `1` for `Unrecovered`,
  `IntegrationNotConfigured` or an error. `-DryRun` logs what it would restart and alert
  without doing either.
- **Interactive, through `conhost.exe --headless`, on purpose.** Unlike the other pwsh tasks
  this one is not S4U: `docker desktop restart` relaunches the Docker Desktop GUI, which must
  land in your session rather than session 0, and the toast needs your desktop. A bare
  interactive pwsh would flash a console window every 30 minutes, so the action is
  `conhost.exe --headless pwsh.exe -NoProfile -File ...`, which runs it without one. It still
  runs as you, never SYSTEM. It has an execution limit of 20 minutes, runs on battery, and
  ignores a second overlapping instance.
- Run it now: `Start-ScheduledTask -TaskName 'Docker WSL Integration Watchdog'`, or a dry run
  with `pwsh -NoProfile -File scripts\ensure-docker-wsl-integration.ps1 -DryRun`.
### Legacy scripts

Any paths passed via `-LegacyScriptsToArchive` are renamed in place to
`<name>.superseded-<yyyyMMdd>` rather than deleted, so old ad-hoc scripts
this module replaces are preserved for reference but no longer picked up
by anything.

## Pre-trusting workspaces for Claude Code and Codex

Both agents ask for trust once per git working tree, and trusting a parent
folder does not extend to nested repositories. Two optional scripts remove
the prompts for the repos under your owner roots (default
`C:\repos\example-adopter` and `C:\repos\example-adopter-two`):

```powershell
.\scripts\trust-agent-workspaces.ps1                  # each owner root + its direct git children
.\scripts\trust-agent-workspaces.ps1 -Path C:\repos\example-adopter-two\new-repo
.\scripts\install-agent-trust-hook.ps1                # trust every future clone and worktree
```

- `trust-agent-workspaces.ps1` marks each owner root and every direct child
  with a `.git` directory or file (worktrees included) as trusted. With
  `-Path`, only those directories are trusted, and any path outside the owner
  roots is skipped. It writes `projects[<path>].hasTrustDialogAccepted` in
  `~/.claude.json` (forward-slash keys; that file is never created) and a
  `[projects.'<path>']` `trust_level = "trusted"` table in
  `~/.codex/config.toml` for both the Windows path and the WSL `/mnt/<drive>/`
  path. The `projects` format in `~/.claude.json` is undocumented and
  internal to Claude Code, so it may change without notice.
- Before a config file is changed it is copied to `<file>.bak-agent-trust`
  (one backup, overwritten each time). Nothing is written when everything is
  already trusted. Neither script prompts; the installer supports `-WhatIf`
  (for a dry run of the trust step, call `Set-AgentWorkspaceTrust -WhatIf`).
- `install-agent-trust-hook.ps1` writes a `post-checkout` hook into a git
  template directory (default `~/.git-templates/agent-trust`) and sets the
  global `init.templateDir` to it. The hook fires only on a fresh clone or
  `git worktree add`, and it needs no global `core.hooksPath` (if one is set,
  git ignores template hooks and the installer warns). It refuses to replace a
  different `init.templateDir` or a foreign hook unless you pass `-Force`.
- **On Linux / inside WSL** both scripts also run under the Linux pwsh
  (`pwsh` on `PATH`). The default owner root there is `~/repos` (clones live
  flat under it), the config files are `/home/<user>/.claude.json` and
  `/home/<user>/.codex/config.toml`, and Codex keys are the plain Linux path,
  for example `[projects."/home/<user>/repos/x"]`; no `/mnt/<drive>/` key is
  written. Path containment is case-sensitive there (case-insensitive on
  Windows). The hook runs the Linux `pwsh` (the installer prefers a stable path such as
  `/usr/bin/pwsh` or `/snap/bin/pwsh` over a version-pinned snap path, which vanishes on
  the next snap refresh, and warns if it has to fall back to one; pass `-PwshPath` to
  override), and the installer sets the hook
  file to mode 0755, because git silently ignores a non-executable hook; a
  current hook that lost its executable bit is fixed on the next run.
- Git copies template hooks only at `git init` or `git clone`, so clones that
  existed before you installed the template never get the hook. Pass
  `-IncludeExistingClones` (with `-OwnerRoot` to override the roots) to
  install it into them too:

  ```powershell
  .\scripts\install-agent-trust-hook.ps1 -IncludeExistingClones
  ```

  It touches each direct child of an owner root whose `.git` is a directory
  and writes `.git/hooks/post-checkout` (same bytes as the template hook, 0755
  on Linux). It skips, without error: a `.git` file (a linked worktree, which
  shares its main repo's hooks), a child that is not a git repo, a repo with a
  local `core.hooksPath` that points elsewhere (git would ignore the hook; a warning names it;
  a value equal to the repo's own `.git/hooks` is fine and gets the hook), and
  a repo whose existing `post-checkout` was not written by this installer (a
  warning names it; never overwritten, not even with `-Force`). `-WhatIf`
  writes nothing. The returned object lists the repos it changed in
  `ExistingClones`.

## Linux and macOS

The census, waiting feed and session miner jobs are Bash, so they run natively
on Linux and macOS too. `scripts/unix/install-schedule.sh` schedules them; every
entry it writes runs `scripts/unix/run-task.sh <job>`, which does for each run
what Task Scheduler and the checkout bootstrap do on Windows:

- **No overlap.** A per-job `flock -n` lock: a run that finds the previous one
  still going logs `skipped=running` and exits 0, like `IgnoreNew`.
- **A time limit.** coreutils `timeout` with the Windows task's limit (census
  15 minutes, waiting feed 5, session miner 30) and a 10 second kill grace.
- **The checkout update.** Fetch `origin`, switch a clean checkout to `main`,
  fast-forward to `origin/main`, then re-exec from disk; a dirty, diverged,
  offline or slow checkout warns and runs its current code (the waiting feed
  updates at most every 5 minutes).
- **One log line per run** in `~/.cache/wsl-automation-tasks.log`.

macOS needs `brew install flock coreutils` (the runner refuses to start a job
without `flock` and `timeout`), and the waiting feed needs GNU `date`, which
coreutils' `gnubin` directory provides; the runner puts it first on `PATH`.

```bash
bash scripts/unix/install-schedule.sh systemd                 # Linux: user timers
bash scripts/unix/install-schedule.sh launchd                 # macOS: LaunchAgents
bash scripts/unix/install-schedule.sh cron                    # anywhere with cron
bash scripts/unix/install-schedule.sh systemd --jobs usage-census,waiting-feed,session-miner
bash scripts/unix/install-schedule.sh cron --print            # show it, change nothing
```

| Job | Schedule |
| --- | --- |
| `usage-census` (the default) | daily at 12:37 |
| `session-miner` | daily at 07:17 |
| `waiting-feed` | every minute |

- **systemd** writes a oneshot service and a timer per job to
  `~/.config/systemd/user` and enables the timers. The timers are
  `Persistent=true`: a run missed while the machine was off or asleep starts
  once at the next boot or wake. Native Linux has no WSL post-wake transition
  window, so that catch-up is wanted there. User timers stop when you log out
  unless linger is on: `loginctl enable-linger "$USER"` (the installer says
  when it is off).
- **launchd** writes `~/Library/LaunchAgents/local.wsl-automation.<job>.plist`
  and loads it into your login session. launchd runs a calendar job missed
  during sleep once on wake.
- **cron** keeps one marked block in your crontab, replaced on every run; the
  rest of the crontab is left alone. Plain cron has no catch-up.
- Re-running the installer is idempotent. To remove a schedule:
  `systemctl --user disable --now wsl-automation-<job>.timer` and delete its two
  units; `launchctl bootout gui/$(id -u)/local.wsl-automation.<job>` and delete
  the plist; or delete the block from `crontab -e`.
- A scheduler starts jobs with no profile and no desktop session, so keep git
  credentials where such a job can reach them (`gh auth setup-git` with a
  file-stored token) and settings in `~/.config/wsl-automation/settings.env`,
  which every job reads.

## Task history

Windows ships with the Task Scheduler operational log
(`Microsoft-Windows-TaskScheduler/Operational`, the "History" tab in Task
Scheduler) **disabled**. Without it, a scheduled task leaves only its last
result code behind - no start or finish times, no per-run exit codes, and no
record of a run that was terminated at its execution time limit. That gap is
exactly what made a failed Codex Cloud sync run on a new machine hard to
diagnose: the only evidence was a single result code, with no way to tell
when it ran or what it did before failing.

The installer (`scripts\register-tasks.ps1`, via
`Set-WslAutomationScheduledTasks`) enables this log once per run if it is
currently disabled. Pass `-SkipTaskHistory` to opt out. A failure to enable
it only warns - it never aborts task registration.

To read it, once enabled:

```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational |
    Where-Object Message -match '<task name>'
```

Event IDs worth knowing:

- **100** - task instance started.
- **102** - task instance finished.
- **201** - action completed, with its return code.
- **329** - task terminated at its execution time limit (see AGENTS.md's
  "Never leave an interactive prompt in a scheduled-task code path" section -
  this is the signature of a hung `Read-Host` or other unattended prompt, not
  a slow run).

To enable it by hand, from an elevated prompt, without running the
installer:

```powershell
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true
```

## Testing

Tests are written in Pester v5 syntax and are compatible with both Pester
5.7.1 and 6.0.0. From the repository root:

```powershell
Invoke-Pester ./tests
```

No test invokes real `wsl.exe` - every test mocks the module's `Invoke-WslExe`
seam - and all filesystem paths used by the tests live under Pester's
`TestDrive:`. The bash scripts have their own tests (`bash tests/<name>.test.sh`),
which put stubs on `PATH` instead of running Windows programs or reaching the
network; `tests/unix-schedule.test.sh` covers the Linux and macOS runner and
installer, `tests/run-session-miner.test.sh` the session miner wrapper, and
`tests/run-memory-curation.test.sh` the memory curation wrapper.

## Requirements

- PowerShell 7.6 or later, and for the background tasks an **MSI** install of
  PowerShell 7 (`C:\Program Files\PowerShell\7\`) - a Store-packaged pwsh
  cannot run in the session 0 they use.
- Windows (Task Scheduler integration is Windows-only; the module's
  non-scheduling functions are otherwise plain PowerShell 7.6+).
- The "Log on as a batch job" right for the account running the tasks (see
  `scripts\grant-keeper-batch-logon.ps1`).
- WSL2 with the distro the tasks run in already installed.
- `winget` (for the one-time ccstatusline runtime install).
- For Codex Cloud synchronization: authenticated Codex and GitHub CLIs, plus
  `curl`, `jq`, `flock`, and `mktemp` in that distro.
- For the waiting feed: `curl`, `jq`, `flock` and coreutils `timeout` in the
  distro, and a signed-in Claude Code there.
- For the session miner: python3 with PyYAML and the setup in its section.
- For the memory curation: a signed-in Claude Code and python3 in the distro.
- On Linux or macOS instead: bash, git, `flock` and coreutils `timeout`
  (`brew install flock coreutils` on macOS).
