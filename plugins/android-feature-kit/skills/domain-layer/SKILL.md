---
name: domain-layer
description: "Team pattern for the domain layer of an Android feature, kept as a pure Kotlin package inside the feature module: use cases, business rules and validation, domain models, repository interfaces and domain errors returned with the project's own Either. Use it before writing or changing a use case, a business rule, a validation, a domain model, a repository contract or a domain error, even when the task is a ticket or plan that already lists the steps. Not for repository implementations, network, Room or DataStore (data skills) and not for ViewModels or screens. Also for requests in Spanish such as caso de uso, lógica de negocio, regla de negocio, validación, modelo de dominio, contrato de repositorio, error de dominio."
---

# Domain layer

Writes the business core of one feature: what the feature knows (models), what it needs from outside (repository interfaces), what can go wrong in business terms (errors) and what it does (use cases).

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

## Scope

- Work in the domain package of one feature module. Infer the module from the paths the user gave; ask only if more than one module fits.
- Domain code shared by several features lives where the project already keeps it. Read it; do not copy it into the feature.
- Do not edit other modules. If the work needs a change outside the module, list it at the end under "Changes needed outside this module" with the exact snippet.
- Follow the module's existing naming and style over the examples here.

## The dependency rule

The domain package depends on nothing in data or presentation, and on nothing Android.

- Allowed imports: the Kotlin standard library, `kotlinx.coroutines` (for `Flow`), `javax.inject`, the project's `Either`, and other domain packages.
- Not allowed: `android.*`, `androidx.*`, anything from the feature's `data` or `presentation` packages, serialization, Room, network or Hilt module annotations.

The domain has to stay testable on the JVM and stable while data sources and screens change around it. Data implements domain interfaces and presentation calls domain use cases, so every dependency points inward.

The layers are packages, not Gradle modules, so the compiler does not enforce this rule. Check it yourself before finishing (last section).

## Read before writing

- The project's `Either`: its name, which side holds the error and its functions (`map`, `flatMap`, `fold`, `mapLeft` or their equivalents). Use it for every operation that can fail. Do not signal expected failures with `kotlin.Result`, nullable returns or exceptions, and do not add another functional library.
- Existing domain models and errors in the feature and in shared domain code.

If the project has no `Either` yet, ask the user where it should live before writing anything that depends on it.

## Models

```kotlin
internal data class Order(
    val id: OrderId,
    val status: OrderStatus,
    val itemCount: Int,
)

@JvmInline
internal value class OrderId(val value: String)

internal enum class OrderStatus { Open, Shipped, Delivered, Cancelled }
```

- Immutable. Named by business meaning, not by the API field or the table column.
- No serialization, Room or network annotations, and no formatting for display.
- Identifiers and values that carry rules get their own types when the module already does so, instead of loose `String` or `Double`.

## Repository interfaces

The contract that the data package implements. Features are offline-first: the app observes local data and refreshes it from the network. A repository therefore has three kinds of functions:

```kotlin
internal interface OrderRepository {
    fun observeOrder(id: OrderId): Flow<Order?>
    suspend fun getOrder(id: OrderId): Either<OrderError, Order>
    suspend fun refreshOrder(id: OrderId): Either<OrderError, Unit>
    suspend fun cancelOrder(id: OrderId): Either<OrderError, Unit>
}
```

- Observing returns a `Flow` of domain models read from local storage, without `Either`. Missing data is `null` or an empty list, and network failures belong to the refresh. Local read failures are rare and unexpected; the ViewModel protects its collection (see feature-ui-compose).
- One-shot reads that a business rule needs (`getOrder`) are `suspend` and return `Either`, so a use case never receives a storage exception.
- Refreshing and changing data are `suspend` functions that return `Either<FeatureError, T>`.
- Parameters and results are domain types only: no DTOs, entities or response wrappers.
- Name functions by what they mean to the business (`cancelOrder`), not by the endpoint or the query.

## Errors

```kotlin
internal sealed interface OrderError {
    data object NotFound : OrderError
    data object AlreadyDelivered : OrderError
    data object NoConnection : OrderError
    data object Unexpected : OrderError
}
```

- One sealed type per feature, or per use case when it has its own failure modes. Each case is named by business meaning.
- No exceptions, HTTP codes or user-facing messages inside. The data layer maps technical failures to these cases and presentation maps these cases to text.
- Reuse shared errors (no connection, session expired) when the project already defines them.

## Use cases

```kotlin
internal class CancelOrderUseCase @Inject constructor(
    private val repository: OrderRepository,
) {
    suspend operator fun invoke(id: OrderId): Either<OrderError, Unit> {
        val order = when (val result = repository.getOrder(id)) {
            is Either.Left -> return result
            is Either.Right -> result.value
        }
        if (order.status == OrderStatus.Delivered) return OrderError.AlreadyDelivered.left()
        return repository.cancelOrder(id)
    }
}

internal class ObserveOrderUseCase @Inject constructor(
    private val repository: OrderRepository,
) {
    operator fun invoke(id: OrderId): Flow<Order?> = repository.observeOrder(id)
}
```

`Either.Left`, `.value` and `.left()` stand for the project's `Either` API. The use case takes an id and reads the current state itself, so callers never need to hold domain models to call it.

- One public `operator fun invoke`: `suspend` for one-shot work, returning `Flow` for observation.
- Named verb + noun + `UseCase`: `CancelOrderUseCase`, `ObserveOrderUseCase`.
- Constructor injection with `@Inject`. A use case needs no Hilt module.
- No mutable state, no caches, no `CoroutineScope`. Do not switch dispatchers around repository calls, which are already main-safe. Move CPU-heavy domain work (sorting or calculating over large collections, parsing) to the project's injected dispatcher; never hardcode `Dispatchers`.
- Business rules and validation live here. Expected failures return a `Left`; they are not thrown.
- Never catch `CancellationException`, directly or through `catch (e: Exception)` or `runCatching`.
- A use case may call other use cases. It never calls a data source or a repository implementation.
- Every ViewModel call goes through a use case, even when it only forwards to the repository, as `ObserveOrderUseCase` does. A one-line use case is fine: it keeps presentation away from repositories.
- `internal` unless another module needs it. Making it public changes the module's contract, so report it.

## Tests

- JVM unit tests with a fake repository that implements the interface, in the test source set. No mocking library is needed for interfaces the team owns.
- Cover the `Right` path and every `Left` the use case can produce, including each rule it enforces.
- Use `runTest`.

## Before finishing

Search the domain package for forbidden imports, with the Grep tool or ripgrep:

```
rg -n "^import (android|androidx)\.|\.data\.|\.presentation\." <module>/src/main/<package path>/domain
```

Adjust the package names in the pattern to the module's real ones, and confirm that each match is a real violation before changing it.

Check the code you wrote. `references/rules.md` in this skill's folder lists every rule of this skill with a stable ID (DOM-01 to DOM-22, plus the kit-wide KIT-01 to KIT-07); reviews cite those IDs.

- No forbidden imports in the domain package (DOM-03).
- Models are immutable and have no framework annotations (DOM-05).
- Repository interfaces use domain types only. Observation returns `Flow`; changes and refreshes return `Either` (DOM-07 to DOM-10).
- Errors are a sealed type named by business meaning (DOM-11).
- Use cases have one `invoke`, no state, no hardcoded dispatcher and no swallowed cancellation, and their rules are covered by tests (DOM-12 to DOM-15, DOM-19).

Build and test the module, for example `.\gradlew.bat :feature:orders:testDebugUnitTest`, and say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

End the reply with:

- What was created or changed, by file.
- "Changes needed outside this module": each one with the module, the reason and the snippet. Write "None" if there are none.
- Any change to a repository interface, domain model or domain error, since both data and presentation depend on them.
