<#
.SYNOPSIS
Installs the official Android skills that complement android-feature-kit, and optionally copies
the kit's own skills into an app project.

.DESCRIPTION
Official skills come from github.com/android/skills and are installed with Android CLI, so they
stay updatable with `android skills update`. The list is in pack/official-skills.txt.

- Without -Project: installs the official skills globally, once per machine
  (`android skills add <id> --agent=<agents>`). Use this with the marketplace plugin.
- With -Project: installs them into that app repository (`--project=<app>`).
- With -Project and -WithTeamSkills: also copies the kit's skills (skills/*) into the app:
  claude -> .claude/skills, codex -> .agents/skills. Do not combine this with the plugin.
- With -Project and -WithRepoTools: also copies the check scripts (repo-tools/agent-checks)
  into <app>/tools/agent-checks, where the kit's agents and CI use them.

.EXAMPLE
.\scripts\install-pack.ps1

.EXAMPLE
.\scripts\install-pack.ps1 -Project C:\code\my-app -WithTeamSkills -DryRun
#>
[CmdletBinding()]
param(
    [string] $Project,

    [string[]] $Agents = @('claude', 'codex'),

    [switch] $WithTeamSkills,

    [switch] $WithRepoTools,

    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

if (($WithTeamSkills -or $WithRepoTools) -and -not $Project) {
    throw '-WithTeamSkills and -WithRepoTools need -Project <path to the app repository>.'
}

$pluginRoot = Split-Path -Parent $PSScriptRoot
$agentList = $Agents -join ','
$projectPath = if ($Project) { (Resolve-Path -LiteralPath $Project).Path } else { $null }

$officialSkills = Get-Content -LiteralPath (Join-Path $pluginRoot 'pack/official-skills.txt') |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith('#') }

$teamSkillDirs = Get-ChildItem -LiteralPath (Join-Path $pluginRoot 'skills') -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') }

$agentSkillFolders = @{
    'claude' = '.claude/skills'
    'codex'  = '.agents/skills'
}

function Invoke-Step([string] $Description, [scriptblock] $Action) {
    if ($DryRun) {
        Write-Host "[dry-run] $Description"
    } else {
        Write-Host $Description
        & $Action
    }
}

# 1. Official skills through Android CLI
if (-not $DryRun -and -not (Get-Command android -ErrorAction SilentlyContinue)) {
    throw @'
Android CLI is not installed or not on PATH. Install it from cmd.exe:
  curl -fsSL https://dl.google.com/android/cli/latest/windows_x86_64/install.cmd -o "%TEMP%\i.cmd" && "%TEMP%\i.cmd"
Then open a new terminal and run this script again.
'@
}

foreach ($skill in $officialSkills) {
    $arguments = @('skills', 'add', "--agent=$agentList")
    if ($projectPath) { $arguments += "--project=$projectPath" }
    $arguments += $skill
    Invoke-Step "android $($arguments -join ' ')" {
        & android @arguments
        if ($LASTEXITCODE -ne 0) { throw "android skills add failed for '$skill' (exit $LASTEXITCODE)" }
    }
}

# 2. Kit skills copied into the project's agent folders
if ($WithTeamSkills) {
    foreach ($agent in $Agents) {
        $relative = $agentSkillFolders[$agent]
        if (-not $relative) {
            Write-Warning "No skill folder known for agent '$agent'. Kit skills were not copied for it."
            continue
        }
        $target = Join-Path $projectPath $relative
        foreach ($dir in $teamSkillDirs) {
            $destination = Join-Path $target $dir.Name
            Invoke-Step "copy $($dir.Name) -> $destination" {
                New-Item -ItemType Directory -Force -Path $target | Out-Null
                if (Test-Path -LiteralPath $destination) {
                    Remove-Item -LiteralPath $destination -Recurse -Force
                }
                Copy-Item -LiteralPath $dir.FullName -Destination $destination -Recurse
                Copy-Item -LiteralPath (Join-Path $pluginRoot 'LICENSE') -Destination (Join-Path $destination 'LICENSE')
            }
        }
    }
}

# 3. Check scripts copied into the app repository
if ($WithRepoTools) {
    $toolsSource = Join-Path $pluginRoot 'repo-tools/agent-checks'
    $toolsTarget = Join-Path $projectPath 'tools/agent-checks'
    Invoke-Step "copy repo-tools/agent-checks -> $toolsTarget" {
        New-Item -ItemType Directory -Force -Path $toolsTarget | Out-Null
        Get-ChildItem -LiteralPath $toolsSource -File |
            Where-Object { $_.Extension -in '.py', '.md' } |
            Copy-Item -Destination $toolsTarget -Force
    }
}

$scope = if ($projectPath) { $projectPath } else { 'global (this machine)' }
Write-Host ''
Write-Host "Done. Official skills: $($officialSkills.Count), scope: $scope. Kit skills copied: $(if ($WithTeamSkills) { $teamSkillDirs.Count } else { 'no' }). Check scripts: $(if ($WithRepoTools) { 'tools/agent-checks' } else { 'no' })."
Write-Host "Update the official skills later with: android skills update --all --agent=$agentList$(if ($projectPath) { " --project=$projectPath" })"
