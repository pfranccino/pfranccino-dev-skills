# Changelog

## 0.3.0 (unreleased)

- Two entry skills, both explicit only: `develop` orchestrates layer agents to build or change a feature (plan, questions, a brief when behavior changes, delegation, integration, checks, review), and `analyze` searches, explains, diagnoses and reviews without editing.
- Eight agents: `domain-builder`, `data-builder`, `ui-builder` and `feature-integrator` write; `build-doctor`, `test-analyst`, `android-reviewer` and `android-architect` are read-only. Each layer agent preloads its own skill. `data-builder` runs on Haiku by default and on Sonnet for migrations, sync or refresh policy, conflict resolution or encryption.
- A PreToolUse guardrail (`hooks/claude-hooks.json`, `layer_guard.py`) keeps the kit's agents inside their layer and the task's modules (`build/android-feature-kit/scope.json`, written by `develop`), and blocks the usual ways to write files through the shell. Layer patterns can be replaced per project in `.claude/android-feature-kit.json`. It is not a sandbox: Gradle runs the project's build logic.
- `repo-tools/agent-checks`: `gradle_summary.py` and `test_summary.py` summarize Gradle output and JUnit reports as JSON. `install-pack` copies them into an app with `--with-repo-tools` / `-WithRepoTools`.
- Every layer skill has `references/rules.md` with stable rule IDs and the kit-wide `KIT-01` to `KIT-07`; the closing checklists cite them.
- Sections used only in specific cases moved to `references/`: navigation migration and custom `NavType`, Room schema and migrations, DataStore encryption.
- `data-repository`: when it runs only on the data layer, a missing domain interface is requested from domain instead of written.
- Codex review in `develop` uses a JSON schema with finding IDs, owners and the reviewed change's identity (`review_target.py`), and resumes the same Codex session for later rounds.
- `analyze` works without the agents too, doing their read-only work in the session.

## 0.2.0 — 2026-11-16

- `feature-ui-compose`: ViewModels no longer start work in `init`. The stateful screen sends `UiAction.OnStart` from `LaunchedEffect(viewModel)`, and the ViewModel runs it once. If the project's MVI delegate or screens already start the first load another way that runs no work at construction, that way is used instead. The example, the offline-first rule, the tests and the final checklist follow the new pattern.
- `feature-ui-compose`: `UiAction` names use the present tense with an `On` prefix, like Compose callbacks (`OnStart`, `OnRetryClick`, `OnCancelClick`, `OnAmountChange`).

## 0.1.0 — 2026-11-15

First release.

- Skills: `feature-navigation-compose`, `feature-ui-compose`, `domain-layer`, `data-repository`, `data-room`, `data-datastore`.
- `pack/official-skills.txt` with the nine official Android skills that complement the kit.
- `scripts/install-pack.ps1` and `scripts/install-pack.sh`: install the official skills globally or into an app, and optionally copy the kit's skills into an app.
- Reviewed in three rounds between Claude and Codex; 20 findings resolved.
- Documentation of origin for every skill: kit, official Android skills and other authors, with licenses and notices.
