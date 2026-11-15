---
name: data-room
description: "Team pattern for Room in the data layer of an Android feature: entities, DAOs, queries, relations, transactions, type converters, schema export, migrations and their tests, for Room 3 (androidx.room3) and Room 2. Use it before creating or changing an entity, a DAO or query, the database class or its version, or a migration, or before adding Room to a module, even when the task is a ticket or plan that already lists the steps. Use it together with data-repository when the change is part of a repository. Not for key-value settings (data-datastore). Also for requests in Spanish such as base de datos, tabla, entidad, DAO, consulta, migración, Room."
---

# Room

Room is the local source of truth of offline-first features. A mistake here deletes user data, so this skill is strict about versions, schemas and migrations.

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

## Scope

- Entities, DAOs and their mappers live in the feature's data package.
- Before writing, find the `@Database` class that will hold them. If it is in this module, keep entities and DAOs `internal`. If it is in another module, that module cannot see `internal` types, so a registration snippet with them would not compile: report the visibility conflict, and how the project already solves it if it does, instead of writing that snippet.
- Do not edit other modules.

## Step 0: which Room

Read the version catalog (`gradle/libs.versions.toml`) and the build files.

| You find | Do |
| :--- | :--- |
| `androidx.room3:*` | Follow the Room 3 rules below |
| `androidx.room:*` | Follow the Room 2 notes below. Do not migrate to Room 3 as part of another task |
| No Room yet | Use Room 3, the current stable major. Confirm the latest 3.x with `android studio version-lookup` or `android docs search "Room 3"` when Android CLI is available. Adding Room to the project is a change outside the feature: report it |

Never mix both majors in the same database.

## Room 3 essentials

Room 3 changed APIs that models trained on Room 2 get wrong. When unsure about one, check `android docs search` before writing it.

| Topic | Room 3 |
| :--- | :--- |
| Packages and artifacts | `androidx.room3.*`; `androidx.room3:room3-runtime`, `ksp("androidx.room3:room3-compiler")`, `room3-testing`, `room3-paging` |
| Code generation | KSP only, no KAPT. Generates Kotlin only |
| Driver | Required. On Android: `.setDriver(AndroidSQLiteDriver())`, from `androidx.sqlite:sqlite-framework` |
| DAO functions | `suspend`, or returning `Flow` or a registered return type. No blocking DAO functions |
| Threads | No `Executor`. Use `setQueryCoroutineContext(...)` on the builder when a specific dispatcher is needed |
| Transactions | `@Transaction` on DAO functions, or `database.withWriteTransaction { }`, which replaces `runInTransaction` |
| Raw access | `useReaderConnection { }` and `useWriterConnection { }` give a `Transactor` with suspending prepared-statement functions (`usePrepared`). Migrations receive a `SQLiteConnection` instead; do not mix the two. No `SupportSQLiteDatabase` or `Cursor`, except through `room3-sqlite-wrapper` for legacy code |
| Migrations | `Migration(from, to)` overriding `suspend fun migrate(connection: SQLiteConnection)`; run SQL with `connection.execSQL(...)` |
| Paging | Register `@DaoReturnTypeConverters(PagingSourceDaoReturnTypeConverter::class)` on the DAO or database (`room3-paging`) |
| Observing outside DAOs | `database.invalidationTracker.createFlow("table")`. Observer classes were removed |
| Schemas | Gradle plugin `id("androidx.room3")` with `room3 { schemaDirectory("$projectDir/schemas") }` |
| Version | 3.0.3 or later: 3.0.2 fixes a deadlock in `@Transaction` suspend functions with `AndroidSQLiteDriver`, and 3.0.3 fixes a regression in `@Transaction` wrapper functions |

## Room 2 notes (existing projects only)

- Packages `androidx.room.*`, compiler through KSP, Gradle plugin `androidx.room` with `room { schemaDirectory(...) }`.
- Prefer `suspend` and `Flow` DAO functions anyway.
- Write migrations with the signature the project already uses (`SupportSQLiteDatabase` or `SQLiteConnection`).

## Entities and DAOs

```kotlin
@Entity(
    tableName = "orders",
    indices = [Index("customer_id")],
)
internal data class OrderEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "customer_id") val customerId: String,
    @ColumnInfo(name = "status") val status: String,
    @ColumnInfo(name = "updated_at") val updatedAt: Long,
)

@Dao
internal interface OrderDao {

    @Query("SELECT * FROM orders WHERE id = :id")
    fun observeById(id: String): Flow<OrderEntity?>

    @Query("SELECT * FROM orders WHERE customer_id = :customerId ORDER BY updated_at DESC")
    fun observeByCustomer(customerId: String): Flow<List<OrderEntity>>

    @Upsert
    suspend fun upsert(order: OrderEntity)

    @Upsert
    suspend fun upsertAll(orders: List<OrderEntity>)

    @Query("DELETE FROM orders WHERE customer_id = :customerId")
    suspend fun deleteByCustomer(customerId: String)

    @Transaction
    suspend fun replaceForCustomer(customerId: String, orders: List<OrderEntity>) {
        deleteByCustomer(customerId)
        upsertAll(orders)
    }
}
```

- Entities mirror storage, not the screen and not the API. Map DTO to entity and entity to domain in the data package. Entities never leave it.
- Table and column names are explicit, in `snake_case`, so that renaming a Kotlin property never renames a column by accident.
- The primary key is the backend id when there is one.
- Index every column used in `WHERE`, `JOIN` or as a foreign key.
- Store enums as stable strings or codes, never ordinals. Store dates as epoch milliseconds unless the project has a converter.
- Observable queries return `Flow`; one-shot operations are `suspend`. Use `@Upsert` to write network refreshes.
- Writes that must succeed together go in one `@Transaction` function.
- A refresh that replaces rows keeps the rows that have unsynced local changes (see data-repository). Never delete or overwrite them from a network response.
- Lists over large tables use paging instead of loading every row.
- The database is a single `@Singleton` built where the project builds it, and DAOs are provided from it.

## Schema and migrations

Any change to an entity (new table, column, index, type or name) changes the schema:

1. Bump `version` in `@Database`.
2. Add the migration:
   - `AutoMigration(from = N, to = N + 1)` in `@Database(autoMigrations = [...])` for additive changes: a new table, a new nullable column, a column with a default value. Renames and deletions need an `AutoMigrationSpec` (`@RenameColumn`, `@DeleteColumn`, `@RenameTable`, `@DeleteTable`).
   - A manual `Migration(N, N + 1)` for anything Room cannot infer, such as transforming data or splitting a table.
3. Generate the schema JSON for the new version and include it in the change.
4. Write the migration test.

```kotlin
internal val MIGRATION_3_4 = object : Migration(3, 4) {
    override suspend fun migrate(connection: SQLiteConnection) {
        connection.execSQL("ALTER TABLE orders ADD COLUMN note TEXT")
    }
}
```

- `exportSchema` stays `true` and schema files are committed. They are the only record of what users have on their devices, and auto-migrations and migration tests read them.
- Never use `fallbackToDestructiveMigration()` in builds that reach users: it deletes their data at the first missing migration. If a destructive path is really intended for specific old versions, use `fallbackToDestructiveMigrationFrom(...)` for those versions only and say so in the report.
- Never edit a migration or a schema file that has already shipped. Add a new version instead.

## Tests

- DAO tests against an in-memory database built with the same driver: insert, observe, upsert and delete, and check that `Flow` queries emit after each write.
- Migration tests with `MigrationTestHelper` (`room3-testing` on Room 3), usually as instrumented tests. Create the database at the old version, insert realistic rows, run the migrations to the new version and assert that the rows survived. Write one test per migration, plus one from the oldest supported version to the latest.

```kotlin
@Test
fun migrate3To4_keepsOrders() = runTest {
    helper.createDatabase(3).use { connection ->
        connection.execSQL(
            "INSERT INTO orders (id, customer_id, status, updated_at) VALUES ('1', 'c1', 'OPEN', 0)"
        )
    }
    helper.runMigrationsAndValidate(4, listOf(MIGRATION_3_4)).use { connection ->
        connection.prepare("SELECT status, note FROM orders WHERE id = '1'").use { statement ->
            assertTrue(statement.step())
            assertEquals("OPEN", statement.getText(0))
            assertTrue(statement.isNull(1))
        }
    }
}
```

Build `helper` with the project's database class, the same driver and the schema location, using the `MigrationTestHelper` constructor that matches the test type.

## Before finishing

Check the code you wrote:

- The right Room major, with no mixed artifacts or imports.
- Entities and DAOs never leave the data package, and are `internal` when the database is in this module.
- Explicit table and column names; indices on filtered and foreign key columns.
- Version bumped, migration added, schema file generated and included, migration test written.
- No `fallbackToDestructiveMigration()`.
- Changes to the `@Database` class or build files outside the module are in the report with their snippets.

Build and run the tests: `testDebugUnitTest` for DAO tests, and `connectedDebugAndroidTest` for migration tests when a device or Gradle Managed Device is available. Say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

End the reply with:

- What was created or changed, by file.
- "Changes needed outside this module": each one with the module, the reason and the snippet. Write "None" if there are none.
- The schema version change and the migrations added, or "No schema change".
