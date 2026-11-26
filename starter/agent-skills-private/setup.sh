#!/usr/bin/env bash
# setup.sh — one-time cleanup for the acsi-agentskills-private repo.
#
# This repo is a *private* Claude Code plugin marketplace: every skill ships as a
# plugin under plugins/<name>/. Claude Code users can install a bundle with one
# command (Claude Code v2.1.275 or later)
#
#   /plugin install acsi-private-anything-anywhere --marketplace example-adopter/acsi-agentskills-private
#
# which offers to add the marketplace before installing — or, on older CLIs,
# with the two-step form
#
#   /plugin marketplace add example-adopter/acsi-agentskills-private
#   /plugin install acsi-private-anything-anywhere@acsi-agentskills-private
#
# and don't need this script at all. OpenAI Codex installs the same plugins
# from the same marketplace (`codex plugin marketplace add
# example-adopter/acsi-agentskills-private`).
#
# THIS SCRIPT NO LONGER LINKS SKILLS ANYWHERE. It used to link every skill
# into ~/.agents/skills, ~/.agent/skills, ~/.gemini/skills,
# ~/.gemini/antigravity/skills and ~/.cursor/skills for the other agent tools.
# The public registry retired that (example-adopter/acsi-agentskills ADR 0017),
# and the same reasons hold here: Codex installs the plugins from the
# marketplace, so a link there would load every skill a second time, and the
# other homes are not read by anything on the owner's machines. So all five
# homes are RETIRED, and sweep_retired_homes below removes the links an
# earlier version made there and leaves everything else alone.
#
# Claude Code never was in that list. It is served by the plugin marketplace.
# Linking the same skills into ~/.claude/skills as well would double-load them —
# once as a namespaced marketplace plugin and once as a personal skill — which
# wastes context and makes invocation ambiguous. This script removes any such
# links it created in earlier versions (see dedup_claude_code_dir below).
#
# Safe to re-run (idempotent), and safe to run while a bundle has no skills yet.
# Run on Windows (Git Bash) AND in WSL separately; each has its own $HOME.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS_DIR="$REPO_ROOT/plugins"

if [[ ! -d "$PLUGINS_DIR" ]]; then
  echo "ERROR: plugins directory not found at $PLUGINS_DIR" >&2
  exit 1
fi

# Collect every skill directory: plugins/<plugin>/skills/<skill>/SKILL.md.
# Only dedup_claude_code_dir needs the list (it looks for links by skill
# name); the sweep of the retired homes goes by where a link points. Unlike
# the public repo, this private marketplace may legitimately be empty.
SKILL_DIRS=()
for skill_md in "$PLUGINS_DIR"/*/skills/*/SKILL.md; do
  [[ -f "$skill_md" ]] || continue
  [[ -L "$(dirname "$skill_md")" ]] && continue
  SKILL_DIRS+=("$(dirname "$skill_md")")
done

# Detect platform: Git Bash / MSYS / Cygwin on Windows → junctions.
case "${OSTYPE:-}" in
  msys*|cygwin*|win32*) PLATFORM="windows" ;;
  *)                    PLATFORM="unix" ;;
esac

echo "Platform:  $PLATFORM"
echo "Repo:      $REPO_ROOT"
echo "Skills:    ${#SKILL_DIRS[@]}"
echo "\$HOME:     $HOME"
echo ""

# Homes this script used to populate and no longer does. Un-listing a home is
# not enough on a machine that has already run an earlier version: the links
# are still there, still feeding an unmanaged copy of the skill set to that
# agent, and they dangle the moment a skill is renamed. sweep_retired_homes
# reaps them.
RETIRED_HOMES=(
  ".agents/skills"
  ".agent/skills"
  ".gemini/skills"
  ".gemini/antigravity/skills"
  ".cursor/skills"
)

# This repo's checkout under its earlier name, when it sits beside this one
# (links made before the rename point there). Only links into it or into
# $PLUGINS_DIR are ever removed.
RETIRED_REGISTRY_DIR="$(dirname "$REPO_ROOT")/retired-agentskills-private"

# The Windows helpers use PowerShell, as the public registry's setup.sh does:
# cmd.exe cannot digest the quoting MSYS builds for `mklink`/`rmdir`, and
# Get-Item -Force sees both reparse point flavors (Junction and SymbolicLink),
# which fsutil-based detection missed. powershell.exe (Windows PowerShell 5.1)
# rather than pwsh, since a stock Windows install may not have PowerShell 7.
# Single quotes in the -Command strings are safe because Windows paths in this
# repo's layout never contain single quotes.

# win_link_type <msys-path> — echoes Junction/SymbolicLink/empty; rc 0 iff reparse point
win_link_type() {
  local p; p="$(cygpath -w "$1")"
  local t
  t=$(MSYS_NO_PATHCONV=1 powershell.exe -NoProfile -NonInteractive -Command \
    "try { (Get-Item -LiteralPath '$p' -Force -ErrorAction Stop).LinkType } catch { '' }" 2>/dev/null </dev/null | tr -d '\r')
  if [[ -n "$t" ]]; then echo "$t"; return 0; fi
  return 1
}

# win_remove_link <msys-path> — removes the reparse point itself, never recursing into the target
win_remove_link() {
  local p; p="$(cygpath -w "$1")"
  MSYS_NO_PATHCONV=1 powershell.exe -NoProfile -NonInteractive -Command \
    "[System.IO.Directory]::Delete('$p')" </dev/null >/dev/null 2>&1
}

# retired_link_target <path> — echo <path>'s link target; rc 0 only when
# <path> really is a symlink/junction AND we could read where it points. A
# regular file or a real directory gives rc 1, and so does a junction MSYS
# cannot read: guessing there would risk deleting something that isn't ours.
retired_link_target() {
  local p="$1" t
  if [[ "$PLATFORM" = "windows" ]]; then
    win_link_type "$p" >/dev/null || return 1
  else
    [[ -L "$p" ]] || return 1
  fi
  t="$(readlink "$p" 2>/dev/null || true)"
  [[ -n "$t" ]] || return 1
  echo "$t"
}

# ours_target <target> — rc 0 when a link target lies under $PLUGINS_DIR or
# under this repo's checkout under its earlier name: the only targets this
# script ever linked to.
ours_target() {
  case "$1" in
    "$PLUGINS_DIR"/*|"$RETIRED_REGISTRY_DIR"/*) return 0 ;;
  esac
  return 1
}

# remove_link <path> — remove a symlink or junction itself, never its target.
remove_link() {
  if [[ "$PLATFORM" = "windows" ]]; then
    win_remove_link "$1"
  else
    rm "$1"
  fi
}

# sweep_retired_homes — remove the links this script created in RETIRED_HOMES.
#
# Deliberately conservative, because these are directories inside a user's
# $HOME that we no longer manage: a link is removed ONLY if its target lies
# under $PLUGINS_DIR or the earlier-named checkout (ours_target). A regular
# file, a real directory, or a link pointing anywhere else belongs to the user
# and is left untouched — and because the directory is then removed with
# rmdir, which refuses a non-empty directory, one such bystander keeps the
# whole directory alive too. A home that is ITSELF a link (the legacy
# whole-directory form) is removed when its target is ours and otherwise left
# alone without looking inside, so the sweep never reaches through a link into
# a directory it does not own. Silent when there is nothing to do, and never
# fails the script if the paths don't exist.
sweep_retired_homes() {
  local rel dir link target name dir_removed
  local -a removed
  for rel in "${RETIRED_HOMES[@]}"; do
    dir="$HOME/$rel"

    if target="$(retired_link_target "$dir")"; then
      if ours_target "$target"; then
        remove_link "$dir"
        echo "=== $dir (retired home — setup.sh no longer links skills) ==="
        echo "  UNLINK   (legacy whole-directory link)"
      fi
      continue
    fi
    [[ -d "$dir" ]] || continue

    removed=()
    for link in "$dir"/*; do
      # An unmatched glob expands to the literal pattern, which is neither a
      # symlink nor a junction, so retired_link_target rejects it.
      target="$(retired_link_target "$link")" || continue
      ours_target "$target" || continue
      remove_link "$link"
      removed+=("$(basename "$link")")
    done

    dir_removed=0
    if rmdir "$dir" 2>/dev/null; then
      dir_removed=1
    fi

    if [[ ${#removed[@]} -gt 0 ]] || [[ "$dir_removed" -eq 1 ]]; then
      echo "=== $dir (retired home — setup.sh no longer links skills) ==="
      for name in ${removed[@]+"${removed[@]}"}; do
        echo "  UNLINK   $name"
      done
      if [[ "$dir_removed" -eq 1 ]]; then
        echo "  RMDIR    (nothing left in it)"
      fi
    fi
  done
}

# dedup_claude_code_dir — earlier versions of this script also linked skills
# into ~/.claude/skills. Claude Code is served by the marketplace, so remove
# any links we previously created there to avoid double-loading. The same rule
# as the sweep applies: only a link whose target is ours is removed. A legacy
# whole-directory link is removed when it points anywhere into this checkout
# (or the earlier-named one); when it points somewhere else it is the user's,
# and is left alone without looking inside. Real personal skills the user
# keeps in ~/.claude/skills are untouched.
dedup_claude_code_dir() {
  local cc="$HOME/.claude/skills" sd link target printed=0
  if target="$(retired_link_target "$cc")"; then
    case "$target" in
      "$REPO_ROOT"/*|"$RETIRED_REGISTRY_DIR"/*)
        remove_link "$cc"
        echo "=== $cc (de-dup: marketplace owns Claude Code) ==="
        echo "  UNLINK   (legacy whole-directory link)"
        ;;
    esac
    return 0
  fi
  [[ -d "$cc" ]] || return 0
  for sd in ${SKILL_DIRS[@]+"${SKILL_DIRS[@]}"}; do
    link="$cc/$(basename "$sd")"
    target="$(retired_link_target "$link")" || continue
    ours_target "$target" || continue
    if [[ "$printed" -eq 0 ]]; then
      echo "=== $cc (de-dup: marketplace owns Claude Code) ==="
      printed=1
    fi
    remove_link "$link"
    echo "  UNLINK   $(basename "$link")"
  done
}

dedup_claude_code_dir
sweep_retired_homes

echo ""
echo "Setup complete. No skills were linked: install the bundle from the marketplace."
