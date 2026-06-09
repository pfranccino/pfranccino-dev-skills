# How to resolve SDP violations

## What the SDP is (Stable Dependencies Principle)

A module **should only depend on modules more stable than itself**.

```
I (instability) = Ce / (Ce + Ca)
0 = impossible to destabilize  →  1 = completely unstable
```

**Violation:** `core` (I=0.1) depends on `feature:home` (I=0.9)
→ A change in `feature:home` can break `core`.

## Identifying violations from JSON

In `gradle-sanity --json` output:

```json
"sdp_violations": [
  {
    "from": "payments:gateway",
    "to": "payments:ui",
    "I_from": 0.2,
    "I_to": 0.9
  }
]
```

`from` is the more stable module (low I) depending on `to` (high I). The dependency
points in the wrong direction — toward instability.

## Diagnostic pattern

Before acting, understand **why** the dependency exists.

Question: What exact class/function from the unstable module is the stable module using?

```bash
grep -r "import.*payments.ui" payments/gateway/src/
```

## Remediation strategies

### Strategy 1: Move the abstraction to the stable module

The stable module defines the interface; the unstable one implements it.

```
BEFORE:
gateway (I=0.2) → ui (I=0.9)   ← SDP violation

AFTER:
gateway (I=0.2) defines: interface Renderer
ui (I=0.9) implements: class AndroidRenderer : Renderer
app injects the implementation
```

**Steps:**
1. Create the interface in `gateway` (or in `common`).
2. Have `ui` implement the interface.
3. Remove the dependency from `gateway` to `ui`.
4. Inject from `app` with Hilt.

---

### Strategy 2: Elevate the contract to an API module

Google's multi-module pattern: separate `:feature:api` from `:feature:impl`.

```
BEFORE:
core → feature:home  (everything mixed in feature:home)

AFTER:
core → feature:home:api   (interfaces and domain models only)
feature:home:impl → feature:home:api  (implementation)
app → feature:home:impl
```

Module structure:
```
feature/
  home/
    api/        ← interfaces + domain models (stable, low I)
    impl/       ← real implementation (unstable, high I)
```

---

### Strategy 3: Reverse the direction (code in the wrong layer)

Sometimes the violation reveals business logic that ended up in the wrong layer.

**Signal:** `domain` uses something from `data` that isn't an interface.
**Fix:** Move that logic to `domain` or create a `Repository` interface in `domain`
that `data` implements.

## Verification

Run sanity again and check that `sdp_violations` is empty in the JSON output.
