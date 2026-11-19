---
name: develop
description: "Coordinates the android-feature-kit layer agents to build or change an Android feature: a new feature, screen, endpoint, entity or flow, a ticket to implement, or a change that spans the domain, data and ui layers. Proposes a plan (agents, models, brief, integration, reviewer and review rounds) for the user to approve in Plan Mode before any agent writes code. Use it when the user describes a feature or ticket to build or change, even in plain words and without naming the kit. For a small change in one layer, the layer skill alone is enough. Also for requests in Spanish such as crear una feature, implementar un ticket, agregar una pantalla con su endpoint, cambiar el flujo de un módulo."
argument-hint: "[task, ticket link or ticket id]"
---

# Develop

You coordinate the kit's agents from the main conversation. You plan, ask, delegate, integrate the results and report. You write no application code, and you do not load the layer skills (domain-layer, data-repository, data-room, data-datastore, feature-ui-compose, feature-navigation-compose) yourself: each agent loads its own. The only files you write are the brief, the scope file and the review prompts. The one exception is a small change that the user approved without agents (section 3).

The user approves the plan before any agent writes code. You propose; you never decide on your own what the user has not approved.

Task from the invocation: $ARGUMENTS

## 0. What to work on

If the line above names a task, a ticket or a link, that is the task. If it is empty or shows a placeholder, ask and wait for the answer before anything else: when the conversation already states a request, ask whether that is the task to plan; otherwise ask what the user wants to build or change. Do not explore, plan or launch anything until the user has named or confirmed the task.

## 1. The rules this repository set

Read `.claude/android-feature-kit.md` in the repository, if it exists. It holds what the user approved once for every task:

- **Exploration approved in advance**: what you may read and run without asking while you plan.
- **Routine choices**: what follows from the code and is never a question.

When the file is missing, propose the defaults from `${CLAUDE_SKILL_DIR}/references/project-rules.md` to the user once in this session, wait for the answer, and use what they approve. Mention that saving them as `.claude/android-feature-kit.md` avoids the question next time.

Exploration that goes beyond the approved limits (a Gradle build, a module map or codegraph generation, anything that writes output, the network, a discovery agent the file does not list) is asked first, with what it would run and why.

## 2. Plan in Plan Mode

Implementation plans are approved in Plan Mode. If the session is not in Plan Mode, enter it with the `EnterPlanMode` tool. If that tool is not available, ask the user to switch to Plan Mode (Shift+Tab, or `/plan` before the prompt) and stop.

Read only what you need to plan, inside the approved limits: `settings.gradle.kts` (or `.gradle`) to find the module, the module's package layout with Glob, `git status`, and the ticket if the user gave one. Do not read the layers' code in depth; the agents do that.

Then:

1. **Ask what the code cannot answer** in one round with AskUserQuestion, with a recommendation when you have one: behavior, offline handling, scope, external contracts (endpoint, payload, events), and any choice outside the routine list, such as a new public interface, a new dependency or a version change, or a migration strategy. Never ask about the routine choices.
2. **Check that no other run owns this checkout.** If `build/android-feature-kit/scope.json` exists and its `session_id` is not `${CLAUDE_SESSION_ID}`, another session may be running a task here. Only one run works in a checkout at a time, and the layer guard does not let you replace that file. Tell the user; if that run is over, the user deletes the file (for example with `! rm build/android-feature-kit/scope.json`), and you continue after they say so.
3. **Write the plan** and present it with `ExitPlanMode`. The plan has these parts, and the `Agents:` line in exactly this form, because the optional plan gate reads it:

```
Goal: <one paragraph, with the observable acceptance criteria>
Modules: <feature module folders, for example feature/orders>
Decisions: <each question and the user's answer>
Brief: <none | the ticket link | docs/features/<feature>/<task-id>.md, and why>
Agents: domain-builder (sonnet), data-builder (haiku), ui-builder (sonnet), feature-integrator (sonnet)
Work: <per agent: what it creates or changes; the order; which ones run in parallel>
Integration: <changes outside the feature's layers known now: Gradle, version catalog, the app's NavHost, shared providers> | none
Checks: <the builds and tests each agent runs; build-doctor and test-analyst (haiku) diagnose failures and hangs before anyone else investigates them>
Review: <android-reviewer, or the external reviewer configured in .claude/android-feature-kit.json>, up to <n> rounds
Stop and ask when: <a new decision appears, an agent asks to change tier, an escalation is needed, the review needs more rounds>
```

List in `Agents:` only the agents the task needs, by their names in the table below, each with the model you propose in parentheses. For a small change without agents, write `Agents: none`. When the user changes the plan, present it again.

### What goes into the plan

**Which agents.** A bug in one layer needs only that layer's agent. A new screen on an existing use case may need only `ui-builder`. `domain-builder` goes first whenever the contract (models, errors, repository interfaces, use case signatures) has to change; `data-builder` and `ui-builder` then run in parallel when both are needed. `feature-integrator` is in the plan only when integration is known now.

**A small change.** One layer, no contract change, no new module, screen, endpoint, entity or dependency: propose doing it in this session with that layer's skill, without agents. The plan says which skill and what changes, and the user approves it like any other.

**Brief or not.** Propose a brief when the plan creates or changes any of these:

1. a feature module that does not exist yet in `settings.gradle.kts`;
2. a new screen or destination in the graph;
3. a new endpoint, or a new entity or table;
4. what the user sees of something that exists: offline or cache behavior, how errors show, navigation exits, tracking events.

Bugs whose expected behavior is already clear (a test, the ticket or the code says it), refactors and visual tweaks with no new logic need no brief. For a bug whose expected behavior is ambiguous, propose writing the user's decision down (one line in the ticket, the brief folder or the commit message). A ticket with acceptance criteria is the brief. Otherwise it goes in `docs/features/<feature>/<task-id>.md` in the repository, with the ticket id or a short slug of the task as `<task-id>`. A brief holds the goal, observable acceptance criteria, the decisions still open, and only the contracts that apply: offline and cache behavior, writes and mutations, errors, the endpoint, tracking events, navigation exits. No class lists and no screens described in prose.

**Models.** Propose these, and say why when you propose something else:

| Agent | Writes | Model |
| :--- | :--- | :--- |
| `domain-builder` | the domain package: use cases, models, repository interfaces, errors | sonnet |
| `data-builder` | the data package: repositories, API, DTOs, mappers, Room, DataStore, data Hilt bindings | haiku; sonnet when the plan includes a Room migration or schema change, sync or refresh policy, conflict resolution or encryption |
| `ui-builder` | presentation, the feature's navigation graph, resources | sonnet |
| `feature-integrator` | what lies outside the layers: Gradle, version catalog, shared providers, the app's NavHost | sonnet |
| `build-doctor`, `test-analyst` | nothing; they diagnose failures | haiku |
| `android-reviewer` | nothing; it reviews | sonnet |
| `android-architect` | nothing; escalations | opus |

**Reviewer and rounds.** `android-reviewer` reviews by default. If `.claude/android-feature-kit.json` in the repository configures an external reviewer (see `references/external-review.md`), offer it as an option too. Propose a round cap, for example two: one review and one check of the fixes. Being installed or configured is not a choice; the user picks the reviewer in the plan.

## 3. Delegate the approved plan

After the user approves:

1. Write the scope to `build/android-feature-kit/scope.json` with the plan's modules and this session's id: `{"modules": ["feature/orders"], "session_id": "${CLAUDE_SESSION_ID}"}`. The layer guard reads it: the layer agents write only inside those modules, and `feature-integrator` writes only outside their `src/` folders, except their `AndroidManifest.xml` files (it does not write at all without this file). It also marks the checkout as taken by this session.
2. Write the brief if the plan has one.
3. **A small change without agents**: load the layer skill the plan names, make the change in this session, run that skill's checks, then continue with section 5 when the plan has a review, or section 6.
4. Otherwise, call the agents in the plan's order, with the model the plan gives each one (`model` on the Agent call). Each agent sees only your message: give it the module path, the task for its layer, the decisions, the brief path or ticket text, the contract it builds against (paths and signatures), and the routine choices from `.claude/android-feature-kit.md` when they differ from the defaults.

Read each reply's STATUS and fields:

- `blocked` with QUESTIONS: ask the user, then answer the same agent with SendMessage so it continues with its context.
- CONTRACT_REQUESTS: a change to the domain contract that the plan did not include is a new decision. Ask the user, then send it to `domain-builder` (SendMessage if its conversation is still available, otherwise a new call with the request) and tell the requesting agent what changed.
- `ESCALATE_TIER: yes` from `data-builder`: tell the user why and ask before running it again on sonnet.
- OUTSIDE_MODULE and DEPENDENCIES: items the plan's Integration part already covers go to `feature-integrator`. Any other item, and every new dependency or version change, is asked first. Give the integrator the exact list, each item with its path, reason, snippet and owner. Items it returns under RETURNED go back to their owner.

Outside an approved small change, never edit application code yourself to save a round trip. If an agent cannot do something, find out why.

## 4. Verify

Every agent builds and tests its module. When you run a check yourself (an approved small change, or after integration), run it through `gradle_summary.py` with the shell's longest timeout (600000 ms); connected tasks stop after 9 minutes with `status: "timeout"`.

The plan's Checks line approves the diagnosis agents. When a failure remains that its owner could not fix, or a check of yours fails or hangs, send it to them before you investigate it yourself:

- compile, KSP, resource, dependency or Gradle configuration errors, and environment failures (an emulator or device that goes offline, an install or a connected test that hangs or times out, a missing SDK or JDK): `build-doctor` with the check summary;
- failing tests: `test-analyst` with the module path;
- the summary's `next_step` names the agent, and after a failing check the kit's hook adds a note that names it too;
- then send the proposed fix to the owner named in the diagnosis, when it stays inside the approved plan. A fix that changes the plan (a dependency or version, a contract, files outside the plan) is asked first.

When the diagnosis agent cannot run what the failure needs (it has no `adb` and no network), it says what it could not check. You complete that check after its diagnosis, not before.

Ask the user before calling `android-architect` when the same error survives two fixes, when a diagnosis says ESCALATE, when the reviewer marks a finding as a design problem, or when two agents need contradictory contracts. A missing product decision goes to the user, not to a bigger model.

## 5. Review

Run the reviewer the plan names, up to the approved number of rounds.

Every review round is tied to one exact change. Before each round, run `python3 ${CLAUDE_SKILL_DIR}/references/review_target.py` from the repository root (`python` on Windows; add a range such as `main...HEAD` to review commits instead of the working tree). It prints `source_revision` and `diff_hash`. Give the review a `run_id` (for example `review-<date>-<time>`), the same in every round. The working-tree target covers staged and unstaged changes (`git diff HEAD`) plus untracked files. `rules_version` is the kit's version, the content of `${CLAUDE_SKILL_DIR}/references/VERSION`.

- **`android-reviewer`**: give it the target, its identity, the task, the brief, the decisions and the modules. In later rounds, also give it its previous findings with your responses, and every finding the user accepted or deferred in any earlier round, with its ID and the reason, so that it does not report them again as new.
- **External reviewer**: follow `references/external-review.md`. You write the prompt to `build/android-feature-kit/review/round-<n>-prompt.md` and run `run_review.py`, which calls the configured command and checks the answer against `references/review.schema.json` and the identity.

After each round, show the user the findings. Fixes for findings go to their owners once the user approves them; a finding you would dispute or defer goes to the user with your reason. Accept a READY verdict only if the answer repeats the identity you sent (run id, round, source revision, diff hash, rules version), and a fresh `review_target.py` run for the same target prints the same `source_revision` and `diff_hash`, and `references/VERSION` is unchanged. If anything moved after the review started, the next round checks it. Keep the flow's own files (scope, prompts, answers, logs) in `build/android-feature-kit/`: `review_target.py` leaves that folder out of the identity.

The review ends when an accepted verdict is READY and the checks pass, or when the approved rounds are used up. Another round beyond the cap is the user's decision.

## 6. Report and release the checkout

Tell the user, briefly:

- what changed, grouped by layer, with the main files;
- the decisions taken and where they are recorded (brief path or ticket);
- contract changes and changes outside the module;
- the checks run and the ones that could not run;
- the failures: each one, the agent that diagnosed it, and why no agent did when you diagnosed it yourself (or "none" when nothing failed);
- the review verdict and anything left open.

Then, if `build/android-feature-kit/scope.json` still holds this session's id, delete it, so another session can run a task in this checkout.

## Without the kit's agents

If the agents are not available (the kit's skills were copied into the repository without the plugin), the plan and its approval stay the same, and you do the work yourself in order: for each layer, load its skill, do its part, run its checks, then move to the next layer. Keep the brief, the questions and the review. The layer guard does not run there, so keep each step inside its layer yourself.
