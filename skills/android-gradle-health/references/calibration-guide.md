# How to calibrate parameters: methodology and academic backing

## What academia says (honest summary)

Before the numbers, the most important context:

> "It was not possible to determine or suggest reference values for Ca, Ce, and
> instability due to the high variation between projects."
>
> — Santos et al., *Software Instability Analysis Based on Afferent and Efferent
> Coupling Measures* (2017), after reviewing 321 versions of 107 open-source projects.

And the JDepend documentation (Robert Martin's original tool):

> "It is really hard to give a threshold for fan-out. The only possible answer is:
> it depends. The more abstract and low-level the component, the lower the value should be."
>
> — pdepend / JDepend documentation

**Practical conclusion:** the thresholds in `analyzer_config.json` are not external
standards — they're reasonable starting points each team should adjust to their
context. This isn't a tool limitation — it's the nature of coupling metrics.

---

## Origin of the parameters

### Ca, Ce, I — Robert C. Martin (1994)

Defined in *OO Design Quality Metrics: An Analysis of Dependencies* (1994) and
formalized in *Agile Software Development: Principles, Patterns, and Practices* (2002).

Formula: `I = Ce / (Ca + Ce)`

- `I = 0` → maximum stability (many depend on it, it depends on nothing)
- `I = 1` → maximum instability (leaf module, depends on many, nobody depends on it)

Martin established that Ce > 20 indicates problematic instability: a change in
any of the numerous external classes may necessitate changes in the package.

**Translated to Android modules:** the threshold of 20 was for *classes*, not modules.
A module depending on more than 5–7 other modules is equivalently problematic.

### SDP — Stable Dependencies Principle

Martin states that packages that are intended to be easily changeable should not depend
on packages that are harder to change. Packages should always have an I value greater
than the modules they depend on.

The `sdp_threshold: 0.3` means: a violation only fires if the instability difference
exceeds 0.3. This is a configurable parameter, not part of Martin's original principle.

### ADP — Acyclic Dependencies Principle

No threshold — it's binary. Either there's a cycle or there isn't. Penalty must always
be high.

---

## Methodology for deriving your own thresholds

### Method 1: Baseline + delta (recommended to start)

The most pragmatic approach: measure first, calibrate after.

```bash
gradle-sanity . --json --quiet
```

Read the JSON output and note the current `score`, `cycles`, `sdp_violations`,
`api_issues`, `fan_out_issues`, and `version_issues` counts.

Then apply the delta rule:

| Goal | Set `fail_on_score_below` to |
|---|---|
| Start without breaking CI | current score − 10 |
| Maintain current state | current score − 5 |
| Force gradual improvement | current score (blocks regression) |
| Set a 1-month target | current score + 10 |

---

### Method 2: Per-module calibration (for mature projects)

Some modules naturally have high Ce or Ca. Before adjusting the global threshold,
categorize modules by sorting the `modules` dict from the JSON by `I`:

Expected output pattern:
```
0.00  Ca=5  Ce=0  core:domain        ← pillar, Ca high is expected
0.00  Ca=4  Ce=0  core:common        ← pillar
0.20  Ca=4  Ce=1  core:network       ← stable, some deps OK
0.50  Ca=2  Ce=2  feature:auth       ← intermediate
0.83  Ca=1  Ce=5  feature:home       ← feature, high I is expected
1.00  Ca=0  Ce=3  app                ← always unstable (entry point)
```

Rules derived from this analysis:

- **Modules with I=0 and high Ca** (`core`, `domain`, `common`): pillars. If their Ce rises, that's an immediate alarm.
- **Feature modules with I ~0.7–0.9**: normal and expected. `sdp_threshold` should be higher than the difference between features.
- **`app` with I=1**: always unstable, it's the entry point. Don't penalize its fan-out.

---

### Method 3: Benchmark against reference projects

**NowInAndroid (Google):** the official Android reference project.

Reference: [github.com/android/nowinandroid](https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md)

Steps:
1. Run `gradle-sanity` on NowInAndroid with your current parameters.
2. Check the score.
3. If NowInAndroid scores < 80 with your params, they're too strict for that project size.

---

## Sources

- Martin, R. C. (1994). *OO Design Quality Metrics: An Analysis of Dependencies*. Object Mentor.
- Martin, R. C. (2002). *Agile Software Development: Principles, Patterns, and Practices*. Prentice Hall.
- Santos, et al. (2017). *Software Instability Analysis Based on Afferent and Efferent Coupling Measures*. ResearchGate.
- Wikipedia. *Software package metrics*. [https://en.wikipedia.org/wiki/Software_package_metrics](https://en.wikipedia.org/wiki/Software_package_metrics)
- Google. *Guide to Android app modularization*. [https://developer.android.com/topic/modularization](https://developer.android.com/topic/modularization)
- NowInAndroid Modularization Learning Journey. [https://github.com/android/nowinandroid](https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md)
