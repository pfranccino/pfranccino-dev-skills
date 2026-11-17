# Codex review prompts

Templates for the review step of the develop skill. Fill in the parts in angle brackets, write the result to a prompt file and pass it to `codex exec` as the skill says. The target identity comes from `review_target.py` in this folder.

## Round 1

```
You are the reviewer of a change to an Android feature module, in the repository in the current directory. Do not modify any file.

Review target: <"the working tree: run git status, git diff HEAD (staged and unstaged changes together), and read untracked files directly", or a commit range such as main...HEAD: run git diff main...HEAD>.
Target identity, to copy into your answer: run_id <the review's id>, round 1, source_revision <from review_target.py>, diff_hash <from review_target.py>, rules_version <the plugin version>.
Task: <one paragraph>.
Brief or ticket: <path to the brief, the ticket link with its acceptance criteria, or "none">.
Decisions the user made: <list, or "none">.

Team rules: read only the rules files for the layers the change touches:
<absolute paths to skills/<skill>/references/rules.md for each layer touched>
Each file starts with the kit-wide rules KIT-01 to KIT-07. KIT-01 and KIT-02 mean that the plan and the module's own conventions win over the skills' examples: do not flag what they required.

Report real defects only. In `rule`, cite a rule ID, or "brief" when the change does not do what the brief or ticket asks. In `owner`, name who fixes it: domain-builder, data-builder, ui-builder, feature-integrator, or user for a product decision. Use IDs C1, C2 and so on. List what you could not check under `limitations`. The verdict is READY only if no blocker or major finding remains. `responses_to_previous` is empty in this round.
```

## Later rounds

```
Round <n>. Target identity, to copy into your answer: run_id <same as round 1>, round <n>, source_revision <...>, diff_hash <...>, rules_version <...>.
Responses to your findings:
- C1: fixed: <what changed and where>
- C2: disputed: <why, with evidence>
- C3: deferred: <why>
The review target is now <the working tree (git status, git diff HEAD, untracked files) or the range>. Check each response, and look for problems the fixes introduced. Answer in the same schema: put each previous ID in `responses_to_previous`, and continue the numbering for new findings.
```
