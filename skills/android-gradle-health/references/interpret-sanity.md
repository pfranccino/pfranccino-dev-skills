# Interpretar el reporte de sanidad

## Estructura real del JSON (`--json`)

```json
{
  "path": "/ruta/al/proyecto",
  "score": 74,
  "modules": {
    "payments:common":  { "ca": 3, "ce": 0, "I": 0.0 },
    "payments:home":    { "ca": 1, "ce": 6, "I": 0.86 },
    "payments:gateway": { "ca": 2, "ce": 1, "I": 0.33 },
    "payments:checkout":{ "ca": 2, "ce": 5, "I": 0.71 }
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

## Campos clave por sección

### `modules` — dict con nombre como clave

| Campo | Descripción |
|---|---|
| `ca` | Fan-in: cuántos módulos dependen de éste |
| `ce` | Fan-out: de cuántos módulos depende éste |
| `I` | Inestabilidad: `Ce / (Ce + Ca)`, rango 0.0–1.0 |

**Nota:** `modules` es un **dict**, no una lista. Las claves son los nombres normalizados
con `:` como separador (ej: `payments:home`, no `:payments:home`).

### `cycles`

Lista de listas. Cada sublista es un ciclo completo con el nodo inicial repetido al final:

```json
["payments:home", "payments:checkout", "payments:home"]
```

Lista vacía `[]` = sin ciclos ✅

### `sdp_violations`

Cada entrada: el módulo `from` (más estable, `I_from` bajo) depende del módulo `to`
(más inestable, `I_to` alto). Violación del Stable Dependencies Principle.

### `api_issues`

Módulos que declaran dependencias con scope `api` pero tienen `Ca = 0`.
`api_deps` lista qué dependencias tienen ese scope innecesario.

### `fan_out_issues`

Módulos cuyo `Ce` supera `high_fan_out_threshold` (default: 5).

### `coupling_issues`

Módulos de alto nivel (inestables, I alto) de los que otros dependen.
Señal de lógica compartida atrapada en el lugar equivocado.

| Campo | Descripción |
|---|---|
| `kind` | `"app"` o `"feature"` |
| `I` | Inestabilidad medida del módulo |
| `ca` | Fan-in actual |
| `max_ca` | Límite configurado para este kind |

**Por defecto es advisory**: aparece en el reporte pero no afecta el score
hasta que se configure `leaf_penalty` o `app_penalty` en `coupling_limits`.

### `orphan_modules`

Módulos con `Ca = 0` y `Ce = 0`. Sin penalización — requieren revisión manual.

---

## Cómo leer el score

```
Score final = 100 − suma de penalizaciones activas
```

Las penalizaciones de `coupling_issues` son **0 por defecto**. Para activarlas
como gate en CI, configurar `leaf_penalty` y/o `app_penalty` en `coupling_limits`.

---

## Patrón de respuesta recomendado al presentar el diagnóstico

1. **Score y estado** — una línea con emoji
2. **Ciclos** — si existen, son lo primero a resolver (−20 pts cada uno)
3. **SDP violations** — segundo en prioridad (−10 pts)
4. **coupling_issues** — señal arquitectónica importante aunque no penalice por defecto
5. **fan_out_issues / api_issues / version_issues** — quick wins
6. **Próximos pasos** priorizados por impacto en score
