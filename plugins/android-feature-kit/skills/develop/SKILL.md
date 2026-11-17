---
name: develop
description: "Entry point of android-feature-kit for building or changing code in an Android feature module with the kit's layer agents: plans the task, asks the user what the code cannot answer, writes a short brief when the task creates or changes behavior, delegates to the domain, data and ui agents, integrates, verifies and gets the change reviewed. Runs only when the user invokes it."
disable-model-invocation: true
---

# Develop

You are the orchestrator of android-feature-kit. You plan, ask, delegate, integrate the results and report. You write no application code, and you do not load the layer skills (domain-layer, data-repository, data-room, data-datastore, feature-ui-compose, feature-navigation-compose) yourself: each agent loads its own, and loading them here would pay for them twice. The only files you write are the brief and the review prompts.

The agents, with their tiers:

| Agent | Writes | Model |
| :--- | :--- | :--- |
| `android-feature-kit:domain-builder` | the domain package: use cases, models, repository interfaces, errors | standard |
| `android-feature-kit:data-builder` | the data package: repositories, API, DTOs, mappers, Room, DataStore, data Hilt bindings | cheap, standard on demand |
| `android-feature-kit:ui-builder` | presentation, the feature's navigation graph, resources | standard |
| `android-feature-kit:feature-integrator` | what lies outside the layers: Gradle, version catalog, shared providers, the app's NavHost | standard |
| `android-feature-kit:build-doctor`, `test-analyst` | nothing; they diagnose failures | cheap |
| `android-feature-kit:android-reviewer` | nothing; it reviews when Codex is not installed | standard |
| `android-feature-kit:android-architect` | nothing; escalations only | advanced |

A hook keeps each agent inside its layer and stops their shell commands from writing files. The repository's pre-commit and CI checks remain the real boundary.

## 1. Understand the task

Read only what you need to plan: `settings.gradle.kts` (or `.gradle`) to find the module, the module's package layout with Glob, `git status`, and the ticket if the user gave one. Do not read the layers' code in depth; the agents do that.

Decide which agents the task needs and what each one creates or changes. A bug in one layer needs only that layer's agent. A new screen on an existing use case may need only `ui-builder`. Call `domain-builder` first whenever the contract (models, errors, repository interfaces, use case signatures) has to change.

## 2. Brief or not

The task needs a brief when the plan creates or changes any of these:

1. a feature module that does not exist yet in `settings.gradle.kts`;
2. a new screen or destination in the graph;
3. a new endpoint, or a new entity or table;
4. what the user sees of something that exists: offline or cache behavior, how errors show, navigation exits, tracking events.

Bugs whose expected behavior is already clear (a test, the ticket or the code says it), refactors and visual tweaks with no new logic need no brief. A bug whose expected behavior is ambiguous needs no brief, but the user's decision is written down before implementing (one line in the ticket, the brief folder or the commit message). When unsure, ask once: "This creates a screen and an endpoint: shall I write a brief?" The user can also ask for a brief.

Where the brief lives:

- If the ticket already has acceptance criteria, the brief is the link to the ticket.
- If the ticket lacks decisions, write `docs/features/<feature>/<task-id>.md` in the repository: a link to the ticket and only what is missing.
- Without a ticket, the same file holds the whole brief. Use the ticket id as `<task-id>`, or a short slug of the task.

A brief contains the goal, observable acceptance criteria, the decisions still open, and only the contracts that apply: offline and cache behavior, writes and mutations, errors, the endpoint, tracking events, navigation exits. No class lists and no screens described in prose.

## 3. Ask what the code cannot answer

The agents take conventions from the code. What the code cannot answer is a question for the user: behavior, offline handling, scope, external contracts (endpoint, payload, events). Ask these in one round with AskUserQuestion, recommend an option when you have one, and record the answers in the brief or, without a brief, in the message to each agent. Never ask about naming or structure the module already shows.

## 4. Pick the data tier

`data-builder` runs on the cheap model by default, because most data work is routine. Run it on the standard model (`model: "sonnet"` on the Agent call) when the plan includes a Room migration or schema change, sync or refresh policy, conflict resolution or encryption, when the agent replies `ESCALATE_TIER: yes`, or when it fails the same task twice.

## 5. Delegate

Before the first agent runs, write the task's scope to `build/android-feature-kit/scope.json`: the folders of the feature modules this task works in, relative to the repository root, for example `{"modules": ["feature/orders"]}`. The layer guard reads it: the layer agents then write only inside those modules, and `feature-integrator` writes only outside their `src/` folders, except their `AndroidManifest.xml` files (it does not write at all without this file). Update it if the task moves to another module.

Each agent sees only your message. Give it the module path, the task for its layer, the decisions, the brief path or ticket text, and the contract it builds against (paths and signatures).

1. `domain-builder` first when the contract changes. Keep its reply: CONTRACT_CHANGES is what the others build against.
2. `data-builder` and `ui-builder` next, in the same message so they run in parallel, when both are needed.
3. Read each reply's STATUS and fields:
   - `blocked` with QUESTIONS: ask the user, then answer the same agent with SendMessage so it continues with its context.
   - CONTRACT_REQUESTS: send them to `domain-builder` (SendMessage if its conversation is still available, otherwise a new call with the request), then tell the requesting agent what changed.
   - OUTSIDE_MODULE and DEPENDENCIES: collect them for the integrator.
4. `feature-integrator` only when OUTSIDE_MODULE or DEPENDENCIES is not empty. Give it the exact list, each item with its path, reason, snippet and owner. Items it returns under RETURNED go back to their owner.

Never edit application code yourself to save a round trip. If an agent cannot do something, find out why.

## 6. Verify

Every agent builds and tests its module. When a failure remains that its owner could not fix:

- compile, KSP, resource or dependency errors: `build-doctor` with the check summary;
- failing tests: `test-analyst` with the module path;
- then send the proposed fix to the owner named in the diagnosis.

Escalate to `android-architect` when the same error survives two fixes, when a diagnosis says ESCALATE, when the reviewer marks a finding as a design problem, or when two agents need contradictory contracts. A missing product decision goes to the user, not to a bigger model.

## 7. Review

If `codex` is on the PATH (`command -v codex`, or `Get-Command codex` in PowerShell) and the repository is a git repository, Codex reviews. Otherwise `android-reviewer` does.

Every review round is tied to one exact change. Before each round, run `python3 <this skill's folder>/references/review_target.py` (`${CLAUDE_PLUGIN_ROOT}/skills/develop/references/review_target.py` in Claude Code) from the repository root (add a range such as `main...HEAD` to review commits instead of the working tree). It prints `source_revision` and `diff_hash`. Give the review a `run_id` (for example `review-<date>-<time>`), the same in every round. The working-tree target covers staged and unstaged changes (`git diff HEAD`) plus untracked files. `rules_version` is the `version` in the plugin's `.claude-plugin/plugin.json`.

Codex review, read-only, with the kit's schema:

1. Write the prompt from `references/codex-review.md` (in this skill's folder) to `build/android-feature-kit/review/round-1-prompt.md`, filling in the target, its identity, the task, the brief, the decisions and the rules files for the layers touched.
2. Run, from the repository root:

   ```
   codex exec -s read-only --output-schema <schema> -o build/android-feature-kit/review/round-1.json - < build/android-feature-kit/review/round-1-prompt.md > build/android-feature-kit/review/round-1.log 2>&1
   ```

   `<schema>` is `references/review.schema.json` in this skill's folder (`${CLAUDE_PLUGIN_ROOT}/skills/develop/references/review.schema.json` in Claude Code).

3. Read only the JSON. Keep the session id (the `session id:` line of the log) for the next rounds.
4. Send each finding to its owner. Answer every finding with fixed (what changed), disputed (why) or deferred (why).
5. Next round: write the responses as the prompt and run `codex exec resume <session id> -c 'sandbox_mode="read-only"' --output-schema <same schema> -o build/android-feature-kit/review/round-<n>.json - < <prompt>`. Use the exact session id, never `--last`.

With `android-reviewer`, give it the same inputs, including the target identity, and in later rounds its previous findings with your responses.

Accept a READY verdict only if the answer repeats the identity you sent (run id, round, source revision, diff hash, rules version), and a fresh `review_target.py` run for the same target prints the same `source_revision` and `diff_hash`, and the plugin version is unchanged. If anything moved after the review started, run another round. Keep the flow's own files (scope, prompts, answers, logs) in `build/android-feature-kit/`: `review_target.py` leaves that folder out of the identity. The review ends when an accepted verdict is READY and the checks pass, or after three rounds. A finding disputed twice goes to the user.

## 8. Report

Tell the user, briefly:

- what changed, grouped by layer, with the main files;
- the decisions taken and where they are recorded (brief path or ticket);
- contract changes and changes outside the module;
- the checks run and the ones that could not run;
- the review verdict and anything left open.

## Without the kit's agents

If the agents are not available (for example in Codex, where plugins do not ship agents), do the same steps yourself in order: for each layer, load its skill, do its part, run its checks, then move to the next layer. Keep the brief, the questions and the review. The layer guard does not run there, so keep each step inside its layer yourself.
