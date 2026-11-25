#!/usr/bin/env bash
# update-kit.sh [--config fleet.env] [--dry-run] [--discard-starter-edits] [--since <commit>]
#
# Moves this clone of the kit to the newest kit, even after add-content.sh
# changed files under starter/ (which makes a plain git pull fail). It:
#
#   1. refuses unless the kit folder is the top of its own git clone, on a
#      branch (not a detached HEAD), with no merge, rebase, cherry-pick,
#      revert or bisect in progress;
#   2. reads fleet.env to find add-content.sh's record of your content
#      choices (a missing fleet.env is fine: then there are none);
#   3. refuses when a tracked file outside starter/ is modified or staged,
#      since it only fast-forwards (commit it on a branch of your own, or
#      git restore it); untracked files (fleet.env, app-manifests/) are left
#      alone, unless the newer kit adds a file at the same path;
#   4. fetches origin and checks your fleet.env with the NEWER kit's loader;
#      when it fails (a new required key, a stricter check) it names the key
#      and changes nothing;
#   5. before discarding starter/ changes, proves they are exactly what
#      add-content.sh wrote: it runs the unmodified add-content.sh of your
#      current commit with your recorded choices in a scratch copy and
#      compares the two starter/ folders. A difference is a hand edit: it
#      refuses and says how to keep it, unless you pass --discard-starter-edits;
#   6. restores starter/ and fast-forwards to origin/HEAD (or origin/main).
#      It refuses when you have local commits;
#   7. with the new code, lists the fleet.env keys the new
#      bootstrap/fleet.env.example added or removed since your old commit
#      (names only, never a value; "required" is the new loader's list), then
#      runs add-content.sh again with your recorded choices. A choice the new
#      catalog no longer offers is named and dropped from the record.
#
# It exits 0 only when the kit is current and your choices are back in
# starter/; every other ending exits 1 and says what was and was not changed.
# It changes only this kit folder and your choices record, and writes nothing
# to GitHub. Repos you already filled from an older starter are not changed:
# see copy-starter.sh --dry-run. --dry-run fetches (which changes no file you
# see) and only reports the rest. Idempotent: on a current kit it changes
# nothing but re-applying your choices, which add-content.sh skips when they
# are in place.
#
# --since <commit>: after you pulled by hand (a copy older than this script),
# list the fleet.env keys changed since <commit>, such as ORIG_HEAD.
# Internal: --after-update <sha> [--ids <list>] is how the script continues in
# the new copy of itself after the fast-forward; do not pass it yourself.
# Needs: bash 4.4+, git, tar, python3, jq; node and npm when you have content
# choices (add-content.sh puts them back with them).

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

DISCARD=0 AFTER="" SINCE="" PASSED_IDS="" HAVE_IDS=0
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --discard-starter-edits) DISCARD=1 ;;
    --since) [ $# -ge 2 ] || die "--since needs a commit"; SINCE=$2; shift ;;
    --after-update) [ $# -ge 2 ] || die "--after-update needs a sha"; AFTER=$2; shift ;;
    --ids) [ $# -ge 2 ] || die "--ids needs a list"; PASSED_IDS=$2; HAVE_IDS=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
require_tools git tar python3 jq
[ -z "$AFTER" ] || SINCE=$AFTER
CONFIG_ARG=""
[ "$CONFIG" = ./fleet.env ] || CONFIG_ARG=" --config $CONFIG"

# ------------------------------------------------------------------ config
CFG_OK=0 CHOICES="" IDS="" CFG_ERR=""
if [ -f "$CONFIG" ]; then
  if CHOICES=$( { load_config "$CONFIG" && choices_file && printf '%s' "$CHOICES"; } 2>"$BOOT_WORK/cfg.err" ); then
    load_config "$CONFIG"
    CFG_OK=1
    if [ -f "$CHOICES" ]; then
      jq -e '.installed | type == "array" and all(type == "string")' "$CHOICES" >/dev/null 2>&1 \
        || die "your content choices record $CHOICES is not {\"installed\": [<id>, ...]}; fix it (or delete it and run add-content.sh again), then run this again. Nothing was changed."
      IDS=$(jq -r '.installed | join(",")' "$CHOICES")
      [ -n "$IDS" ] || IDS=none
    fi
  else
    CHOICES=""
    CFG_ERR=$(sed -n 's/^ERROR: //p' "$BOOT_WORK/cfg.err" | head -n1)
    [ -n "$CFG_ERR" ] || CFG_ERR=$(head -n1 "$BOOT_WORK/cfg.err")
  fi
fi
# The old copy's choices, proven before the fast-forward, win over a re-read.
[ "$HAVE_IDS" = 0 ] || IDS=$PASSED_IDS
if [ -n "$IDS" ]; then
  # add-content.sh puts the choices back, and it needs node and npm.
  for t in node npm; do
    command -v "$t" >/dev/null 2>&1 && continue
    detect_os
    die "$t is required to put your content choices back with add-content.sh ($IDS), and was not found on PATH. Install it: $(node_install_cmd "$t"). Then run this again; bash bootstrap/preflight.sh checks every tool. Nothing was changed."
  done
fi

# keys_of <fleet.env-like file>: its KEY names, sorted.
keys_of() { sed -n 's/^[[:space:]]*\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$1" | sort -u; }

# key_report <old commit> <new example> <file of required keys>: the keys the
# example gained or lost since <old commit>. The kit keeps no rename table, so
# a renamed key shows as one removed and one new.
key_report() {
  local old_ex=$BOOT_WORK/example.old k mine
  if ! git -C "$KIT" show "$1:bootstrap/fleet.env.example" > "$old_ex" 2>/dev/null; then
    log "(no bootstrap/fleet.env.example at ${1:0:12}, so the fleet.env key changes are not listed)"
    return 0
  fi
  keys_of "$old_ex" > "$BOOT_WORK/keys.old"
  keys_of "$2" > "$BOOT_WORK/keys.new"
  comm -13 "$BOOT_WORK/keys.old" "$BOOT_WORK/keys.new" > "$BOOT_WORK/keys.added"
  comm -23 "$BOOT_WORK/keys.old" "$BOOT_WORK/keys.new" > "$BOOT_WORK/keys.removed"
  if [ ! -s "$BOOT_WORK/keys.added" ] && [ ! -s "$BOOT_WORK/keys.removed" ]; then
    log "fleet.env keys: none added or removed since ${1:0:12}."
    return 0
  fi
  log "fleet.env keys changed since ${1:0:12} (bootstrap/fleet.env.example explains each):"
  while IFS= read -r k; do
    if grep -qxF -- "$k" "$3"; then
      log "  new, required: $k (set it in your fleet.env)"
    else
      log "  new, optional: $k (empty or absent means the default)"
    fi
  done < "$BOOT_WORK/keys.added"
  mine=""
  [ ! -f "$CONFIG" ] || mine=$(keys_of "$CONFIG")
  while IFS= read -r k; do
    if grep -qxF -- "$k" <<<"$mine"; then
      log "  removed: $k (your fleet.env sets it; delete that line if the kit refuses it)"
    else
      log "  removed: $k"
    fi
  done < "$BOOT_WORK/keys.removed"
}

# config_refusal <before|after|current>: fleet.env does not load under the
# newer kit (before the update), under this one after it, or on a current kit.
config_refusal() {
  local choices="your content choices"
  [ -z "$IDS" ] || choices="your content choices ($IDS)"
  {
    printf 'ERROR: your %s does not load under the %s kit: %s\n' "$CONFIG" "$([ "$1" = before ] && echo newer || echo current)" "${CFG_ERR:-invalid}"
    case $1 in
      before)
        printf 'Nothing was changed: HEAD, starter/ (with %s) and %s are as they were.\n' "$choices" "$CONFIG"
        printf 'The newer example: git -C %q show %s:bootstrap/fleet.env.example\n' "$KIT" "$target" ;;
      after)
        printf 'The kit WAS updated, and starter/ now holds only the new kit'"'"'s files: %s are NOT in it.\n' "$choices"
        printf 'Your record of them is unchanged, and this script puts them back once fleet.env loads.\n' ;;
      current)
        printf 'Nothing was changed. If starter/ lacks %s (after an update by hand), this script puts them back once fleet.env loads.\n' "$choices" ;;
    esac
    printf 'Fix that in %s (bootstrap/fleet.env.example explains every key), then run: bash bootstrap/update-kit.sh%s\n' "$CONFIG" "$CONFIG_ARG"
    [ "$1" = before ] || printf 'Until it succeeds, status.sh counts step 1 as done from the record alone.\n'
  } >&2
  exit 1
}

# ------------------------------------------------------------------ the rest
# Runs in the NEW copy of the script after a fast-forward, or directly on a
# current kit.
rest() {
  local tier id kept=() gone=() core=() out=$BOOT_WORK/reapply.out args reapply=1 since
  log ""
  if [ -n "$SINCE" ]; then
    if since=$(git -C "$KIT" rev-parse --verify -q "$SINCE^{commit}"); then
      printf '%s\n' "${CONFIG_REQUIRED[@]}" > "$BOOT_WORK/keys.required"
      key_report "$since" "$HERE/fleet.env.example" "$BOOT_WORK/keys.required"
    else
      log "(--since $SINCE is not a commit here, so the fleet.env key changes are not listed)"
    fi
  fi
  if [ "$CFG_OK" = 0 ] && [ -f "$CONFIG" ]; then
    if [ -n "$AFTER" ]; then config_refusal after; else config_refusal current; fi
  elif [ "$CFG_OK" = 0 ]; then
    log "No $CONFIG yet; copy bootstrap/fleet.env.example to it and run: bash bootstrap/status.sh${CONFIG_ARG}"
  fi
  if [ -n "$IDS" ] && [ "$IDS" != none ]; then
    IFS=, read -r -a ids <<<"$IDS"
    for id in "${ids[@]}"; do
      tier=$(jq -r --arg id "$id" '[.items[] | select(.id == $id) | .tier][0] // "gone"' "$HERE/content-catalog.json")
      case $tier in
        recommended|opinionated) kept+=("$id") ;;
        core) core+=("$id") ;;
        *) gone+=("$id") ;;
      esac
    done
    if [ $((${#gone[@]} + ${#core[@]})) -gt 0 ]; then
      [ ${#gone[@]} -eq 0 ] || log "The new catalog (bootstrap/content-catalog.json) no longer offers: ${gone[*]}"
      [ ${#core[@]} -eq 0 ] || log "Now core items, always in starter/: ${core[*]}"
      if [ ${#kept[@]} -gt 0 ]; then IDS=$(IFS=,; printf '%s' "${kept[*]}"); else IDS=none; fi
      if [ "$DRY_RUN" = 1 ]; then
        did "drop them from your choices record, then: add-content.sh --items $IDS"
        reapply=0
      else
        jq --arg ids "$IDS" '.installed = ($ids | if . == "none" then [] else split(",") end)' "$CHOICES" > "$CHOICES.tmp"
        mv "$CHOICES.tmp" "$CHOICES"
        log "Dropped them from your choices record ($CHOICES); choose others with: bash bootstrap/add-content.sh${CONFIG_ARG} --items <ids>"
      fi
    fi
  fi
  if [ -n "$IDS" ] && [ "$reapply" = 1 ]; then
    args=(--config "$CONFIG" --items "$IDS")
    [ "$DRY_RUN" = 0 ] || args+=(--dry-run)
    if ! "$BASH" "$HERE/add-content.sh" "${args[@]}" >"$out" 2>&1; then
      cat "$out" >&2
      die "add-content.sh failed on your recorded choices ($IDS; its output is above), so they are NOT all in starter/. Fix what it says, then run: bash bootstrap/update-kit.sh${CONFIG_ARG}"
    fi
    cat "$out"
  elif [ -z "$IDS" ] && [ "$CFG_OK" = 1 ]; then
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
  # No finish(): its "nothing to change" would hide add-content.sh's writes.
  log "Next: bash bootstrap/status.sh${CONFIG_ARG}"
  exit 0
}

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
[ -z "$AFTER" ] || { log "Updated from ${AFTER:0:12} to $(git -C "$KIT" rev-parse --short=12 HEAD)."; rest; }

# A merge, rebase, cherry-pick, revert or bisect half done, or a detached HEAD:
# a fast-forward on top of either would be wrong, so say how to get out.
gp() { git -C "$KIT" rev-parse --path-format=absolute --git-path "$1"; }
in_progress() { # what, command
  die "a $1 is in progress in $KIT, so it cannot be updated. Finish it, or undo it with: git -C $KIT $2 (then run this again). Nothing was changed."
}
[ ! -e "$(gp MERGE_HEAD)" ] || in_progress merge "merge --abort"
if [ -d "$(gp rebase-apply)" ]; then
  if [ -e "$(gp rebase-apply/applying)" ]; then in_progress "git am" "am --abort"; else in_progress rebase "rebase --abort"; fi
fi
[ ! -d "$(gp rebase-merge)" ] || in_progress rebase "rebase --abort"
[ ! -e "$(gp CHERRY_PICK_HEAD)" ] || in_progress cherry-pick "cherry-pick --abort"
[ ! -e "$(gp REVERT_HEAD)" ] || in_progress revert "revert --abort"
[ ! -e "$(gp BISECT_LOG)" ] || in_progress bisect "bisect reset"
if ! git -C "$KIT" symbolic-ref -q HEAD >/dev/null; then
  die "HEAD is detached in $KIT (at $(git -C "$KIT" rev-parse --short=12 HEAD), not on a branch), so a fast-forward would move no branch. Go back to your branch with: git -C $KIT switch main (git warns if that leaves commits behind), then run this again. Nothing was changed."
fi
if [ "$CFG_OK" = 0 ]; then
  if [ -f "$CONFIG" ]; then
    log "note: $CONFIG does not load under your current kit (${CFG_ERR:-invalid}); the newer kit's loader decides below."
  else
    log "note: no $CONFIG, so there are no content choices to put back."
  fi
fi

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
    printf 'Commit them on a branch of your own, or restore them (git restore <path>), then run this again. Nothing was changed.\n'
  } >&2
  exit 1
fi

# ------------------------------------------------------------------ fetch
git -C "$KIT" fetch --quiet origin 2>"$BOOT_WORK/fetch.err" \
  || die "git fetch origin failed in $KIT; check the remote with: git -C $KIT remote -v. Nothing was changed."
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

# ------------------------------------------------------------------ the newer kit's checks
# Run before anything is discarded: the newer loader on fleet.env, and the
# untracked files the newer kit would overwrite (git refuses those mid-update).
nk=$BOOT_WORK/newkit; mkdir -p "$nk"
git -C "$KIT" archive "$new" bootstrap | tar -x -C "$nk"
if [ -f "$CONFIG" ] && ! "$BASH" -c '. "$1/bootstrap/lib/common.sh"; load_config "$2"' _ "$nk" "$CONFIG" >/dev/null 2>"$BOOT_WORK/newcfg.err"; then
  CFG_ERR=$(sed -n 's/^ERROR: //p' "$BOOT_WORK/newcfg.err" | head -n1)
  [ -n "$CFG_ERR" ] || CFG_ERR=$(head -n1 "$BOOT_WORK/newcfg.err")
  "$BASH" -c '. "$1/bootstrap/lib/common.sh"; printf "%s\n" "${CONFIG_REQUIRED[@]}"' _ "$nk" > "$BOOT_WORK/keys.required" 2>/dev/null || : > "$BOOT_WORK/keys.required"
  key_report "$old" "$nk/bootstrap/fleet.env.example" "$BOOT_WORK/keys.required"
  config_refusal before
fi
git -C "$KIT" diff --name-only -z --diff-filter=A "$old" "$new" > "$BOOT_WORK/added.z"
collide=()
while IFS= read -r -d '' p; do
  case $p in starter/*) continue ;; esac   # starter/ is cleaned first
  [ ! -e "$KIT/$p" ] && [ ! -L "$KIT/$p" ] || collide+=("$p")
done < "$BOOT_WORK/added.z"
if [ ${#collide[@]} -gt 0 ]; then
  {
    printf 'ERROR: the newer kit adds files where you have untracked ones, and git would refuse to overwrite them mid-update:\n'
    printf '  %s\n' "${collide[@]}"
    printf 'Move them out of %s, then run this again. Nothing was changed.\n' "$KIT"
  } >&2
  exit 1
fi

# ------------------------------------------------------------------ starter edits
if [ ${#starter_paths[@]} -gt 0 ] && [ "$DISCARD" = 0 ]; then
  hand=()
  if [ -n "$IDS" ]; then
    tmp=$(mktemp -d "$BOOT_WORK/pristine.XXXXXX")
    git -C "$KIT" archive HEAD bootstrap starter library | tar -x -C "$tmp"
    mkdir -p "$BOOT_WORK/state"
    if ! ADOPT_STATE_FILE="$BOOT_WORK/state/proof.json" GH=/nonexistent \
        "$BASH" "$tmp/bootstrap/add-content.sh" --config "$CONFIG" --items "$IDS" >"$BOOT_WORK/proof.out" 2>&1; then
      {
        printf 'ERROR: add-content.sh could not be re-run in a scratch copy, so whether starter/ holds only its files is unknown. Its last lines:\n'
        tail -n 15 "$BOOT_WORK/proof.out" | sed 's/^/  | /'
        printf 'It installs npm packages from the npm registry: check the network and node/npm (bash bootstrap/preflight.sh), then run this again.\n'
        printf 'If you have no edits of your own under starter/, --discard-starter-edits skips this check. Nothing was changed.\n'
      } >&2
      exit 1
    fi
    if ! python3 -I -B -c '
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
' "$tmp/starter" "$KIT/starter" > "$BOOT_WORK/hand.txt" 2>"$BOOT_WORK/hand.err"; then
      die "the comparison of starter/ with add-content.sh's output failed ($(tail -n1 "$BOOT_WORK/hand.err")), so your starter/ edits are not known. Nothing was changed."
    fi
    while IFS= read -r line; do hand+=("$line"); done < "$BOOT_WORK/hand.txt"
  else
    hand=("${starter_paths[@]}")
  fi
  if [ ${#hand[@]} -gt 0 ]; then
    {
      if [ -n "$IDS" ]; then
        printf 'ERROR: starter/ differs from what add-content.sh writes for your choices (%s), so these are your own edits:\n' "$IDS"
      else
        printf 'ERROR: starter/ has changes and no readable content choices record (or fleet.env does not load) to prove they are add-content.sh'"'"'s, so they count as your own edits:\n'
      fi
      printf '  %s\n' "${hand[@]:0:20}"
      [ ${#hand[@]} -le 20 ] || printf '  ... and %d more\n' $((${#hand[@]} - 20))
      printf 'Save them outside the clone first (a patch of the changes plus a tar of the new files):\n'
      printf '  mkdir ~/kit-starter-backup && cd %q &&\n' "$KIT"
      printf '  git diff --binary HEAD -- starter > ~/kit-starter-backup/starter-edits.patch &&\n'
      printf '  git ls-files --others -- starter | tar -cf ~/kit-starter-backup/starter-new-files.tar -T -\n'
      printf 'Starter edits belong in a pull request on your own repo after copy-starter.sh, not in the kit.\n'
      printf 'Then discard them: run this again with --discard-starter-edits. Nothing was changed.\n'
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
if ! git -C "$KIT" merge --ff-only --quiet "$new"; then
  die "the fast-forward failed (git's message is above) after starter/ was reset, so your content choices (${IDS:-none recorded}) are NOT in starter/. Fix what git says, then run: bash bootstrap/update-kit.sh${CONFIG_ARG} (it puts them back)"
fi
log "$summary"
# exec skips the EXIT trap: remove the scratch folder now, and hand the new
# copy everything it needs on its command line ("$BASH": the bash running
# now, which passed the version check; plain `bash` can be macOS's 3.2).
rm -rf "$BOOT_WORK"
ids_arg=()
[ -z "$IDS" ] || ids_arg=(--ids "$IDS")
exec "$BASH" "$HERE/update-kit.sh" --config "$CONFIG" --after-update "$old" "${ids_arg[@]}"
}
update_kit; exit 0
