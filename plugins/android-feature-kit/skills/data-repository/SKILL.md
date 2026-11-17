---
name: data-repository
description: "Team pattern for the offline-first data layer of an Android feature module: repository implementations, remote data sources, API definitions and DTOs, mappers, network calls that return the project's own Either, mapping technical failures to domain errors, refresh and sync, and Hilt bindings. Use it before writing or changing a repository implementation, an API call, an endpoint, a DTO, a mapper, a data source, caching or sync, even when the task is a ticket or plan that already lists the steps. Repository interfaces belong to domain-layer. For Room entities, DAOs and migrations also use data-room; for DataStore also use data-datastore. Not for use cases or screens. Also for requests in Spanish such as repositorio, capa de datos, llamada a la API, servicio, endpoint, DTO, mapper, caché, sincronización, offline."
---

# Data layer, offline-first

Implements the domain's repository interfaces for one feature. Local storage is the source of truth that the app observes, and the network keeps it up to date.

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

## Scope

- Work in the data package of one feature module. Infer the module from the paths the user gave; ask only if more than one module fits.
- Implement interfaces declared in the feature's domain package. If the interface does not exist yet, write it first following domain-layer. When you work only on the data layer (for example as the kit's `data` agent), do not write it: stop and ask for it, with the signatures you need.
- Do not edit other modules (the shared HTTP client, the database class, app-level DI). If the work needs a change there, list it at the end under "Changes needed outside this module" with the exact snippet.
- Follow the module's existing naming and style over the examples here.

## Read before writing

- The project's network helper: the function that executes a call and returns `Either` with the network error type. Every remote call goes through it.
- The project's `Either` and its functions.
- How the project injects dispatchers (a qualifier such as `@IoDispatcher`) and its application `CoroutineScope`, if any.
- The shared HTTP client and how features create their API definitions from it.
- Existing repositories in the module.

If the network helper or the `Either` does not exist yet, ask the user where it should live. Do not write a private one inside the feature.

## Layout and visibility

```
data/
├─ remote/   OrderApi, OrderDto, OrderRemoteDataSource
├─ local/    OrderEntity and OrderDao (data-room), or a DataStore source (data-datastore)
├─ mapper/   OrderDto.toEntity(), OrderEntity.toDomain()
├─ OrderRepositoryImpl
└─ di/       OrderDataModule
```

Use the module's own package names if they differ.

Everything in the data package is `internal`. No DTO, entity, data source or network error type is visible outside it; the rest of the feature only sees the domain interface.

## Remote

```kotlin
internal class OrderRemoteDataSource @Inject constructor(
    private val api: OrderApi,
) {
    suspend fun fetchOrder(id: String): Either<NetworkError, OrderDto> =
        safeApiCall { api.getOrder(id) }
}
```

`safeApiCall` and `NetworkError` stand for the project's helper and error type.

- The API definition returns DTOs. The data source wraps each call with the network helper and returns `Either<NetworkError, Dto>`. It does not throw, and it does not add its own try/catch around calls.
- DTOs mirror the backend, and fields the backend may omit are nullable. Serialization annotations are allowed in the data package (network DTOs, typed DataStore models), never in domain models.
- Mapping a DTO validates what the domain requires. A missing required field becomes an error, not a crash and not a silent default.
- Do not log request or response bodies that contain personal data, tokens or amounts.

## Repository

An excerpt: `cancelOrder`, the per-resource lock (`orderLocks`) and the DAO functions it calls (`findById`, `upsertIfNotPending`) are not shown.

```kotlin
internal class OrderRepositoryImpl @Inject constructor(
    private val remote: OrderRemoteDataSource,
    private val dao: OrderDao,
) : OrderRepository {

    override fun observeOrder(id: OrderId): Flow<Order?> =
        dao.observeById(id.value).map { entity -> entity?.toDomain() }

    override suspend fun getOrder(id: OrderId): Either<OrderError, Order> {
        val entity = try {
            dao.findById(id.value)
        } catch (e: SQLiteException) {
            return OrderError.Unexpected.left()
        } ?: return OrderError.NotFound.left()
        return entity.toDomain().right()
    }

    override suspend fun refreshOrder(id: OrderId): Either<OrderError, Unit> =
        orderLocks.withLock(id) {
            val dto = when (val response = remote.fetchOrder(id.value)) {
                is Either.Left -> return@withLock response.value.toOrderError().left()
                is Either.Right -> response.value
            }
            val entity = dto.toEntityOrNull() ?: return@withLock OrderError.Unexpected.left()
            try {
                dao.upsertIfNotPending(entity)
            } catch (e: SQLiteException) {
                return@withLock OrderError.Unexpected.left()
            }
            Unit.right()
        }

    // cancelOrder: remote first, under the same lock, then store the confirmed result.
}

private fun NetworkError.toOrderError(): OrderError = when (this) {
    NetworkError.NoConnection, NetworkError.Timeout -> OrderError.NoConnection
    is NetworkError.Http -> if (code == 404) OrderError.NotFound else OrderError.Unexpected
    NetworkError.Serialization, NetworkError.Unknown -> OrderError.Unexpected
}
```

`Either.Left`, `.value`, `.left()` and `.right()` stand for the project's `Either` API, and `SQLiteException` for the exception type of the database driver the project uses. `orderLocks` is a per-resource lock (see the offline-first rules). Branching with `when` and early returns keeps `suspend` calls outside lambdas, so it works whether or not the project's `map` and `fold` are `inline`. Use those combinators only for non-suspending steps, or when you have checked they are `inline`.

### Offline-first rules

- **Observe from local only.** The screen gets cached data immediately and updates whenever local storage changes.
- **Refresh writes local.** Fetch from the network, then write to local storage in one transaction. On failure, return the mapped domain error and leave local data untouched.
- **One source of truth.** Never hand network data straight to the caller when the same data is observed from local storage: the screen would show two versions of the truth.
- **One-shot reads** that business rules need (`getOrder`) return `Either` and map storage failures to the domain error, so a use case never receives a storage exception.
- **Changes: choose per operation, and state the choice in your reply.**
  - Remote first, then store the confirmed result locally. This is the default for anything the backend must validate or authorize: money, permissions, server-side rules.
  - Local first, with a pending sync. Only for user-owned data where a later conflict is acceptable, and only if the project has a sync mechanism. Write the change and its pending marker in one transaction, and let the project's sync mechanism deliver it with its retries. A refresh never overwrites or deletes a row that still has a pending change.
- **Unknown outcomes.** A timeout or a dropped connection on a mutation is an unknown outcome: the server may have applied it. Never retry a mutation automatically. Refresh the resource, and send the backend's idempotency key when the API has one. A local write failure after a remote success does not undo the server change.
- **No stale overwrites.** Refreshes and mutations of the same resource are serialized: hold one per-resource lock (the project's mechanism, or a `Mutex` per resource) across the network call and the local write of both. Otherwise a slow refresh that started before a cancellation can store the old state after it. If responses carry a version or `updatedAt`, also skip writes older than the local row.
- **Background sync** uses the project's existing mechanism (for example a WorkManager worker). Do not create a new scheduler inside the feature; report it if one is missing.

### Errors and threading

- Map every network error, validation failure and expected storage failure to the domain error type of the interface, with an exhaustive `when`. Catch the exception type of the storage in use: the database driver's exception for Room, `IOException` for DataStore writes (`edit`, `updateData`). Never catch `Exception` or `Throwable`. The domain never sees `NetworkError`, `IOException`, database exceptions or HTTP codes.
- Repositories are main-safe. `suspend` calls from Room, Retrofit or Ktor already are. Switch to the injected dispatcher only for blocking work or heavy mapping, and never hardcode `Dispatchers.IO`.
- Never catch `CancellationException`, directly or through `catch (e: Exception)` or `runCatching`.

## Hilt

```kotlin
@Module
@InstallIn(SingletonComponent::class)
internal abstract class OrderDataModule {

    @Binds
    abstract fun bindOrderRepository(impl: OrderRepositoryImpl): OrderRepository

    companion object {
        @Provides
        fun provideOrderApi(client: SharedHttpClient): OrderApi = client.create()
    }
}
```

`SharedHttpClient` and `create()` stand for however the project builds API definitions from its shared client.

- Bind the implementation to the domain interface with `@Binds`. Use `@Provides` only for what cannot be built with `@Inject` (the API definition, a DAO taken from the database).
- Scope a repository with `@Singleton` only when it holds state (an in-memory cache, a `Mutex`); otherwise leave it unscoped. Follow the project if it does otherwise.

## Tests

- Repository tests with fake data sources, or with an in-memory database as described in data-room: a successful refresh writes local data and observers emit it; a failed refresh returns the mapped error and leaves local data unchanged; each network error maps to the expected domain error.
- Mapper tests for DTO edge cases: missing fields, unknown enum values, empty lists.

## Before finishing

Check the code you wrote. `references/rules.md` in this skill's folder lists every rule of this skill with a stable ID (REPO-01 to REPO-27, plus the kit-wide KIT-01 to KIT-07); reviews cite those IDs.

- No DTO, entity, data source or network error type is visible outside the data package (REPO-04).
- Every remote call goes through the network helper and returns `Either` (REPO-03, REPO-05).
- Observation reads from local storage, refresh writes to it, and no data reaches the caller from two sources (REPO-09 to REPO-11).
- Each change operation says whether it is remote-first or local-first. Local-first changes are stored with their pending marker in one transaction, and refresh leaves pending rows alone (REPO-13, REPO-14).
- Refreshes and mutations of the same resource share a per-resource lock. No mutation is retried automatically (REPO-15, REPO-16).
- Every failure is mapped to a domain error with an exhaustive `when`. No cancellation is swallowed and no dispatcher is hardcoded (REPO-18 to REPO-20).
- The repository is bound to its domain interface with `@Binds` (REPO-22).

Build and test the module, for example `.\gradlew.bat :feature:orders:compileDebugKotlin :feature:orders:testDebugUnitTest`, and say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

End the reply with:

- What was created or changed, by file.
- "Changes needed outside this module": each one with the module, the reason and the snippet. Write "None" if there are none.
- For each change operation, whether it is remote-first or local-first.
