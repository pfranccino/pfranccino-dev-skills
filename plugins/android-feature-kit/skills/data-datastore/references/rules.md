# data-datastore rules

Every normative rule of the data-datastore skill, with a stable ID. Reviews cite these IDs, and the skill's "Before finishing" checklist points to them. The Source column names the section of `SKILL.md`, or of `references/encryption.md`, that explains the rule. When a rule changes there, change it here too. IDs are never reused.

## Rules shared by every skill of the kit

These rules have the same IDs in every skill's rules file. Where a skill has no sentence for a rule, the rule is kit policy, marked as such in the Source column.

| ID | Rule | Source |
| :--- | :--- | :--- |
| KIT-01 | The skill applies even when the task arrives as a detailed plan or ticket: the plan says what to build, the skill says how the team builds it. If the plan and the skill disagree, say so and follow the plan. A review does not flag a deviation the plan required. | Introduction of every skill |
| KIT-02 | The module's existing naming, packages and conventions win over the skill's examples when they differ in style. A review does not flag a style that follows the module. | Scope of domain-layer, data-repository, feature-ui-compose and feature-navigation-compose; kit policy for data-room and data-datastore, which have no such sentence |
| KIT-03 | The module is inferred from the paths or files the user gave; ask before writing only if more than one module fits. | Scope of domain-layer, data-repository, feature-ui-compose and feature-navigation-compose; kit policy for data-room and data-datastore, which have no such sentence |
| KIT-04 | Other modules are not edited. Each change needed outside the module is reported under "Changes needed outside this module" with the module, the reason and the exact snippet, or the report says "None". | Scope and Before finishing of every skill |
| KIT-05 | The concrete names the skill's examples stand for (the project's `Either`, MVI delegate, network helper, side effect collector, design system, dispatcher qualifier, application scope) are read from the project before writing. A required piece that does not exist is asked about, never invented or copied privately into the feature. | Read before writing of every skill, generalized as kit policy |
| KIT-06 | Before finishing, the module is built and tested with its real path and variant, and the report says which checks could not run. | Before finishing of every skill |
| KIT-07 | The final report lists what was created or changed, by file. If other team skills also apply to the task, they give one combined report instead of one per skill. | Before finishing of every skill |

## DataStore rules

| ID | Rule | Source |
| :--- | :--- | :--- |
| DS-01 | The local data source that reads and writes the store lives in the feature's data package and is `internal`. Other modules are not edited (KIT-04). | Scope |
| DS-02 | The DataStore instance is provided once, at application scope, from a Hilt module. If the project keeps such providers outside the feature, the snippet goes in the report instead of editing that module. | Scope |
| DS-03 | The storage fits the data, and the reply says why: Preferences DataStore for a few independent flags or values; typed DataStore with a serializer for one object whose fields evolve together; Room (data-room) for lists, filters, anything where a `WHERE` would help, or more than one small object; secrets and sensitive values (tokens, identifiers of the user) in typed DataStore encrypted with `datastore-tink`, keys in Android Keystore, never plain Preferences. | Choose the storage |
| DS-04 | One instance per file per process: the store is provided once as a `@Singleton` and never built in a composable, a ViewModel or a data source. | Rules that prevent the common bugs |
| DS-05 | The store runs in an application-scoped context that has a `Job`. Never `viewModelScope`. | Rules that prevent the common bugs |
| DS-06 | Stored types are immutable (a `data class` with `val`s, or generated Proto classes), and updates use `updateData { it.copy(...) }` or `edit { }`. | Rules that prevent the common bugs |
| DS-07 | Only an `IOException` on read falls back to defaults, through `retryWhen` (never `catch`, which ends the flow): emit the default, wait and retry a few times, then let the error reach the ViewModel's `catch` (feature-ui-compose). Every other error is rethrown, so a serializer bug is not hidden as empty settings. | Rules that prevent the common bugs |
| DS-08 | Typed serializers wrap parse failures in `CorruptionException`, and every store sets a corruption handler with a policy chosen for its data (`ReplaceFileCorruptionHandler` with defaults for settings; for a session it means signing in again). Data that cannot be lost is kept in Room or on the backend, not in DataStore. | Rules that prevent the common bugs |
| DS-09 | No `runBlocking` on DataStore from the main thread. The data source exposes `Flow` and `suspend` functions. | Rules that prevent the common bugs |
| DS-10 | Each store has its own Hilt qualifier when more than one store has the same type. | Rules that prevent the common bugs |
| DS-11 | Keys and file names are permanent after release, and keys are `private` to the data source. | Rules that prevent the common bugs |
| DS-12 | Single-process and multi-process DataStore are not mixed on one file. Multi-process is used only when another process really shares the file. | Rules that prevent the common bugs |
| DS-13 | Stored types stay in the data package; the repository maps them to domain models. | Rules that prevent the common bugs |
| DS-14 | DataStore 1.3 recommends `DataStore.Builder` over `DataStoreFactory`; the builder takes a `CoroutineContext` (the application scope's), not a scope. On DataStore 1.2 or earlier, typed stores use `DataStoreFactory.create(serializer, corruptionHandler, migrations, scope) { file }` with the same application scope. | Typed DataStore (DataStore 1.3) |
| DS-15 | Replacing `SharedPreferences` passes `SharedPreferencesMigration(context, "<old file name>")` in `migrations`, and the old key names stay until the migration has shipped. | Preferences DataStore |
| DS-16 | Encrypted stores wrap their serializer in `AeadSerializer` with `associatedData` unique per file. The keyset is built once, inside the singleton provider, because it touches disk and the Keystore. Decryption failures arrive as `CorruptionException`, so the corruption handler decides what happens. | Encryption (`references/encryption.md`) |
| DS-17 | Encrypted files and their keyset preferences are excluded from Auto Backup and device transfer, and a restore is treated as signed out, because the Keystore key does not travel with a backup. The snippet for the app module's backup and data extraction rules is in the report. | Encryption (`references/encryption.md`) |
| DS-18 | Tests build the store on a temporary file with a unique name per test, using the test's scope (for example `backgroundScope` in `runTest`), and cover defaults on the first read, a write followed by a read, an `IOException` that emits defaults and recovers, a corrupt file handled by the corruption policy, and, for encrypted stores, a missing or invalid key. | Tests |
| DS-19 | The final report lists the file names and keys created, since renaming them later loses user data. | Before finishing |
| DS-20 | Before writing, read the DataStore version in the version catalog (1.3 or later has `DataStore.Builder` and `datastore-tink`), the project's application `CoroutineScope` and its Hilt qualifier, and the existing stores and their file names, so none is reused by accident. | Read before writing |
| DS-21 | Each file stays small, because DataStore rewrites the whole file on every write. | Choose the storage |
| DS-22 | Before writing a Preferences store, run `android docs search "Preferences DataStore Builder"` when Android CLI is available; if the project's version offers a builder for Preferences, prefer it. | Preferences DataStore |
