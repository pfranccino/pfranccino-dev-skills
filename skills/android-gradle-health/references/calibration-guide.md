# Cómo calibrar los parámetros: respaldo y metodología

## Lo que dice la academia (resumen honesto)

Antes de los números, el contexto más importante:

> "No fue posible determinar o sugerir valores de referencia para Ca, Ce e inestabilidad
> debido a la alta variación entre proyectos."
>
> — Santos et al., *Software Instability Analysis Based on Afferent and Efferent
> Coupling Measures* (2017), tras revisar 321 versiones de 107 proyectos open source.

Y la documentación de JDepend (la herramienta original de Robert Martin):

> "Es realmente difícil dar un umbral para fan-out. La única respuesta posible es:
> depende. Cuanto más abstracto y de bajo nivel sea el componente, menor debe ser el valor."
>
> — pdepend / JDepend documentation

**Conclusión práctica:** los umbrales en `analyzer_config.json` no son estándares externos,
son puntos de partida razonables que cada equipo debe ajustar a su contexto. Esto no es una
limitación de la herramienta — es la naturaleza de las métricas de acoplamiento.

---

## Origen de los parámetros: qué mide cada uno

### Ca, Ce, I — Robert C. Martin (1994)

Definidos en *OO Design Quality Metrics: An Analysis of Dependencies* (1994) y
formalizados en *Agile Software Development: Principles, Patterns, and Practices* (2002).

La fórmula es: `I = Ce / (Ca + Ce)`

- `I = 0` → máxima estabilidad (muchos dependen de él, él no depende de nadie)
- `I = 1` → máxima inestabilidad (módulo hoja, depende de muchos, nadie depende de él)

Martin estableció que valores de Ce > 20 indican inestabilidad problemática: un cambio
en cualquiera de las numerosas clases externas puede causar la necesidad de cambios en el paquete.

**Traducido a módulos Android:** el umbral de 20 era para *clases*, no módulos.
Un módulo que depende de más de 5–7 otros módulos es equivalentemente problemático.

### SDP — Stable Dependencies Principle

Martin propone que los módulos que deben ser fácilmente modificables no deben depender
de módulos más difíciles de cambiar. Los paquetes siempre deben tener un valor I mayor que
los módulos de los que dependen.

El `sdp_threshold: 0.3` en el config significa: solo se dispara una violación si la diferencia
de inestabilidad entre dos módulos supera 0.3. Esto es un parámetro configurable, no parte
del principio original de Martin.

### ADP — Acyclic Dependencies Principle

No tiene umbral — es binario. O hay ciclo o no hay ciclo. La penalización siempre debe ser alta.

---

## Metodología para derivar tus propios umbrales

### Método 1: Baseline + delta (recomendado para empezar)

El enfoque más pragmático: mide primero, calibra después.

```bash
# 1. Medir el estado actual del proyecto
gradle-sanity . --json > baseline.json

# 2. Ver el score y las violaciones actuales
python3 -c "
import json
d = json.load(open('baseline.json'))
print(f'Score: {d[\"score\"]}')
print(f'Ciclos: {len(d[\"violations\"][\"cycles\"])}')
print(f'SDP: {len(d[\"violations\"][\"sdp\"])}')
print(f'API innecesario: {len(d[\"violations\"][\"unnecessary_api\"])}')
"
```

Luego aplicar la regla del delta:

| Si quieres... | Entonces... |
|---|---|
| Arrancar sin romper CI de entrada | `fail_on_score_below = score_actual - 10` |
| Mantener el estado actual | `fail_on_score_below = score_actual - 5` |
| Forzar mejora gradual | `fail_on_score_below = score_actual` (bloquea regresión) |
| Fijar un objetivo a 1 mes | `fail_on_score_below = score_actual + 10` |

---

### Método 2: Calibración por módulo (para proyectos maduros)

Algunos módulos naturalmente tienen valores altos de Ce o Ca. Antes de ajustar el umbral
global, categorizar los módulos:

```bash
# Ver inestabilidad por módulo
gradle-sanity . --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for m in sorted(d['modules'], key=lambda x: x['instability']):
    print(f'{m[\"instability\"]:.2f}  Ca={m[\"ca\"]:2d}  Ce={m[\"ce\"]:2d}  {m[\"name\"]}')
"
```

Output esperado:
```
0.00  Ca=5   Ce=0   core:domain
0.00  Ca=4   Ce=0   core:common
0.20  Ca=4   Ce=1   core:network
0.50  Ca=2   Ce=2   feature:auth
0.83  Ca=1   Ce=5   feature:home
1.00  Ca=0   Ce=3   app
```

Reglas derivadas de este análisis:

- **Módulos con I=0 y Ca alto** (`core`, `domain`, `common`): son los pilares. Si su Ce sube, es señal de alarma inmediata. Considerar `high_fan_out_threshold` de 1–2 para ellos.
- **Módulos feature con I ~0.7–0.9**: normal y esperado. El `sdp_threshold` debe ser mayor que la diferencia entre features.
- **`app` con I=1**: siempre inestable, es el punto de entrada. No penalizar su fan-out.

---

### Método 3: Benchmark contra proyectos de referencia

**NowInAndroid (Google):** el proyecto de referencia oficial de Android.
Tiene ~20 módulos con una estructura de dependencias bien documentada.

Referencia: [github.com/android/nowinandroid/docs/ModularizationLearningJourney.md](https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md)

Usar NowInAndroid como benchmark:
1. Correr `gradle-sanity` sobre NowInAndroid con tus parámetros actuales.
2. Ver qué score obtiene.
3. Si obtienes < 80 en NowInAndroid, tus parámetros son demasiado estrictos para ese tamaño de proyecto.

---

## Cómo ajustar cada parámetro específico

### `sdp_threshold` — el más delicado

Controla cuánta diferencia de inestabilidad dispara una violación SDP.

**Señal para subirlo (más permisivo):**
```
Muchas violaciones SDP entre features (feature:home → feature:search)
```
Features que dependen entre sí no siempre es malo si ambas son inestables (I ~0.8).
Subir a 0.5 elimina estos falsos positivos.

**Señal para bajarlo (más estricto):**
```
core:domain (I=0.0) depende de feature:home (I=0.9) — no hay violación detectada
```
Si el threshold es 0.3 pero la diferencia es 0.9, sí se detecta (0.9 > 0.3). Pero si
`core` (I=0.1) depende de algo con I=0.3, la diferencia es solo 0.2 — no se detectaría
con threshold=0.3. Bajarlo a 0.15 lo detectaría.

**Rangos orientativos:**

| Contexto | sdp_threshold recomendado |
|---|---|
| Prototipo / arquitectura en definición | 0.5 |
| App con capas definidas (data/domain/ui) | 0.3 (default) |
| App con múltiples equipos, capas críticas | 0.2 |
| Microservicios o lib pública con API estricta | 0.15 |

---

### `high_fan_out_threshold` — cuándo un módulo "depende de demasiados"

Google en su guía de modularización indica que cada módulo introduce overhead de
configuración, y que si el número de módulos alcanza cierto umbral, gestionar configuración
consistente se vuelve un desafío. El número correcto depende de si se necesita
reusabilidad, control de visibilidad estricto, o Play Feature Delivery.

Regla empírica derivada de este principio:

```
high_fan_out_threshold ≈ log₂(total_módulos) + 2
```

| Módulos totales | Threshold sugerido | Razonamiento |
|---|---|---|
| 5 | 5 | Casi cualquier módulo puede depender de la mitad |
| 10 | 5–6 | Un feature puede depender de 5 cores |
| 20 | 6–7 | La complejidad crece, el threshold sube poco |
| 40 | 7–8 | Un módulo con 8 deps ya es sospechoso |
| 80+ | 8–9 | En proyectos muy grandes, 9 es el límite razonable |

**Excepción importante:** el módulo `app` casi siempre tiene fan-out igual al número
de features. Considera excluirlo del análisis o darle un threshold propio si la
herramienta lo permite.

---

### `cycle` — nunca bajar de 15

El ADP (Acyclic Dependencies Principle) es el más respaldado académicamente.
Martin define claramente que un paquete X es estable si muchos otros dependen de él
mientras que él no depende de otros, y que los ciclos destruyen esta propiedad haciendo
imposible desestabilizar una unidad sin afectar a las demás.

No hay justificación para penalizar ciclos con menos de 15 puntos. Si tu equipo considera
que los ciclos son "normales", el problema es de cultura de deuda técnica, no del umbral.

---

## Señales de que necesitas recalibrar

| Situación | Acción |
|---|---|
| El score no cambia nunca entre PRs | El umbral de CI está muy bajo — subir `fail_on_score_below` |
| CI falla el 80% de los PRs por score | El umbral está muy alto para el estado actual — medir baseline y reajustar |
| Muchas violaciones SDP entre módulos del mismo nivel | `sdp_threshold` demasiado bajo — subir a 0.4–0.5 |
| Fan-out detectado en `app` pero no en features gordas | `high_fan_out_threshold` mal calibrado para la estructura del proyecto |
| El equipo ignora el reporte porque "siempre está rojo" | Recalibrar con el Método 1 (baseline + delta) desde cero |

---

## Fuentes

- Martin, R. C. (1994). *OO Design Quality Metrics: An Analysis of Dependencies*. Object Mentor.
- Martin, R. C. (2002). *Agile Software Development: Principles, Patterns, and Practices*. Prentice Hall.
- Santos, et al. (2017). *Software Instability Analysis Based on Afferent and Efferent Coupling Measures*. ResearchGate.
- Wikipedia. *Software package metrics*. [https://en.wikipedia.org/wiki/Software_package_metrics](https://en.wikipedia.org/wiki/Software_package_metrics)
- Google. *Guide to Android app modularization* (2026). [https://developer.android.com/topic/modularization](https://developer.android.com/topic/modularization)
- Google. *Common modularization patterns*. [https://developer.android.com/topic/modularization/patterns](https://developer.android.com/topic/modularization/patterns)
- autonomousapps/dependency-analysis-gradle-plugin. [https://github.com/autonomousapps/dependency-analysis-gradle-plugin](https://github.com/autonomousapps/dependency-analysis-gradle-plugin)
- NowInAndroid Modularization Learning Journey. [https://github.com/android/nowinandroid](https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md)
