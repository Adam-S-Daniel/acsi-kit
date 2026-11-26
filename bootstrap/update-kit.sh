#!/usr/bin/env bash
# update-kit.sh [--config fleet.env] [--dry-run] [--discard-starter-edits] [--kit <clone>]
#
# Moves a clone of the kit to the newest kit, even after add-content.sh
# changed files under starter/ (which makes a plain git pull fail). The
# README's "Update your copy of the kit" runs the NEWEST copy of this script
# from a temporary folder with --kit <clone>, so it works on a clone older
# than the script too. It:
#
#   1. refuses unless the kit folder is the top of its own git clone, on a
#      branch (not a detached HEAD), with no merge, rebase, cherry-pick,
#      revert or bisect in progress;
#   2. reads fleet.env (--config) to find add-content.sh's record of your
#      content choices. With no fleet.env at that path it refuses when
#      starter/ has changes or a choices record exists, and names --config;
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
#      compares the two starter/ folders (contents and executable bits). A
#      difference is a hand edit: it refuses, unless you pass
#      --discard-starter-edits;
#   6. saves every starter/ change (a patch, and a copy of new files) to
#      ~/kit-starter-backup-<old commit>, restores starter/ and fast-forwards
#      to origin/HEAD (or origin/main). It refuses when you have local commits;
#   7. with the new code, lists the fleet.env keys the new
#      bootstrap/fleet.env.example added or removed since your old commit
#      (names only, never a value; "required" is the new loader's list), then
#      runs add-content.sh again with your recorded choices. A choice the new
#      catalog no longer offers is named and dropped from the record.
#
# It exits 0 only when the kit is current and your choices are back in
# starter/; every other ending (an interrupt included) exits non-zero and
# says what was and was not changed and the command to run next. It changes
# only the kit folder, your choices record and the backup folder, and writes
# nothing to GitHub. Repos you already filled from an older starter are not
# changed: see copy-starter.sh --dry-run. --dry-run fetches (which changes no
# file you see) and only reports the rest. On a current kit it changes nothing
# but re-applying your choices, which add-content.sh skips when they are in
# place.
#
# Before the update it notes which setup steps status.sh counts as done (a
# read-only run of the current kit's status.sh); afterwards it names any the
# newer kit's checks no longer count as done (a check that now covers more,
# such as a secret now needed in more repos), with the command to run again.
#
# add-content.sh's list of every file it put back goes to a log file outside
# the kit (named in the output; only the per-tree counts are printed), and the
# run ends with a short "Do this now" block: a key the copy step needs that
# your fleet.env lacks (TIME_ZONE), each step the newer kit reopened, and each
# existing repo that needs a pull request for the content, then "Next:".
#
# Internal: --after-update <sha> [--ids <list>] [--done-before <lines>] is how
# the script continues in the new copy of itself after the fast-forward; do
# not pass it yourself.
# Needs: bash 4.4+, git, tar, python3, jq; node and npm when you have content
# choices (add-content.sh puts them back with them).

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

DISCARD=0 AFTER="" PASSED_IDS="" HAVE_IDS=0 KIT_ARG="" DONE_BEFORE=""
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --discard-starter-edits) DISCARD=1 ;;
    --kit) [ $# -ge 2 ] || die "--kit needs the path of the kit's clone"; KIT_ARG=$2; shift ;;
    --after-update) [ $# -ge 2 ] || die "--after-update needs a sha"; AFTER=$2; shift ;;
    --ids) [ $# -ge 2 ] || die "--ids needs a list"; PASSED_IDS=$2; HAVE_IDS=1; shift ;;
    --done-before) [ $# -ge 2 ] || die "--done-before needs a list"; DONE_BEFORE=$2; shift ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
require_tools git tar python3 jq
if [ -n "$KIT_ARG" ]; then
  KIT=$(cd "$KIT_ARG" 2>/dev/null && pwd -P) || die "--kit $KIT_ARG is not a folder"
fi
B=$KIT/bootstrap   # the kit's own scripts (this file may run from a temporary copy)

# q <word>: the word quoted for pasting into a shell.
q() { printf '%q' "$1"; }
CONFIG_ARG=$(config_arg)
# TODO: the "Do this now" lines rest() prints before its "Next:" line.
TODO=()
# abs_config_arg: " --config <absolute path>" for a command run from another
# folder (a fresh clone), when the config exists; fleet.env stays where it is.
abs_config_arg() {
  [ -f "$CONFIG" ] || { printf '%s' "$CONFIG_ARG"; return 0; }
  printf ' --config %q' "$(cd "$(dirname "$CONFIG")" && pwd -P)/$(basename "$CONFIG")"
}
# next_cmd: how to run the update again from where the kit is now.
next_cmd() {
  if [ -f "$B/update-kit.sh" ]; then
    printf 'cd %s && bash bootstrap/update-kit.sh%s' "$(q "$KIT")" "$CONFIG_ARG"
  else
    printf 'the update block in the kit'"'"'s README ("Update your copy of the kit"), from %s' "$(q "$KIT")"
  fi
}

# Interrupts (Ctrl-C) and failures after the first change say where things stand.
STAGE="nothing was changed"
on_signal() {
  trap - INT TERM
  printf '\nINTERRUPTED: %s.\nNext: %s\n' "$STAGE" "$(next_cmd)" >&2
  exit 130
}
trap on_signal INT TERM

# read_choices: IDS from the record at $CHOICES (none when it lists nothing).
read_choices() {
  [ -f "$CHOICES" ] || return 0
  jq -e '.installed | type == "array" and all(type == "string")' "$CHOICES" >/dev/null 2>&1 \
    || die "your content choices record $CHOICES is not {\"installed\": [<id>, ...]}; fix it (or delete it and run add-content.sh again), then run this again. Nothing was changed."
  IDS=$(jq -r '.installed | join(",")' "$CHOICES")
  [ -n "$IDS" ] || IDS=none
}
# need_node: add-content.sh puts the choices back, and it needs node and npm.
need_node() {
  local t
  [ -n "$IDS" ] || return 0
  for t in node npm; do
    command -v "$t" >/dev/null 2>&1 && continue
    detect_os
    die "$t is required to put your content choices back with add-content.sh ($IDS), and was not found on PATH. Install it: $(node_install_cmd "$t"). Then run this again; bash bootstrap/preflight.sh${CONFIG_ARG} checks every tool. Nothing was changed."
  done
}
# no_config_refusal <why>: no fleet.env at $CONFIG, yet there are choices to keep.
no_config_refusal() {
  {
    printf 'ERROR: there is no fleet.env at %s, and %s.\n' "$CONFIG" "$1"
    printf 'Without it this script cannot find your content choices to put back. If your fleet.env is elsewhere, pass its path:\n'
    printf '  --config /path/to/fleet.env   (the README'"'"'s update block sets it on its first line)\n'
    printf 'Nothing was changed.\n'
  } >&2
  exit 1
}
# records: the content choices records in the state folder, one per line.
records() { find "$(state_dir)" -maxdepth 1 -name '*.content-choices.json' 2>/dev/null || true; }

# steps_done <status.sh> <out file>: "<id><TAB><title>" for each step that
# status.sh (read-only) counts as done; 1 when status.sh fails.
steps_done() {
  "$BASH" "$1" --config "$CONFIG" > "$BOOT_WORK/status.txt" 2>/dev/null || return 1
  sed -nE 's/^(done|asked: done) +([^ ]+) +(.*)$/\2	\3/p' "$BOOT_WORK/status.txt" > "$2"
}

# ------------------------------------------------------------------ config
CFG_OK=0 CHOICES="" IDS="" CFG_ERR=""
if [ -f "$CONFIG" ]; then
  if CHOICES=$( { load_config "$CONFIG" && choices_file && printf '%s' "$CHOICES"; } 2>"$BOOT_WORK/cfg.err" ); then
    load_config "$CONFIG"
    CFG_OK=1
    read_choices
  else
    CHOICES=""
    CFG_ERR=$(sed -n 's/^ERROR: //p' "$BOOT_WORK/cfg.err" | head -n1)
    [ -n "$CFG_ERR" ] || CFG_ERR=$(head -n1 "$BOOT_WORK/cfg.err")
  fi
fi
# The old copy's choices, proven before the fast-forward, win over a re-read.
[ "$HAVE_IDS" = 0 ] || IDS=$PASSED_IDS
need_node

# copy_key_todo <key> <copy step>: a "Do this now" line for a key the newer
# kit's copy-starter.sh needs, when this fleet.env leaves it empty.
COPY_KEY_TODO=0
copy_key_todo() {
  local v="CFG_$1" help="bootstrap/fleet.env.example explains it"
  [ -z "${!v:-}" ] || return 0
  [ "$1" != TIME_ZONE ] || help=${_TIME_ZONE_HELP#set TIME_ZONE in fleet.env to }
  COPY_KEY_TODO=1
  TODO+=("Set $1 in $CONFIG ($help). Until it is set, copy-starter.sh${2:+ (step $2)} refuses and status.sh keeps step 0 open.")
}

# content_log: CONTENT_LOG, where add-content.sh's full output goes: a file
# in the state folder (outside the kit), named for the kit's commit. A dry run
# writes nothing there: its output goes to the scratch folder, and is not named.
content_log() {
  local d
  if [ "$DRY_RUN" = 1 ]; then CONTENT_LOG=$BOOT_WORK/add-content.log; return 0; fi
  d=$(state_dir)
  mkdir -p "$d" && chmod 700 "$d"
  CONTENT_LOG=$d/update-kit-$(git -C "$KIT" rev-parse --short=12 HEAD).log
}
# content_report: add-content.sh's output without its one line per file (a
# count and the log's path instead), and a "Do this now" line for each repo
# that already exists, which the content reaches only through a pull request.
# The lines add-content.sh prints when a repo already exists: the first names
# the repo and tree, and the next three are its advice, which points at the
# per-file lines above it. Here those lines are in the log, so the advice is
# left out and the "Do this now" line names the log instead.
EXISTS_RE='^([^ ]+) already exists, so this reached only starter/([^ ]+)\. Open a pull request on it$'
content_report() {
  local n line advice=0
  n=$(grep -cE '^  (add|change): ' "$CONTENT_LOG" || true)
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ $EXISTS_RE ]]; then
      advice=3
      if [ "$DRY_RUN" = 1 ]; then
        TODO+=("Open a pull request on ${BASH_REMATCH[1]} (never a push to its default branch) with the starter/${BASH_REMATCH[2]} files the run without --dry-run adds or changes, with your names as copy-starter.sh writes them.")
      else
        TODO+=("Open a pull request on ${BASH_REMATCH[1]} (never a push to its default branch) that adds the starter/${BASH_REMATCH[2]} files listed in $CONTENT_LOG, with your names as copy-starter.sh writes them.")
      fi
      [ "${BASH_REMATCH[2]}" != agent-skills ] || TODO[${#TODO[@]}-1]+=" When it merges, run bash bootstrap/regenerate.sh$(config_arg) skills-locks."
      continue
    fi
    if [ "$advice" -gt 0 ]; then advice=$((advice - 1)); continue; fi
    [[ $line =~ ^\ \ (add|change):\  ]] || printf '  %s\n' "$line"
  done < "$CONTENT_LOG"
  if [ "$n" = 0 ]; then :
  elif [ "$DRY_RUN" = 1 ]; then log "  ($n file(s) would be added or changed in starter/)"
  else log "  ($n file(s) added or changed in starter/; the list is in $CONTENT_LOG)"; fi
}

# keys_of <fleet.env-like file>: its KEY names, sorted.
keys_of() { sed -n 's/^[[:space:]]*\([A-Z][A-Z0-9_]*\)=.*/\1/p' "$1" | sort -u; }

# required_lists <bootstrap folder>: writes $BOOT_WORK/keys.required (the keys
# that kit's load_config requires), keys.copy (those it leaves optional but
# its copy-starter.sh requires) and copy.step (the first steps.json step that
# runs copy-starter.sh), all read from that kit, so the report says what the
# NEW kit enforces.
required_lists() {
  "$BASH" -c '. "$1/lib/common.sh"; printf "%s\n" "${CONFIG_REQUIRED[@]}"' _ "$1" > "$BOOT_WORK/keys.required" 2>/dev/null || : > "$BOOT_WORK/keys.required"
  "$BASH" -c '. "$1/lib/common.sh"; printf "%s\n" "${CONFIG_REQUIRED_BY_COPY[@]}"' _ "$1" > "$BOOT_WORK/keys.copy" 2>/dev/null || : > "$BOOT_WORK/keys.copy"
  jq -r '[.steps[] | select(.run | tostring | test("copy-starter[.]sh"))][0].id // ""' "$1/steps.json" > "$BOOT_WORK/copy.step" 2>/dev/null || : > "$BOOT_WORK/copy.step"
}

# key_report <old commit> <new example>: the keys the example gained or lost
# since <old commit> (required_lists first). The kit keeps no rename table, so
# a renamed key shows as one removed and one new.
key_report() {
  local old_ex=$BOOT_WORK/example.old k mine step
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
  step=$(cat "$BOOT_WORK/copy.step")
  while IFS= read -r k; do
    if grep -qxF -- "$k" "$BOOT_WORK/keys.required"; then
      log "  new, required: $k (set it in your fleet.env)"
    elif grep -qxF -- "$k" "$BOOT_WORK/keys.copy"; then
      log "  new, needed before the copy step${step:+ (step $step)}: $k (copy-starter.sh refuses until it is set in your fleet.env; this update does not need it)"
      copy_key_todo "$k" "$step"
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
        printf 'The newer example: git -C %s show %s:bootstrap/fleet.env.example\n' "$(q "$KIT")" "$target" ;;
      after)
        printf 'The kit WAS updated, and starter/ now holds only the new kit'"'"'s files: %s are NOT in it.\n' "$choices"
        printf 'Your record of them is unchanged, and this script puts them back once fleet.env loads.\n' ;;
      current)
        printf 'Nothing was changed. If starter/ lacks %s, this script puts them back once fleet.env loads.\n' "$choices" ;;
    esac
    printf 'Fix that in %s (bootstrap/fleet.env.example explains every key), then run: %s\n' "$CONFIG" "$(next_cmd)"
    [ "$1" = before ] || printf 'Until it succeeds, status.sh counts step 1 as done from the record alone.\n'
  } >&2
  exit 1
}

# reopened: the steps done before the update (DONE_BEFORE, matched by title,
# since a newer steps.json can renumber) that status.sh no longer counts done,
# each with its command and, for status.sh's next step, status.sh's reason.
reopened() {
  local id title run next after why n=0
  printf '%s\n' "$DONE_BEFORE" > "$BOOT_WORK/done.before"
  log ""
  log "Checking which setup steps are still done under the newer kit (bootstrap/status.sh, read-only)..."
  if ! steps_done "$B/status.sh" "$BOOT_WORK/done.after"; then
    log "(status.sh failed, so steps that the newer kit's checks reopen are not listed: run bash bootstrap/status.sh${CONFIG_ARG})"
    return 0
  fi
  next=$(sed -nE 's/^Next: ([^ ]+) .*/\1/p' "$BOOT_WORK/status.txt" | head -n1)
  after=$(cut -f2- "$BOOT_WORK/done.after")
  while IFS=$'\t' read -r _ title; do
    [ -n "$title" ] || continue
    ! grep -qxF -- "$title" <<<"$after" || continue
    id=$(jq -r --arg t "$title" '[.steps[] | select(.title == $t) | .id][0] // ""' "$B/steps.json")
    [ -n "$id" ] || continue   # the newer kit dropped or renamed that step
    run=$(jq -r --arg t "$title" '[.steps[] | select(.title == $t) | .run][0] // ""' "$B/steps.json")
    [ "$n" -gt 0 ] || log "Steps that were done before this update and are NOT done under the newer kit (its checks ask for more):"
    n=$((n + 1))
    run=$(with_config_arg "$run")
    log "  step $id, $title: $run"
    # status.sh explains only its next step; the 4-space lines under "Not done yet:".
    why=""
    [ "$id" != "$next" ] || why=$(sed -n '/^  Not done yet:$/,$ { /^    /s/^    //p; }' "$BOOT_WORK/status.txt")
    [ -z "$why" ] || sed 's/^/    why: /' <<<"$why"
    # A config step's run text copies the example over your fleet.env, so its
    # "Do this now" line is status.sh's reason instead; when that reason is a
    # key the copy step needs, the key's own line (copy_key_todo) says it.
    if [ "$(jq -r --arg t "$title" '[.steps[] | select(.title == $t) | .check.type][0]' "$B/steps.json")" = config ]; then
      if [ "$COPY_KEY_TODO" = 0 ]; then
        if [ -n "$why" ]; then why=$(paste -sd' ' - <<<"$why"); else why="edit $CONFIG (bash bootstrap/status.sh${CONFIG_ARG} says why)"; fi
        TODO+=("Step $id ($title) is not done under the newer kit: $why")
      fi
    else
      TODO+=("Step $id ($title) is not done under the newer kit: $run")
    fi
  done < "$BOOT_WORK/done.before"
  [ "$n" -gt 0 ] || log "Every setup step that was done before this update is still done."
}

# ------------------------------------------------------------------ the rest
# Runs in the NEW copy of the script after a fast-forward, or on a current kit.
rest() {
  local tier id kept=() gone=() core=() args reapply=1
  log ""
  if [ -n "$AFTER" ]; then
    required_lists "$B"
    key_report "$AFTER" "$B/fleet.env.example"
  fi
  if [ "$CFG_OK" = 0 ] && [ -f "$CONFIG" ]; then
    if [ -n "$AFTER" ]; then config_refusal after; else config_refusal current; fi
  elif [ "$CFG_OK" = 0 ]; then
    [ -z "$(records)" ] || no_config_refusal "a content choices record exists ($(records | tr '\n' ' '))"
    log "No $CONFIG yet; copy bootstrap/fleet.env.example to it and run: bash bootstrap/status.sh${CONFIG_ARG}"
  fi
  if [ -n "$IDS" ] && [ "$IDS" != none ]; then
    IFS=, read -r -a ids <<<"$IDS"
    for id in "${ids[@]}"; do
      tier=$(jq -r --arg id "$id" '[.items[] | select(.id == $id) | .tier][0] // "gone"' "$B/content-catalog.json")
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
    [ "$DRY_RUN" = 1 ] || STAGE="the kit is updated, but your content choices ($IDS) are not all back in starter/"
    log "Putting your content choices back with add-content.sh ($IDS; npm ci can take a minute):"
    content_log
    if ! "$BASH" "$B/add-content.sh" "${args[@]}" > "$CONTENT_LOG" 2>&1; then
      content_report
      [ "$DRY_RUN" = 0 ] || die "add-content.sh --dry-run failed on your recorded choices ($IDS; its output is above). Fix what it says, then run: $(next_cmd)"
      die "add-content.sh failed on your recorded choices ($IDS; its output is above, all of it in $CONTENT_LOG), so they are NOT all in starter/. Fix what it says, then run: $(next_cmd)"
    fi
    content_report
    STAGE="nothing was left half done"
  elif [ -z "$IDS" ] && [ "$CFG_OK" = 1 ]; then
    log "No recorded content choices yet; choose with: bash bootstrap/add-content.sh${CONFIG_ARG} --items <ids|recommended|none>"
  fi
  if [ -n "$DONE_BEFORE" ] && [ "$CFG_OK" = 1 ]; then
    reopened
  fi
  if [ "$CFG_OK" = 1 ]; then
    log ""
    log "Repos you already filled from an older starter are NOT updated by this script."
    log "bash bootstrap/copy-starter.sh${CONFIG_ARG} --dry-run <starter-subdir> <owner/repo> shows what the newer"
    log "starter would change there and lists files that differ on the default branch as REFUSED;"
    log "read those before any --force."
  fi
  log ""
  if [ ${#TODO[@]} -gt 0 ]; then
    log "Do this now:"
    for i in "${!TODO[@]}"; do log "  $((i + 1)). ${TODO[$i]}"; done
  fi
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
    printf 'Instead: clone the kit fresh beside it, and in the new clone run\n'
    printf '  bash bootstrap/add-content.sh%s --items <ids>\n' "$(abs_config_arg)"
    if [ -n "$IDS" ]; then printf 'Your recorded content choices: %s\n' "$IDS"; fi
  } >&2
  exit 1
fi
[ -z "$AFTER" ] || { STAGE="the kit is updated, but your content choices are not put back yet"; log "Updated from ${AFTER:0:12} to $(git -C "$KIT" rev-parse --short=12 HEAD)."; rest; }

# A merge, rebase, cherry-pick, revert or bisect half done, or a detached HEAD:
# a fast-forward on top of either would be wrong, so say how to get out.
gp() { git -C "$KIT" rev-parse --path-format=absolute --git-path "$1"; }
in_progress() { # what, command
  die "a $1 is in progress in $KIT, so it cannot be updated. Finish it, or undo it with: git -C $(q "$KIT") $2 (then run this again). Nothing was changed."
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
  die "HEAD is detached in $KIT (at $(git -C "$KIT" rev-parse --short=12 HEAD), not on a branch), so a fast-forward would move no branch. Go back to your branch with: git -C $(q "$KIT") switch main (git warns if that leaves commits behind), then run this again. Nothing was changed."
fi
if [ "$CFG_OK" = 0 ]; then
  if [ -f "$CONFIG" ]; then
    log "note: $CONFIG does not load under your current kit (${CFG_ERR:-invalid}); the newer kit's loader decides below."
  else
    [ -z "$(git -C "$KIT" status --porcelain -- starter)" ] || no_config_refusal "starter/ has changes (add-content.sh's, or your own)"
    [ -z "$(records)" ] || no_config_refusal "a content choices record exists ($(records | tr '\n' ' '))"
    log "note: no $CONFIG and no content choices record, so there are no choices to put back."
  fi
fi

# save_starter: every starter/ change, to a new folder outside the clone.
save_starter() {
  local n=1
  BACKUP=$HOME/kit-starter-backup-${old:0:12}
  while [ -e "$BACKUP" ]; do n=$((n + 1)); BACKUP=$HOME/kit-starter-backup-${old:0:12}-$n; done
  case $BACKUP/ in "$KIT"/*) die "the backup folder $BACKUP would be inside the kit; set HOME to a folder outside it. Nothing was changed." ;; esac
  mkdir -p "$BACKUP"
  git -C "$KIT" diff --binary HEAD -- starter > "$BACKUP/starter-edits.patch"
  git -C "$KIT" ls-files -z --others --exclude-standard -- starter > "$BOOT_WORK/untracked.z"
  python3 -I -B -c '
import os, shutil, sys
kit, dest, lst = sys.argv[1:4]
for rel in open(lst, "rb").read().split(b"\0"):
    if rel:
        rel = os.fsdecode(rel)
        os.makedirs(os.path.join(dest, os.path.dirname(rel)), exist_ok=True)
        shutil.copy2(os.path.join(kit, rel), os.path.join(dest, rel), follow_symlinks=False)
' "$KIT" "$BACKUP/new-files" "$BOOT_WORK/untracked.z"
}

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
if ! git -C "$KIT" fetch --quiet origin 2>"$BOOT_WORK/fetch.err"; then
  sed 's/^/  | /' "$BOOT_WORK/fetch.err" | tail -n 5 >&2
  die "git fetch origin failed in $KIT (git's last lines are above); check the network and the remote (git -C $(q "$KIT") remote -v). Nothing was changed."
fi
target=""
if t=$(git -C "$KIT" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null) && [ -n "$t" ]; then
  target=$t
elif git -C "$KIT" rev-parse --verify -q refs/remotes/origin/main >/dev/null; then
  target=origin/main
else
  die "no origin/HEAD or origin/main in $KIT; check the remote with: git -C $(q "$KIT") remote -v. Nothing was changed."
fi
old=$(git -C "$KIT" rev-parse HEAD)
new=$(git -C "$KIT" rev-parse "$target^{commit}")
if [ "$old" = "$new" ]; then
  skip "the kit is current ($(git -C "$KIT" rev-parse --short=12 HEAD))"
  rest
fi
if ! git -C "$KIT" merge-base --is-ancestor "$old" "$new"; then
  die "your HEAD ($(git -C "$KIT" rev-parse --short HEAD)) is not an ancestor of $target ($(git -C "$KIT" rev-parse --short "$new")): you have local commits or are on another branch. See them with: git -C $(q "$KIT") log --oneline $target..HEAD. Nothing was changed."
fi

# ------------------------------------------------------------------ the newer kit's checks
# Run before anything is discarded: the newer loader on fleet.env, and the
# untracked files the newer kit would overwrite (git refuses those mid-update).
nk=$BOOT_WORK/newkit; mkdir -p "$nk"
git -C "$KIT" archive "$new" bootstrap | tar -x -C "$nk"
if [ -f "$CONFIG" ] && ! "$BASH" -c '. "$1/bootstrap/lib/common.sh"; load_config "$2"' _ "$nk" "$CONFIG" >/dev/null 2>"$BOOT_WORK/newcfg.err"; then
  CFG_ERR=$(sed -n 's/^ERROR: //p' "$BOOT_WORK/newcfg.err" | head -n1)
  [ -n "$CFG_ERR" ] || CFG_ERR=$(head -n1 "$BOOT_WORK/newcfg.err")
  required_lists "$nk/bootstrap"
  key_report "$old" "$nk/bootstrap/fleet.env.example"
  config_refusal before
fi
# A key only the newer kit knows (a new required one, set ahead of the
# update) fails the current loader: find the record through the newer one.
if [ "$CFG_OK" = 0 ] && [ -f "$CONFIG" ]; then
  CHOICES=$("$BASH" -c '. "$1/bootstrap/lib/common.sh"; load_config "$2"; choices_file; printf "%s" "$CHOICES"' _ "$nk" "$CONFIG" 2>/dev/null) || CHOICES=""
  [ -z "$CHOICES" ] || read_choices
  need_node
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
    # The CURRENT add-content.sh's loader refuses keys it does not know yet
    # (a new required one): hand it fleet.env without them.
    proof_cfg=$BOOT_WORK/proof.env
    known=" $("$BASH" -c '. "$1/bootstrap/lib/common.sh"; printf "%s " "${CONFIG_KEYS[@]}"' _ "$tmp") "
    : > "$proof_cfg"
    if [ -f "$CONFIG" ]; then
      while IFS= read -r line || [ -n "$line" ]; do
        k=$(printf '%s' "$line" | sed -n 's/^[[:space:]]*\([A-Z][A-Z0-9_]*\)=.*/\1/p')
        [ -n "$k" ] && [[ $known != *" $k "* ]] && continue
        printf '%s\n' "$line" >> "$proof_cfg"
      done < "$CONFIG"
    fi
    if ! "$BASH" -c '. "$1/bootstrap/lib/common.sh"; load_config "$2"' _ "$tmp" "$proof_cfg" >/dev/null 2>"$BOOT_WORK/oldcfg.err"; then
      {
        printf 'ERROR: your fleet.env loads under the newer kit but not under your current one (%s),\n' "$(sed -n 's/^ERROR: //p' "$BOOT_WORK/oldcfg.err" | head -n1)"
        printf 'so add-content.sh cannot be re-run to prove starter/ holds only its changes.\n'
        printf 'If you made no edits of your own under starter/, run again with --discard-starter-edits: it saves every starter/ change to ~/kit-starter-backup-%s first. Nothing was changed.\n' "${old:0:12}"
      } >&2
      exit 1
    fi
    log "Checking that starter/ holds only add-content.sh's changes (it re-runs in a scratch copy; npm ci can take a minute)..."
    if ! ADOPT_STATE_FILE="$BOOT_WORK/state/proof.json" GH=/nonexistent \
        "$BASH" "$tmp/bootstrap/add-content.sh" --config "$proof_cfg" --items "$IDS" >"$BOOT_WORK/proof.out" 2>&1; then
      {
        printf 'ERROR: add-content.sh could not be re-run in a scratch copy, so whether starter/ holds only its files is unknown. Its last lines:\n'
        tail -n 15 "$BOOT_WORK/proof.out" | sed 's/^/  | /'
        printf 'It installs npm packages from the npm registry: check the network and node/npm (bash bootstrap/preflight.sh%s), then run this again.\n' "$CONFIG_ARG"
        printf 'If you have no edits of your own under starter/, --discard-starter-edits skips this check (it saves every starter/ change first). Nothing was changed.\n'
      } >&2
      exit 1
    fi
    if ! python3 -I -B -c '
import os, stat, sys
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
                    out[rel] = ("f", bool(os.stat(p).st_mode & stat.S_IXUSR), fh.read())
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
      printf 'Starter edits belong in a pull request on your own repo after copy-starter.sh, not in the kit.\n'
      printf 'To go ahead, run the same command again with --discard-starter-edits added (in the README'"'"'s\n'
      printf 'update block: at the end of its last line). It first saves every starter/ change\n'
      printf '(a patch, and a copy of new files) to ~/kit-starter-backup-%s. Nothing was changed.\n' "${old:0:12}"
    } >&2
    exit 1
  fi
fi

# ------------------------------------------------------------------ steps done now
done_arg=()
if [ "$DRY_RUN" = 0 ] && [ "$CFG_OK" = 1 ] && [ -f "$B/status.sh" ]; then
  log "Noting which setup steps are done before the update (bootstrap/status.sh, read-only)..."
  if steps_done "$B/status.sh" "$BOOT_WORK/done.before" && [ -s "$BOOT_WORK/done.before" ]; then
    done_arg=(--done-before "$(cat "$BOOT_WORK/done.before")")
  fi
fi

# ------------------------------------------------------------------ fast-forward
n=$(git -C "$KIT" rev-list --count "$old..$new")
summary="${old:0:12} -> ${new:0:12}, $n commit(s)"
if [ "$DRY_RUN" = 1 ]; then
  if [ ${#starter_paths[@]} -gt 0 ]; then
    did "save ${#starter_paths[@]} starter/ change(s) to ~/kit-starter-backup-${old:0:12} and discard them (add-content.sh rewrites its own afterward)"
    WRITES=$((WRITES + 1))
  fi
  did "fast-forward $target: $summary"
  WRITES=$((WRITES + 1))
  log ""
  log "Next: run this again without --dry-run; the key check and the content re-apply follow the update."
  finish
  exit 0
fi
if [ ${#starter_paths[@]} -gt 0 ]; then
  save_starter
  log "Saved ${#starter_paths[@]} starter/ change(s) to $BACKUP (starter-edits.patch, new-files/)."
  STAGE="starter/ may be partly reset (its changes are saved in $BACKUP) and the kit is not updated yet"
  if ! git -C "$KIT" restore --source=HEAD --staged --worktree -- starter || ! git -C "$KIT" clean -fdq -- starter; then
    die "resetting starter/ failed (git's message is above): $STAGE. Next: $(next_cmd)"
  fi
  STAGE="starter/ is reset (its changes are saved in $BACKUP) and the kit is not updated yet"
  log "Discarded them; add-content.sh puts your choices back after the update."
fi
if ! git -C "$KIT" merge --ff-only --quiet "$new"; then
  die "the fast-forward failed (git's message is above): $STAGE; your content choices (${IDS:-none recorded}) are NOT in starter/. Fix what git says, then run: $(next_cmd)"
fi
STAGE="the kit is updated, but your content choices are not put back yet"
log "$summary"
# exec skips the EXIT trap: remove the scratch folder now, and hand the new
# copy everything it needs on its command line ("$BASH": the bash running
# now, which passed the version check; plain `bash` can be macOS's 3.2).
rm -rf "$BOOT_WORK"
ids_arg=()
[ -z "$IDS" ] || ids_arg=(--ids "$IDS")
exec "$BASH" "$B/update-kit.sh" --config "$CONFIG" --after-update "$old" "${ids_arg[@]}" "${done_arg[@]}"
}
update_kit; exit 0
