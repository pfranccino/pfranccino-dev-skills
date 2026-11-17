# Guía del Android Feature Kit

Cómo instalar los agentes del kit en una app Android y cómo pedirles trabajo, con ejemplos. Vale para la versión 0.4.0 o superior del plugin.

La misma guía, como página con los tipos de agentes y el flujo dibujado, está en https://pfranccino.github.io/pfranccino-dev-skills/ (el archivo es [GUIA.html](GUIA.html)).

La idea es simple: le hablas a Claude como a un compañero de equipo. Claude decide qué parte del kit usar, te muestra un plan y no escribe código hasta que lo apruebas.

## Antes de empezar

- Claude Code con el plugin `android-feature-kit` 0.4.0 o superior.
- Python 3.8 o superior en el PATH. Los hooks del kit lo usan; sin Python, dejan pasar todo.
- La app en un repositorio git, con el Gradle wrapper (`gradlew`).
- Opcional: Android CLI, para las skills oficiales de Google.
- Opcional: Codex u otra herramienta de línea de comandos, si quieres un revisor externo además de `android-reviewer`.

## Instalación paso a paso

### 1. Instala o actualiza el plugin

En Claude Code:

```
/plugin marketplace add pfranccino/pfranccino-dev-skills
/plugin install android-feature-kit@pfranccino-dev-skills
```

Si ya lo tenías instalado, actualízalo. En `/plugin`, pestaña **Installed**, abre `android-feature-kit` y elige **Update now**; o en la terminal corre `claude plugin update android-feature-kit@pfranccino-dev-skills`. Después corre `/reload-plugins` o reinicia Claude Code. `/plugin marketplace update` solo refresca el catálogo y no actualiza el plugin instalado. En `/plugin` deberías ver la versión 0.4.0.

### 2. Agrega el ruteo al CLAUDE.md de la app (opcional)

Pega este párrafo al final del `CLAUDE.md` del repositorio de la app. Es el mismo que está en [`skills/develop/references/claude-md-block.md`](skills/develop/references/claude-md-block.md):

```markdown
<!-- android-feature-kit:start -->
## Android feature work (android-feature-kit)

Requests to build or change a feature (a new feature, screen, endpoint, entity or flow, a ticket to implement) go through the kit's `develop` skill. Questions about the code, failing builds or tests, reviews and architecture questions go through its `analyze` skill. A small change in one layer uses that layer's skill directly. Code changes, small ones included, start only after the user approves the plan in Plan Mode; analysis plans are approved in the conversation. The kit's limits and routine choices for this repository are in `.claude/android-feature-kit.md`.
<!-- android-feature-kit:end -->
```

Claude carga el `CLAUDE.md` en todas las sesiones, por eso el párrafo es corto. Sin él, las skills igual se activan por su descripción, pero el párrafo hace más confiable que Claude elija la ruta correcta y que pida aprobación también en los cambios chicos.

### 3. Copia las reglas del repositorio (opcional)

Copia [`skills/develop/references/project-rules.md`](skills/develop/references/project-rules.md) a `.claude/android-feature-kit.md` en la app. Ese archivo tiene lo que el equipo aprueba una sola vez, para todas las tareas:

- **Exploración aprobada de antemano.** Lo que Claude puede leer y correr sin preguntarte mientras planifica. Por defecto: leer archivos, buscar y usar git de solo lectura. Para builds, tests, mapas generados, la red o cualquier agente, pregunta antes.
- **Elecciones rutinarias.** Nombres, dónde va cada archivo, reutilizar helpers o componentes que ya existen y la estructura de los tests. Siguen lo que muestra el código y nunca son pregunta. Todo lo demás se pregunta.

Ajusta las listas a tu proyecto. Por ejemplo, si quieres que Claude pueda usar el agente Explore para recorrer módulos grandes sin preguntarte, cambia `Discovery agents: none` por `Discovery agents: Explore`.

Las skills leen este archivo solo cuando se activan. No lo pongas en `.claude/rules/`, porque esa carpeta se carga en todas las sesiones. Sin el archivo, `develop` y `analyze` te proponen estos mismos valores una vez por sesión.

### 4. Configura el plan gate y el revisor externo (opcional)

Crea `.claude/android-feature-kit.json` en la app solo si quieres alguna de estas dos cosas:

```json
{
  "planGate": true,
  "reviewer": {
    "name": "Codex",
    "command": ["codex", "exec", "-s", "read-only", "--output-schema", "{schema}", "-o", "{output}", "-"]
  }
}
```

- `planGate`: bloquea a los agentes que escriben código si no están en el plan que aprobaste en Plan Mode, o si correrían con otro modelo. Viene apagado porque todavía no se ha probado en sesiones reales.
- `reviewer`: cualquier herramienta que lea el prompt por la entrada estándar y devuelva el JSON del esquema de revisión. El ejemplo es para Codex. Que esté configurado no significa que se use siempre: tú eliges el revisor en cada plan.

El detalle de la configuración del revisor está en [`skills/develop/references/external-review.md`](skills/develop/references/external-review.md).

### 5. Copia los scripts de chequeo a la app (opcional)

Los agentes compilan y corren tests a través de `gradle_summary.py` y `test_summary.py`, que resumen la salida de Gradle en un JSON corto. Si la app no los tiene, los agentes usan la copia del plugin. Tenerlos en la app sirve para que el equipo y la CI lean los mismos resúmenes.

Desde un clon de este repositorio (el script también instala las skills oficiales en la app, así que necesita Android CLI):

```powershell
# Windows
.\plugins\android-feature-kit\scripts\install-pack.ps1 -Project C:\code\mi-app -WithRepoTools
```

```bash
# macOS o Linux
bash plugins/android-feature-kit/scripts/install-pack.sh --project ~/code/mi-app --with-repo-tools
```

Sin Android CLI, copia a mano los `.py` y el `README.md` de [`repo-tools/agent-checks/`](repo-tools/agent-checks/) a `tools/agent-checks/` en la app.

### 6. Revisa el .gitignore

El kit guarda sus archivos de trabajo en `build/android-feature-kit/`: el alcance de la tarea, el plan aprobado y los prompts y respuestas de la revisión. Los proyectos Android suelen ignorar `build/`; confirma que la carpeta `build/` de la raíz también está ignorada.

### 7. Haz commit

Sube a la app el `CLAUDE.md`, `.claude/android-feature-kit.md`, `.claude/android-feature-kit.json` y `tools/agent-checks/`, los que hayas usado. Así todo el equipo trabaja con las mismas reglas.

## Qué ruta toma cada pedido

| Lo que pides | Qué se activa | Cómo apruebas |
| :--- | :--- | :--- |
| Un cambio chico en una capa: un scroll, un texto, un mapper | La skill de esa capa, sin agentes | Un plan corto en Plan Mode |
| Una feature, una pantalla con su endpoint, un ticket o un plan escrito | `develop` y los agentes por capa | Un plan completo en Plan Mode |
| Una pregunta sobre el código, un build o tests que fallan, una revisión | `analyze` | En la conversación |

Claude elige la ruta por la descripción de cada skill y por el párrafo del `CLAUDE.md`. Si un pedido no toma la ruta que esperabas, usa los atajos `/android-feature-kit:develop` o `/android-feature-kit:analyze`.

## Ejemplos

### "Necesito modificar la screen de órdenes para que tenga un scroll"

Es un cambio chico en una sola capa, la de presentación. No hacen falta agentes.

1. Claude carga la skill `feature-ui-compose`.
2. Lee la pantalla de órdenes y una o dos pantallas vecinas para seguir sus convenciones. Esto entra en la exploración aprobada, así que no te pregunta.
3. Si el código no responde algo de comportamiento, te pregunta. Por ejemplo, si el encabezado con el total se desplaza con la lista o queda fijo. Lo que el código ya muestra, como usar `LazyColumn` si el módulo ya lo usa, no se pregunta.
4. Te muestra un plan corto en Plan Mode, por ejemplo:

   ```
   Goal: la lista de órdenes se desplaza cuando no cabe en la pantalla; el encabezado queda fijo.
   Modules: feature/orders
   Agents: none
   Work: en OrdersScreen.kt, la lista pasa a LazyColumn y se agrega una preview con 30 órdenes. Skill: feature-ui-compose.
   Checks: compilar y correr los tests de :feature:orders
   Review: ninguna
   ```

5. Lo apruebas. Claude hace el cambio en la misma conversación y corre los chequeos del módulo.
6. Te dice qué cambió y qué chequeos corrió.

Si quieres una revisión, agrégalo al pedido: "y que lo revise android-reviewer". Si Claude empieza a editar sin mostrarte un plan, por ejemplo en un repositorio sin el párrafo del `CLAUDE.md`, dile "muéstrame el plan primero" o usa `/android-feature-kit:develop`.

### "Lee el plan que dejé en el módulo :orders para que lo podamos implementar"

Es una implementación con varias capas, así que se activa `develop`.

1. La tarea es tu plan. Si Claude no encuentra el archivo, te pregunta la ruta. Para ahorrarte esa pregunta, dila en el pedido: "lee feature/orders/PLAN.md".
2. Claude entra en Plan Mode y lee lo justo: tu plan, `settings.gradle.kts`, la estructura de paquetes del módulo y `git status`.
3. Revisa si tu plan sirve como brief. Si tiene criterios de aceptación, se usa tal cual. Si le faltan decisiones, propone escribir solo lo que falta en `docs/features/orders/<id>.md`.
4. Te pregunta en una sola ronda lo que ni tu plan ni el código responden: qué pasa sin conexión, cómo se muestra un error, el payload del endpoint, los eventos de tracking.
5. Revisa que ninguna otra sesión esté trabajando en el mismo checkout.
6. Te muestra su plan. Por ejemplo, si tu plan era cancelar una orden desde el detalle:

   ```
   Goal: cancelar una orden desde el detalle. El botón aparece solo en órdenes pendientes; al cancelar, la orden pasa a Cancelada; sin conexión se muestra un error y la orden no cambia.
   Modules: feature/orders
   Decisions: sin conexión, error en la misma pantalla y sin cambios locales (tu respuesta)
   Brief: feature/orders/PLAN.md, porque ya tiene criterios de aceptación
   Agents: domain-builder (sonnet), data-builder (haiku), ui-builder (sonnet)
   Work: domain-builder agrega CancelOrderUseCase y el error OrderNotCancellable; después, en paralelo, data-builder implementa POST /orders/{id}/cancel y ui-builder agrega el botón y su estado
   Integration: none
   Checks: compileDebugKotlin y testDebugUnitTest de :feature:orders; build-doctor y test-analyst (haiku) si algo falla
   Review: android-reviewer, hasta 2 rondas
   Stop and ask when: aparece una decisión nueva, un agente pide otro modelo, hace falta escalar, la revisión necesita más rondas
   ```

7. Lo apruebas en Plan Mode. Claude Code te ofrece "Yes, and use auto mode", "Yes, manually approve edits" o "No, keep planning". Con la última le explicas qué cambiar y te propone el plan de nuevo.
8. Recién ahí empieza el trabajo. Claude registra el alcance de la tarea y escribe el brief si el plan lo incluye. Después corre `domain-builder`, y luego `data-builder` y `ui-builder` en paralelo. `feature-integrator` solo entra si el plan tiene integración: Gradle, el catálogo de versiones o el NavHost de la app.
9. Mientras trabajan, Claude te pregunta antes de:
   - cambiar el contrato de dominio de una forma que el plan no traía;
   - agregar una dependencia o cambiar una versión;
   - pasar `data-builder` a sonnet;
   - llamar a `android-architect`;
   - hacer una ronda de revisión más allá del tope.

   Si un agente se detiene por una decisión, la pregunta te llega a ti y el agente sigue donde quedó.
10. Cada agente compila y prueba su parte. Si algo falla, `build-doctor` o `test-analyst` diagnostican y el arreglo vuelve al agente dueño de esa capa.
11. Revisa el revisor que elegiste, hasta el tope de rondas. Ves los hallazgos, con el ID de la regla que rompen (por ejemplo `UI-14`), y decides cuáles se arreglan.
12. Claude te reporta qué cambió por capa, qué decisiones se tomaron y dónde quedaron, qué chequeos corrieron y el veredicto de la revisión. Al final libera el checkout.

### "Agrega la pantalla de detalle de orden; el backend tiene GET /orders/{id}"

Igual que el ejemplo anterior, pero sin un plan tuyo. Como crea una pantalla y un endpoint, Claude propone escribir un brief en `docs/features/orders/<id>.md` con el objetivo, los criterios de aceptación y las decisiones abiertas. Si la nueva pantalla se monta en el NavHost de la app, el plan incluye a `feature-integrator`.

### "¿Por qué falla el build de :orders?"

Se activa `analyze`. Claude te propone en la conversación algo como: "build-doctor (haiku) correría `./gradlew :feature:orders:compileDebugKotlin` a través de `gradle_summary.py`; eso escribe en la carpeta build". Le dices que sí. Te devuelve la causa, el archivo y la línea, el arreglo propuesto y quién debería hacerlo. No cambia nada. Si después le dices "arréglalo", eso ya es trabajo de `develop`, con su plan.

### "Revisa mi rama contra main"

Se activa `analyze`. Te ofrece `android-reviewer` (sonnet) y, si lo configuraste, el revisor externo. Tú eliges. Los hallazgos vienen con severidad, el ID de la regla, el archivo y la línea, y quién lo arregla.

### "Explícame cómo carga los datos el módulo orders"

Se activa `analyze` y lee los puntos de entrada del módulo: el grafo, las pantallas, los ViewModels, los casos de uso y los repositorios. Si tienes instalado android-module-map, te ofrece generar el mapa del módulo, pero antes te pregunta, porque escribe en `docs/architecture/`.

### Los atajos

- `/android-feature-kit:develop agrega el filtro por fecha en órdenes`: va directo a `develop` con esa tarea.
- `/android-feature-kit:develop` sin texto: te pregunta qué quieres hacer y espera.
- `/android-feature-kit:analyze ¿dónde se usa OrderRepository?`: va directo a `analyze`.

## Qué te pregunta y qué no

Nunca te pregunta por lo que el código ya muestra:

- nombres de clases, funciones, archivos y paquetes;
- en qué paquete de la capa va cada archivo;
- reutilizar un helper, una extensión o un componente del design system que ya existe;
- la estructura de los tests nuevos.

Siempre te pregunta por:

- comportamiento, manejo sin conexión, cómo se muestran los errores, salidas de navegación y eventos;
- alcance y contratos externos, como el endpoint o el payload;
- una interfaz pública nueva, una dependencia nueva o un cambio de versión, y la estrategia de una migración;
- cambiar el modelo de un agente, escalar a `android-architect` o hacer más rondas de revisión;
- qué hallazgos de la revisión se arreglan;
- cualquier exploración fuera de los límites aprobados.

Si quieres que deje de preguntarte por algo, agrégalo a las elecciones rutinarias en `.claude/android-feature-kit.md`.

## Problemas comunes

**Mi pedido no activó `develop` ni `analyze`.** Usa el atajo, o menciona el kit en el pedido. Tener el párrafo en el `CLAUDE.md` ayuda.

**Claude dice que otra sesión tiene el checkout.** Solo una tarea del kit trabaja a la vez en un checkout. Si la otra sesión ya terminó o se cerró, borra el archivo tú mismo con `! rm build/android-feature-kit/scope.json` y dile a Claude que siga. Claude no lo puede borrar por su cuenta.

**El plan gate bloqueó un agente.** El plan aprobado no tenía una línea `Agents:` con ese agente, o el agente iba a correr con otro modelo. Pídele a Claude que te muestre el plan de nuevo con el agente y su modelo entre paréntesis.

**Los hooks no hacen nada.** Falta Python 3.8 o superior en el PATH. Sin Python, los hooks dejan pasar todo.

**El revisor externo falla.** Claude te muestra el estado que devuelve `run_review.py`. Revisa que el comando de `.claude/android-feature-kit.json` exista en el PATH (por ejemplo `codex`) y mira el log en `build/android-feature-kit/review/`.

## Dónde está cada cosa

| Qué | Dónde |
| :--- | :--- |
| Ruteo para el `CLAUDE.md` de la app | `skills/develop/references/claude-md-block.md` |
| Reglas del repositorio (plantilla) | `skills/develop/references/project-rules.md`, copiada a `.claude/android-feature-kit.md` en la app |
| Plan gate y revisor externo | `.claude/android-feature-kit.json` en la app |
| Archivos de trabajo de cada tarea | `build/android-feature-kit/` en la app |
| Scripts de chequeo | `tools/agent-checks/` en la app, o `repo-tools/agent-checks/` del plugin |
| Reglas del equipo con ID | `skills/<skill>/references/rules.md` |
| Cómo decide el kit y por qué | [README.md](README.md), secciones "How the kit decides" y "Why the kit is built this way" |
