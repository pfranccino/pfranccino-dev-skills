# pfranccino-dev-skills

Collection of Claude skills — software analysis and architecture tools.

## Available skills

| Skill | What it does |
|---|---|
| [`android-gradle-health`](skills/android-gradle-health/) | Analyzes and improves architectural health of Android multi-module projects with [android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer): cycles, SDP violations, Ca/Ce/I metrics, health score, and misplaced shared logic. Runs the CLIs, captures JSON output, and turns it into actionable diagnostics with remediation steps. |

## Structure

```
pfranccino-dev-skills/
├── README.md
└── skills/
    └── android-gradle-health/
        ├── SKILL.md          # entry point: description, command map, JSON schemas, workflow
        ├── references/       # on-demand guides (fix-cycles, fix-sdp, thresholds, etc.)
        └── examples/         # ready-to-copy configs by project size
```

Each skill lives in `skills/<name>/` with its `SKILL.md` as the entry point.

## Usage

To use a skill in Claude Code, copy its folder to the skills directory:

```bash
# Personal (all your sessions)
cp -r skills/android-gradle-health ~/.claude/skills/

# Per project
cp -r skills/android-gradle-health <your-project>/.claude/skills/
```

Claude will activate it automatically when the context matches its `description`.

## License

MIT
