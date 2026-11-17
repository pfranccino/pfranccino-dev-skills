# Schema and migrations

Part of the data-room skill. Read it before changing an entity, the `@Database` class or its version.

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

## Migration tests

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
