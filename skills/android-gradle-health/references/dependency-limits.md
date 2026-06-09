# Dependency limits: coupling_limits and coupling_overrides

## How the detection works (no name-based heuristics)

The detector identifies high-level modules that others depend on — using measured
metrics, not module names:

1. **Automatically excludes** modules with `I < leaf_instability` (default: 0.70).
   Core/common have low I → never flagged, their high Ca is expected.
2. **Detects app** by reading the build file: if it contains `com.android.application`, it's an app.
3. **Everything else** with `I >= 0.70` and `Ca > leaf_max_ca` is a `feature` (misplaced shared logic).

```
I = 0.0 → very stable (core, common)     → excluded, high Ca is correct
I = 0.5 → intermediate (data, domain)    → excluded if I < 0.70
I = 0.83 → unstable (feature)            → flagged if Ca > leaf_max_ca
```

In the `gradle-sanity --json` output:

```json
"coupling_issues": [
  { "module": "payments:checkout", "kind": "feature", "I": 0.71, "ca": 2, "max_ca": 1 }
]
```

## Configuration in `analyzer_config.json`

```json
"coupling_limits": {
  "leaf_instability": 0.70,
  "leaf_max_ca":      1,
  "leaf_penalty":     0,
  "app_max_ca":       0,
  "app_penalty":      0
},

"coupling_overrides": {
  "payments": "leaf",
  "legacymodule": "ignore",
  "app": "app"
}
```

### Parameters

| Parameter | Description | Default |
|---|---|---|
| `leaf_instability` | Minimum I to consider a module as leaf/feature | 0.70 |
| `leaf_max_ca` | Maximum allowed Ca for a feature module | 1 |
| `leaf_penalty` | Points deducted per feature with excessive Ca | 0 (advisory) |
| `app_max_ca` | Maximum allowed Ca for the app module | 0 |
| `app_penalty` | Points deducted per app with Ca > 0 | 0 (advisory) |

### `coupling_overrides` — possible values

| Value | Effect |
|---|---|
| `"app"` | Force treatment as entry point (app) |
| `"leaf"` | Force treatment as feature/leaf |
| `"ignore"` | Exclude module from this validation |

Matches by full name first, then by last path segment:
`"payments:home"` or just `"home"` both work.

---

## When to use `coupling_overrides`

The inference works well in most cases. Use overrides when:

**`"ignore"`** — module in transition or with known special architecture:
```json
"coupling_overrides": { "legacy-bridge": "ignore" }
```

**`"app"`** — module with a different name that also applies `com.android.application`:
```json
"coupling_overrides": { "launcher": "app" }
```

**`"leaf"`** — module with artificially low I (many build-time deps like kapt/ksp)
that is conceptually a feature:
```json
"coupling_overrides": { "payments": "leaf" }
```

---

## Recommendations by project size

Always start in advisory mode (`leaf_penalty: 0`). Review the issues in the report
and decide if they're real problems before activating the gate.

| Size | leaf_instability | leaf_max_ca | leaf_penalty | app_penalty |
|---|---|---|---|---|
| Prototype (1–5 modules) | 0.80 | 2 | 0 | 0 |
| Small app (5–15) | 0.75 | 1 | 0 | 5 |
| Medium app (15–30) | 0.70 | 1 | 5 | 10 |
| Large app (30+) | 0.65 | 1 | 8 | 15 |

Lower `leaf_instability` → more modules fall within the validation scope.
In large projects, layer boundaries should be stricter.
