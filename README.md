# pfranccino-dev-skills

A marketplace of Claude Code plugins for Android development.

## Plugins

| Plugin | What it does |
| :--- | :--- |
| [`android-feature-kit`](plugins/android-feature-kit/) | Skills to build an Android feature module layer by layer: Navigation Compose 2 graphs, MVI presentation with Compose, pure Kotlin domain, offline-first data, Room 3 and DataStore. On top of them, layer agents that the main conversation coordinates after you approve the plan (`develop`), an analysis flow that does not change source (`analyze`), guardrail hooks and Gradle check scripts. Both flows load from plain requests; `/android-feature-kit:develop` and `/android-feature-kit:analyze` are shortcuts. Works together with a selection of Google's official Android skills; its README documents which skills are ours, which are official and which come from other authors. |

## Install

In Claude Code:

```
/plugin marketplace add pfranccino/pfranccino-dev-skills
/plugin install android-feature-kit@pfranccino-dev-skills
```

Each plugin's README covers its extra setup. `android-feature-kit` also needs the official Android skills, installed with Android CLI.

## Structure

```
pfranccino-dev-skills/
├── .claude-plugin/marketplace.json   Claude Code marketplace
└── plugins/
    └── android-feature-kit/
        ├── .claude-plugin/plugin.json
        ├── skills/                    one folder per skill, each with its SKILL.md and references/
        ├── agents/                    the layer and analysis agents
        ├── hooks/                     the layer guard, the plan gate and their tests
        ├── repo-tools/agent-checks/   Gradle and test summary scripts, copied into an app repository
        ├── pack/official-skills.txt   official Android skills that complement the kit
        ├── scripts/                   install-pack.ps1, install-pack.sh
        ├── README.md
        ├── CHANGELOG.md
        └── THIRD_PARTY_NOTICES.md
```

To add a plugin, create its folder under `plugins/` and register it in `.claude-plugin/marketplace.json`.

## Test changes locally

From a clone, before pushing:

```
claude plugin validate .
/plugin marketplace add ./                      (inside Claude Code, in the clone)
```

## License

MIT, see [LICENSE](LICENSE). Each plugin lists its third-party material in its own `THIRD_PARTY_NOTICES.md`.
