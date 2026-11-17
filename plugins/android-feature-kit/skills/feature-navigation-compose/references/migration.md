# Migrating existing navigation in a module

Part of the feature-navigation-compose skill. Read it before migrating a module's existing navigation; the rest of the skill still applies.

Use when the module already has navigation (string routes, public destination routes, screens that receive `NavController`, an Activity or Fragment per screen, direct navigation to another feature) and the task is to move it to the closed graph pattern above.

The scope rule is the point of this mode: one module per task, internals only, so each migration is one small change that compiles and ships on its own.

- One module per task. If the user names several, handle them one at a time, each as a self-contained change with its own report.
- Nothing outside the module is edited, and nothing outside may stop compiling or change behavior because of this change.
- Migrate navigation only. Do not redesign UI, business logic, ViewModels or dependency injection, and do not rename things navigation does not require.
- If the module holds several independent flows and the whole is too large for one change, migrate one flow, and say which ones remain.

Steps:

1. **Inventory before editing.** List every destination, how it is reached (start, from inside, from outside the module), its arguments, every place the module navigates to another module, the current back behavior, and every public navigation symbol. Search other modules read-only to find which of those public symbols are used from outside. Prefer a semantic search: `android studio find-usages --short <Symbol>` (Android CLI with the project open in Android Studio; add `--context-file <file>` for symbols with common names) or the LSP find-references tool when available. Fall back to searching imports of the symbol, and say which method you used.
2. **Design the target surface.** The graph marker, the `internal` routes, and the graph extension signature with its configuration and exit callbacks. Every navigation to another module becomes an exit callback named by what happened.
3. **Migrate the internals.** Type-safe `internal` routes, destinations registered in the feature graph, stateful and stateless screen pairs without `NavController`, side effects mapped to callbacks in the screen.
4. **Keep consumers working with bridges.** See below.
5. **Preserve behavior.** Same start destination, same back stack after each step of the flow, same back behavior. If something must change, say it explicitly.
6. **Verify.** Build the module and run its existing tests when the environment allows it. If it cannot be run, say so.

Bridges, so that no consumer has to change in the same task:

- A public entry point that is used from outside (a public function, a public route, an Activity, a Fragment) stays. Turn it into a thin bridge that delegates to the new graph, and mark it `@Deprecated` with a message naming its replacement. Never delete a public symbol that has usages outside the module.
- A public symbol with no usages outside the module becomes `internal` or is removed.
- Where the module navigated directly to another module: move the call out of screens and ViewModels into an exit callback. If the module owns the host that mounts the graph, wire the callback there to the same call as before. If the host is outside the module, give the callback a temporary default that keeps the previous behavior, mark it with a `TODO`, and report it.
- Existing data passing that breaks the rules but still works (a shared ViewModel, a loose `savedStateHandle` key) stays unless navigation cannot be migrated without changing it. Report it as follow-up.

A migration report adds, to the usual closing report:

- The inventory, as a short table.
- Each bridge left in place, with what must happen outside the module before it can be removed.
- Behavior differences, or "None".
