# Maintaining the kit

For the kit's owner and the agents working on it; adopters can skip this.

- **Re-pin.** Each `export/manifests/*.yml` names a `source_sha`. To pick up
  newer source repos, check them out beside this clone, move the shas, run
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
