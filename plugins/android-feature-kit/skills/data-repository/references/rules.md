# data-repository rules

Every normative rule of the data-repository skill, with a stable ID. Reviews cite these IDs, and the skill's "Before finishing" checklist points to them. The Source column names the section of `SKILL.md` that explains the rule. When a rule changes in `SKILL.md`, change it here too. IDs are never reused.

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

## Repository rules

| ID | Rule | Source |
| :--- | :--- | :--- |
| REPO-01 | Work in the data package of one feature module. Do not edit other modules (the shared HTTP client, the database class, app-level DI); report each change needed there (KIT-04). | Scope |
| REPO-02 | Implement interfaces declared in the feature's domain package. If one does not exist yet, write it first following domain-layer, or, when working only on the data layer (for example as the kit's `data` agent), do not write it: stop and ask for it with the signatures needed. | Scope |
| REPO-03 | Every remote call goes through the project's network helper, which returns the project's `Either` with the network error type. If the helper or the `Either` does not exist yet, ask where it should live; never write a private one inside the feature. | Read before writing |
| REPO-04 | Everything in the data package is `internal`. No DTO, entity, data source or network error type is visible outside it; the rest of the feature only sees the domain interface. | Layout and visibility |
| REPO-05 | The API definition returns DTOs. A remote data source wraps each call with the network helper and returns `Either<NetworkError, Dto>`; it does not throw and adds no try/catch of its own around calls. | Remote |
| REPO-06 | DTOs mirror the backend, and fields the backend may omit are nullable. Serialization annotations are allowed in the data package (network DTOs, typed DataStore models), never in domain models. | Remote |
| REPO-07 | Mapping a DTO validates what the domain requires: a missing required field becomes an error, not a crash and not a silent default. | Remote |
| REPO-08 | Request or response bodies that contain personal data, tokens or amounts are never logged. | Remote |
| REPO-09 | Observation reads from local storage only. | Offline-first rules |
| REPO-10 | A refresh fetches from the network, then writes local storage in one transaction. On failure it returns the mapped domain error and leaves local data untouched. | Offline-first rules |
| REPO-11 | One source of truth: network data never goes straight to the caller when the same data is observed from local storage. | Offline-first rules |
| REPO-12 | One-shot reads that business rules need return `Either` and map storage failures to the domain error, so a use case never receives a storage exception. | Offline-first rules |
| REPO-13 | Every change operation is remote-first or local-first, and the reply says which. Remote first means calling the backend, then storing the confirmed result locally; it is the default for anything the backend must validate or authorize (money, permissions, server-side rules). | Offline-first rules |
| REPO-14 | Local-first changes are only for user-owned data where a later conflict is acceptable, and only if the project has a sync mechanism. The change and its pending marker are written in one transaction, and the project's sync mechanism delivers it with its retries. A refresh never overwrites or deletes a row that still has a pending change. | Offline-first rules |
| REPO-15 | A timeout or dropped connection on a mutation is an unknown outcome: the server may have applied it. Mutations are never retried automatically: refresh the resource, and send the backend's idempotency key when the API has one. A local write failure after a remote success does not undo the server change. | Offline-first rules |
| REPO-16 | Refreshes and mutations of the same resource are serialized with one per-resource lock (the project's mechanism, or a `Mutex` per resource) held across the network call and the local write of both. When responses carry a version or `updatedAt`, writes older than the local row are skipped. | Offline-first rules |
| REPO-17 | Background sync uses the project's existing mechanism (for example a WorkManager worker). No new scheduler is created inside the feature; a missing one is reported. | Offline-first rules |
| REPO-18 | Every network error, validation failure and expected storage failure is mapped to the interface's domain error with an exhaustive `when`. Only the storage's exception type is caught (the database driver's exception for Room, `IOException` for DataStore writes with `edit` or `updateData`), never `Exception` or `Throwable`. The domain never sees `NetworkError`, `IOException`, database exceptions or HTTP codes. | Errors and threading |
| REPO-19 | Repositories are main-safe. They switch to the injected dispatcher only for blocking work or heavy mapping, and never hardcode `Dispatchers.IO`. | Errors and threading |
| REPO-20 | `CancellationException` is never caught, directly or through `catch (e: Exception)` or `runCatching`. | Errors and threading |
| REPO-21 | `suspend` calls stay outside the `Either` combinators' lambdas (branch with `when` and early returns); `map` and `fold` are used only for non-suspending steps, or when they are checked to be `inline`. | Repository |
| REPO-22 | The implementation is bound to its domain interface with `@Binds`. `@Provides` is used only for what `@Inject` cannot build (the API definition, a DAO taken from the database). | Hilt |
| REPO-23 | A repository is `@Singleton` only when it holds state (an in-memory cache, a `Mutex`); otherwise it is unscoped, unless the project does otherwise. | Hilt |
| REPO-24 | Repository tests use fake data sources, or an in-memory database as described in data-room, and cover: a successful refresh writes local data and observers emit it; a failed refresh returns the mapped error and leaves local data unchanged; each network error maps to the expected domain error. Mapper tests cover DTO edge cases: missing fields, unknown enum values, empty lists. | Tests |
| REPO-25 | The final report lists, for each change operation, whether it is remote-first or local-first. | Before finishing |
| REPO-26 | Before writing, read the project's network helper, its `Either` and functions, how it injects dispatchers (a qualifier such as `@IoDispatcher`) and its application `CoroutineScope` if any, the shared HTTP client and how features create API definitions from it, and the existing repositories in the module. | Read before writing |
| REPO-27 | Room entities, DAOs and migrations also follow data-room, and DataStore also follows data-datastore. Use cases and screens are out of scope. | Description |
