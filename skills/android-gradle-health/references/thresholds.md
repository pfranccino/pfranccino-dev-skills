# Holguras recomendadas por magnitud de proyecto

Los parámetros de `sanity_weights` no son estándares externos — son puntos de partida ajustables.
Este archivo da recomendaciones concretas según el tamaño y contexto de tu proyecto.

---

## Los parámetros explicados

| Parámetro | Qué controla | Default |
|---|---|---|
| `cycle` | Penalización por ciclo detectado | 20 |
| `sdp_violation` | Penalización por violación SDP | 10 |
| `unnecessary_api` | Penalización por scope `api` innecesario | 5 |
| `high_fan_out_threshold` | Cuántos `Ce` antes de considerar fan-out excesivo | 5 |
| `high_fan_out_penalty` | Penalización por módulo con fan-out excesivo | 3 |
| `hardcoded_version` | Penalización por versión hardcodeada | 2 |
| `sdp_threshold` | Diferencia de inestabilidad que dispara una violación SDP | 0.3 |
| `fail_on_score_below` *(analyzer.yml)* | Gate de CI — cuándo fallar el pipeline | — |

> **Regla que nunca cambia:** `cycle` siempre debe ser alto (≥15). Un ciclo es un ciclo
> sin importar el tamaño del proyecto. Es lo único que no se negocia.

---

## Recomendaciones por magnitud

### 🌱 Prototipo / Solo dev (1–5 módulos)

Arquitectura aún en definición. El foco es construir, no pulir.

```json
"sanity_weights": {
  "cycle":                 20,
  "sdp_violation":          7,
  "unnecessary_api":        3,
  "high_fan_out_threshold": 8,
  "high_fan_out_penalty":   2,
  "hardcoded_version":      1,
  "sdp_threshold":          0.5
}
```
```yaml
# analyzer.yml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 50
```

**Razonamiento:**
- `sdp_threshold: 0.5` — permite que módulos con inestabilidades similares dependan entre sí sin penalizar.
- `high_fan_out_threshold: 8` — en un proyecto pequeño, un módulo `common` con 7 dependencias es normal.
- `fail_on_score_below: 50` — solo bloquea si está realmente mal, no en arq. en construcción.

---

### 📱 App pequeña (5–15 módulos, 1–3 devs)

La arquitectura ya está tomando forma. Vale la pena que el CI empiece a cuidarla.

```json
"sanity_weights": {
  "cycle":                 20,
  "sdp_violation":         10,
  "unnecessary_api":        5,
  "high_fan_out_threshold": 6,
  "high_fan_out_penalty":   3,
  "hardcoded_version":      2,
  "sdp_threshold":          0.3
}
```
```yaml
# analyzer.yml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 65
```

**Razonamiento:** Valores default de la herramienta. Son el punto de equilibrio para la mayoría de proyectos en crecimiento.

---

### 🏗️ App mediana (15–30 módulos, 2–5 devs)

Múltiples features, posiblemente más de un dev tocando el mismo módulo.
El fan-out empieza a importar — un módulo con 8 dependencias ya es sospechoso.

```json
"sanity_weights": {
  "cycle":                 20,
  "sdp_violation":         10,
  "unnecessary_api":        5,
  "high_fan_out_threshold": 5,
  "high_fan_out_penalty":   4,
  "hardcoded_version":      2,
  "sdp_threshold":          0.25
}
```
```yaml
# analyzer.yml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 72
```

**Razonamiento:**
- `sdp_threshold: 0.25` — más estricto. Con más módulos, las capas deben estar más claras.
- `high_fan_out_penalty: 4` — subir la penalización incentiva a dividir módulos gordos.
- `fail_on_score_below: 72` — da espacio para deuda técnica controlada pero bloquea degradación.

---

### 🏢 App grande (30+ módulos, 5+ devs / múltiples squads)

La arquitectura es infraestructura. Una violación SDP en un módulo compartido
puede costar días de trabajo a tres equipos.

```json
"sanity_weights": {
  "cycle":                 20,
  "sdp_violation":         15,
  "unnecessary_api":        5,
  "high_fan_out_threshold": 4,
  "high_fan_out_penalty":   5,
  "hardcoded_version":      3,
  "sdp_threshold":          0.2
}
```
```yaml
# analyzer.yml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 78
```

**Razonamiento:**
- `sdp_violation: 15` — más caro porque el impacto real es mayor con más equipos.
- `high_fan_out_threshold: 4` — un módulo con 5+ dependencias es señal de que necesita dividirse.
- `sdp_threshold: 0.2` — muy estricto: los límites entre capas deben ser nítidos.
- `fail_on_score_below: 78` — umbral alto porque la arquitectura ya debe estar madura.

---

## Cómo elegir tu umbral de partida

Si no sabes cuál categoría aplica, ejecuta primero sin umbrales:

```bash
gradle-sanity . --json > baseline.json
python3 -c "import json; d=json.load(open('baseline.json')); print(f'Score actual: {d[\"score\"]}')"
```

Luego elige un `fail_on_score_below` que sea **10 puntos por debajo del score actual**.
Esto evita que el CI falle de entrada y te da margen para mejorar gradualmente.

```
Score actual: 71  →  fail_on_score_below: 61  (arrancar)
                  →  fail_on_score_below: 65  (después de 1 sprint)
                  →  fail_on_score_below: 70  (objetivo)
```

---

## Señales de que tus holguras están mal calibradas

| Síntoma | Problema probable | Ajuste |
|---|---|---|
| El CI falla en cada PR por score | Umbral muy alto para el estado actual | Bajar `fail_on_score_below` 10 pts |
| Nadie presta atención al score porque nunca falla | Umbral muy bajo | Subir 5 pts cada sprint |
| Muchas violaciones SDP "falsas" | `sdp_threshold` muy bajo | Subir a 0.4 |
| Fan-out siempre penaliza a `app` | `high_fan_out_threshold` muy bajo | Subir 2 unidades |
| Los ciclos no pesan lo suficiente en el equipo | `cycle` percibido como "un número más" | Considerar subirlo a 25 |

---

## Ver también

Los configs listos para copiar están en `examples/`:
- `examples/prototype/` — prototipo y solo dev
- `examples/small/` — app pequeña
- `examples/medium/` — app mediana
- `examples/large/` — app grande
