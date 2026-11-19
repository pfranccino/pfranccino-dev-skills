# Changelog

## 0.4.1 (unreleased)

Failing checks reach the diagnosis agents. In a real `develop` run, Claude diagnosed a dependency failure and a hung emulator in the main conversation instead of calling `build-doctor`, and a later review round raised again a finding the user had accepted in round 1.

- New hook, `hooks/failure_router.py`. When `gradle_summary.py` or `test_summary.py` reports a failure or a timeout in the main session, or a writing agent returns STATUS failed or blocked with a failing check, it adds a note for Claude that names `build-doctor` or `test-analyst` and the log. The note launches nothing: in `develop` the plan's Checks line approves those agents, and in `analyze` Claude proposes them. It also listens to `PostToolUseFailure`, because a shell command that exits with an error is a failed tool call in Claude Code and never reaches `PostToolUse`. Checks run in the background are not covered.
- `gradle_summary.py`: `--timeout <minutes>` stops the command and its child processes, and the summary says `status: "timeout"` (exit code 124). Connected tasks stop after 9 minutes by default, before a 10-minute shell call is cut; `--timeout 0` turns the limit off. On Linux and macOS the command runs in its own process group, so the timeout, or stopping the script, also stops what the command started. `next_step` and `raw_log_path` come near the top of the summary, so they survive when Claude Code cuts long output. A bare `./gradlew` that the working directory lacks is found in a parent folder, up to the repository root; an explicit wrapper path such as `./android/gradlew` runs as given, and on Windows it now runs the `gradlew.bat` at that path instead of the one in the working directory. Both summaries gain `next_step`: `test-analyst` when only test tasks failed, `build-doctor` for any other failure or a timeout, `null` when nothing failed. Their `schema_version` is 2. Apps that copied the scripts into `tools/agent-checks/` need to copy them again (`install-pack` with `--with-repo-tools`).
- `develop`: section 4 names environment failures (an emulator or device offline, an install or a connected test that hangs, a missing SDK or JDK) and says the main session sends a failure to its diagnosis agent before investigating it. The final report lists each failure, the agent that diagnosed it, and why none did when Claude diagnosed it alone.
- `analyze` proposes the diagnosis agent before investigating a failed check.
- The `CLAUDE.md` block has one more sentence: a check that fails or hangs goes first to `build-doctor` or `test-analyst`. Apps that pasted the block need to replace it.
- The descriptions of `build-doctor` and `test-analyst` say to use them proactively in `develop` and to propose them in `analyze`, and `build-doctor` covers device and adb problems during connected tests. Every agent that runs Gradle gives the shell call its longest timeout (600000 ms), and the writing agents copy `status`, `next_step` and `raw_log_path` into CHECKS for a failure they could not fix.
- Review rounds carry the findings the user accepted or deferred in every earlier round, so the reviewer does not raise them again as new. This covers `android-reviewer` and the external reviewer's prompt in `references/external-review.md`, whose later rounds also bring the decisions list up to date.
- Layer guard: the agents may pass `--timeout` to `gradle_summary.py`. A shell command that names `approved-plan.json` is still blocked, even when it only cites the file as text; the message now says to write such a file with the Write tool. A full path to `android.exe` was already accepted.
- README and GUIA: the agents start in the main session's working directory and cannot `cd`; restart Claude Code after installing Android CLI; connected tests on an API 37 emulator needed platform-tools 37 or newer.
- `install-pack` passes `claude-code` to Android CLI instead of `claude`, which Android CLI 1.1 rejects as an invalid agent. The `-Agents` / `--agents` value for Claude is now `claude-code`. The fix was merged after 0.4.0, and installed plugins receive it with this version.

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
