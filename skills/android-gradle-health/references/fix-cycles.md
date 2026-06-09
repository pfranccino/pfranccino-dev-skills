# How to break dependency cycles

## What a cycle is

`A depends on B` and `B depends on A`. Gradle compiles fine, but it violates the
ADP (Acyclic Dependencies Principle) and makes refactoring impossible without
breaking everything downstream.

## Identifying the cycle from JSON

In the `gradle-sanity --json` output, `cycles` is a list of lists. Each sublist
is a complete cycle with the starting node repeated at the end:

```json
"cycles": [
  ["payments:home", "payments:checkout", "payments:home"]
]
```

This means: `home → checkout → home`.

## Remediation strategies

### Strategy 1: Interface extraction (most common)

**Situation:** `home` uses something from `checkout` and `checkout` uses something from `home`.

**Solution:** Extract the contract to the most stable module both already consume.

```
BEFORE:
home ←→ checkout  (cycle)

AFTER:
home → common ← checkout
         ↑
    (interface here)
```

**Steps:**
1. Identify exactly what class from `checkout` is used by `home` and vice versa.
2. Create an interface in `common` (or `core`) for each cross-dependency.
3. Replace the direct dependency with the interface.
4. Inject the implementation with Hilt from the `app` module.

**Example:**

```kotlin
// common/src/main/kotlin/NavigationController.kt
interface NavigationController {
    fun navigateToCheckout(cartId: String)
}

// home/HomeViewModel.kt — no longer imports anything from checkout
class HomeViewModel(
    private val nav: NavigationController  // injected by Hilt
) { ... }

// app/ — registers the real implementation
@Module
@InstallIn(SingletonComponent::class)
object NavigationModule {
    @Provides
    fun provideNav(impl: CheckoutNavigationImpl): NavigationController = impl
}
```

---

### Strategy 2: Mediator module (event bus / shared state)

**Situation:** Modules communicate via events or shared state.

**Solution:** Create a `:shared:events` module both consume.

```
BEFORE:
feature:home ←→ feature:notifications  (cycle via events)

AFTER:
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

### Strategy 3: Invert the dependency (less common)

**Situation:** A high-level module accidentally depends on a low-level one that in turn needs it.

**Solution:** Determine the "correct" direction and move the code accordingly.

Key question: **Who should know about whom?**
- `feature` knows about `domain` ✅
- `domain` knows about `feature` ❌ → move logic to `feature` or define an interface in `domain`

---

## Verification

Run sanity again and check that `cycles` is empty:

```bash
gradle-sanity <path> --json --quiet
```

Or use the exit code for scripted verification:

```bash
gradle-sanity <path> --fail-on-cycle --quiet
# exit code 0 = no cycles ✅
```

## PR checklist

- [ ] `gradle-sanity --fail-on-cycle` exits with code 0
- [ ] `gradle-impact` on modified modules shows no unexpected regressions
- [ ] Unit tests for each involved module pass
