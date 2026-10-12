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
  reusable-triage.yml         # agente de triage de peticiones (tarea A)
  ci.yml                      # tests propios de core: hook y triage
  reusable-ci.yml             # tests, lint (ruff) y tipos (mypy) con uv.lock (tarea 6)
  reusable-security.yml       # bandit, pip-audit, licencias, gitleaks y cambios del agente (tarea 7)
  reusable-agent-review.yml   # revisor: compara el PR con su spec y comenta (tarea 8)
  reusable-agent-respond.yml  # atiende @claude en un PR y sube el cambio como el bot (tarea 8)
  reusable-agent-feature.yml  # aprobado → PR de spec; merge de la spec → PR de implementación (extensión F)
  reusable-supply-chain.yml   # imagen: prueba, SBOM, firma con cosign y atestaciones SLSA (tarea 9)
  reusable-promote.yml        # abre el PR en gitops (tarea 10)
  reusable-traceability.yml   # informe por release (tarea E)
agent-standards/              # reglas, constitución y permisos base (tarea 3)
prompts/                      # instrucciones del revisor y del triage (tareas 8, A)
policies/                     # reglas para revisar la config del agente (tarea 7)
scripts/triage/               # prompt builder, esquema y aplicación del triage (tarea A)
scripts/traceability/         # generador del informe (tarea E)
```

## Triage de peticiones

`reusable-triage.yml` separa **pensar** de **actuar**:

| Job | Quién | Permisos | Qué hace |
|---|---|---|---|
| `analyze` | Claude (modelo sin herramientas) | Leer issues | Lee la petición y devuelve un JSON con tipo, prioridad, tamaño, criterios, duplicados y riesgos |
| `apply` | Script determinista | Escribir issues | Valida el JSON contra listas cerradas, neutraliza el texto y aplica etiquetas y comentario |

El texto de la petición nunca pasa por la shell ni por expresiones `${{ }}`. Si contiene una prompt injection, lo peor que consigue es una propuesta mal clasificada que revisa un humano; el modelo no puede añadir `aprobado` ni mencionar a nadie.

Requiere en el repo que lo llama el secreto `CLAUDE_CODE_OAUTH_TOKEN`, generado con `claude setup-token`.

```bash
python3 -m pytest scripts/triage agent-standards/hooks -q   # tests
```

## Bitácora

Pasos, decisiones, configuración manual y problemas resueltos de la POC: [docs/poc/README.md](docs/poc/README.md).

## Repos de la POC

- [poc-almagentic-app](https://github.com/acbacb77/poc-almagentic-app): código y harness del agente
- [poc-almagentic-gitops](https://github.com/acbacb77/poc-almagentic-gitops): estado deseado del cluster
