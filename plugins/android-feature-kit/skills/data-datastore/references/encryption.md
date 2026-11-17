# Encryption with datastore-tink

Part of the data-datastore skill. Read it before writing or changing a store that holds sensitive values.

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
