# domain-layer rules

Every normative rule of the domain-layer skill, with a stable ID. Reviews cite these IDs, and the skill's "Before finishing" checklist points to them. The Source column names the section of `SKILL.md` that explains the rule. When a rule changes in `SKILL.md`, change it here too. IDs are never reused.

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

## Domain rules

| ID | Rule | Source |
| :--- | :--- | :--- |
| DOM-01 | Work in the domain package of one feature module. Domain code shared by several features stays where the project keeps it: read it, do not copy it into the feature. | Scope |
| DOM-02 | Do not edit other modules (KIT-04). | Scope |
| DOM-03 | The domain package imports only the Kotlin standard library, `kotlinx.coroutines` (for `Flow`), `javax.inject`, the project's `Either` and other domain packages. Never `android.*`, `androidx.*`, anything from the feature's `data` or `presentation` packages, serialization, Room, network or Hilt module annotations. | The dependency rule |
| DOM-04 | Every operation that can fail uses the project's `Either`. Expected failures are not signaled with `kotlin.Result`, nullable returns or exceptions, and no other functional library is added. If the project has no `Either` yet, ask where it should live before writing anything that depends on it. | Read before writing |
| DOM-05 | Domain models are immutable and named by business meaning, not by the API field or the table column. They carry no serialization, Room or network annotations and no formatting for display. | Models |
| DOM-06 | Identifiers and values that carry rules get their own types when the module already does so, instead of loose `String` or `Double`. | Models |
| DOM-07 | Repository observation returns a `Flow` of domain models read from local storage, without `Either`. Missing data is `null` or an empty list, and network failures belong to the refresh. Local read failures are rare and unexpected; the ViewModel protects its collection (feature-ui-compose). | Repository interfaces |
| DOM-08 | One-shot reads that a business rule needs are `suspend` and return `Either`, so a use case never receives a storage exception. | Repository interfaces |
| DOM-09 | Refresh and change functions are `suspend` and return `Either<FeatureError, T>`. | Repository interfaces |
| DOM-10 | Repository parameters and results are domain types only (no DTOs, entities or response wrappers), and functions are named by what they mean to the business, not by the endpoint or the query. | Repository interfaces |
| DOM-11 | Errors are one sealed type per feature, or per use case when it has its own failure modes, with each case named by business meaning. No exceptions, HTTP codes or user-facing messages inside. Shared errors (no connection, session expired) are reused when the project already defines them. | Errors |
| DOM-12 | A use case has one public `operator fun invoke` (`suspend` for one-shot work, returning `Flow` for observation), is named verb + noun + `UseCase`, and uses constructor injection with `@Inject` and no Hilt module. | Use cases |
| DOM-13 | Use cases hold no mutable state, caches or `CoroutineScope`, and do not switch dispatchers around repository calls, which are already main-safe. CPU-heavy domain work (sorting or calculating over large collections, parsing) runs on the project's injected dispatcher; `Dispatchers` is never hardcoded. | Use cases |
| DOM-14 | Business rules and validation live in use cases. Expected failures return a `Left`; they are not thrown. | Use cases |
| DOM-15 | `CancellationException` is never caught, directly or through `catch (e: Exception)` or `runCatching`. | Use cases |
| DOM-16 | A use case may call other use cases. It never calls a data source or a repository implementation. | Use cases |
| DOM-17 | Every ViewModel call goes through a use case, even one that only forwards to the repository. | Use cases |
| DOM-18 | Use cases are `internal` unless another module needs them. Making one public changes the module's contract and is reported. | Use cases |
| DOM-19 | Use cases have JVM unit tests in the test source set, with a fake repository that implements the interface (no mocking library is needed for interfaces the team owns), run with `runTest`, covering the `Right` path and every `Left` the use case can produce, including each rule it enforces. | Tests |
| DOM-20 | The final report lists every change to a repository interface, domain model or domain error, because both data and presentation depend on them. | Before finishing |
| DOM-21 | Before writing, read the project's `Either` (its name, which side holds the error and its functions such as `map`, `flatMap`, `fold`, `mapLeft` or their equivalents) and the existing domain models and errors in the feature and in shared domain code. | Read before writing |
| DOM-22 | Before finishing, search the domain package for forbidden imports with Grep or ripgrep (`rg -n "^import (android\|androidx)\.\|\.data\.\|\.presentation\." <module>/src/main/<package path>/domain`), with the package names adjusted to the module's real ones, and confirm each match is a real violation before changing it. | Before finishing |
