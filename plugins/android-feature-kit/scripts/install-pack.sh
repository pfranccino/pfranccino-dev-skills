#!/usr/bin/env bash
# Installs the official Android skills that complement android-feature-kit, and optionally copies
# the kit's own skills into an app project.
#
# Official skills come from github.com/android/skills and are installed with Android CLI, so they
# stay updatable with `android skills update`. The list is in pack/official-skills.txt.
#
#   (no --project)                       install the official skills globally, once per machine
#   --project <app>                      install them into that app repository
#   --project <app> --with-team-skills   also copy the kit's skills (skills/*) into the app:
#                                        claude-code -> .claude/skills, codex -> .agents/skills
#                                        (do not combine this with the plugin)
#   --project <app> --with-repo-tools    also copy the check scripts (repo-tools/agent-checks)
#                                        into <app>/tools/agent-checks, where the kit's agents
#                                        and CI use them
#
# Usage:
#   scripts/install-pack.sh [--project ~/code/my-app] [--agents claude-code,codex] [--with-team-skills] [--with-repo-tools] [--dry-run]
set -euo pipefail

plugin_root="$(cd "$(dirname "$0")/.." && pwd)"
project=""
agents="claude-code,codex"
with_team_skills=false
with_repo_tools=false
dry_run=false

while [ $# -gt 0 ]; do
  case "$1" in
    --project) project="$2"; shift 2 ;;
    --agents) agents="$2"; shift 2 ;;
    --with-team-skills) with_team_skills=true; shift ;;
    --with-repo-tools) with_repo_tools=true; shift ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

if { [ "$with_team_skills" = true ] || [ "$with_repo_tools" = true ]; } && [ -z "$project" ]; then
  echo "--with-team-skills and --with-repo-tools need --project <path to the app repository>" >&2
  exit 2
fi
if [ -n "$project" ]; then
  project="$(cd "$project" && pwd)"
fi

step() {
  local description="$1"; shift
  if [ "$dry_run" = true ]; then
    echo "[dry-run] $description"
  else
    echo "$description"
    "$@"
  fi
}

# 1. Official skills through Android CLI
if [ "$dry_run" = false ] && ! command -v android >/dev/null 2>&1; then
  cat >&2 <<'MSG'
Android CLI is not installed or not on PATH. Install it:
  macOS (Apple silicon): curl -fsSL https://dl.google.com/android/cli/latest/darwin_arm64/install.sh | bash
  macOS (Intel):         curl -fsSL https://dl.google.com/android/cli/latest/darwin_x86_64/install.sh | bash
  Linux x86-64:          curl -fsSL https://dl.google.com/android/cli/latest/linux_x86_64/install.sh | bash
Then open a new terminal and run this script again.
MSG
  exit 1
fi

official_count=0
while IFS= read -r line || [ -n "$line" ]; do
  skill="$(echo "$line" | tr -d '\r' | xargs)"
  case "$skill" in ''|'#'*) continue ;; esac
  args=(skills add "--agent=$agents")
  if [ -n "$project" ]; then args+=("--project=$project"); fi
  args+=("$skill")
  step "android ${args[*]}" android "${args[@]}"
  official_count=$((official_count + 1))
done < "$plugin_root/pack/official-skills.txt"

# 2. Kit skills copied into the project's agent folders
copied=0
if [ "$with_team_skills" = true ]; then
  IFS=',' read -r -a agent_list <<< "$agents"
  for agent in "${agent_list[@]}"; do
    case "$agent" in
      claude-code) relative=".claude/skills" ;;
      codex) relative=".agents/skills" ;;
      *) echo "warning: no skill folder known for agent '$agent'; kit skills not copied for it" >&2; continue ;;
    esac
    target="$project/$relative"
    for dir in "$plugin_root"/skills/*/; do
      name="$(basename "$dir")"
      [ -f "$dir/SKILL.md" ] || continue
      step "copy $name -> $target/$name" \
        bash -c 'mkdir -p "$1" && rm -rf "$1/$2" && cp -R "$3" "$1/$2" && cp "$4" "$1/$2/LICENSE"' _ "$target" "$name" "${dir%/}" "$plugin_root/LICENSE"
      copied=$((copied + 1))
    done
  done
fi

# 3. Check scripts copied into the app repository
if [ "$with_repo_tools" = true ]; then
  target="$project/tools/agent-checks"
  step "copy repo-tools/agent-checks -> $target" \
    bash -c 'mkdir -p "$1" && cp "$2"/*.py "$2"/README.md "$1"/' _ "$target" "$plugin_root/repo-tools/agent-checks"
fi

echo
echo "Done. Official skills: $official_count, scope: ${project:-global (this machine)}. Kit skill copies: $copied. Check scripts: $([ "$with_repo_tools" = true ] && echo "tools/agent-checks" || echo no)."
echo "Update the official skills later with: android skills update --all --agent=$agents${project:+ --project=$project}"
