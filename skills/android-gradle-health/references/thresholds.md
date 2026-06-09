# Recommended thresholds by project size

The `sanity_weights` parameters are not external standards — they're adjustable
starting points. This file gives concrete recommendations by size and context.

---

## Parameters explained

| Parameter | Controls | Default |
|---|---|---|
| `cycle` | Penalty per detected cycle | 20 |
| `sdp_violation` | Penalty per SDP violation | 10 |
| `unnecessary_api` | Penalty per unnecessary `api` scope | 5 |
| `high_fan_out_threshold` | Ce count before fan-out is excessive | 5 |
| `high_fan_out_penalty` | Penalty per module with excessive fan-out | 3 |
| `hardcoded_version` | Penalty per hardcoded version | 2 |
| `sdp_threshold` | Instability difference that triggers an SDP violation | 0.3 |
| `fail_on_score_below` *(analyzer.yml)* | CI gate — when to fail the pipeline | — |

> **Rule that never changes:** `cycle` must always be high (≥15). A cycle is a cycle
> regardless of project size. This is the one non-negotiable.

---

## Recommendations by size

### 🌱 Prototype / Solo dev (1–5 modules)

Architecture still taking shape. Focus is building, not polishing.

```json
"sanity_weights": {
  "cycle": 20, "sdp_violation": 7, "unnecessary_api": 3,
  "high_fan_out_threshold": 8, "high_fan_out_penalty": 2,
  "hardcoded_version": 1, "sdp_threshold": 0.5
}
```
```yaml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 50
```

**Rationale:** `sdp_threshold: 0.5` lets modules with similar instabilities depend on
each other. `high_fan_out_threshold: 8` because a `common` with 7 deps is normal at
this scale. Score gate at 50 only blocks truly broken architectures.

---

### 📱 Small app (5–15 modules, 1–3 devs)

Architecture taking form. CI should start watching.

```json
"sanity_weights": {
  "cycle": 20, "sdp_violation": 10, "unnecessary_api": 5,
  "high_fan_out_threshold": 6, "high_fan_out_penalty": 3,
  "hardcoded_version": 2, "sdp_threshold": 0.3
}
```
```yaml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 65
```

**Rationale:** Tool defaults. Balanced for most growing projects.

---

### 🏗️ Medium app (15–30 modules, 2–5 devs)

Multiple features, possibly multiple devs touching the same module.
Fan-out starts mattering — a module with 8 deps is suspicious.

```json
"sanity_weights": {
  "cycle": 20, "sdp_violation": 10, "unnecessary_api": 5,
  "high_fan_out_threshold": 5, "high_fan_out_penalty": 4,
  "hardcoded_version": 2, "sdp_threshold": 0.25
}
```
```yaml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 72
```

**Rationale:** `sdp_threshold: 0.25` is stricter — with more modules, layers should be
clearer. Higher fan-out penalty incentivizes splitting fat modules.

---

### 🏢 Large app (30+ modules, 5+ devs / multiple squads)

Architecture is infrastructure. An SDP violation in a shared module can cost
three teams days of work.

```json
"sanity_weights": {
  "cycle": 20, "sdp_violation": 15, "unnecessary_api": 5,
  "high_fan_out_threshold": 4, "high_fan_out_penalty": 5,
  "hardcoded_version": 3, "sdp_threshold": 0.2
}
```
```yaml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 78
```

**Rationale:** `sdp_violation: 15` because real impact is higher with more teams.
`sdp_threshold: 0.2` — layer boundaries must be sharp. High score gate because
architecture should already be mature.

---

## How to choose your starting threshold

If unsure which category applies, run sanity first and read the JSON:

```bash
gradle-sanity . --json --quiet
```

Check the `score` and `modules` count, then set `fail_on_score_below` to
**10 points below current score**. This avoids breaking CI on day one and gives
room for gradual improvement.

```
Current score: 71  →  fail_on_score_below: 61  (start)
                   →  fail_on_score_below: 65  (after 1 sprint)
                   →  fail_on_score_below: 70  (target)
```

---

## Signs your thresholds are miscalibrated

| Symptom | Likely problem | Adjustment |
|---|---|---|
| CI fails on every PR | Score gate too high | Lower `fail_on_score_below` by 10 |
| Nobody pays attention because it never fails | Score gate too low | Raise 5 pts per sprint |
| Many "false" SDP violations | `sdp_threshold` too low | Raise to 0.4 |
| Fan-out always flags `app` | `high_fan_out_threshold` too low | Raise by 2 |
| Cycles don't feel costly enough | `cycle` perceived as "just a number" | Consider raising to 25 |

See ready-to-copy configs in `examples/`.
