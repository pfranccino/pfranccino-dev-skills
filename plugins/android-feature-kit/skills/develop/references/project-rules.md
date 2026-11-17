# android-feature-kit: rules for this repository

What the team approves once, for every task. The `develop` and `analyze` skills read this file when they start; Claude does not load it in other sessions. Copy it to `.claude/android-feature-kit.md` in the app repository and edit the lists. Do not put it in `.claude/rules/`, which Claude loads in every session.

## Exploration approved in advance

While planning or answering, Claude may do these without asking:

- Read any file in this repository.
- Search with Grep and Glob.
- Run read-only git commands (`status`, `diff`, `log`, `show`, `blame`, `ls-files`).
- Discovery agents: none.

Claude asks before anything else: Gradle builds or test runs, module map or codegraph generation, anything that writes output, network access, or any agent.

## Routine choices

These follow what the code already shows, and are never questions:

- Names of classes, functions, files and packages, following the module's existing names.
- Where a file goes inside the layer packages the module already uses.
- Reusing an existing helper, extension, base class or design-system component.
- The structure of new tests, following the module's existing tests.

Everything else is asked: behavior, offline handling, errors the user sees, navigation exits, tracking events, scope, external contracts, a new public interface, a new dependency or a version change, and a migration strategy.
