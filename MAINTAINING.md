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
  writes what it would change to the run summary. A failed run opens or
  updates one open issue, "Re-sync from sources is failing", with the run's
  link and the failed step's name, and the next successful run closes it:
  watch for that issue rather than the Actions tab. It never re-pins
  `agentskills-private` (its source is private) and does not rewrite
  `library/`, so do those by hand. By hand, the fallback: check the sources
  out beside this clone, move the shas, run `npm ci` in the
  `_agent-guidance` checkout and in the `skills-evals` checkout's
  `explorer/` (two exports run that Node code: `_agent-guidance`'s scripts,
  and the esbuild build of `skills-evals`' two explorer pages), run
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
