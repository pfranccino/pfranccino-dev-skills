# pfranccino-dev-skills

A marketplace of plugins for Claude Code and Codex for Android development.

## Plugins

| Plugin | What it does |
| :--- | :--- |
| [`android-feature-kit`](plugins/android-feature-kit/) | Skills to build an Android feature module layer by layer: Navigation Compose 2 graphs, MVI presentation with Compose, pure Kotlin domain, offline-first data, Room 3 and DataStore. Works together with a selection of Google's official Android skills; its README documents which skills are ours, which are official and which come from other authors. |

## Install

Claude Code:

```
/plugin marketplace add pfranccino/pfranccino-dev-skills
/plugin install android-feature-kit@pfranccino-dev-skills
```

Codex:

```
codex plugin marketplace add pfranccino/pfranccino-dev-skills
codex plugin add android-feature-kit@pfranccino-dev-skills
```

Each plugin's README covers its extra setup. `android-feature-kit` also needs the official Android skills, installed with Android CLI.

## Structure

```
pfranccino-dev-skills/
├── .claude-plugin/marketplace.json   Claude Code marketplace
├── .agents/plugins/marketplace.json  Codex marketplace
└── plugins/
    └── android-feature-kit/
        ├── .claude-plugin/plugin.json
        ├── .codex-plugin/plugin.json
        ├── skills/                    one folder per skill, each with its SKILL.md
        ├── pack/official-skills.txt   official Android skills that complement the kit
        ├── scripts/                   install-pack.ps1, install-pack.sh
        ├── README.md
        ├── CHANGELOG.md
        └── THIRD_PARTY_NOTICES.md
```

To add a plugin, create its folder under `plugins/` and register it in both marketplace files.

## Test changes locally

From a clone, before pushing:

```
claude plugin validate .
/plugin marketplace add ./                      (Claude Code, inside the clone)
codex plugin marketplace add .
```

To try a branch from GitHub before it is merged: `codex plugin marketplace add pfranccino/pfranccino-dev-skills@<branch>`.

## License

MIT, see [LICENSE](LICENSE). Each plugin lists its third-party material in its own `THIRD_PARTY_NOTICES.md`.
