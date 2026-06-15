# android-gradle-health

Claude Code plugin that wraps [android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer)
and turns its output into actionable diagnostics with concrete remediation steps.

## What it does

Analyzes the architectural health of Android multi-module Gradle projects:

- Detects dependency cycles (−20 pts each)
- Flags SDP violations (−10 pts)
- Reports misused `api` vs `implementation` scopes (−5 pts)
- Measures Ca / Ce / I metrics per module
- Identifies shared logic placed in the wrong layer
- Generates an overall health score (0–100)

## Prerequisites

- [pipx](https://pipx.pypa.io) in PATH

The skill works in two modes:

| Mode | When to use | Setup |
|---|---|---|
| Permanent install | Frequent use on your own machine | `pipx install android-gradle-analyzer` |
| Temporal (no install) | CI, shared envs, one-off runs | None — `pipx run --spec` handles it |

See the [Prerequisite section in SKILL.md](SKILL.md#prerequisito-verificar-instalación) for details.

## Installation

### As a skills-directory plugin (personal, all sessions)

```bash
cp -r android-gradle-health ~/.claude/skills/
```

Claude Code picks it up on the next session as `android-gradle-health@skills-dir`.
Invoke the skill manually with `/android-gradle-health:android-gradle-health`
or let Claude activate it automatically when the context matches.

### As a project plugin (shared with your team)

```bash
cp -r android-gradle-health <your-android-project>/.claude/skills/
```

Commit the `.claude/` directory so teammates get the plugin when they clone.

### Via CLI

```bash
claude plugin init android-gradle-health
```

## Skill invocation

| Trigger | Command |
|---|---|
| Manual slash command | `/android-gradle-health:android-gradle-health` |
| Auto (by Claude) | When Gradle, cycles, SDP, Ca/Ce/I, or health score is mentioned |

## Key commands the skill runs

```bash
gradle-sanity  <path> --json              # full health report
gradle-analyzer <path> --format mermaid   # dependency graph
gradle-impact  <project> <module>         # change impact
gradle-externals <project> <module>       # reverse dependencies
```

## Plugin structure

```
android-gradle-health/
├── .claude-plugin/
│   └── plugin.json       # plugin manifest
├── SKILL.md              # skill definition and workflow
├── references/           # on-demand guides (cycles, SDP, scopes, …)
├── examples/             # ready-to-copy configs by project size
├── README.md             # this file
└── CHANGELOG.md          # version history
```

## License

MIT
