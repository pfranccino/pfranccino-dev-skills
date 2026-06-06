# Cómo romper ciclos entre módulos

## Qué es un ciclo

`A depende de B` y `B depende de A`. Gradle permite compilar igual, pero viola el ADP (Acyclic Dependencies Principle) y hace el refactoring imposible sin romper todo.

## Identificar el ciclo exacto

```bash
gradle-sanity <ruta/modulo> --json | jq '.violations.cycles'
```

Output típico:
```
["payments:home", "payments:checkout", "payments:home"]
```

Esto significa: `home → checkout → home`.

## Estrategias de remediación

### Estrategia 1: Extracción de interfaz (la más común)

**Situación:** `home` usa algo de `checkout` y `checkout` usa algo de `home`.

**Solución:** Extraer el contrato al módulo más estable que ambos ya consumen.

```
ANTES:
home ←→ checkout  (ciclo)

DESPUÉS:
home → common ← checkout
         ↑
    (interfaz aquí)
```

**Pasos:**
1. Identificar exactamente qué clase de `checkout` usa `home` y viceversa.
2. Crear una interfaz en `common` (o `core`) para cada dependencia cruzada.
3. Reemplazar la dependencia directa por la interfaz.
4. Inyectar la implementación con Hilt desde el módulo `app`.

**Ejemplo:**

```kotlin
// common/src/main/kotlin/NavigationController.kt
interface NavigationController {
    fun navigateToCheckout(cartId: String)
}

// home/HomeViewModel.kt — ya no importa nada de checkout
class HomeViewModel(
    private val nav: NavigationController  // inyectado por Hilt
) { ... }

// app/ — registra la implementación real
@Module
@InstallIn(SingletonComponent::class)
object NavigationModule {
    @Provides
    fun provideNav(impl: CheckoutNavigationImpl): NavigationController = impl
}
```

---

### Estrategia 2: Módulo mediador (event bus / shared state)

**Situación:** Los módulos se comunican con eventos o estado compartido.

**Solución:** Crear un módulo `:shared:events` que ambos consuman.

```
ANTES:
feature:home ←→ feature:notifications  (ciclo por eventos)

DESPUÉS:
feature:home → shared:events ← feature:notifications
```

```kotlin
// shared:events/UserEvent.kt
sealed class UserEvent {
    data class LoggedIn(val userId: String) : UserEvent()
    object LoggedOut : UserEvent()
}
```

---

### Estrategia 3: Invertir la dependencia (menos común)

**Situación:** Un módulo de alto nivel depende accidentalmente de uno de bajo nivel que a su vez lo necesita.

**Solución:** Determinar cuál es la dirección "correcta" y mover el código en consecuencia.

Pregunta clave: **¿Quién debería saber de quién?**
- `feature` sabe de `domain` ✅
- `domain` sabe de `feature` ❌ → mover la lógica a `feature` o a una interfaz en `domain`

---

## Validar que el ciclo está roto

```bash
gradle-sanity <ruta/modulo> --fail-on-cycle --quiet
echo "Exit code: $?"  # 0 = sin ciclos ✅
```

## Checklist antes de hacer PR

- [ ] `gradle-sanity --fail-on-cycle` sale con código 0
- [ ] `gradle-impact` sobre los módulos modificados no muestra regresiones inesperadas
- [ ] Tests unitarios de cada módulo involucrado pasan
