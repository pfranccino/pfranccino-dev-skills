---
name: android-gradle-health
description: Analiza y mejora la salud arquitectónica de proyectos Android multi-módulo usando android-gradle-analyzer. Úsala siempre que el usuario mencione dependencias Gradle, ciclos entre módulos, violaciones SDP, métricas Ca/Ce/I, health score, impacto de cambios, qué módulos se rompen si cambio X, lógica compartida mal ubicada, o quiera saber si su arquitectura está bien. También activa para preguntas sobre coupling_limits, coupling_overrides, modularización, scopes de Gradle (api vs implementation), o calibración de holguras.
---

# Android Gradle Health

Skill que envuelve [android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer)
y convierte su output en diagnósticos accionables con pasos concretos de remediación.

## Prerequisito: verificar instalación

```bash
gradle-analyzer-menu --version
```

Si no está instalada:

```bash
pipx install git+https://github.com/pfranccino/android-gradle-analyzer.git
```

---

## Mapa de comandos

| Lo que el usuario quiere | Comando | Referencia |
|---|---|---|
| Ver dependencias de un módulo | `gradle-analyzer <ruta/modulo>` | — |
| Saber quién consume un módulo | `gradle-externals <ruta/proyecto> <modulo>` | — |
| Salud general del proyecto | `gradle-sanity <ruta/modulo> --json` | `references/interpret-sanity.md` |
| Qué se rompe si cambio X | `gradle-impact <ruta/proyecto> <modulo>` | — |
| Ciclos detectados | `gradle-sanity` → ver `cycles` | `references/fix-cycles.md` |
| Violaciones SDP | `gradle-sanity` → ver `sdp_violations` | `references/fix-sdp.md` |
| Scopes mal declarados | `gradle-sanity` → ver `api_issues` | `references/fix-scopes.md` |
| Lógica compartida mal ubicada | `gradle-sanity` → ver `coupling_issues` | `references/dependency-limits.md` |
| Calibrar holguras por tamaño | config en `coupling_limits` | `references/thresholds.md` |
| Entender el origen de los parámetros | — | `references/calibration-guide.md` |
| Integrar en CI/CD | `gradle-sanity --fail-on-cycle --fail-on-score-below N` | `references/ci-cd.md` |

---

## Flujo de trabajo estándar

### 1. Diagnóstico inicial

```bash
gradle-sanity <ruta/modulo> --json > sanity.json
```

Leer `sanity.json` y priorizar por impacto en score:

1. 🔴 **`cycles`** (−20 pts cada uno) → leer `references/fix-cycles.md`
2. 🟠 **`sdp_violations`** (−10 pts) → leer `references/fix-sdp.md`
3. 🟡 **`api_issues`** (−5 pts) → leer `references/fix-scopes.md`
4. 🟡 **`fan_out_issues`** (−3 pts) → revisar Ce del módulo
5. 🔵 **`version_issues`** (−2 pts) → migrar a Version Catalog
6. ⚪ **`coupling_issues`** (advisory por defecto) → leer `references/dependency-limits.md`

### 2. Análisis de impacto antes de refactorizar

```bash
gradle-impact <ruta/proyecto> <modulo-a-cambiar>
```

### 3. Visualizar el grafo

```bash
gradle-analyzer <ruta/modulo> --format mermaid
```

---

## Interpretación rápida del score

| Score | Estado | Acción |
|---|---|---|
| 90–100 | 🟢 Excelente | Agregar a CI como quality gate |
| 70–89 | 🟡 Bueno | Resolver api_issues y version_issues |
| 50–69 | 🟠 Mejorable | Atender sdp_violations esta sprint |
| < 50 | 🔴 Crítico | Ciclos activos: resolver antes de agregar features |

**`coupling_issues` no afecta el score por defecto.** Aparece como señal
arquitectónica en el reporte. Para activarlo como gate en CI, configurar
`leaf_penalty` y `app_penalty` en `coupling_limits`. Ver `references/dependency-limits.md`.

---

## Métricas Ca / Ce / I

| Métrica | Qué mide | Valor ideal |
|---|---|---|
| **Ca** (fan-in) | Cuántos módulos dependen de éste | Alto en core/common |
| **Ce** (fan-out) | De cuántos depende éste | Bajo en módulos estables |
| **I** (inestabilidad) | `Ce / (Ce + Ca)` | 0 = estable · 1 = hoja |

---

## Referencias

| Archivo | Cuándo leerlo |
|---|---|
| `references/interpret-sanity.md` | Entender la estructura del JSON de sanidad |
| `references/fix-cycles.md` | El reporte tiene entradas en `cycles` |
| `references/fix-sdp.md` | El reporte tiene entradas en `sdp_violations` |
| `references/fix-scopes.md` | El reporte tiene entradas en `api_issues` |
| `references/dependency-limits.md` | El reporte tiene `coupling_issues`, o el usuario quiere configurar `coupling_limits` |
| `references/thresholds.md` | El usuario quiere calibrar holguras según tamaño de proyecto |
| `references/calibration-guide.md` | El usuario quiere entender el origen de los parámetros o respaldar decisiones frente al equipo |
| `references/ci-cd.md` | Integrar el análisis en GitHub Actions |

## Ejemplos listos para copiar

Configs en `examples/` por magnitud de proyecto:

| Carpeta | Perfil |
|---|---|
| `examples/prototype/` | Solo dev, 1–5 módulos — advisory, sin gates de Ca |
| `examples/small/` | 1–3 devs, 5–15 módulos — gate suave en app |
| `examples/medium/` | 2–5 devs, 15–30 módulos — gates activos en feature y app |
| `examples/large/` | 5+ devs, 30+ módulos — gates estrictos |

Cada carpeta incluye `analyzer_config.json` + `analyzer.yml` listos para copiar
a la raíz del proyecto Android.
