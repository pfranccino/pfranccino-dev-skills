# External reviewer

The kit's default reviewer is the `android-reviewer` agent. A repository can also configure an external reviewer: any command-line tool that reads a prompt on standard input and returns a JSON answer that follows `review.schema.json` in this folder. It runs only when the user picks it in the plan.

## Configure it

In the app repository, `.claude/android-feature-kit.json`:

```json
{
  "reviewer": {
    "name": "Codex",
    "command": ["codex", "exec", "-s", "read-only", "--output-schema", "{schema}", "-o", "{output}", "-"],
    "timeout_seconds": 1800
  }
}
```

- `command` is the program and its arguments, as a list. It runs from the repository root, with the prompt on standard input.
- `{schema}` becomes the absolute path of `review.schema.json`, for tools that can enforce a schema.
- `{output}` becomes the path where the tool must write its JSON answer. Without `{output}` in the command, the answer is read from standard output.
- `{prompt_file}` becomes the path of the prompt, for tools that take a file instead of standard input.
- `name` is how the plan and the report name the reviewer. `timeout_seconds` is optional (1800 by default).

The tool must not modify the repository. Run it in a read-only mode when it has one, as the Codex example does.

## Run a round

1. Write the prompt from the templates below to `build/android-feature-kit/review/round-<n>-prompt.md`.
2. From the repository root, run:

   ```
   python3 <this folder>/run_review.py --round <n> --run-id <run id> --source-revision <...> --diff-hash <...> --rules-version <...>
   ```

   (`python` on Windows. `<this folder>` is `${CLAUDE_SKILL_DIR}/references` from the develop skill, with the plugin or with the skills copied into the repository. `--rules-version` is the content of `VERSION` in this folder.)
3. Read only the summary it prints. With `"status": "ok"`, the answer is in `build/android-feature-kit/review/round-<n>.json`, it follows the schema, and it repeats the identity you sent. With any other status, read `problems`; the tool's output is in `round-<n>.log`. Exit codes: 0 valid answer, 1 the tool failed or its answer is not valid, 2 no reviewer configured or bad arguments.

Each round is a new call: the tool keeps no session between rounds, so a later round's prompt carries the previous findings and your responses.

## Round 1

```
You are the reviewer of a change to an Android feature module, in the repository in the current directory. Do not modify any file.

Review target: <"the working tree: run git status, git diff HEAD (staged and unstaged changes together), and read untracked files directly", or a commit range such as main...HEAD: run git diff main...HEAD>.
Target identity, to copy into your answer: run_id <the review's id>, round 1, source_revision <from review_target.py>, diff_hash <from review_target.py>, rules_version <the content of VERSION in this folder>.
Task: <one paragraph>.
Brief or ticket: <path to the brief, the ticket link with its acceptance criteria, or "none">.
Decisions the user made: <list, or "none">.

Team rules: read only the rules files for the layers the change touches:
<absolute paths to skills/<skill>/references/rules.md for each layer touched>
Each file starts with the kit-wide rules KIT-01 to KIT-07. KIT-01 and KIT-02 mean that the plan and the module's own conventions win over the skills' examples: do not flag what they required.

Report real defects only. In `rule`, cite a rule ID, or "brief" when the change does not do what the brief or ticket asks. In `owner`, name who fixes it: domain-builder, data-builder, ui-builder, feature-integrator, or user for a product decision. Use IDs C1, C2 and so on. List what you could not check under `limitations`. The verdict is READY only if no blocker or major finding remains. `responses_to_previous` is empty in this round.

Answer with one JSON object that follows this schema, and nothing else:
<the contents of review.schema.json>
```

Drop the last two lines when the command passes `{schema}` to a tool that enforces it.

## Later rounds

The round 1 prompt, with the round number and identity updated and the decisions list brought up to date with what the user decided since, followed by:

```
This is round <n>. Your previous findings, as you reported them:
<the findings array from the previous round's JSON>
Responses to your findings:
- C1: fixed: <what changed and where>
- C2: disputed: <why, with evidence>
- C3: deferred: <why>
- C4: accepted: <the user keeps it as it is, and why>
Accepted exceptions from every earlier round. The user accepted or deferred these findings; do not report them again as new findings. If a later change means one no longer holds, report it again with its original ID and say what changed:
- C3 (round 1): deferred: <reason>
Check each response, and look for problems the fixes introduced. Put each previous ID in `responses_to_previous`, and continue the numbering for new findings.
```

The accepted exceptions list covers the whole review: each round adds the findings the user accepted or deferred in it, and no entry is dropped. Each later round starts from the round 1 prompt, so the prompt repeats only the previous round's findings and responses, and the list carries what came before.
