# pfranccino-dev-skills

Colección de skills para Claude — herramientas de análisis y arquitectura de software.

## Skills disponibles

| Skill | Qué hace |
|---|---|
| [`android-gradle-health`](skills/android-gradle-health/) | Analiza y mejora la salud arquitectónica de proyectos Android multi-módulo con [android-gradle-analyzer](https://github.com/pfranccino/android-gradle-analyzer): ciclos, violaciones SDP, métricas Ca/Ce/I, health score y lógica compartida mal ubicada. Convierte el output en diagnósticos accionables con pasos de remediación. |

## Estructura

```
pfranccino-dev-skills/
├── README.md
└── skills/
    └── android-gradle-health/
        ├── SKILL.md          # entrada: descripción, mapa de comandos, flujo
        ├── references/       # guías bajo demanda (fix-cycles, thresholds, etc.)
        └── examples/         # configs por tamaño de proyecto, listos para copiar
```

Cada skill vive en `skills/<nombre>/` con su `SKILL.md` como punto de entrada.

## Uso

Para usar una skill en Claude Code, copia su carpeta al directorio de skills:

```bash
# Personal (todas tus sesiones)
cp -r skills/android-gradle-health ~/.claude/skills/

# Por proyecto
cp -r skills/android-gradle-health <tu-proyecto>/.claude/skills/
```

Claude la activará automáticamente cuando el contexto coincida con su `description`.

## Licencia

MIT
