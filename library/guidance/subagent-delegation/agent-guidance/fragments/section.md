## Subagent delegation (model routing)

- **Every delegation passes `model`** (code, review, plan, research); unset,
  it inherits yours. `haiku` for search, log extraction, test-checked
  mechanical edits, never security review; `sonnet` for clear-spec
  implementation you review; `opus` for fresh-context correctness review,
  and security review at `effort: "high"`. Else effort `medium`, never
  `max`.
- **Do judgment and ~10-call tasks yourself** (plan, architecture, root
  cause, the spec); delegate bigger implementation. Fork (your model and
  context) only under ~100k tokens. A child that skips this file
  (Explore/Plan, `omitClaudeMd`) needs constraints in its prompt.
- **Each call re-reads all context**: past ~150k tokens, hand off to a fresh
  session; keep tool output small; poll with scripts, not models.
- Delegated work is done when a verifier exits 0: name the exact command,
  run LAST (a trailing `echo $?` hides the tool's code), and require its
  code back. "Cannot run it" is BLOCKED; a count off-spec, stop-and-report;
  a self-contradicting report ("2 failed", "exit 0"), re-run it. **Prove the
  verifier can fail first:** `python3 test_foo.py` with no `__main__` block
  exits 0 having asserted nothing. Name the RUNNER
  (`python3 -m pytest <paths> -q`), never the file, and require the test
  COUNT too.
- **A working subagent OWNS the tree — do not commit or push under it.** A
  push mid-flight plus its `git commit --amend` diverges a published branch
  (recover by reset and a fresh commit, never force-push), and its
  `git checkout -- <file>` discards your edits. Wait for a clean
  `git status` plus a recorded result; decline a stop hook's "commit and
  push" nudge.
- **A subagent that has REPORTED can still be holding the tree**: its
  BACKGROUND CHILDREN are not reaped Check for descendants
  (`ps -eo pid,etimes,cmd | grep '[y]our-command'`); `md5sum` inputs before
  and after (differ → not evidence); prefer a per-run output path; kill
  orphans, and say so.
- **A subagent that goes quiet is not working — check activity, not the
  clock.** Watch its transcript's mtime, with threshold and fallback preset.
- **A live-test prompt states the credential boundary** — which
  `HOME`/profile, what it may read, and that it must not copy real
  credentials to pass: a throwaway one, or none; else it's the operator's
  call.
- **A scratch tree can still reach production.** `cp -a` copies
  `.git/config`, so a copy inherits `origin`; but `git remote remove origin`
  in a `git worktree` strips the PARENT's remote. Run
  `/acsi-coding-anywhere:disarm-inherited-reach` before disarming.
