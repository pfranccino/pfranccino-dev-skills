# Integración CI/CD con android-gradle-analyzer

## Flags disponibles para CI

```bash
# Falla el pipeline si hay ciclos
gradle-sanity <ruta> --fail-on-cycle --quiet

# Falla si el score cae por debajo de N
gradle-sanity <ruta> --fail-on-score-below 70 --quiet

# Salida JSON para parsear en el pipeline
gradle-sanity <ruta> --json > sanity-report.json

# Combinar: falla en ciclos Y si el score baja de 70
gradle-sanity <ruta> --fail-on-cycle --fail-on-score-below 70 --quiet
```

## GitHub Actions — ejemplo completo

```yaml
# .github/workflows/architecture-health.yml
name: Architecture Health

on:
  pull_request:
    branches: [main, develop]

jobs:
  gradle-health:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install android-gradle-analyzer
        run: pipx install git+https://github.com/pfranccino/android-gradle-analyzer.git

      - name: Run sanity check (fail on cycles)
        run: |
          gradle-sanity . --fail-on-cycle --quiet
        working-directory: ${{ github.workspace }}

      - name: Run sanity check (score gate)
        run: |
          gradle-sanity . --fail-on-score-below 70 --quiet

      - name: Generate JSON report (artifact)
        if: always()
        run: |
          gradle-sanity . --json > sanity-report.json

      - name: Upload sanity report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sanity-report
          path: sanity-report.json

      - name: Comment score on PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('sanity-report.json'));
            const score = report.score;
            const emoji = score >= 90 ? '🟢' : score >= 70 ? '🟡' : score >= 50 ? '🟠' : '🔴';
            const body = `## Architecture Health Report\n\n${emoji} Score: **${score}/100**\n\nCycles: ${report.violations.cycles.length} | SDP violations: ${report.violations.sdp.length}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body
            });
```

## Configuración por proyecto con `analyzer.yml`

Crear en la raíz del proyecto Android:

```yaml
# analyzer.yml
sanity:
  fail_on_cycle: true
  fail_on_score_below: 75
  output_dir: reports/sanity

impact:
  output_dir: reports/impact

analyzer:
  output_dir: reports/diagrams
  format: mermaid
```

Con esto, el comando en CI simplifica a:

```bash
gradle-sanity .  # toma configuración de analyzer.yml automáticamente
```

## Estrategia de rollout recomendada

1. **Semana 1:** Correr en modo informativo (sin `--fail-on-*`), solo subir artifact.
2. **Semana 2:** Activar `--fail-on-cycle`. Los ciclos son bloqueantes.
3. **Semana 3:** Activar `--fail-on-score-below 50`. Solo bloquea arquitecturas críticas.
4. **Mes 2+:** Subir gradualmente el umbral: 60 → 70 → 75 a medida que la arquitectura mejora.

## Analizar módulos específicos en PR

Para proyectos grandes, analizar solo los módulos tocados en el PR:

```bash
# Obtener módulos modificados
CHANGED=$(git diff --name-only origin/main | grep "build.gradle" | xargs -I{} dirname {} | sort -u)

for MODULE in $CHANGED; do
  echo "Analyzing $MODULE..."
  gradle-sanity "$MODULE" --fail-on-cycle --quiet
done
```
