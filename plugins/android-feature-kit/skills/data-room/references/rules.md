# data-room rules

Every normative rule of the data-room skill, with a stable ID. Reviews cite these IDs, and the skill's "Before finishing" checklist points to them. The Source column names the section of `SKILL.md`, or of `references/migrations.md`, that explains the rule. When a rule changes there, change it here too. IDs are never reused.

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

## Room rules

| ID | Rule | Source |
| :--- | :--- | :--- |
| ROOM-01 | Entities, DAOs and their mappers live in the feature's data package. Other modules are not edited (KIT-04). | Scope |
| ROOM-02 | Before writing, find the `@Database` class that will hold them. If it is in this module, entities and DAOs are `internal`. If it is in another module, that module cannot see `internal` types: report the visibility conflict, and how the project already solves it if it does, instead of writing a registration snippet that would not compile. | Scope |
| ROOM-03 | Read the version catalog and build files and use the Room major the project uses: `androidx.room3:*` follows the Room 3 rules; `androidx.room:*` follows the Room 2 notes and is not migrated to Room 3 as part of another task; with no Room yet, use Room 3, confirm the latest 3.x with `android studio version-lookup` or `android docs search "Room 3"` when Android CLI is available, and report adding Room as a change outside the feature. Never mix both majors in one database. | Step 0: which Room |
| ROOM-04 | Room 3 APIs: packages `androidx.room3.*` and artifacts `room3-runtime`, `room3-compiler` (KSP only, no KAPT), `room3-testing`, `room3-paging`; a driver is set (`.setDriver(AndroidSQLiteDriver())` on Android); DAO functions are `suspend`, return `Flow` or a registered return type, never blocking; no `Executor` (use `setQueryCoroutineContext` when a specific dispatcher is needed); transactions use `@Transaction` or `withWriteTransaction`, which replaces `runInTransaction`; `useReaderConnection` and `useWriterConnection` give a `Transactor`, migrations receive a `SQLiteConnection`, and the two are not mixed; no `SupportSQLiteDatabase` or `Cursor` except through `room3-sqlite-wrapper` for legacy code; migrations are `Migration(from, to)` overriding `suspend fun migrate(connection: SQLiteConnection)` with `connection.execSQL(...)`; paging registers `@DaoReturnTypeConverters(PagingSourceDaoReturnTypeConverter::class)`; observation outside DAOs uses `invalidationTracker.createFlow`; schemas use the Gradle plugin `id("androidx.room3")` with `room3 { schemaDirectory("$projectDir/schemas") }`. When unsure about a Room 3 API, check `android docs search` before writing it. | Room 3 essentials |
| ROOM-05 | Room 3 is at version 3.0.3 or later. | Room 3 essentials |
| ROOM-06 | On Room 2: packages `androidx.room.*`, compiler through KSP, Gradle plugin `androidx.room` with `room { schemaDirectory(...) }`; DAO functions are still `suspend` and `Flow`; migrations use the signature the project already uses (`SupportSQLiteDatabase` or `SQLiteConnection`). | Room 2 notes |
| ROOM-07 | Entities mirror storage, not the screen and not the API. DTO to entity and entity to domain mapping happens in the data package. Entities and DAOs never leave the data package. | Entities and DAOs |
| ROOM-08 | Table and column names are explicit and in `snake_case`, so renaming a Kotlin property never renames a column. | Entities and DAOs |
| ROOM-09 | The primary key is the backend id when there is one. | Entities and DAOs |
| ROOM-10 | Every column used in `WHERE`, in a `JOIN` or as a foreign key is indexed. | Entities and DAOs |
| ROOM-11 | Enums are stored as stable strings or codes, never ordinals. Dates are stored as epoch milliseconds unless the project has a converter. | Entities and DAOs |
| ROOM-12 | Observable queries return `Flow`; one-shot operations are `suspend`. Network refreshes are written with `@Upsert`. | Entities and DAOs |
| ROOM-13 | Writes that must succeed together are in one `@Transaction` function. | Entities and DAOs |
| ROOM-14 | A refresh that replaces rows keeps the rows that have unsynced local changes (data-repository); a network response never deletes or overwrites them. | Entities and DAOs |
| ROOM-15 | Lists over large tables use paging instead of loading every row. | Entities and DAOs |
| ROOM-16 | The database is a single `@Singleton` built where the project builds it, and DAOs are provided from it. | Entities and DAOs |
| ROOM-17 | Any change to an entity (new table, column, index, type or name) bumps `version` in `@Database` and adds a migration: `AutoMigration(from = N, to = N + 1)` for additive changes (a new table, a new nullable column, a column with a default value); an `AutoMigrationSpec` (`@RenameColumn`, `@DeleteColumn`, `@RenameTable`, `@DeleteTable`) for renames and deletions; a manual `Migration(N, N + 1)` for anything Room cannot infer, such as transforming data or splitting a table. The schema JSON for the new version is generated and included, and a migration test is written. | Schema and migrations (`references/migrations.md`) |
| ROOM-18 | `exportSchema` stays `true` and schema files are committed. | Schema and migrations |
| ROOM-19 | `fallbackToDestructiveMigration()` is never used in builds that reach users. If a destructive path is really intended for specific old versions, `fallbackToDestructiveMigrationFrom(...)` is used for those versions only and the report says so. | Schema and migrations; `references/migrations.md` |
| ROOM-20 | A migration or schema file that has already shipped is never edited; a new version is added instead. | Schema and migrations |
| ROOM-21 | DAO tests run against an in-memory database built with the same driver, covering insert, observe, upsert and delete, and check that `Flow` queries emit after each write. | Tests |
| ROOM-22 | Each migration has a `MigrationTestHelper` test (`room3-testing` on Room 3), usually instrumented: create the database at the old version, insert realistic rows, run the migrations to the new version and assert the rows survived. One test per migration, plus one from the oldest supported version to the latest. `helper` is built with the project's database class, the same driver and the schema location, using the constructor that matches the test type. | Migration tests (`references/migrations.md`) |
| ROOM-23 | The final report states the schema version change and the migrations added, or "No schema change". | Before finishing |
| ROOM-24 | data-room is used together with data-repository when the change is part of a repository. Key-value settings belong to data-datastore. | Description |
| ROOM-25 | Before finishing, DAO tests run with `testDebugUnitTest`, and migration tests with `connectedDebugAndroidTest` when a device or Gradle Managed Device is available; the report says which could not run. | Before finishing |
