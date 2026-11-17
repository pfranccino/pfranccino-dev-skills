<!-- android-feature-kit:start -->
## Android feature work (android-feature-kit)

Requests to build or change a feature (a new feature, screen, endpoint, entity or flow, a ticket to implement) go through the kit's `develop` skill. Questions about the code, failing builds or tests, reviews and architecture questions go through its `analyze` skill. The shortcuts are `/android-feature-kit:develop` and `/android-feature-kit:analyze`. A small change in one layer uses that layer's skill directly, without agents.

Nothing that writes code starts without approval:

- Implementation plans are approved in Plan Mode, and no writing agent runs before that.
- Analysis plans are approved in the conversation.
- A decision that appears after approval (a new contract, dependency or version, a tier change, an escalation, another review round) is asked before it is applied.
- Only one kit run works in this checkout at a time.

### Exploration approved in advance

While planning or answering, Claude may do these without asking:

- Read any file in this repository.
- Search with Grep and Glob.
- Run read-only git commands (`status`, `diff`, `log`, `show`, `blame`, `ls-files`).
- Discovery agents: none.

Claude asks before anything else: Gradle builds or test runs, module map or codegraph generation, anything that writes output, network access, or any agent.

### Routine choices

These follow what the code already shows, and are never questions:

- Names of classes, functions, files and packages, following the module's existing names.
- Where a file goes inside the layer packages the module already uses.
- Reusing an existing helper, extension, base class or design-system component.
- The structure of new tests, following the module's existing tests.

Everything else is asked: behavior, offline handling, errors the user sees, navigation exits, tracking events, scope, external contracts, a new public interface, a new dependency or a version change, and a migration strategy.
<!-- android-feature-kit:end -->
