# Maintaining the kit

For the kit's owner and the agents working on it; adopters can skip this.

- **Re-pin.** Each `export/manifests/*.yml` names a `source_sha`. The daily
  `resync` job (`.github/workflows/resync.yml`, also run by hand from the
  Actions tab) moves each one to its source's default-branch head
  (`export/resync.py`), regenerates `starter/`, runs `export/tests`, and
  opens or updates one pull request from `resync/auto`. Before merging it,
  tier any new skill or guidance section in `bootstrap/content-catalog.json`
  and record every departure in `export/DECISIONS.md`. It needs a GitHub App
  with contents and pull-requests write on this repo, named by the
  repository variable `RESYNC_APP_CLIENT_ID` (its client id) and the
  repository secret `RESYNC_APP_PEM` (its private key); without them it only
  writes what it would change to the run summary. **Hold-back:** if one
  source's new head breaks the export or its tests,
  `export/resync_holdback.py` regenerates and tests the new pins, then each
  moved source alone, and keeps that source at its old pin while the others
  move (if each passes alone but not together, it holds all of them back and
  no pull request opens). The pull request's summary has a "Held back"
  section, and the job opens or updates the same issue below, naming the held
  sources and the run, without failing. The failing output's tail goes to a
  file on the runner for the fix routine, never into the issue or pull
  request (public repo). A held source needs an `edits` entry or patch that
  follows its change, then it re-pins on the next run. **Fix routine:** a
  held source also fires a Claude cloud routine that follows it
  (`export/FIX-ROUTINE.md` is its guide) and pushes a `resync-fix/` branch,
  at most once a UTC day and never while such a pull request is open. The
  routine can push but cannot open pull requests or comment, so
  `.github/workflows/resync-fix-pr.yml` opens the pull request from the last
  commit's message, labels it and links it on the issue; review and merge it
  like any other. A run that finds every source at its pin closes a stale
  `resync/auto` pull request. The fire needs the
  repository variable `RESYNC_FIXER_FIRE_URL` and the Actions secret
  `RESYNC_FIXER_FIRE_BEARER`, both from the routine's API trigger on
  claude.ai; without them the step fails naming the missing one. The routine
  cannot run PowerShell, so a fix that touches a shipped `.ps1` asks for a
  Pester run on Windows. A failed run opens or
  updates one open issue, "Re-sync from sources is failing", with the run's
  link and the failed step's name; only a run with nothing held back closes
  it: watch for that issue rather than the Actions tab. The fleet's daily
  scheduled-run health audit (`.github/workflows/scheduled-run-health.yml`)
  also watches the job's scheduled runs and files its own `ci` issue, the
  one the owner's fleet agents pick up (`_agent-guidance` lists this repo
  under `cron_coverage.fleet` in its `repos.yml`). It never re-pins
  `agentskills-private` (its source is private) and does not rewrite
  `library/`, so do those by hand. By hand, the fallback: check the sources
  out beside this clone, move the shas, run `npm ci` in the
  `_agent-guidance` checkout and in the `skills-evals` checkout's
  `explorer/` (two exports run that Node code: `_agent-guidance`'s scripts,
  and the esbuild build of `skills-evals`' three explorer pages), run
  `python3 export/export.py` to rewrite `starter/`, then
  `bash run-all-tests.sh` (as root: `unshare --pid --fork --mount-proc --
  bash run-all-tests.sh`), and record every departure in
  `export/DECISIONS.md`.
- **CI.** `test` (`.github/workflows/ci.yml`) and `agent-checks` are the
  required checks. `test` needs the `PRIVACY_DENYLIST` repository secret
  (one regular expression per line) and fails without it.
- **Outside pull requests** never get that secret, so `test` fails on them by
  design. Read the change, bring it in on a branch of this repo, and close
  the outside pull request with thanks.
- **Issues** are the feedback channel. Nothing here acts on an issue by
  itself; never give an issue template a label the owner's automation reads.
- **No `CLAUDE.md`, `AGENTS.md` or `.claude/settings.json` at the root.**
  Adopters run Claude Code in their clone, so anything there would load into
  their setup session.
