# Cómo resolver violaciones SDP

## Qué es el SDP (Stable Dependencies Principle)

Un módulo **solo debe depender de módulos más estables que él mismo**.

```
I (inestabilidad) = Ce / (Ce + Ca)
0 = imposible desestabilizar  →  1 = completamente inestable
```

**Violación:** `core` (I=0.1) depende de `feature:home` (I=0.9)
→ Un cambio en `feature:home` puede romper `core`.

## Identificar la violación

```bash
gradle-sanity <ruta/modulo> --json | jq '.sdp_violations'
```

Output:
```json
[
  {
    "from": "payments:gateway",
    "to": "payments:ui",
    "I_from": 0.2,
    "I_to": 0.9
  }
]
```

## Patrón de diagnóstico

Antes de actuar, entender **por qué** existe esa dependencia.

Pregunta: ¿Qué clase/función exacta del módulo inestable está usando el módulo estable?

```bash
# Ver qué importa el módulo estable del inestable
grep -r "import.*payments.ui" payments/gateway/src/
```

## Estrategias de remediación

### Estrategia 1: Mover la abstracción al módulo estable

El módulo estable define la interfaz; el inestable la implementa.

```
ANTES:
gateway (I=0.2) → ui (I=0.9)   ← violación SDP

DESPUÉS:
gateway (I=0.2) define: interface Renderer
ui (I=0.9) implementa: class AndroidRenderer : Renderer
app inyecta la implementación
```

**Pasos:**
1. Crear la interfaz en `gateway` (o en `common`).
2. Hacer que `ui` implemente la interfaz.
3. Eliminar la dependencia de `gateway` a `ui`.
4. Inyectar desde `app` con Hilt.

---

### Estrategia 2: Elevar el contrato a un módulo de API

Patrón multi-módulo de Google: separar `:feature:api` de `:feature:impl`.

```
ANTES:
core → feature:home  (feature:home tiene todo mezclado)

DESPUÉS:
core → feature:home:api   (solo interfaces y modelos)
feature:home:impl → feature:home:api  (implementación)
app → feature:home:impl
```

Estructura de módulos:
```
feature/
  home/
    api/        ← interfaces + modelos de dominio (estable, I bajo)
    impl/       ← implementación real (inestable, I alto)
```

En `settings.gradle.kts`:
```kotlin
include(":feature:home:api")
include(":feature:home:impl")
```

---

### Estrategia 3: Revertir la dirección (cuando el código está en el lugar equivocado)

A veces la violación revela que lógica de negocio terminó en la capa equivocada.

**Señal:** `domain` usa algo de `data` que no es una interfaz.
**Fix:** Mover esa lógica a `domain` o crear una interfaz `Repository` en `domain` que `data` implementa.

## Verificar

```bash
gradle-sanity <ruta/modulo> --json | jq '.sdp_violations | length'
# Debe ser 0
```
