# Gradle scopes: when to use each

## Decision tree

```
Do consumers of this module need this dependency in their classpath?
├── YES → api(...)
└── NO → Tests only?
          ├── YES → testImplementation(...) or androidTestImplementation(...)
          └── NO → Compile-time only (no runtime)?
                    ├── YES → compileOnly(...)
                    └── NO → implementation(...)   ← default for most cases
```

## Quick reference

| Scope | When to use | Example |
|---|---|---|
| `implementation` | Most cases | Retrofit, ViewModel, Room |
| `api` | Your module **re-exports** types from this lib in its public API | A `:core:network` that exposes `Response<T>` from Retrofit |
| `testImplementation` | Unit tests only | MockK, JUnit, Turbine |
| `androidTestImplementation` | Instrumented tests only | Espresso, Compose UI test |
| `kapt` / `ksp` | Annotation processors | Hilt, Room, Moshi codegen |
| `compileOnly` | Available at compile time, not at runtime | `@Keep` annotations, preview APIs |
| `debugImplementation` | Debug builds only | LeakCanary |

## The unnecessary `api` problem

In `gradle-sanity --json` output, `api_issues` lists modules with `Ca = 0` using `api` scope:

```json
"api_issues": [
  { "module": "payments:ui", "api_deps": ["core:network"] }
]
```

This means nobody depends on `payments:ui`, so its `api` scope is pointless —
it only increases compilation time without benefit.

**Fix:**
```kotlin
// BEFORE
dependencies {
    api(libs.retrofit)  // Ca = 0, nobody re-exports this
}

// AFTER
dependencies {
    implementation(libs.retrofit)  // correct
}
```

## When `api` IS correct

Only when the dependency's type appears in your module's public signature:

```kotlin
// :core:network exposes this:
class ApiResponse<T>(val data: T, val meta: ResponseMeta)
//                                        ↑ Retrofit type
```

Here `:core:network` must declare Retrofit with `api`, because any module using
`ApiResponse<T>` needs `ResponseMeta` in its classpath.

## Hardcoded versions → Version Catalog

In `gradle-sanity --json` output, `version_issues` lists hardcoded version strings:

```json
"version_issues": [
  { "module": "payments:gateway", "versions": ["com.google.dagger:hilt:2.48"] }
]
```

**Fix:**
```kotlin
// BEFORE (hardcoded, −2 pts per module)
implementation("com.google.dagger:hilt-android:2.51")

// AFTER (Version Catalog)
implementation(libs.hilt.android)
```

In `gradle/libs.versions.toml`:
```toml
[versions]
hilt = "2.51"

[libraries]
hilt-android = { group = "com.google.dagger", name = "hilt-android", version.ref = "hilt" }
```
