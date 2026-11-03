#!/usr/bin/env bash
# apply-settings.sh [--config fleet.env] [--dry-run | --check] [--owner LOGIN] [--track base|evals|all]
#
# Applies repo-settings' fleet.yml to your repos with repo-settings' own
# engine, the way the owner's fleet is run: merge methods, auto-merge, the
# Actions policy (full-SHA pins, read-only token, fork-run approval), the
# security features, the agent-authored and eval-scaffold labels, and the
# rulesets with each repo's real required checks (acsi-agentskills: privacy,
# pytest, pytest-windows, plugin-runtime-approval, agent-checks; skills-evals:
# test, agent-checks; and so on, as fleet.yml lists them). The kit keeps no
# ruleset files of its own.
#
#   1. clones OWNER/repo-settings (its default branch: merge the repo-settings
#      starter pull request first) to a temp dir;
#   2. leaves skills-evals out while it does not exist: it is the evals
#      track's (steps.json), so a base-only setup applies fleet.yml to the
#      other repos, with its skills-evals entry dropped from a copy of the
#      file. /adopt-evals creates it and applies again. --track base always
#      leaves it out, and --track evals keeps only it (and fails while it
#      does not exist); status.sh passes each step's track to --check;
#   3. refuses while GUIDANCE_SYNC_APP_ID is empty in fleet.env, or
#      ROSTER_WRITER_APP_ID while skills-evals is kept: fleet.yml names both
#      Apps as ruleset bypass actors (roster only in skills-evals' entry), and
#      the engine refuses to plan without their ids (export/DECISIONS.md C12).
#      This is why the Apps come before the first apply;
#   4. refuses while fleet.yml names another repo of this owner that does not
#      exist (the example platform and its sites, until you remove them:
#      export/REGENERATE.md, "repo-settings/fleet.yml's repo list");
#   5. runs `scripts/repo_settings.py apply --config repo-settings/fleet.yml
#      --owner <owner> --cms-label-only skip` (with --dry-run, the engine's
#      own preview), as repo-settings.yml's apply job does;
#   6. reads back with `scripts/repo_settings.py diff`, which exits 0 only
#      when nothing drifts.
#
# The engine calls `gh api` with your gh login, which must be an admin of
# every repo it touches. --owner LOGIN applies another owner's repos (your
# OWNER_TWO): sign gh in as that account first (gh auth switch). After this
# first apply, repo-settings.yml applies on every merge, behind the
# fleet-apply environment's approval.
#
# --check runs steps 1 to 4 and 6 only: read-only, exit 0 when nothing drifts
# (verify.sh's settings group). Idempotent: the engine writes only what differs. Needs: git, gh, python3
# with PyYAML (repo-settings' requirements.txt).

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

TARGET="" CHECK=0 TRACK=all
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --owner) [ $# -ge 2 ] || die "--owner needs a login"; TARGET=$2; shift 2 ;;
    --track) [ $# -ge 2 ] || die "--track needs base, evals or all"; TRACK=$2; shift 2 ;;
    --check) CHECK=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done
check_track "$TRACK"
require_tools git python3 "$GH"
load_config "$CONFIG"
TARGET=${TARGET:-$CFG_OWNER}
known=0
while IFS= read -r o; do [ "${o,,}" = "${TARGET,,}" ] && known=1; done < <(owners)
[ "$known" = 1 ] || die "--owner must be OWNER or OWNER_TWO from fleet.env"
python3 -c 'import yaml' 2>/dev/null || die "the engine needs PyYAML: python3 -m pip install -r requirements.txt in repo-settings"

[ -n "$CFG_GUIDANCE_SYNC_APP_ID" ] || die "GUIDANCE_SYNC_APP_ID empty in fleet.env: fleet.yml names that App as a ruleset bypass actor and the engine refuses to plan without it. Run create-apps.sh first."

RS="$BOOT_WORK/repo-settings"
clone_repo "$CFG_OWNER/repo-settings" "$RS" --depth 1
ENGINE="$RS/scripts/repo_settings.py" FLEET="$RS/repo-settings/fleet.yml"
[ -f "$ENGINE" ] && [ -f "$FLEET" ] \
  || die "$CFG_OWNER/repo-settings has no scripts/repo_settings.py or repo-settings/fleet.yml on its default branch: merge the repo-settings starter pull request first"

# declared <fleet.yml>: the repos it declares for TARGET (names only).
declared() {
  python3 -I - "$1" "$TARGET" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
owner = sys.argv[2].lower()
for r in doc.get("repos") or []:
    name = str((r or {}).get("name", ""))
    if name.split("/", 1)[0].lower() == owner:
        print(name)
PY
}
mapfile -t DECLARED < <(declared "$FLEET")
[ ${#DECLARED[@]} -gt 0 ] || die "fleet.yml in $CFG_OWNER/repo-settings declares no repo of $TARGET"
# skills-evals is the evals track's: keep it only when it exists (all) or
# when asked for it alone (evals); --track base always drops it.
EVALS_KEEP=0 EVALS_DECLARED=0
for r in "${DECLARED[@]}"; do [ "${r#*/}" != "$EVALS_REPO" ] || EVALS_DECLARED=1; done
[ "$TRACK" != evals ] || [ "$EVALS_DECLARED" = 1 ] || die "fleet.yml in $CFG_OWNER/repo-settings declares no $TARGET/$EVALS_REPO"
if [ "$TRACK" != base ] && [ "$EVALS_DECLARED" = 1 ]; then
  if gh_read "repos/$TARGET/$EVALS_REPO"; then EVALS_KEEP=1
  elif [ "$GH_HTTP" != 404 ]; then die "could not read $TARGET/$EVALS_REPO (HTTP $GH_HTTP)"
  elif [ "$TRACK" = evals ]; then die "$TARGET/$EVALS_REPO does not exist (HTTP 404): the evals track creates it first (create-repos.sh $EVALS_REPO)"
  else log "skip: fleet.yml declares $TARGET/$EVALS_REPO, which does not exist yet: the evals track's repo, left out of this run (/adopt-evals adds it)"; fi
fi
if [ "$EVALS_KEEP" = 1 ] && [ -z "$CFG_ROSTER_WRITER_APP_ID" ]; then
  die "ROSTER_WRITER_APP_ID empty in fleet.env: fleet.yml names the roster App as a ruleset bypass actor in $EVALS_REPO's entry and the engine refuses to plan without it. Run create-apps.sh roster first (the evals track)."
fi
# The engine then reads a copy of fleet.yml without skills-evals' entries
# (or, for --track evals, with only them); everything else is kept.
if [ "$EVALS_DECLARED" = 1 ] && { [ "$EVALS_KEEP" = 0 ] || [ "$TRACK" = evals ]; }; then
  python3 -I - "$FLEET" "$BOOT_WORK/fleet.yml" "$EVALS_REPO" "$TRACK" <<'PY' || die "could not write the filtered copy of fleet.yml"
import sys, yaml
src, dst, evals, track = sys.argv[1:5]
doc = yaml.safe_load(open(src, encoding="utf-8")) or {}
def is_evals(r):
    return str((r or {}).get("name", "")).split("/", 1)[-1] == evals
doc["repos"] = [r for r in doc.get("repos") or [] if is_evals(r) == (track == "evals")]
with open(dst, "w", encoding="utf-8") as f:
    yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
PY
  FLEET="$BOOT_WORK/fleet.yml"
  mapfile -t DECLARED < <(declared "$FLEET")
  [ ${#DECLARED[@]} -gt 0 ] || die "fleet.yml in $CFG_OWNER/repo-settings declares no other repo of $TARGET"
fi
absent=()
for r in "${DECLARED[@]}"; do
  if gh_read "repos/$r"; then continue; fi
  [ "$GH_HTTP" = 404 ] || die "could not read $r (HTTP $GH_HTTP)"
  absent+=("$r")
done
if [ ${#absent[@]} -gt 0 ]; then
  for r in "${absent[@]}"; do printf 'MISSING: fleet.yml declares %s, which this gh login cannot see (HTTP 404)\n' "$r" >&2; done
  die "remove the repos you do not have from repo-settings/fleet.yml (and their rows in tests/test_repo_settings.py) in a pull request, or create them; then run this again"
fi
log "fleet.yml declares ${#DECLARED[@]} repo(s) of $TARGET; all exist"

run_engine() { # subcommand [args]
  env GUIDANCE_SYNC_APP_ID="$CFG_GUIDANCE_SYNC_APP_ID" ROSTER_WRITER_APP_ID="$CFG_ROSTER_WRITER_APP_ID" \
    python3 -I "$ENGINE" "$1" --config "$FLEET" --owner "$TARGET" "${@:2}"
}
[ "$CHECK" = 0 ] || [ "$DRY_RUN" = 0 ] || die "--check is read-only already; drop --dry-run"
if [ "$CHECK" = 0 ] && [ "$DRY_RUN" = 1 ]; then
  log "== engine preview (apply --dry-run)"
  run_engine apply --dry-run --cms-label-only skip || die "the engine's preview failed (see above)"
  log "Dry run: the engine wrote nothing."
  exit 0
fi
if [ "$CHECK" = 0 ]; then
  log "== apply"
  run_engine apply --cms-label-only skip || die "the engine's apply failed (see above)"
  WRITES=$((WRITES + 1))
fi
log "== read back (diff)"
rc=0
run_engine diff > "$BOOT_WORK/diff.out" 2>&1 || rc=$?
case $rc in
  0) log "no drift: every repo of $TARGET matches fleet.yml" ;;
  1) cat "$BOOT_WORK/diff.out"; die "$([ "$CHECK" = 1 ] && echo "the repos drift from fleet.yml; run apply-settings.sh" || echo "drift remains after apply") (see above)" ;;
  *) cat "$BOOT_WORK/diff.out"; die "the engine's diff failed (exit $rc)" ;;
esac
[ "$CHECK" = 1 ] || finish
