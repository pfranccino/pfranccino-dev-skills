# pfranccino-dev-skills

Collection of Claude Code plugins — software analysis and architecture tools.

## Available plugins

| Plugin | What it does |
|---|---|
| [`android-gradle-health`](skills/android-gradle-health/) | Analyzes and shows the architectural health of Android multi-module projects with [android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer): dependency graph, cycles, SDP violations, Ca/Ce/I metrics, health score, and misplaced shared logic. Runs the CLIs, captures JSON output, and presents the findings as a clear diagnosis. |

## Structure

Each plugin follows the official Claude Code plugin structure:

```
pfranccino-dev-skills/
└── skills/
    └── android-gradle-health/
        ├── .claude-plugin/
        │   └── plugin.json       # plugin manifest (name, version, author)
        ├── SKILL.md              # entry point: description, commands, JSON schemas, workflow
        ├── references/           # on-demand guides (fix-cycles, fix-sdp, thresholds, etc.)
        ├── examples/             # ready-to-copy configs by project size
        ├── README.md             # plugin documentation
        └── CHANGELOG.md          # version history
```

## Installation

### Personal (all your sessions)

```bash
cp -r skills/android-gradle-health ~/.claude/skills/
```

The plugin loads automatically as `android-gradle-health@skills-dir` on the next session.
Claude activates it when the context matches its `description`, or invoke it manually
with `/android-gradle-health:android-gradle-health`.

### Per project (shared with your team)

```bash
cp -r skills/android-gradle-health <your-project>/.claude/skills/
```

Commit the `.claude/` directory so teammates get the plugin when they clone.

### Via CLI

```bash
claude plugin init android-gradle-health
```

## License

MIT
