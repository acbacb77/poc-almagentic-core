# poc-almagentic-core

Núcleo del **ALM agéntico** de la POC: el camino estándar que consumen las aplicaciones.
Contiene los workflows reutilizables (CI, seguridad, revisión por agente, supply chain, promoción y trazabilidad) y los estándares comunes de los agentes.

**Solo lo modifican humanos.** El agente de código trabaja en `poc-almagentic-app` y no puede cambiar los controles que lo vigilan.

## Cómo se consume

Las aplicaciones llaman a los workflows de este repo por versión:

```yaml
jobs:
  ci:
    uses: acbacb77/poc-almagentic-core/.github/workflows/reusable-ci.yml@v1
```

## Versionado

- Etiquetas semánticas (`v1.0.0`) y una etiqueta móvil por versión mayor (`v1`).
- Un cambio incompatible exige una nueva versión mayor; las apps la adoptan con un PR propio.

## Estructura (se completa tarea a tarea)

```
.github/workflows/
  reusable-ci.yml             # build, tests, lint (tarea 6)
  reusable-security.yml       # Semgrep, Trivy, gitleaks (tarea 7)
  reusable-agent-review.yml   # revisor con permisos mínimos (tarea 8)
  reusable-supply-chain.yml   # SBOM, firma, atestación (tarea 9)
  reusable-promote.yml        # abre el PR en gitops (tarea 10)
  reusable-traceability.yml   # informe por release (tarea E)
agent-standards/              # reglas, constitución y permisos base (tarea 3)
prompts/                      # instrucciones del revisor y del triage (tareas 8, A)
policies/                     # reglas para revisar la config del agente (tarea 7)
scripts/traceability/         # generador del informe (tarea E)
```

## Repos de la POC

- [poc-almagentic-app](https://github.com/acbacb77/poc-almagentic-app): código y harness del agente
- [poc-almagentic-gitops](https://github.com/acbacb77/poc-almagentic-gitops): estado deseado del cluster
