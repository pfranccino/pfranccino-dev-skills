# Scopes de Gradle: cuándo usar cada uno

## Árbol de decisión

```
¿Los consumidores de este módulo necesitan esta dependencia en su classpath?
├── SÍ → api(...)
└── NO → ¿Solo en tests?
          ├── SÍ → testImplementation(...) o androidTestImplementation(...)
          └── NO → ¿Solo en tiempo de compilación (sin runtime)?
                    ├── SÍ → compileOnly(...)
                    └── NO → implementation(...)   ← default en la mayoría de casos
```

## Resumen rápido

| Scope | Cuándo usarlo | Ejemplo |
|---|---|---|
| `implementation` | La gran mayoría de casos | Retrofit, ViewModel, Room |
| `api` | Tu módulo **reexporta** tipos de esta lib en su API pública | Un `:core:network` que expone `Response<T>` de Retrofit |
| `testImplementation` | Solo en tests unitarios | MockK, JUnit, Turbine |
| `androidTestImplementation` | Solo en tests instrumentados | Espresso, Compose UI test |
| `kapt` / `ksp` | Procesadores de anotaciones | Hilt, Room, Moshi codegen |
| `compileOnly` | Disponible en compilación, no en runtime | Anotaciones `@Keep`, APIs de preview |
| `debugImplementation` | Solo en builds debug | LeakCanary |

## El problema de `api` innecesario

El analyzer detecta módulos con `Ca = 0` que usan `api`. Esto significa:
- Nadie depende de ese módulo Y reexporta sus tipos.
- El `api` solo aumenta el tiempo de compilación sin beneficio.

**Fix:**
```kotlin
// ANTES
dependencies {
    api(libs.retrofit)  // Ca = 0, nadie reexporta esto
}

// DESPUÉS
dependencies {
    implementation(libs.retrofit)  // correcto
}
```

## Cuándo `api` SÍ tiene sentido

Solo cuando el tipo de la dependencia aparece en la firma pública de tu módulo:

```kotlin
// :core:network expone esto:
class ApiResponse<T>(val data: T, val meta: ResponseMeta)
//                                        ↑ tipo de Retrofit
```

En este caso `:core:network` sí debe declarar Retrofit con `api`, porque cualquier módulo que use `ApiResponse<T>` necesita `ResponseMeta` en su classpath.

## Versiones hardcodeadas → Version Catalog

```kotlin
// ANTES (hardcodeado, −2 pts por módulo)
implementation("com.google.dagger:hilt-android:2.51")

// DESPUÉS (Version Catalog)
implementation(libs.hilt.android)
```

En `gradle/libs.versions.toml`:
```toml
[versions]
hilt = "2.51"

[libraries]
hilt-android = { group = "com.google.dagger", name = "hilt-android", version.ref = "hilt" }
```

## Scopes de test más comunes en Android

```kotlin
dependencies {
    // Unit tests (JVM)
    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    testImplementation(libs.turbine)
    testImplementation(libs.coroutines.test)

    // Instrumented tests (dispositivo/emulador)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.compose.ui.test.junit4)

    // Anotaciones de Hilt para tests
    kaptTest(libs.hilt.compiler)
    kaptAndroidTest(libs.hilt.compiler)
}
```
