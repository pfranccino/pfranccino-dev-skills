# Android Feature Kit

Agent skills for Claude Code and Codex to build an Android feature module layer by layer: navigation, presentation, domain, data, Room and DataStore.

The kit works together with a selection of Google's official Android skills. This document says where every skill comes from:

1. [Skills in this kit](#1-skills-in-this-kit): bundled in this plugin.
2. [Official Android skills](#2-official-android-skills): from Google, installed with Android CLI, not bundled.
3. [Work from other authors](#3-work-from-other-authors): what was adapted, what informed an idea, what is a candidate and what was not adopted.

## 1. Skills in this kit

| Skill | Use it for |
| :--- | :--- |
| [`feature-navigation-compose`](skills/feature-navigation-compose/SKILL.md) | Feature graphs, routes, exit callbacks, results and back handling with Navigation Compose 2 type-safe routes; migrating a module to that pattern |
| [`feature-ui-compose`](skills/feature-ui-compose/SKILL.md) | Screen contracts (UiState, UiAction, SideEffect), MVI ViewModels by interface delegation, stateful and stateless Compose screens, previews |
| [`domain-layer`](skills/domain-layer/SKILL.md) | Pure Kotlin use cases, business rules, domain models, repository interfaces and domain errors with the project's own `Either` |
| [`data-repository`](skills/data-repository/SKILL.md) | Offline-first repositories, remote data sources, DTOs, mappers, error mapping, sync rules, Hilt bindings |
| [`data-room`](skills/data-room/SKILL.md) | Room 3 (and Room 2) entities, DAOs, transactions, schema export, migrations and migration tests |
| [`data-datastore`](skills/data-datastore/SKILL.md) | Preferences and typed DataStore, the DataStore 1.3 builder, corruption policy, encryption with `datastore-tink` |

### Conventions the skills assume

These are fixed decisions; the skills do not discuss them:

- Each feature is one Gradle module, and its layers are packages inside it (`presentation`, `domain`, `data`).
- The domain package depends on nothing in data or presentation and on nothing Android.
- The project has its own `Either` type, used from the network layer up.
- MVI by interface delegation: the ViewModel implements the MVI contract `by mvi(initialState)`, and a `CollectSideEffect` composable collects side effects.
- ViewModels talk to use cases only.
- Offline-first data, Hilt, and Navigation Compose 2 (not Navigation 3).

The skills read the project for the concrete names (the `Either` API, the MVI delegate, the network helper, the design system) instead of inventing them.

### Where each skill comes from

| Skill | Origin | Built from |
| :--- | :--- | :--- |
| `feature-navigation-compose` | Original team pattern by pfranccino | Checked against the official guides on [type-safe navigation](https://developer.android.com/guide/navigation/design/type-safety), [multi-module navigation](https://developer.android.com/guide/navigation/integrations/multi-module), [navigation testing](https://developer.android.com/guide/navigation/testing/compose) and the [`SavedStateHandle` reference](https://developer.android.com/reference/kotlin/androidx/lifecycle/SavedStateHandle) |
| `feature-ui-compose` | Written for this kit | [UI layer](https://developer.android.com/topic/architecture/ui-layer), [UI events](https://developer.android.com/topic/architecture/ui-layer/events) and [Hilt release notes](https://developer.android.com/jetpack/androidx/releases/hilt) (`hiltViewModel` package). Points to the official `jetpack-compose-performance` skill for stability rules instead of repeating them |
| `domain-layer` | Written for this kit | [Domain layer](https://developer.android.com/topic/architecture/domain-layer) guide |
| `data-repository` | Written for this kit | [Data layer](https://developer.android.com/topic/architecture/data-layer) and [offline-first](https://developer.android.com/topic/architecture/data-layer/offline-first) guides. Independently written; the idea of the repository as the boundary where technical errors become domain errors was informed by the `android-data-layer` skill in [rcosteira79/android-skills](https://github.com/rcosteira79/android-skills) |
| `data-room` | Written for this kit | [Room guide](https://developer.android.com/training/data-storage/room), [migrations](https://developer.android.com/training/data-storage/room/migrating-db-versions), [Room 3 release notes](https://developer.android.com/jetpack/androidx/releases/room3) and the Room 3 API reference (`Migration`, `MigrationTestHelper`, `RoomDatabase.Builder`, `useReaderConnection`) |
| `data-datastore` | Adapted | Storage choice, read errors, corruption handling, serializer structure and the single-instance rule are adapted from the `datastore` skill in [rcosteira79/android-skills](https://github.com/rcosteira79/android-skills), which is itself adapted from [Meet-Miyani/compose-skill](https://github.com/Meet-Miyani/compose-skill). Both MIT; notices in [`NOTICE.md`](skills/data-datastore/NOTICE.md). Extended with the [DataStore guide](https://developer.android.com/topic/libraries/architecture/datastore), the [DataStore 1.3 release notes](https://developer.android.com/jetpack/androidx/releases/datastore) and the `DataStore.Builder`, `FileStorage` and `AeadSerializer` references |

### How they were reviewed

Claude wrote and Codex reviewed, in three rounds of debate with web search against the official documentation. Codex raised 20 findings; all were resolved before release. Examples of what changed:

- Results returned through `SavedStateHandle` are cleared with `savedStateHandle[KEY] = null`, because `remove` detaches the flow and the next result never arrives.
- Room 3.0.3 is the minimum version, and `useReaderConnection` works with a `Transactor`, not a `SQLiteConnection`.
- Refreshes and mutations of the same resource share a lock, so a slow refresh cannot overwrite a newer change.
- Encrypted DataStore files are excluded from backup, because the Keystore key does not travel with the backup.

## 2. Official Android skills

From [github.com/android/skills](https://github.com/android/skills) (Apache-2.0), maintained by Google and updated often. They are **not bundled** in this plugin: they are installed with [Android CLI](https://developer.android.com/tools/agents/android-cli), so `android skills update` keeps them current. The list lives in [`pack/official-skills.txt`](pack/official-skills.txt).

| Skill | Use it for |
| :--- | :--- |
| `android-cli` | Using Android CLI: SDK, emulators, running the app, UI inspection, Compose preview rendering, docs search |
| `testing-setup` | Testing strategy and setup: unit, UI, screenshot and end-to-end harnesses |
| `jetpack-compose-performance` | Diagnosing recomposition, stability, lazy layouts and rendering performance |
| `edge-to-edge` | System bars, insets and IME handling for edge-to-edge UI |
| `android-intent-security` | Securing intents, exported components and pending intents |
| `android-permissions-security` | Runtime permissions and permission-related risks |
| `anr-audit-and-fix` | Finding and fixing ANRs |
| `android-profiler` | Recording and analyzing Perfetto traces and heap dumps |
| `r8-analyzer` | Auditing R8 configuration and keep rules |

Install `agp-9-upgrade` only when the project upgrades the Android Gradle Plugin.

Not recommended with this kit:

- `navigation-3` and `adaptive`: they move the app to Navigation 3, and this kit uses Navigation 2.
- `migrate-xml-views-to-jetpack-compose` and `ios-to-android`: for migrating legacy code.
- Device-specific skills (Wear OS, TV, XR, cars, camera, widgets): only if the app targets them.
- The official `android-skills` plugin for Claude Code or Codex: it installs all of Google's skills at once, including the two above.

## 3. Work from other authors

### Adapted into this kit

| Source | Author | License | Used in |
| :--- | :--- | :--- | :--- |
| [`datastore` skill](https://github.com/rcosteira79/android-skills/blob/fa39ae26f224/plugins/android-skills/skills/datastore/SKILL.md) | Ricardo Costeira | MIT | `data-datastore` |
| [compose-skill](https://github.com/Meet-Miyani/compose-skill/tree/5841d1e146d2), through the `datastore` skill above | Meet Miyani | MIT | `data-datastore` |

Their notices travel with the skill in [`skills/data-datastore/NOTICE.md`](skills/data-datastore/NOTICE.md) and are repeated in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

### Informed an idea, no text copied

| Source | Author | Idea |
| :--- | :--- | :--- |
| [`android-data-layer` skill](https://github.com/rcosteira79/android-skills) | Ricardo Costeira | The repository is where technical errors become domain errors (`data-repository`) |

### Candidates, not installed

| Source | Author | License | When to consider it |
| :--- | :--- | :--- | :--- |
| [android-testing-skills](https://github.com/skydoves/android-testing-skills) | Jaewoong Eum (skydoves) | Apache-2.0 | When the team writes Compose UI tests and adb-based checks |
| [compose-rules](https://github.com/mrmans0n/compose-rules) | Nacho Lopez | Apache-2.0 | Lint rules for ktlint or detekt; not a skill, but enforces Compose conventions on every build |

### Evaluated and not adopted

These are team-fit decisions, not defects in those projects.

| Source | Author | License | Why not |
| :--- | :--- | :--- | :--- |
| [android-agent-skills](https://github.com/piyushverma0/android-agent-skills) | Piyush Verma | MIT | Its Room skill covers Room 2 only (no Room 3) and wraps DAO calls in `withContext(Dispatchers.IO)`, which Room's `suspend` functions make unnecessary |
| [Skills](https://github.com/PL-Coding-GmbH/Skills) | PL Coding GmbH (Philipp Lackner) | MIT | Built on Koin and Ktor, and names navigation callbacks by destination (`onNavigateToEditor`), which this kit forbids |
| [compose-performance-skills](https://github.com/skydoves/compose-performance-skills) | Jaewoong Eum (skydoves) | Apache-2.0 | Overlaps the official `jetpack-compose-performance` skill |
| [compose-skill](https://github.com/Meet-Miyani/compose-skill) | Meet Miyani | MIT | Oriented to Compose Multiplatform. Its eval suite is a good model for evaluating this kit later |
| [compose-skill](https://github.com/aldefy/compose-skill) | Adit Lal | MIT, with Apache-2.0 material from AOSP | One large skill with many references; useful to read, too broad to install |
| [awesome-android-agent-skills](https://github.com/new-silvermoon/awesome-android-agent-skills) | Sagar Das | Apache-2.0 | General-purpose skills (its data layer skill has 51 lines) that do not follow this kit's conventions |

## Install

### 1. The plugin (once per developer, for all projects)

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

### 2. The official skills (once per machine)

Install [Android CLI](https://developer.android.com/tools/agents/android-cli) and open a new terminal:

| System | Command |
| :--- | :--- |
| Windows (`cmd.exe`) | `curl -fsSL https://dl.google.com/android/cli/latest/windows_x86_64/install.cmd -o "%TEMP%\i.cmd" && "%TEMP%\i.cmd"` |
| macOS, Apple silicon | `curl -fsSL https://dl.google.com/android/cli/latest/darwin_arm64/install.sh \| bash` |
| macOS, Intel | `curl -fsSL https://dl.google.com/android/cli/latest/darwin_x86_64/install.sh \| bash` |
| Linux x86-64 | `curl -fsSL https://dl.google.com/android/cli/latest/linux_x86_64/install.sh \| bash` |

Then clone this repository and run the script from its root:

```powershell
# Windows
.\plugins\android-feature-kit\scripts\install-pack.ps1
```

```bash
# macOS or Linux
bash plugins/android-feature-kit/scripts/install-pack.sh
```

Without a project path, the script installs the official skills globally for Claude Code and Codex. It runs `android skills add --agent=claude,codex <id>` for each skill in [`pack/official-skills.txt`](pack/official-skills.txt), so you can also run those commands by hand.

### Alternative: everything inside an app repository

Use this when the skills must travel with the app repository, for example for CI agents or teammates who do not install the plugin:

```powershell
# Windows
.\plugins\android-feature-kit\scripts\install-pack.ps1 -Project C:\code\my-app -WithTeamSkills
```

```bash
# macOS or Linux
bash plugins/android-feature-kit/scripts/install-pack.sh --project ~/code/my-app --with-team-skills
```

This installs the official skills into the app and copies the kit's skills into `<app>/.claude/skills/` and `<app>/.agents/skills/`. Commit the result. Do not combine it with the plugin in the same project, or the agent sees every kit skill twice.

Every option has a dry run: `-DryRun` / `--dry-run`.

## Update

- Kit skills: `/plugin marketplace update pfranccino-dev-skills` in Claude Code, `codex plugin marketplace upgrade` in Codex. If you copied them into an app, run the script again.
- Official skills: `android skills update --all --agent=claude,codex`. Add `--project=<app>` if you installed them into an app.

## Changing a skill

- Kit skills: keep the folder name equal to the `name` in the frontmatter, record the change in [CHANGELOG.md](CHANGELOG.md), and bump `version` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.
- Official skills: do not edit them in place, because `android skills update` overwrites them. Copy the skill, rename it, and add it to `skills/` as a kit skill with its origin documented above.

## License

MIT, see [LICENSE](LICENSE). Third-party material and its licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
