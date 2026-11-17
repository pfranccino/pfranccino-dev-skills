---
name: analyze
description: "Read-only entry point of android-feature-kit for an Android project: search the code, explain a module or flow, diagnose a failing build or failing tests, review a diff against the team rules, or escalate an architecture question. Edits nothing. Runs only when the user invokes it."
disable-model-invocation: true
---

# Analyze

Answers questions about an Android project without changing it. Nothing in this flow edits source files. Builds, indexes and reports may write their own output (build folders, `docs/architecture/`), but only through the tools named below. When the user wants something changed, end with what to change and suggest `/android-feature-kit:develop`.

No spec or brief is needed. Start from the user's question.

## Route the question

| The user wants | Do |
| :--- | :--- |
| To find something (where X is defined, what uses Y, which screens call Z) | Search in this session with Grep and Glob. If the project has a codegraph index (`.codegraph/`) and `codegraph` is installed, use it for callers and references. For a broad sweep across many modules, use the built-in Explore agent and keep only its conclusion. |
| To understand a module, a feature or a flow | If the `module-map` skill is available, run it on the module and explain from the generated document (layers, flows from the ViewModels, Hilt graph, layer violations, edges to review); do not redraw its diagrams. Otherwise read the module's entry points (graph, screens, ViewModels, use cases, repositories) and explain from them. Stay in this session: explanations are a conversation. |
| Whether a module follows the layer rules | If the user's android-module-map is installed with its `module_check.py`, run it with `--generate --json` (it writes nothing into the project) and report what it found, including what it could not check. Otherwise read the rules files of the layers involved and the module's imports. |
| To know why the build fails | `android-feature-kit:build-doctor`, with the failing command or its check summary. |
| To know why tests fail | `android-feature-kit:test-analyst`, with the module path. |
| A review of a diff or branch | Codex when `codex` is on the PATH, with the review prompt and schema in the develop skill's `references/` folder (`${CLAUDE_PLUGIN_ROOT}/skills/develop/references/` in Claude Code); otherwise `android-feature-kit:android-reviewer`. |
| An architecture decision, or a problem that spans layers or modules | `android-feature-kit:android-architect`, with the evidence gathered so far. |
| The state of dependencies | `toml-deps-checker` and then `deps-changelog-diff` when they are installed; read their JSON, not the full output. |
| An audit (ANRs, Compose performance, R8, intents, permissions, edge-to-edge) | The matching official Android skill when it is installed (`anr-audit-and-fix`, `jetpack-compose-performance`, `r8-analyzer`, `android-intent-security`, `android-permissions-security`, `edge-to-edge`). |

The team rules, with IDs, are in each layer skill's `references/rules.md` (`${CLAUDE_PLUGIN_ROOT}/skills/<skill>/references/rules.md` in Claude Code). When an answer depends on whether code follows them, read only the rules file for that layer and cite the IDs.

## Without the kit's agents

When the agents are not available (for example in Codex, where plugins do not ship agents), do their work in this session, read-only:

- Build failures: run the failing command through `gradle_summary.py` (in `tools/agent-checks/` of the repository, or `repo-tools/agent-checks/` of the plugin) and read only its JSON. Open the files at the reported lines, classify each cause (layer code, dependency, KSP, resource, Gradle configuration, environment), and give the smallest fix with its owner layer.
- Failing tests: run `test_summary.py --module <module path>`, read each failing test and the code it exercises, and say whether the code, the test, timing or the environment is wrong. When the test and the brief disagree about expected behavior, ask the user.
- Reviews: read the change (`git diff HEAD` plus untracked files for the working tree, or the range's diff) and only the rules files of the layers it touches, and report findings with rule IDs.
- Architecture questions: read the code involved and the rules files, keep the team decisions fixed (one module per feature with layer packages, pure Kotlin domain, the project's `Either`, MVI by delegation, offline-first, Hilt, Navigation Compose 2), and give options with their cost and a recommendation.

## Answer

- Lead with the answer, then the evidence as `file:line`.
- Separate what the code shows from what you infer.
- Say what you could not check (a build you could not run, a module you did not read).
- If the answer reveals a defect, describe the fix and its owner layer, and suggest `/android-feature-kit:develop` to apply it.
