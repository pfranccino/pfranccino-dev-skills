---
name: data-datastore
description: "Team pattern for Jetpack DataStore in the data layer of an Android feature: choosing Preferences, typed DataStore or Room, one instance per file at application scope, the DataStore.Builder API of DataStore 1.3, serializers and corruption handling, encryption with datastore-tink, migration from SharedPreferences, Hilt wiring and tests. Use it before storing settings, flags, small user state, session or token data, or before touching an existing DataStore, even when the task is a ticket or plan that already lists the steps. Not for lists or relational data (data-room). Also for requests in Spanish such as preferencias, configuración, guardar ajustes, DataStore, SharedPreferences, guardar token o sesión."
---

# DataStore

Stores small settings and state for one feature. DataStore bugs are quiet: a second instance, a broad `catch` or a missing corruption handler loses data without a crash. This skill exists to avoid those.

Apply it even when the task arrives as a detailed plan or ticket: the plan says what to build, this skill says how the team builds it. If the plan and this skill disagree, say so and follow the plan.

Parts of this skill are adapted from the `datastore` skill in [rcosteira79/android-skills](https://github.com/rcosteira79/android-skills), itself adapted from [Meet-Miyani/compose-skill](https://github.com/Meet-Miyani/compose-skill). Both are MIT; the notices are in `NOTICE.md` next to this file.

## Scope

- The local data source that reads and writes the store lives in the feature's data package and is `internal`.
- The DataStore instance is provided once, at application scope, from a Hilt module. If the project keeps such providers outside the feature, put the snippet in the report instead of editing that module.
- Do not edit other modules. List needed changes at the end under "Changes needed outside this module" with the exact snippet.

## Read before writing

- The DataStore version in the version catalog. 1.3 or later has `DataStore.Builder` and `datastore-tink`.
- The project's application `CoroutineScope` and its Hilt qualifier (`@ApplicationScope` in the examples).
- Existing stores and their file names, so you do not reuse one by accident.

## Choose the storage

| Need | Use |
| :--- | :--- |
| A few independent flags or values (onboarding done, theme, last selected tab) | Preferences DataStore |
| One object whose fields evolve together (settings, session state) | Typed DataStore with a serializer |
| Lists, filters, anything where a `WHERE` would help, or more than one small object | Room (data-room) |
| Secrets and sensitive values (tokens, identifiers of the user) | Typed DataStore encrypted with `datastore-tink`, keys in Android Keystore. Never plain Preferences |

DataStore rewrites the whole file on every write, so keep each file small.

## Rules that prevent the common bugs

- **One instance per file per process.** A second instance on the same file throws `IllegalStateException`. Provide it once as a `@Singleton`; never build it in a composable, a ViewModel or a data source.
- **Application scope.** The store runs in an application-scoped context that has a `Job`. Never `viewModelScope`: cancelling it kills pending writes.
- **Immutable stored types.** A `data class` with `val`s, or generated Proto classes. Update with `updateData { it.copy(...) }` or `edit { }`, which are atomic.
- **Read errors: only `IOException` falls back to defaults, and observation must survive it.** `catch` ends the flow, so a collector that falls back with `catch` never sees later writes. Use `retryWhen` instead: on an `IOException`, emit the default, wait and retry a few times, then let the error reach the ViewModel's `catch` (feature-ui-compose). Rethrow everything else, so that a serializer bug is not hidden as empty settings.
- **Corruption.** Typed serializers wrap parse failures in `CorruptionException`, and every store sets a corruption handler, so one corrupt file does not break every read. Choose the policy per store: `ReplaceFileCorruptionHandler` with defaults is right for settings, and for a session it means signing in again. Data that cannot be lost does not belong in DataStore; keep it in Room or on the backend.
- **No `runBlocking`** on DataStore from the main thread. Expose `Flow` and `suspend` functions.
- **One Hilt qualifier per store** when more than one store has the same type. Two unqualified `DataStore<Preferences>` bindings fail the build.
- **Keys and file names are permanent.** Renaming a key or a file after release loses the stored value. Keys are `private` to the data source.
- **Process mode.** Do not mix single-process and multi-process DataStore on the same file. Use multi-process only when another process really shares the file.
- **Stored types stay in the data package.** The repository maps them to domain models.

## Typed DataStore (DataStore 1.3)

DataStore 1.3 recommends `DataStore.Builder` over `DataStoreFactory`. It takes a `CoroutineContext`, not a scope:

```kotlin
@Serializable
internal data class AppSettings(
    val themeMode: String = "system",
    val lastSelectedTab: String? = null,
)

internal object AppSettingsSerializer : Serializer<AppSettings> {
    override val defaultValue = AppSettings()

    override suspend fun readFrom(input: InputStream): AppSettings =
        try {
            Json.decodeFromString(input.readBytes().decodeToString())
        } catch (e: SerializationException) {
            throw CorruptionException("Cannot read app settings", e)
        }

    override suspend fun writeTo(t: AppSettings, output: OutputStream) {
        output.write(Json.encodeToString(t).encodeToByteArray())
    }
}

@Provides
@Singleton
fun provideAppSettingsStore(
    @ApplicationContext context: Context,
    @ApplicationScope scope: CoroutineScope,
): DataStore<AppSettings> =
    DataStore.Builder(
        storage = FileStorage(AppSettingsSerializer) {
            context.dataStoreFile("app_settings.json")
        },
        context = scope.coroutineContext,
    )
        .setCorruptionHandler(ReplaceFileCorruptionHandler { AppSettingsSerializer.defaultValue })
        .build()
```

This store holds nothing sensitive. A model with user identifiers, tokens or session data uses the encrypted serializer described below.

On DataStore 1.2 or earlier, use `DataStoreFactory.create(serializer, corruptionHandler, migrations, scope) { file }` with the same application scope.

## Preferences DataStore

```kotlin
@Provides
@Singleton
@OrdersPreferences
fun provideOrdersPreferences(
    @ApplicationContext context: Context,
    @ApplicationScope scope: CoroutineScope,
): DataStore<Preferences> =
    PreferenceDataStoreFactory.create(
        corruptionHandler = ReplaceFileCorruptionHandler { emptyPreferences() },
        scope = scope,
        produceFile = { context.preferencesDataStoreFile("orders_preferences") },
    )

internal class OrdersPreferencesDataSource @Inject constructor(
    @OrdersPreferences private val dataStore: DataStore<Preferences>,
) {
    val onboardingDone: Flow<Boolean> = dataStore.data
        .map { preferences -> preferences[ONBOARDING_DONE] ?: false }
        .retryWhen { cause, attempt ->
            if (cause is IOException && attempt < 3) {
                emit(false)
                delay(500L * (attempt + 1))
                true
            } else {
                false
            }
        }

    suspend fun setOnboardingDone() {
        dataStore.edit { preferences -> preferences[ONBOARDING_DONE] = true }
    }

    private companion object {
        val ONBOARDING_DONE = booleanPreferencesKey("onboarding_done")
    }
}
```

`@OrdersPreferences` is a Hilt qualifier for this store. Before writing, run `android docs search "Preferences DataStore Builder"` if Android CLI is available: if the project's version offers a builder for Preferences, prefer it.

When replacing `SharedPreferences`, pass `SharedPreferencesMigration(context, "<old file name>")` in `migrations`, and keep the old key names until the migration has shipped.

## Encryption with datastore-tink

For sensitive values, `androidx.datastore:datastore-tink` wraps an existing serializer:

```kotlin
AeadConfig.register()

val aead = AndroidKeysetManager.Builder()
    .withSharedPref(context, "session_keyset", "session_keyset_prefs")
    .withKeyTemplate(KeyTemplate.createFrom(PredefinedAeadParameters.AES256_GCM))
    .withMasterKeyUri("android-keystore://session_master_key")
    .build()
    .keysetHandle
    .getPrimitive(RegistryConfiguration.get(), Aead::class.java)

val serializer = AeadSerializer(
    aead = aead,
    wrappedSerializer = SessionSerializer,
    associatedData = "session.json".encodeToByteArray(),
)
```

`SessionSerializer` is a serializer built like `AppSettingsSerializer`, for the session model.

- Use this serializer in place of the plain one when building the store.
- `associatedData` is unique per file, so one encrypted file cannot be swapped for another.
- Decryption failures arrive as `CorruptionException`, so the corruption handler decides what happens. For a session, that usually means resetting to defaults and asking the user to sign in again.
- Building the keyset touches disk and the Keystore: do it once, inside the singleton provider.
- Exclude the encrypted file and the keyset preferences from Auto Backup and device transfer. The Keystore key does not travel with a backup, so restored ciphertext cannot be decrypted; treat a restore as signed out. The backup and data extraction rules live in the app module: put the snippet in the report.

## Tests

- Build the store on a temporary file with a unique name per test, using the test's scope (for example `backgroundScope` in `runTest`), so tests never share a file or an instance.
- Cover defaults on the first read, a write followed by a read, an `IOException` that emits defaults and recovers when the file can be read again, a corrupt file handled by the corruption policy, and, for encrypted stores, a missing or invalid key.

## Before finishing

Check the code you wrote:

- The storage choice fits the data, and the reply says why.
- One instance per file, `@Singleton`, application scope, and a qualifier when several stores share a type.
- Reads fall back only on `IOException`, through `retryWhen` so observation continues. Typed serializers throw `CorruptionException`, and each store has a corruption policy chosen for its data.
- No `runBlocking`, no `viewModelScope`, and no keys or stored types outside the data package.
- Sensitive values are encrypted with `datastore-tink`, and the encrypted files are excluded from backup.

Build and test the module, for example `.\gradlew.bat :feature:orders:testDebugUnitTest`, and say which checks you could not run.

If other team skills also apply to this task, give one combined report instead of one per skill.

End the reply with:

- What was created or changed, by file.
- "Changes needed outside this module" (DI providers, application scope, dependencies such as `datastore-tink`): each one with the module, the reason and the snippet. Write "None" if there are none.
- The file names and keys created, since renaming them later loses user data.
