#!/usr/bin/env bash
# update-kit.sh [--config fleet.env] [--dry-run] [--discard-starter-edits]
#
# Moves this clone of the kit to the newest kit, even after add-content.sh
# changed files under starter/ (which makes a plain git pull fail). It:
#
#   1. refuses unless the kit folder is the top of its own git clone;
#   2. reads fleet.env when it loads (a missing or invalid one is not fatal
#      here) to find add-content.sh's record of your content choices;
#   3. refuses when a tracked file outside starter/ is modified or staged,
#      since it only fast-forwards (commit it on a branch of your own, or
#      git restore it); untracked files (fleet.env, app-manifests/) are left
#      alone;
#   4. before discarding starter/ changes, proves they are exactly what
#      add-content.sh wrote: it runs the unmodified add-content.sh of your
#      current commit with your recorded choices in a scratch copy and
#      compares the two starter/ folders. A difference is a hand edit: it
#      refuses and says how to keep it, unless you pass --discard-starter-edits;
#   5. fetches origin, restores starter/ and fast-forwards to origin/HEAD
#      (or origin/main). It refuses when you have local commits;
#   6. with the new code, lists the fleet.env keys the new bootstrap/fleet.env.example
#      added or dropped (names only, never a value), then runs add-content.sh
#      again with your recorded choices.
#
# It changes only this kit folder and writes nothing to GitHub. Repos you
# already filled from an older starter are not changed: see copy-starter.sh
# --dry-run. --dry-run fetches (which changes no file you see) and only
# reports the rest. Idempotent: on a current kit it changes nothing.
# Internal: --after-update <sha> is how the script continues in the new copy
# of itself after the fast-forward; do not pass it yourself.
# Needs: bash 4.4+, git, tar, python3, jq.

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

DISCARD=0 AFTER=""
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --discard-starter-edits) DISCARD=1 ;;
    --after-update) [ $# -ge 2 ] || die "--after-update needs a sha"; AFTER=$2; shift ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
require_tools git tar python3 jq

CFG_OK=0 CHOICES="" IDS="" CFG_ERR=""
# Load fleet.env when it is usable; a failure is reported, never fatal.
if [ -f "$CONFIG" ]; then
  if CHOICES=$( { load_config "$CONFIG" && choices_file && printf '%s' "$CHOICES"; } 2>"$BOOT_WORK/cfg.err" ); then
    load_config "$CONFIG"
    CFG_OK=1
    if [ -f "$CHOICES" ] && jq -e '.installed | type == "array"' "$CHOICES" >/dev/null 2>&1; then
      IDS=$(jq -r '.installed | join(",")' "$CHOICES")
      [ -n "$IDS" ] || IDS=none
    fi
  else
    CHOICES=""
    CFG_ERR=$(sed 's/^ERROR: //' "$BOOT_WORK/cfg.err" | head -n1)
  fi
fi

# ------------------------------------------------------------------ the rest
# Runs in the NEW copy of the script after a fast-forward, or directly on a
# current kit.
rest() {
  local example miss
  log ""
  if [ "$CFG_OK" = 1 ]; then
    :
  elif [ -f "$CONFIG" ]; then
    log "Your $CONFIG does not load under this kit: ${CFG_ERR:-invalid}."
    log "Run: bash bootstrap/status.sh${CONFIG_ARG}   (it names the key to fix)"
  else
    log "No $CONFIG yet; copy bootstrap/fleet.env.example to it and run: bash bootstrap/status.sh${CONFIG_ARG}"
  fi
  if [ -f "$CONFIG" ]; then
    example=$HERE/fleet.env.example
    sed -n 's/^[[:space:]]*\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$CONFIG" | sort -u > "$BOOT_WORK/keys.mine"
    sed -n 's/^[[:space:]]*\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$example" | sort -u > "$BOOT_WORK/keys.example"
    miss=$(comm -13 "$BOOT_WORK/keys.mine" "$BOOT_WORK/keys.example" | tr '\n' ' ')
    if [ -n "$miss" ]; then
      log "Keys in the new fleet.env.example that your $CONFIG lacks: ${miss% }"
      log "  (new since your copy; empty means the default unless status.sh says it is required)"
    fi
    miss=$(comm -23 "$BOOT_WORK/keys.mine" "$BOOT_WORK/keys.example" | tr '\n' ' ')
    if [ -n "$miss" ]; then
      log "Keys in your $CONFIG that the new fleet.env.example does not have: ${miss% }"
      log "  (the strict parser refuses unknown keys: remove them)"
    fi
  fi
  if [ "$CFG_OK" = 1 ] && [ -n "$IDS" ]; then
    local args=(--config "$CONFIG" --items "$IDS") out=$BOOT_WORK/reapply.out
    [ "$DRY_RUN" = 0 ] || args+=(--dry-run)
    if bash "$HERE/add-content.sh" "${args[@]}" >"$out" 2>&1; then
      cat "$out"
    else
      local gone=() id kept=()
      IFS=, read -r -a ids <<<"$IDS"
      for id in "${ids[@]}"; do
        if [ "$id" = none ] || jq -e --arg id "$id" '.items[] | select(.id == $id)' "$HERE/content-catalog.json" >/dev/null 2>&1; then
          kept+=("$id"); else gone+=("$id")
        fi
      done
      if [ ${#gone[@]} -eq 0 ]; then cat "$out"; die "add-content.sh failed on your recorded choices (above)"; fi
      log "The new catalog (bootstrap/content-catalog.json) no longer has: ${gone[*]}"
      if [ ${#kept[@]} -gt 0 ]; then
        local keep
        keep=$(IFS=,; printf '%s' "${kept[*]}")
        args=(--config "$CONFIG" --items "$keep")
        [ "$DRY_RUN" = 0 ] || args+=(--dry-run)
        bash "$HERE/add-content.sh" "${args[@]}" || die "add-content.sh failed on the remaining choices"
      fi
      log "Run bash bootstrap/add-content.sh${CONFIG_ARG} --items <ids> again to choose from the current catalog."
    fi
  elif [ "$CFG_OK" = 1 ]; then
    log "No recorded content choices yet; choose with: bash bootstrap/add-content.sh${CONFIG_ARG} --items <ids|recommended|none>"
  fi
  if [ "$CFG_OK" = 1 ]; then
    log ""
    log "Repos you already filled from an older starter are NOT updated by this script."
    log "bash bootstrap/copy-starter.sh --dry-run <starter-subdir> <owner/repo> shows what the newer"
    log "starter would change there and lists files that differ on the default branch as REFUSED;"
    log "read those before any --force."
  fi
  log ""
  log "Next: bash bootstrap/status.sh${CONFIG_ARG}"
  [ -n "$AFTER" ] || finish
  exit 0
}
CONFIG_ARG=""
[ "$CONFIG" = ./fleet.env ] || CONFIG_ARG=" --config $CONFIG"

# ------------------------------------------------------------------ the clone
kit_real=$(cd "$KIT" && pwd -P)
top=$(git -C "$KIT" rev-parse --show-toplevel 2>/dev/null) || top=""
if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$kit_real" ]; then
  {
    printf 'ERROR: %s is not a git clone of the kit (a downloaded copy, or a folder inside another repository), so it cannot be updated in place.\n' "$KIT"
    printf 'Instead: clone the kit fresh beside it, copy your fleet.env into the new clone, and run\n'
    printf '  bash bootstrap/add-content.sh --items <ids>\n'
    printf 'there again.\n'
    if [ -n "$IDS" ]; then printf 'Your recorded content choices: %s\n' "$IDS"; fi
  } >&2
  exit 1
fi
if [ "$CFG_OK" = 0 ] && [ -z "$AFTER" ]; then
  if [ -f "$CONFIG" ]; then
    log "note: $CONFIG does not load (${CFG_ERR:-invalid}); continuing without re-applying your content choices."
  else
    log "note: no $CONFIG; continuing without re-applying your content choices."
  fi
fi
[ -z "$AFTER" ] || { log "Updated from ${AFTER:0:12} to $(git -C "$KIT" rev-parse --short=12 HEAD)."; rest; }

# Everything from here on is one function, so bash has read all of it before
# the fast-forward replaces this very file.
update_kit() {
# ------------------------------------------------------------------ classify
starter_paths=() bad=()
status=$BOOT_WORK/status.z
git -C "$KIT" status --porcelain=v1 -z > "$status"
skip_next=0
while IFS= read -r -d '' rec; do
  if [ "$skip_next" = 1 ]; then   # the original path of a rename or copy
    skip_next=0
    case $rec in starter/*) starter_paths+=("$rec") ;; *) bad+=("$rec") ;; esac
    continue
  fi
  xy=${rec:0:2} p=${rec:3}
  case $xy in R*|C*|?R|?C) skip_next=1 ;; esac
  case $p in
    starter/*) starter_paths+=("$p") ;;
    *) [ "$xy" = '??' ] || bad+=("$p") ;;
  esac
done < "$status"
if [ ${#bad[@]} -gt 0 ]; then
  {
    printf 'ERROR: tracked files outside starter/ are modified or staged, and this script only fast-forwards:\n'
    printf '  %s\n' "${bad[@]:0:20}"
    [ ${#bad[@]} -le 20 ] || printf '  ... and %d more\n' $((${#bad[@]} - 20))
    printf 'Commit them on a branch of your own, or restore them (git restore <path>), then run this again.\n'
  } >&2
  exit 1
fi

# ------------------------------------------------------------------ fetch
git -C "$KIT" fetch --quiet origin 2>"$BOOT_WORK/fetch.err" \
  || die "git fetch origin failed in $KIT; check the remote with: git -C $KIT remote -v"
target=""
if t=$(git -C "$KIT" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null) && [ -n "$t" ]; then
  target=$t
elif git -C "$KIT" rev-parse --verify -q refs/remotes/origin/main >/dev/null; then
  target=origin/main
else
  die "no origin/HEAD or origin/main in $KIT; check the remote with: git -C $KIT remote -v"
fi
old=$(git -C "$KIT" rev-parse HEAD)
new=$(git -C "$KIT" rev-parse "$target^{commit}")
if [ "$old" = "$new" ]; then
  skip "the kit is current ($(git -C "$KIT" rev-parse --short=12 HEAD))"
  rest
fi
if ! git -C "$KIT" merge-base --is-ancestor "$old" "$new"; then
  die "your HEAD ($(git -C "$KIT" rev-parse --short HEAD)) is not an ancestor of $target ($(git -C "$KIT" rev-parse --short "$new")): you have local commits or are on another branch. See them with: git -C $KIT log --oneline origin/main..HEAD"
fi

# ------------------------------------------------------------------ starter edits
if [ ${#starter_paths[@]} -gt 0 ] && [ "$DISCARD" = 0 ]; then
  hand=()
  if [ "$CFG_OK" = 1 ] && [ -n "$IDS" ]; then
    tmp=$(mktemp -d "$BOOT_WORK/pristine.XXXXXX")
    git -C "$KIT" archive HEAD bootstrap starter library | tar -x -C "$tmp"
    mkdir -p "$BOOT_WORK/state"
    if ! ADOPT_STATE_FILE="$BOOT_WORK/state/proof.json" GH=/nonexistent \
        bash "$tmp/bootstrap/add-content.sh" --config "$CONFIG" --items "$IDS" >"$BOOT_WORK/proof.out" 2>&1; then
      hand=("${starter_paths[@]}")
    else
      while IFS= read -r line; do hand+=("$line"); done < <(python3 -I -B -c '
import os, sys
IGN_DIRS = {"__pycache__", ".pytest_cache", "node_modules"}
def walk(root):
    out = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in IGN_DIRS]
        for f in dirs + files:
            p = os.path.join(d, f)
            if f in dirs and not os.path.islink(p):
                continue
            if f in (".DS_Store",) or f.endswith(".pyc"):
                continue
            rel = os.path.relpath(p, root)
            if os.path.islink(p):
                out[rel] = ("l", os.readlink(p))
            elif os.path.isfile(p):
                with open(p, "rb") as fh:
                    out[rel] = ("f", fh.read())
    return out
a, b = walk(sys.argv[1]), walk(sys.argv[2])
for rel in sorted(set(a) | set(b)):
    if a.get(rel) != b.get(rel):
        print("starter/" + rel)
' "$tmp/starter" "$KIT/starter")
    fi
  else
    hand=("${starter_paths[@]}")
  fi
  if [ ${#hand[@]} -gt 0 ]; then
    {
      printf 'ERROR: starter/ differs from what add-content.sh writes, so these are your own edits (or add-content.sh could not be re-run here):\n'
      printf '  %s\n' "${hand[@]:0:20}"
      [ ${#hand[@]} -le 20 ] || printf '  ... and %d more\n' $((${#hand[@]} - 20))
      printf 'Keep them first: git -C %s diff HEAD -- starter > my-starter-edits.patch, and copy any new file.\n' "$KIT"
      printf 'Starter edits belong in a pull request on your own repo after copy-starter.sh, not in the kit.\n'
      printf 'To discard them anyway, run this again with --discard-starter-edits.\n'
    } >&2
    exit 1
  fi
fi

# ------------------------------------------------------------------ fast-forward
n=$(git -C "$KIT" rev-list --count "$old..$new")
summary="${old:0:12} -> ${new:0:12}, $n commit(s)"
if [ "$DRY_RUN" = 1 ]; then
  [ ${#starter_paths[@]} -eq 0 ] || did "discard ${#starter_paths[@]} starter/ change(s) (add-content.sh rewrites them afterward)"
  did "fast-forward $target: $summary"
  WRITES=$((WRITES + 1))
  log ""
  log "Next: run this again without --dry-run; the key check and the content re-apply follow the update."
  finish
  exit 0
fi
if [ ${#starter_paths[@]} -gt 0 ]; then
  git -C "$KIT" restore --source=HEAD --staged --worktree -- starter
  git -C "$KIT" clean -fdq -- starter
  log "Discarded ${#starter_paths[@]} starter/ change(s); add-content.sh puts your choices back."
fi
git -C "$KIT" merge --ff-only --quiet "$new"
log "$summary"
exec bash "$HERE/update-kit.sh" --config "$CONFIG" --after-update "$old"
}
update_kit; exit 0
