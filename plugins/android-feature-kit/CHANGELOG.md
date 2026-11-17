# Changelog

## 0.4.0 (unreleased)

How the kit is triggered and who decides changed. The main conversation coordinates the agents, and nothing writes code before you approve the plan.

- `develop` and `analyze` load from plain requests ("add a cancel button to the order detail, with its endpoint"), not only from their commands. `/android-feature-kit:develop` and `/android-feature-kit:analyze` stay as shortcuts. Called with no task, they ask what you want and wait.
- `develop` proposes a plan in Plan Mode (goal, modules, decisions, brief, an `Agents:` line with the model for each agent, integration, checks, reviewer and round cap) and launches no writing agent until you approve it. A decision that appears later (a contract change the plan did not include, a new dependency or version, a tier change, an escalation, another review round) is asked before it is applied. A small change in one layer is proposed without agents.
- `analyze` proposes how it will answer, in the conversation, and asks before builds, test runs, module maps, codegraph indexes or the network.
- Two files for the app repository, both optional: `skills/develop/references/claude-md-block.md`, a one-paragraph block for `CLAUDE.md` with the routing and the rule that code changes start only after you approve the plan; and `skills/develop/references/project-rules.md`, copied to `.claude/android-feature-kit.md`, with the exploration approved in advance and the routine choices that are never questions. The skills read the rules file only when they run. Without it, they propose its defaults once per session.
- The four writing agents now say they run on a plan you approved, and stop on any choice outside the routine list, technical or product.
- Reviewer: `android-reviewer` by default. An external reviewer is any command-line tool configured in `.claude/android-feature-kit.json` that reads the prompt on standard input and returns JSON that follows `review.schema.json`. `references/run_review.py` runs it and checks the answer and the target identity. You pick the reviewer and the round cap in the plan; having a tool installed no longer selects it. Codex works through this configuration. The rules version in a review's identity now comes from `skills/develop/references/VERSION`, so it also works with the skills copied into a repository.
- Optional plan gate (`hooks/plan_gate.py`, off by default, `"planGate": true` in `.claude/android-feature-kit.json`): when you approve a plan in Plan Mode it records the agents and models on the plan's `Agents:` line, as approved and with your edits, and it blocks writing agents the plan does not list or that would run on another model. The layer guard blocks writes to that record. Unit-tested; not yet tested in a live session.
- One kit run per checkout: `scope.json` now carries the session id. While it belongs to another session, no writing agent can start and no session can replace the file; you release a stale one by deleting it. The kit's agents never write in `build/android-feature-kit/`. `develop` deletes its own scope when it reports.
- `GUIA.md`: a step-by-step guide in Spanish to install the kit in an app and use it, with examples. `GUIA.html` is the same guide as a page, with the agent types and the flow, published at https://pfranccino.github.io/pfranccino-dev-skills/ by the repository's `.github/workflows/pages.yml` on every change to it in `main`.
- The plugin is for Claude Code only: the Codex plugin manifest, the Codex marketplace file and the skills' `agents/openai.yaml` were removed.
- `install-pack` passes `claude-code` to Android CLI instead of `claude`, which Android CLI 1.1 rejects as an invalid agent. The `-Agents` / `--agents` value for Claude is now `claude-code`.

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
