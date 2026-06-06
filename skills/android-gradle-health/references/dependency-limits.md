# Límites de dependencias: coupling_limits y coupling_overrides

## Cómo funciona la detección (sin keywords de nombres)

`_check_leaf_coupling()` detecta módulos de alto nivel de los que otros dependen.
No usa nombres — usa métricas medidas:

1. **Excluye automáticamente** módulos con `I < leaf_instability` (default: 0.70).
   Core/common tienen I bajo → nunca penalizados, Ca alto es esperado en ellos.
2. **Detecta app** leyendo el build file: si contiene `com.android.application` es app.
3. **El resto** con `I >= 0.70` y `Ca > leaf_max_ca` son `feature` (lógica compartida mal ubicada).

```
I = 0.0 → muy estable (core, common)     → excluido, Ca alto es correcto
I = 0.5 → intermedio (data, domain)       → excluido si I < 0.70
I = 0.83 → inestable (feature)            → incluido si Ca > leaf_max_ca
```

## Configuración en `analyzer_config.json`

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

### Parámetros

| Parámetro | Descripción | Default |
|---|---|---|
| `leaf_instability` | I mínimo para considerar un módulo como hoja/feature | 0.70 |
| `leaf_max_ca` | Ca máximo permitido para un módulo feature | 1 |
| `leaf_penalty` | Puntos a restar por feature con Ca excesivo | 0 (advisory) |
| `app_max_ca` | Ca máximo permitido para el módulo app | 0 |
| `app_penalty` | Puntos a restar por app con Ca > 0 | 0 (advisory) |

### `coupling_overrides` — valores posibles

| Valor | Efecto |
|---|---|
| `"app"` | Fuerza tratamiento como punto de entrada (app) |
| `"leaf"` | Fuerza tratamiento como feature/hoja |
| `"ignore"` | Excluye el módulo de esta validación |

Match por nombre completo primero, luego por último segmento del path:
`"payments:home"` o simplemente `"home"` funcionan ambos.

---

## Cuándo usar `coupling_overrides`

La inferencia funciona bien en la mayoría de casos. Usar overrides cuando:

**`"ignore"`** — módulo en transición o con arquitectura especial conocida:
```json
"coupling_overrides": {
  "legacy-bridge": "ignore"
}
```

**`"app"`** — módulo con nombre distinto que también aplica `com.android.application`,
o si la detección automática por plugin falla:
```json
"coupling_overrides": {
  "launcher": "app"
}
```

**`"leaf"`** — módulo con I bajo artificialmente (muchas deps en build time como kapt/ksp)
pero que conceptualmente es una feature:
```json
"coupling_overrides": {
  "payments": "leaf"
}
```

---

## Recomendaciones por tamaño de proyecto

### Arrancar en modo advisory (leaf_penalty: 0)

Siempre empezar sin penalización. El reporte muestra los problemas sin romper CI.
Revisarlos manualmente y decidir si son problemas reales antes de activar el gate.

### Activar gradualmente

```json
"coupling_limits": {
  "leaf_instability": 0.70,
  "leaf_max_ca":      1,
  "leaf_penalty":     5,
  "app_max_ca":       0,
  "app_penalty":      10
}
```

| Tamaño | leaf_instability | leaf_max_ca | leaf_penalty | app_penalty |
|---|---|---|---|---|
| Prototipo (1–5 mód.) | 0.80 | 2 | 0 | 0 |
| App pequeña (5–15) | 0.75 | 1 | 0 | 5 |
| App mediana (15–30) | 0.70 | 1 | 5 | 10 |
| App grande (30+) | 0.65 | 1 | 8 | 15 |

**`leaf_instability` más bajo** → más módulos quedan dentro del scope de validación.
En proyectos grandes las capas deben estar más definidas — bajar el umbral tiene sentido.
