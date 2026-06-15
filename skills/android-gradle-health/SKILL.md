---
name: android-gradle-health
description: >
  Analyzes and shows the architectural health of Android multi-module projects using
  android-gradle-analyzer. Use whenever the user mentions Gradle dependencies, module
  cycles, SDP violations, Ca/Ce/I metrics, health scores, change impact, what breaks
  if module X changes, misplaced shared logic, or wants to see how healthy their architecture
  is. Also triggers for questions about coupling_limits, coupling_overrides,
  modularization, Gradle scopes (api vs implementation), or threshold calibration.
  Triggers even if the user doesn't name the tool — if they have
  an Android multi-module project and ask about dependencies or architecture, this
  skill applies.
---

# Android Gradle Health

Skill for diagnosing architectural health of Android multi-module projects by running
[android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer) CLIs,
capturing their JSON output, and delivering actionable analysis.

## Prerequisite: verify installation

```bash
pipx list | grep android-gradle-analyzer
```

### Option A — Permanent installation (recommended)

If not installed:

```bash
pipx install android-gradle-analyzer
```

> Requires **android-gradle-analyzer ≥ 1.7.0** (`--json` output in all 4 tools).
>
> **Recommended:** Use `pipx` for isolated tool installation. If `pipx` is not available,
> install it with `brew install pipx` (macOS) or `pip install pipx` (Linux/Windows).

#### Optional: Enhanced Kotlin DSL support

If the project uses Kotlin DSL (`.gradle.kts` files) and you need better accuracy via AST parsing:

```bash
pipx install "android-gradle-analyzer[kts]"
```

The base version supports `.kts` files using regex, but the `[kts]` extra adds
tree-sitter-kotlin AST parser that correctly handles:
- Multiline dependency declarations
- Commented dependency code
- Complex Kotlin DSL syntax

### Option B — Temporary env, no installation

If you don't want to install the tool permanently, prefix every command with
`pipx run --spec "android-gradle-analyzer>=1.4.0"`. `pipx` creates an isolated
temporary Python environment, reuses it on subsequent calls in the session,
and never modifies your global environment. Only requires `pipx` in PATH.

```bash
# Example: instead of gradle-sanity <path> --json --quiet
pipx run --spec "android-gradle-analyzer>=1.4.0" gradle-sanity <path> --json --quiet
```

| When to use | Option |
|---|---|
| Own machine, frequent use | A — permanent install |
| CI/CD or shared envs without write permissions | B — `pipx run --spec` |
| Testing a specific version without affecting the installed one | B — `pipx run --spec "android-gradle-analyzer==X.Y.Z"` |

---

## The four commands — always use `--json --quiet`

> If using Option B, prefix every command with `pipx run --spec "android-gradle-analyzer>=1.4.0"`.

Every command supports `--json` (structured output to stdout) and `--quiet`
(suppresses progress). Always use both to get clean, parseable data.

| Command | What it returns | When to use |
|---|---|---|
| `gradle-sanity <path> --json --quiet` | Score, Ca/Ce/I per module, cycles, SDP violations, issues | Health diagnosis |
| `gradle-impact <project> <module> --json --quiet` | Direct and transitive dependents, impact percentage | Risk assessment before changes |
| `gradle-externals <project> <module> --json --quiet` | External callers with scopes and transitive cone | Safe refactoring analysis |
| `gradle-analyzer <path> --json --quiet` | Dependency graph with scopes per module | Dependency mapping |

Common flags:

| Flag | Effect |
|---|---|
| `--engine static\|dynamic\|auto` | Extraction engine (default: `static` — text-only, safe) |
| `--config <path>` | Custom `analyzer_config.json` |
| `--focus <module[,module]>` | Focus analysis on specific modules |
| `--depth N\|all` | Limit traversal depth (default: `all`) |

### Extraction engines

| Engine | How it works | When to use |
|---|---|---|
| `static` *(default)* | Parses `build.gradle(.kts)` as text | Always safe, no JDK needed |
| `dynamic` | Runs `gradlew` and reads Gradle's resolved model | When static misses Version Catalogs or convention plugins |
| `auto` | Tries dynamic, falls back to static | Best-effort accuracy |

⚠️ `dynamic` executes the project's build. Only use on trusted repos.

---

## Operating workflow

### Step 1: Run the command and capture JSON

Always pipe to a variable or file. For sanity (the most common entry point):

```bash
gradle-sanity <path> --json --quiet
```

### Step 2: Analyze the JSON

Parse the output and prioritize findings by score impact.

For `gradle-sanity` output, triage in this order:

| Priority | Field | Score impact | Reference to read |
|---|---|---|---|
| 🔴 Critical | `cycles` | −20 pts each | `references/fix-cycles.md` |
| 🟠 High | `sdp_violations` | −10 pts each | `references/fix-sdp.md` |
| 🟡 Medium | `api_issues` | −5 pts each | `references/fix-scopes.md` |
| 🟡 Medium | `fan_out_issues` | −3 pts each | Review module's Ce |
| 🔵 Low | `version_issues` | −2 pts each | Recommend Version Catalog migration |
| ⚪ Advisory | `coupling_issues` | 0 pts (default) | `references/dependency-limits.md` |

### Step 3: Present diagnosis

Structure the response as:

1. **Score and status** — one line with the score and severity emoji
2. **Top findings** — prioritized list of issues with specific module names and metrics
3. **Remediation steps** — concrete actions per issue (read the corresponding reference)
4. **Next steps** — what to run next or what config to adjust

---

## JSON schemas

### `gradle-sanity --json` output

```json
{
  "schema_version": 1,
  "tool": "sanity",
  "path": "/path/to/project",
  "root": "/path/to/project",
  "focus": ["module1", "module2"],
  "context_modules": 10,
  "score": 74,
  "modules": {
    "payments:common":   { "ca": 3, "ce": 0, "I": 0.0 },
    "payments:home":     { "ca": 1, "ce": 6, "I": 0.86 },
    "payments:gateway":  { "ca": 2, "ce": 1, "I": 0.33 },
    "payments:checkout": { "ca": 2, "ce": 5, "I": 0.71 }
  },
  "cycles": [
    ["payments:home", "payments:checkout", "payments:home"]
  ],
  "sdp_violations": [
    { "from": "payments:gateway", "to": "payments:home", "I_from": 0.33, "I_to": 0.86 }
  ],
  "api_issues": [
    { "module": "payments:ui", "api_deps": ["core:network"] }
  ],
  "fan_out_issues": [
    { "module": "payments:home", "ce": 6 }
  ],
  "version_issues": [
    { "module": "payments:gateway", "versions": ["com.google.dagger:hilt:2.48"] }
  ],
  "orphan_modules": ["payments:experimental"],
  "coupling_issues": [
    { "module": "payments:checkout", "kind": "feature", "I": 0.71, "ca": 2, "max_ca": 1 }
  ]
}
```

Field reference for `modules` entries:

| Field | Meaning |
|---|---|
| `ca` | Afferent coupling (fan-in): how many modules depend on this one |
| `ce` | Efferent coupling (fan-out): how many modules this one depends on |
| `I` | Instability: `Ce / (Ce + Ca)`, range 0.0–1.0 |

Score formula: `100 − sum of all active penalties`.
`coupling_issues` penalties are 0 by default (advisory mode).

### `gradle-impact --json` output

```json
{
  "schema_version": 1,
  "tool": "impact",
  "target": "core",
  "total_modules": 10,
  "levels": {
    "1": ["app", "database", "model", "network", "payments", "util"],
    "2": ["cart", "checkout", "legacy"]
  },
  "total_impacted": 9,
  "impact_percent": 90.0
}
```

### `gradle-externals --json` output

```json
{
  "schema_version": 1,
  "tool": "external",
  "project": "/path/to/project",
  "target": "payments",
  "depth": "all",
  "external_callers": {
    "cart": { "payments": ["implementation"] },
    "checkout": { "payments": ["implementation"] }
  },
  "caller_cone": {
    "cart": 1,
    "checkout": 1,
    "app": 2,
    "legacy": 3
  }
}
```

### `gradle-analyzer --json` output

```json
{
  "schema_version": 1,
  "tool": "analyzer",
  "path": "/path/to/project",
  "modules": ["app", "core", "payments"],
  "dependencies": {
    "app": { "implementation": ["core", "payments"] },
    "payments": { "implementation": ["core"], "api": ["network"] }
  },
  "cycles": []
}
```

---

## Score interpretation

| Score | Status | Action |
|---|---|---|
| 90–100 | 🟢 Excellent | Healthy — maintain and monitor |
| 70–89 | 🟡 Good | Resolve api_issues and version_issues |
| 50–69 | 🟠 Needs attention | Address sdp_violations this sprint |
| < 50 | 🔴 Critical | Active cycles — resolve before adding features |

---

## Metrics quick reference

| Metric | Measures | Healthy pattern |
|---|---|---|
| **Ca** (fan-in) | How many depend on this module | High for core/common/shared |
| **Ce** (fan-out) | How many this module depends on | Low for stable modules |
| **I** (instability) | `Ce / (Ce + Ca)` | 0 = stable pillar · 1 = leaf/feature |

---

## References — when to read each

| File | Read when |
|---|---|
| `references/fix-cycles.md` | `cycles` is non-empty |
| `references/fix-sdp.md` | `sdp_violations` is non-empty |
| `references/fix-scopes.md` | `api_issues` is non-empty |
| `references/dependency-limits.md` | `coupling_issues` is non-empty, or user asks about `coupling_limits` |
| `references/thresholds.md` | User wants to calibrate thresholds by project size |
| `references/calibration-guide.md` | User wants academic backing or methodology for parameter choices |

## Ready-to-copy configs

In `examples/` by project size:

| Folder | Profile |
|---|---|
| `examples/prototype/` | Solo dev, 1–5 modules — advisory only, no Ca gates |
| `examples/small/` | 1–3 devs, 5–15 modules — soft app gate |
| `examples/medium/` | 2–5 devs, 15–30 modules — active feature and app gates |
| `examples/large/` | 5+ devs, 30+ modules — strict gates |

Each folder includes `analyzer_config.json` + `analyzer.yml` ready to copy
to the Android project root.
