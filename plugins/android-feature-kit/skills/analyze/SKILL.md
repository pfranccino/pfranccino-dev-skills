---
name: analyze
description: "Answers questions about an Android project built with android-feature-kit without changing its source: find where something is defined or used, explain a module, feature or flow, check a module against the layer rules, diagnose a failing Gradle build or failing tests, review a diff or branch against the team rules, check dependencies, or work through an architecture question. Use it when the user asks about the code, a failure or a change, even in plain words and without naming the kit. Also for requests in Spanish such as explicar un módulo, por qué falla el build, por qué fallan los tests, revisar un diff, dónde se usa, cómo funciona este flujo."
argument-hint: "[question]"
---

# Analyze

Answers questions about an Android project without changing its source. You propose how you will answer, the user approves it in the conversation, and nothing runs beyond what they approved.

Question from the invocation: $ARGUMENTS

## Start

If the line above holds a question, answer that one. If it is empty or shows a placeholder, ask and wait for the answer before anything else: when the conversation already states a question, ask whether that is the one to answer; otherwise ask what the user wants to know.

Read `.claude/android-feature-kit.md` in the repository, if it exists. Its exploration approved in advance is what you may do without asking: usually reading files, searching, and read-only git. When the file is missing, propose the defaults from `${CLAUDE_SKILL_DIR}/../develop/references/project-rules.md` once in this session and wait for the answer.

Anything beyond those limits is proposed first, in one short message: which agent or tool, on which model, what it runs, and what it writes. Gradle builds, test runs, module maps and codegraph indexes write their own output (build folders, `docs/architecture/`, `.codegraph/`) even though they do not change source files, so they are always proposed. Wait for the user's answer before running them.

## Route the question

| The user wants | Propose |
| :--- | :--- |
| To find something (where X is defined, what uses Y, which screens call Z) | Search in this session with Grep and Glob. If the project has a codegraph index (`.codegraph/`) and `codegraph` is installed, offer it for callers and references. For a broad sweep across many modules, offer the built-in Explore agent and keep only its conclusion. |
| To understand a module, a feature or a flow | If the `module-map` skill is available, offer to run it on the module and explain from the generated document (layers, flows from the ViewModels, Hilt graph, layer violations, edges to review); do not redraw its diagrams. Otherwise read the module's entry points (graph, screens, ViewModels, use cases, repositories) and explain from them. Explanations stay in this session. |
| Whether a module follows the layer rules | If the user's android-module-map is installed with its `module_check.py`, offer to run it with `--generate --json` (it writes nothing into the project) and report what it found, including what it could not check. Otherwise read the rules files of the layers involved and the module's imports. |
| To know why the build fails | `android-feature-kit:build-doctor` (haiku), with the failing command or its check summary. It runs Gradle. |
| To know why tests fail | `android-feature-kit:test-analyst` (haiku), with the module path. It may run the tests. |
| A review of a diff or branch | `android-feature-kit:android-reviewer` (sonnet). If `.claude/android-feature-kit.json` configures an external reviewer, offer it too, with the prompt and schema in the develop skill's `references/` folder (`${CLAUDE_SKILL_DIR}/../develop/references/external-review.md`). The user picks. |
| An architecture decision, or a problem that spans layers or modules | `android-feature-kit:android-architect` (opus), with the evidence gathered so far. |
| The state of dependencies | `toml-deps-checker` and then `deps-changelog-diff` when they are installed; read their JSON, not the full output. They use the network. |
| An audit (ANRs, Compose performance, R8, intents, permissions, edge-to-edge) | The matching official Android skill when it is installed (`anr-audit-and-fix`, `jetpack-compose-performance`, `r8-analyzer`, `android-intent-security`, `android-permissions-security`, `edge-to-edge`). |

The team rules, with IDs, are in each layer skill's `references/rules.md` (`${CLAUDE_SKILL_DIR}/../<skill>/references/rules.md`). When an answer depends on whether code follows them, read only the rules file for that layer and cite the IDs.

## Without the kit's agents

When the agents are not available (the kit's skills were copied into the repository without the plugin), propose doing their work in this session, without changing source files:

- Build failures: run the failing command through `gradle_summary.py` (in `tools/agent-checks/` of the repository, or `repo-tools/agent-checks/` of the plugin) and read only its JSON. Open the files at the reported lines, classify each cause (layer code, dependency, KSP, resource, Gradle configuration, environment), and give the smallest fix with its owner layer.
- Failing tests: run `test_summary.py --module <module path>`, read each failing test and the code it exercises, and say whether the code, the test, timing or the environment is wrong. When the test and the brief disagree about expected behavior, ask the user.
- Reviews: read the change (`git diff HEAD` plus untracked files for the working tree, or the range's diff) and only the rules files of the layers it touches, and report findings with rule IDs.
- Architecture questions: read the code involved and the rules files, keep the team decisions fixed (one module per feature with layer packages, pure Kotlin domain, the project's `Either`, MVI by delegation, offline-first, Hilt, Navigation Compose 2), and give options with their cost and a recommendation.

## Answer

- Lead with the answer, then the evidence as `file:line`.
- Separate what the code shows from what you infer.
- Say what you could not check (a build you could not run, a module you did not read).
- If the answer reveals a defect, describe the fix and its owner layer. When the user wants it fixed, that is a development task: plan it with the develop skill, which asks for approval in Plan Mode.
