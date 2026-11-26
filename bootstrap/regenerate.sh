#!/usr/bin/env bash
# regenerate.sh [--config fleet.env] [--dry-run] [--check] [--track base|evals|all] <task>
#
# Rebuilds, after adoption, the generated files the export could not build
# offline (export/REGENERATE.md), with each repo's own tooling, and proposes
# each repo's result as a pull request on branch regenerate/<task>. --check
# changes nothing: it reads your repos' default branches and exits 0 when the
# task is done there, 1 when it is not (verify.sh regen:<task> runs this).
#
# Tasks, in the order the quick start runs them:
#
#   skills-locks   skills.lock in every repo. acsi-agentskills: its own generator
#                  pins its HEAD (`scripts/generate_skills_lock.py`), checked
#                  with --check and --check-current. acsi-agentskills-private: the
#                  same file, copied. _agent-guidance, repo-settings and
#                  wsl-automation: acsi-agentskills' generator run with --repo on
#                  a clone of your acsi-agentskills, keeping each lock's bundles.
#                  Merge the acsi-agentskills pull request first, then rerun for
#                  the copy in acsi-agentskills-private.
#   hook-pin       _agent-guidance repos.yml skills_bootstrap.ref: the
#                  acsi-agentskills commit whose .claude/hooks/skills-bootstrap.sh
#                  has the sha256 repos.yml already records (the export
#                  computed it). Refuses when your registry's hook bytes
#                  differ. Afterwards the nightly skills-lock-bump.yml keeps it
#                  current with scripts/bump-hook-pin.sh.
#   run-health-sha the places the base repos' code names a commit of the
#                  source owner's _agent-guidance become your _agent-guidance
#                  default branch's commit (all but one: the recipe in
#                  _agent-guidance's own docs/codex-cloud.md, which a Codex
#                  user pastes by hand, keeps the source's commit; its comment
#                  says how to bump it). In scheduled-run-health.yml (repo-settings,
#                  skills-evals, acsi-agentskills, wsl-automation) the
#                  forty-zero placeholder: a cross-repo reusable workflow takes
#                  a full sha. In the base repos' copies it also turns the
#                  commented schedule line into the daily schedule, which the
#                  starter leaves off until the pin. In acsi-agentskills, in the
#                  same pull request: scripts/cloud-env-setup.sh's
#                  fleet_pin_commit (the commit cloud sessions download the
#                  fleet-guidance installer at; until it is yours they print
#                  "fleet-guidance: setup skipped") and, in
#                  .github/workflows/ci.yml, the ref of the step that checks
#                  out the eval-protection gate (lib/guidance_pins.py).
#                  Each of the two is written only when it does not name a
#                  commit of your repo yet. When it is about to write
#                  fleet_pin_commit, it first refuses, changing nothing, if
#                  .claude/hooks/fleet-memory.sh at the new commit does not
#                  have the sha256 cloud-env-setup.sh records
#                  (fleet_pin_sha256, which it never writes); a pin that
#                  already names a commit of yours with that digest is left
#                  alone and not compared again.
#   codex-pin      wsl-automation scripts/sync-codex-cloud-environments.sh:
#                  bootstrap_revision and bootstrap_sha256 become your
#                  acsi-agentskills HEAD and its hook's digest, and
#                  fleet_pin_commit and fleet_pin_sha256 your _agent-guidance
#                  HEAD and the digest of its .claude/hooks/fleet-memory.sh;
#                  then the script's own test
#                  (tests/sync-codex-cloud-environments.test.sh) runs.
#   actions-lock   `gh actions-lock --no-narrow` in each repo that has
#                  .github/workflows/actions.lock, proposing any change;
#                  --check runs `gh actions-lock --verify`. Needs the gh
#                  extension: gh extension install github/gh-actions-lock.
#   evals-fleet    repo-settings: merges repo-settings/fleet.evals.yml (the
#                  starter's skills-evals element) into repo-settings/fleet.yml
#                  and deletes the fragment, with lib/fleet_fragment.py
#                  (PyYAML: an element fleet.yml already declares is left as
#                  it is). The evals track's (export/DECISIONS.md C13), so it
#                  runs only once skills-evals exists; --check passes once
#                  fleet.yml declares OWNER/skills-evals and no fragment is left.
#
# skills-evals is the evals track's: the tasks leave it alone while it does
# not exist (a base-only setup), and include it once it does; evals-fleet,
# which edits repo-settings for it, is the evals track's too (regen_track). --track base
# or --track evals limits a task to that track's repos (status.sh passes
# each step's track to --check, so the base steps never look at
# skills-evals); --track evals fails while skills-evals does not exist.
#
# Each task needs the starter pull requests of the repos it reads merged.
# Idempotent: a repo already current gets no commit and no pull request.
# Pushes only to regenerate/<task>, never with force, and checks the commit
# reached it (lib/pr.sh). Needs: git, gh, jq, python3 (PyYAML for hook-pin,
# run-health-sha and evals-fleet).

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
# shellcheck source=lib/pr.sh
. "$HERE/lib/pr.sh"

CHECK=0 TASK="" TRACK=all
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --check) CHECK=1 ;;
    --track) [ $# -ge 2 ] || die "--track needs base, evals or all"; TRACK=$2; shift ;;
    --track=*) TRACK=${1#--track=} ;;
    -*) die "unknown option: $1" ;;
    *) [ -z "$TASK" ] || die "give one task"; TASK=$1 ;;
  esac
  shift
done
check_track "$TRACK"
[ -n "$TASK" ] || { usage; die "give a task: ${REGEN_TASKS[*]}"; }
known=0; for t in "${REGEN_TASKS[@]}"; do [ "$t" = "$TASK" ] && known=1; done
[ "$known" = 1 ] || die "unknown task: $TASK (expected one of: ${REGEN_TASKS[*]})"
require_tools git jq python3 "$GH"
load_config "$CONFIG"
O=$CFG_OWNER
ZERO40=0000000000000000000000000000000000000000
NOT_DONE=0
# all: skills-evals counts once it exists (a base-only setup has none).
if [ "$TRACK" = all ] && ! evals_repo_exists; then TRACK=base; log "skip: $O/$EVALS_REPO does not exist yet (the evals track creates it)"; fi
# in_task <repo>: whether this run covers that repo.
in_task() { on_track "$TRACK" "$(regen_track "$TASK" "$1")"; }

# clone <repo>: a full clone of OWNER/<repo> at $BOOT_WORK/<repo> (once).
clone() {
  local d="$BOOT_WORK/$1"
  [ -d "$d" ] || clone_repo "$O/$1" "$d"
  CLONE=$d
}
# need <repo> <path>: the starter must be merged for this task to make sense.
need() {
  clone "$1"
  [ -e "$CLONE/$2" ] || die "$O/$1 has no $2 on its default branch: merge its starter pull request first"
}
notdone() { NOT_DONE=$((NOT_DONE + 1)); printf 'NOT DONE: %s\n' "$*"; }
current() { printf 'current: %s\n' "$*"; }

# propose <repo> <title> <body> <edit function> <path>...: run the edit on a
# regenerate/<task> branch of the clone and open a pull request for it.
propose() {
  local repo=$1 title=$2 body=$3 fn=$4; shift 4
  clone "$repo"
  local d=$CLONE default
  default=$(default_branch_of "$d")
  start_branch "$d" "$default" "regenerate/$TASK"
  "$fn" "$d"
  if git -C "$d" diff --quiet -- "$@" && [ -z "$(git -C "$d" status --porcelain -- "$@")" ] \
     && [ -z "$(git -C "$d" rev-list "origin/$default..HEAD")" ]; then
    skip "$O/$repo: already current"; return 0
  fi
  git -C "$d" --no-pager diff --stat -- "$@"
  open_pr "$d" "$O/$repo" "$default" "regenerate/$TASK" "$title" "$body" "$@"
}

# ------------------------------------------------------------ skills-locks
REG_GEN=scripts/generate_skills_lock.py
lock_bundles() { jq -r '.bundles | join(",")' "$1"; }

edit_registry_lock() {
  (cd "$1" && python3 -I "$REG_GEN" --registry "$O/acsi-agentskills" --bundles "$(lock_bundles skills.lock)" -o skills.lock >/dev/null)
}
edit_private_lock() { cp "$REG_DIR/skills.lock" "$1/skills.lock"; }
edit_consumer_lock() {
  python3 -I "$REG_DIR/$REG_GEN" --repo "$REG_DIR" --registry "$O/acsi-agentskills" \
    --bundles "$(lock_bundles "$1/skills.lock")" -o "$1/skills.lock" >/dev/null
}

task_skills_locks() {
  local r
  need acsi-agentskills "$REG_GEN"; REG_DIR=$CLONE
  if [ "$CHECK" = 1 ]; then
    if (cd "$REG_DIR" && python3 -I "$REG_GEN" --check >/dev/null 2>&1 && python3 -I "$REG_GEN" --check-current >/dev/null 2>&1); then
      current "$O/acsi-agentskills skills.lock pins a commit of its own and matches it"
    else notdone "$O/acsi-agentskills skills.lock (still the export's forty zeros, or stale)"; fi
    clone acsi-agentskills-private
    if cmp -s "$REG_DIR/skills.lock" "$CLONE/skills.lock" && ! grep -qF "$ZERO40" "$CLONE/skills.lock"; then
      current "$O/acsi-agentskills-private skills.lock is acsi-agentskills' copy"
    else notdone "$O/acsi-agentskills-private skills.lock differs from acsi-agentskills'"; fi
    for r in _agent-guidance repo-settings wsl-automation; do
      clone "$r"
      if python3 -I "$REG_DIR/$REG_GEN" --repo "$REG_DIR" --check -o "$CLONE/skills.lock" >/dev/null 2>&1; then
        current "$O/$r skills.lock pins your acsi-agentskills"
      else notdone "$O/$r skills.lock (still pins the source registry's commit)"; fi
    done
    return 0
  fi
  local body="Regenerates skills.lock with acsi-agentskills' own scripts/generate_skills_lock.py, pinning your registry (the kit's export/REGENERATE.md). No skill content changes."
  if grep -qF "$ZERO40" "$REG_DIR/skills.lock" || ! (cd "$REG_DIR" && python3 -I "$REG_GEN" --check >/dev/null 2>&1); then
    propose acsi-agentskills "Pin skills.lock to this registry" "$body" edit_registry_lock skills.lock
    log "Merge that pull request, then run this again for acsi-agentskills-private and the consumers."
    return 0
  fi
  current "$O/acsi-agentskills skills.lock"
  propose acsi-agentskills-private "Copy acsi-agentskills' skills.lock" "$body" edit_private_lock skills.lock
  for r in _agent-guidance repo-settings wsl-automation; do
    need "$r" skills.lock
    propose "$r" "Pin skills.lock to your acsi-agentskills" "$body" edit_consumer_lock skills.lock
  done
}

# ------------------------------------------------------------ hook-pin
HOOK=.claude/hooks/skills-bootstrap.sh
repos_yml_pin() { # repos.yml -> "ref sha256"
  python3 -I - "$1" <<'PY'
import sys, yaml
b = (yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}).get("skills_bootstrap") or {}
print(b.get("ref", ""), b.get("sha256", ""))
PY
}
hook_sha_at() { git -C "$REG_DIR" show "$1:$HOOK" 2>/dev/null | sha256_stdin; }
edit_hook_pin() {
  python3 -I - "$1/repos.yml" "$NEW_REF" <<'PY'
import re, sys, yaml
path, ref = sys.argv[1:3]
lines = open(path, encoding="utf-8").read().split("\n")
start = lines.index("skills_bootstrap:")
for i in range(start + 1, len(lines)):
    if lines[i] and not lines[i].startswith((" ", "#")):
        sys.exit("repos.yml: skills_bootstrap has no ref line")
    if re.fullmatch(r"  ref: [0-9a-f]{40}", lines[i]):
        lines[i] = f"  ref: {ref}"
        break
open(path, "w", encoding="utf-8").write("\n".join(lines))
got = (yaml.safe_load(open(path, encoding="utf-8")) or {})["skills_bootstrap"]["ref"]
if got != ref:
    sys.exit("repos.yml: the rewrite did not take")
PY
}
task_hook_pin() {
  local ref sum head
  need acsi-agentskills "$HOOK"; REG_DIR=$CLONE
  need _agent-guidance repos.yml
  read -r ref sum < <(repos_yml_pin "$CLONE/repos.yml")
  [[ $sum =~ ^[0-9a-f]{64}$ ]] || die "repos.yml skills_bootstrap.sha256 is not a sha256"
  if git -C "$REG_DIR" cat-file -e "$ref^{commit}" 2>/dev/null && [ "$(hook_sha_at "$ref")" = "$sum" ]; then
    current "$O/_agent-guidance repos.yml pins your acsi-agentskills hook"; return 0
  fi
  if [ "$CHECK" = 1 ]; then notdone "$O/_agent-guidance repos.yml skills_bootstrap.ref is not a commit of your acsi-agentskills with that hook"; return 0; fi
  head=$(git -C "$REG_DIR" rev-parse HEAD)
  [ "$(hook_sha_at "$head")" = "$sum" ] \
    || die "your acsi-agentskills $HOOK at $head does not have the sha256 repos.yml records; the two copies have drifted. Run _agent-guidance's scripts/bump-hook-pin.sh to re-pin both ref and sha256 after reviewing the hook."
  NEW_REF=$head
  propose _agent-guidance "Pin the skills-bootstrap hook to your acsi-agentskills" \
    "Sets repos.yml skills_bootstrap.ref to $head, the acsi-agentskills commit whose $HOOK has the sha256 repos.yml already records (the kit's export/REGENERATE.md)." \
    edit_hook_pin repos.yml
}

# ------------------------------------------------------------ run-health-sha
RH=.github/workflows/scheduled-run-health.yml
# The starter ships the caller with no schedule (a schedule at the
# placeholder sha fails every day): the marker line becomes it with the pin.
RH_MARK="  # schedule-starts-with-the-pin: - cron: '47 8 * * *'"
edit_run_health() {
  # -i.bak, then removing the backup: the one in-place form GNU and BSD (macOS) sed share.
  sed -i.bak "s|scheduled-run-health-reusable.yml@$ZERO40|scheduled-run-health-reusable.yml@$AG_SHA|" "$1/$RH"
  rm -f "$1/$RH.bak"
  python3 -I - "$1/$RH" "$RH_MARK" <<'PY'
import sys
path, mark = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
if mark + "\n" in text:
    text = text.replace(mark + "\n", "  schedule:\n    - cron: '47 8 * * *'\n", 1)
    open(path, "w", encoding="utf-8").write(text)
PY
}
# The two more places acsi-agentskills names a commit of _agent-guidance
# (lib/guidance_pins.py finds and rewrites them): the commit cloud sessions
# download the fleet-guidance installer at, and the eval-protection gate's
# checkout in ci.yml.
REG=acsi-agentskills
CES=scripts/cloud-env-setup.sh
CI_YML=.github/workflows/ci.yml
FM=.claude/hooks/fleet-memory.sh
PINS="$HERE/lib/guidance_pins.py"
# pins <command> <file> <label> [args]: prints what it read; on a file of the
# wrong shape it prints one ERROR line naming <label> and returns 2.
pins() { python3 -I -B "$PINS" "$@"; }
# fm_sha_at <_agent-guidance clone> <commit>: the installer's sha256 there, or "" when it has none.
fm_sha_at() { git -C "$1" cat-file -e "$2:$FM" 2>/dev/null || return 0; git -C "$1" show "$2:$FM" | sha256_stdin; }
# in_guidance <_agent-guidance clone> <sha>: whether that is a commit of the clone.
in_guidance() { git -C "$1" cat-file -e "$2^{commit}" 2>/dev/null; }
# registry_pins <_agent-guidance clone>: read both places from the registry's
# default branch, before anything is written anywhere. Sets RP_FLEET and
# RP_GATE to "" when that part is current, else to what is wrong with it.
# Any commit of your _agent-guidance passes, not only its HEAD: a later bump
# is still current.
registry_pins() {
  local ag=$1 reg commit sum ref at
  need "$REG" "$CES"; reg=$CLONE
  [ -e "$reg/$CI_YML" ] || die "$O/$REG has no $CI_YML on its default branch: merge its starter pull request first"
  commit=$(pins setup-read "$reg/$CES" "$O/$REG $CES") || exit 1
  sum=${commit#* } commit=${commit%% *}
  ref=$(pins gate-read "$reg/$CI_YML" "$O/$REG $CI_YML" "$O") || exit 1
  RP_FLEET="" RP_GATE=""
  if ! in_guidance "$ag" "$commit"; then
    RP_FLEET="fleet_pin_commit ${commit:0:12} is not a commit of your _agent-guidance, so cloud sessions cannot download the fleet-guidance installer"
  elif [ "$(fm_sha_at "$ag" "$commit")" != "$sum" ]; then
    RP_FLEET="$FM at fleet_pin_commit ${commit:0:12} does not have the sha256 fleet_pin_sha256 records (${sum:0:12})"
  fi
  in_guidance "$ag" "$ref" || RP_GATE="the step \"Check out the eval-protection gate\" checks out ${ref:0:12}, which is not a commit of your _agent-guidance"
  # About to write the gate's ref: prove that rewrite now, before any repo is
  # touched (gate-read already refused a file that could not be rewritten).
  if [ "$CHECK" = 0 ] && [ -n "$RP_GATE" ]; then pins gate-try "$reg/$CI_YML" "$O/$REG $CI_YML" "$O" "$AG_SHA" || exit 1; fi
  [ "$CHECK" = 0 ] && [ -n "$RP_FLEET" ] || return 0
  # About to write fleet_pin_commit: the installer at the new commit must be
  # the one the registry's digest line names, or cloud sessions would refuse it.
  at=$(fm_sha_at "$ag" "$AG_SHA")
  [ "$at" = "$sum" ] \
    || die "$O/_agent-guidance $FM at ${AG_SHA:0:12} has sha256 ${at:0:12}$([ -n "$at" ] || echo '(no such file)'), and $O/$REG $CES records ${sum:0:12} (fleet_pin_sha256): the two copies of the fleet-guidance installer have drifted. Nothing was changed. Bring the repo that is on the older kit up to the newer one (bootstrap/copy-starter.sh for that repo, then merge its pull request) and run this again."
}
edit_registry_pins() {
  edit_run_health "$1"
  if [ -n "$RP_FLEET" ]; then pins setup-set "$1/$CES" "$O/$REG $CES" "$AG_SHA" || exit 1; fi
  if [ -n "$RP_GATE" ]; then pins gate-set "$1/$CI_YML" "$O/$REG $CI_YML" "$O" "$AG_SHA" || exit 1; fi
}
task_run_health_sha() {
  local r pinned health
  need _agent-guidance .github/workflows/scheduled-run-health-reusable.yml
  AG_SHA=$(git -C "$CLONE" rev-parse HEAD); local ag=$CLONE
  RP_FLEET="" RP_GATE=""
  if in_task "$REG"; then registry_pins "$ag"; fi
  for r in $(regen_repos run-health-sha); do
    in_task "$r" || continue
    need "$r" "$RH"
    pinned=$(grep -oE 'scheduled-run-health-reusable\.yml@[0-9a-f]{40}' "$CLONE/$RH" | head -n1 | cut -d@ -f2 || true)
    health=""
    if [ -z "$pinned" ] || [ "$pinned" = "$ZERO40" ] || ! in_guidance "$ag" "$pinned" || grep -qxF -- "$RH_MARK" "$CLONE/$RH"; then
      health="$RH still calls the reusable at ${pinned:-no} sha, or has no schedule yet"
    fi
    if [ "$r" != "$REG" ]; then
      if [ -z "$health" ]; then current "$O/$r $RH calls your _agent-guidance at $pinned"; continue; fi
      if [ "$CHECK" = 1 ]; then notdone "$O/$r $health"; continue; fi
      propose "$r" "Call your _agent-guidance's scheduled-run-health reusable" \
        "Replaces the export's forty-zero placeholder with $AG_SHA, your _agent-guidance default branch (a cross-repo reusable workflow takes a full sha; the kit's export/REGENERATE.md), and starts the daily schedule, which waits for the pin." \
        edit_run_health "$RH"
      continue
    fi
    # The registry: three files, one pull request; each part has its own line.
    if [ -z "$health$RP_FLEET$RP_GATE" ]; then
      current "$O/$r $RH calls your _agent-guidance at $pinned, and $CES and $CI_YML name commits of it"; continue
    fi
    if [ "$CHECK" = 1 ]; then
      if [ -n "$health" ]; then notdone "$O/$r $health"; fi
      if [ -n "$RP_FLEET" ]; then notdone "$O/$r $CES: $RP_FLEET"; fi
      if [ -n "$RP_GATE" ]; then notdone "$O/$r $CI_YML: $RP_GATE"; fi
      continue
    fi
    propose "$r" "Name your _agent-guidance's commit in the three places that pin it" \
      "Sets $AG_SHA, your _agent-guidance default branch, wherever this repo still names a commit your _agent-guidance does not have: the scheduled-run-health reusable in $RH (a cross-repo reusable workflow takes a full sha), with its daily schedule; fleet_pin_commit in $CES, the commit cloud sessions download the fleet-guidance installer at ($FM there has the sha256 fleet_pin_sha256 already records, which is not changed); and the ref of the eval-protection gate's checkout in $CI_YML (the kit's export/REGENERATE.md)." \
      edit_registry_pins "$RH" "$CES" "$CI_YML"
  done
}

# ------------------------------------------------------------ codex-pin
CX=scripts/sync-codex-cloud-environments.sh
# Two pins in one file: the registry's skills-bootstrap hook (CX_BOOT) and
# _agent-guidance's fleet-guidance installer (CX_FLEET). Each is "" when
# current, else what is wrong; the edit writes only the ones that are not.
edit_codex_pin() {
  if [ -n "$CX_BOOT" ]; then
    sed -i.bak -e "s/^readonly bootstrap_revision='[0-9a-f]\{40\}'/readonly bootstrap_revision='$CX_REV'/" \
      -e "s/^readonly bootstrap_sha256='[0-9a-f]\{64\}'/readonly bootstrap_sha256='$CX_SUM'/" "$1/$CX"
    rm -f "$1/$CX.bak"
  fi
  if [ -n "$CX_FLEET" ]; then pins codex-set "$1/$CX" "$O/wsl-automation $CX" "$CX_FLEET_REV" "$CX_FLEET_SUM" || exit 1; fi
  (cd "$1" && bash tests/sync-codex-cloud-environments.test.sh >"$BOOT_WORK/cx-test.out" 2>&1) \
    || { tail -n 20 "$BOOT_WORK/cx-test.out" >&2; die "tests/sync-codex-cloud-environments.test.sh failed with the new pin"; }
  log "tests/sync-codex-cloud-environments.test.sh passed with the new pin"
}
task_codex_pin() {
  local rev sum ag frev fsum
  need acsi-agentskills "$HOOK"; REG_DIR=$CLONE
  need _agent-guidance "$FM"; ag=$CLONE
  need wsl-automation "$CX"
  rev=$(sed -n "s/^readonly bootstrap_revision='\([0-9a-f]\{40\}\)'$/\1/p" "$CLONE/$CX")
  sum=$(sed -n "s/^readonly bootstrap_sha256='\([0-9a-f]\{64\}\)'$/\1/p" "$CLONE/$CX")
  [ -n "$rev" ] && [ -n "$sum" ] || die "$CX has no bootstrap_revision/bootstrap_sha256 lines"
  frev=$(pins codex-read "$CLONE/$CX" "$O/wsl-automation $CX") || exit 1
  fsum=${frev#* } frev=${frev%% *}
  CX_BOOT="" CX_FLEET=""
  if [ "$rev" = "$ZERO40" ]; then CX_BOOT="bootstrap pin is still zeros"
  elif ! git -C "$REG_DIR" cat-file -e "$rev^{commit}" 2>/dev/null || [ "$(hook_sha_at "$rev")" != "$sum" ]; then CX_BOOT="bootstrap pin is not your registry"; fi
  if [[ $frev =~ ^1+$ ]] || [[ $fsum =~ ^1+$ ]]; then CX_FLEET="fleet-guidance pin is still the placeholder"
  elif ! in_guidance "$ag" "$frev"; then CX_FLEET="fleet_pin_commit ${frev:0:12} is not a commit of your _agent-guidance"
  elif [ "$(fm_sha_at "$ag" "$frev")" != "$fsum" ]; then CX_FLEET="$FM at fleet_pin_commit ${frev:0:12} does not have the sha256 fleet_pin_sha256 records"; fi
  if [ -z "$CX_BOOT$CX_FLEET" ]; then
    current "$O/wsl-automation $CX pins your acsi-agentskills hook and your _agent-guidance's fleet-guidance installer"; return 0
  fi
  if [ "$CHECK" = 1 ]; then
    if [ -n "$CX_BOOT" ]; then notdone "$O/wsl-automation $CX ($CX_BOOT)"; fi
    if [ -n "$CX_FLEET" ]; then notdone "$O/wsl-automation $CX ($CX_FLEET)"; fi
    return 0
  fi
  CX_REV=$(git -C "$REG_DIR" rev-parse HEAD)
  CX_SUM=$(hook_sha_at "$CX_REV")
  CX_FLEET_REV=$(git -C "$ag" rev-parse HEAD)
  CX_FLEET_SUM=$(fm_sha_at "$ag" "$CX_FLEET_REV")
  propose wsl-automation "Pin the Codex Cloud bootstrap to your acsi-agentskills and _agent-guidance" \
    "Sets whichever of the two pins is not yours yet: bootstrap_revision to $CX_REV with bootstrap_sha256, its $HOOK digest; and fleet_pin_commit to $CX_FLEET_REV with fleet_pin_sha256, the digest of your _agent-guidance's $FM there (the kit's export/REGENERATE.md). tests/sync-codex-cloud-environments.test.sh passes with it." \
    edit_codex_pin "$CX"
}

# ------------------------------------------------------------ actions-lock
LOCK=.github/workflows/actions.lock
edit_actions_lock() {
  (cd "$1" && "$GH" actions-lock --no-narrow >"$BOOT_WORK/al.out" 2>&1) \
    || { tail -n 20 "$BOOT_WORK/al.out" >&2; die "gh actions-lock --no-narrow failed in $(basename "$1")"; }
}
task_actions_lock() {
  local r
  "$GH" actions-lock --help >/dev/null 2>&1 || die "gh actions-lock is not installed: gh extension install github/gh-actions-lock"
  for r in "${FLEET_REPOS[@]}"; do
    in_task "$r" || continue
    clone "$r"
    if [ ! -f "$CLONE/$LOCK" ]; then
      # The kit's tree ships one, so the repo will too once its starter pull
      # request is merged: until then the task is not done, not vacuously done.
      if [ "$CHECK" = 1 ] && [ -f "$HERE/../starter/$(kit_tree "$r")/$LOCK" ]; then
        notdone "$O/$r has no $LOCK yet (merge its starter pull request first)"
      else log "skip: $O/$r has no $LOCK"; fi
      continue
    fi
    if [ "$CHECK" = 1 ]; then
      if (cd "$CLONE" && "$GH" actions-lock --verify >/dev/null 2>&1); then current "$O/$r $LOCK verifies"
      else notdone "$O/$r $LOCK (gh actions-lock --verify reports findings)"; fi
      continue
    fi
    propose "$r" "Regenerate actions.lock" \
      "Runs gh actions-lock --no-narrow, as the repo's AGENTS.md says; review this diff as you would a sha pin (the kit's export/REGENERATE.md)." \
      edit_actions_lock "$LOCK"
  done
}

# ------------------------------------------------------------ evals-fleet
FRAG="repo-settings/fleet.evals.yml"
edit_evals_fleet() {
  python3 -I -B "$HERE/lib/fleet_fragment.py" merge "$1" || die "could not merge $FRAG into repo-settings/fleet.yml (see above)"
}
task_evals_fleet() {
  evals_repo_exists || die "$O/$EVALS_REPO does not exist (HTTP 404): the evals track creates it first (create-repos.sh $EVALS_REPO)"
  need repo-settings repo-settings/fleet.yml
  if python3 -I -B "$HERE/lib/fleet_fragment.py" check "$CLONE" "$O" >"$BOOT_WORK/frag.out" 2>&1; then
    current "$O/repo-settings repo-settings/fleet.yml declares $O/$EVALS_REPO"; return 0
  fi
  if [ "$CHECK" = 1 ]; then sed -n 's/^NOT DONE: /&/p; s/^ERROR: /&/p' "$BOOT_WORK/frag.out"; NOT_DONE=$((NOT_DONE + 1)); return 0; fi
  propose repo-settings "Declare skills-evals in fleet.yml" \
    "Moves skills-evals' element from $FRAG into repo-settings/fleet.yml and deletes the fragment, so the next settings apply protects skills-evals (the kit's export/DECISIONS.md C13). Merge it once the roster App's id is set as ROSTER_WRITER_APP_ID: fleet.yml then names it." \
    edit_evals_fleet repo-settings/fleet.yml "$FRAG"
}

[ "$CHECK" = 0 ] || [ "$DRY_RUN" = 0 ] || die "--check is read-only already; drop --dry-run"
log "Owner $O, task $TASK$([ "$CHECK" = 1 ] && echo ', CHECK')$([ "$DRY_RUN" = 1 ] && echo ', DRY RUN')$([ "$TRACK" = all ] || echo ", $TRACK track")"
covered=0
while IFS= read -r r; do in_task "$r" && covered=1; done < <(regen_repos "$TASK")
[ "$covered" = 1 ] || die "$TASK edits no repo of the $TRACK track"
case $TASK in
  skills-locks) task_skills_locks ;;
  hook-pin) task_hook_pin ;;
  run-health-sha) task_run_health_sha ;;
  codex-pin) task_codex_pin ;;
  actions-lock) task_actions_lock ;;
  evals-fleet) task_evals_fleet ;;
esac
if [ "$CHECK" = 1 ]; then
  if [ "$NOT_DONE" = 0 ]; then log "$TASK: done"; exit 0; fi
  log "$TASK: $NOT_DONE item(s) not done; run bootstrap/regenerate.sh $TASK"; exit 1
fi
finish
