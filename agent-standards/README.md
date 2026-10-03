# agent-standards

Estándar común para los agentes de código de la organización. Versión actual: ver [`VERSION`](VERSION).

## Capas del harness

| Capa | Fichero | Qué hace | ¿Se puede saltar? |
|---|---|---|---|
| 1. Contexto | `AGENTS.base.md` | Le dice al agente cómo trabajar y qué no tocar | Sí: es una guía, no una barrera |
| 2. Constitución | `constitution.base.md` | Principios que Spec Kit aplica a cada spec y plan | Sí: se revisa en el PR |
| 3. Permisos | `claude-settings.base.json` → `permissions` | Lista de lo permitido, lo que pregunta y lo prohibido | Parcialmente: solo ve el comando tal como se escribe |
| 4. Hooks | `hooks/guard.py` | Bloquea rutas protegidas, push a main, secretos; registra cada bloqueo | Difícil: analiza cada subcomando |
| 5. Sandbox | `claude-settings.base.json` → `sandbox` | El sistema operativo limita red y lectura de secretos en Bash | No desde el agente |
| 6. Identidad | `scripts/start-agent.sh` | Token de 1 hora de una GitHub App sin permiso Workflows | No: lo impone GitHub |
| 7. Plataforma | CODEOWNERS + ruleset de `main` | PR obligatorio y aprobación humana | No: lo impone GitHub |

Las capas 1 a 5 viven en el repo de la aplicación y las ejecuta Claude Code. Las capas 6 y 7 las impone GitHub, así que siguen funcionando aunque el agente consiga saltarse las anteriores.

## Cómo lo consume un repo de aplicación

1. Copia `AGENTS.base.md` al principio de su `AGENTS.md` y añade debajo su sección específica.
2. Copia `constitution.base.md` en `.specify/memory/constitution.md` y añade, si hace falta, principios propios.
3. Parte de `claude-settings.base.json` para su `.claude/settings.json`, añadiendo los comandos de su stack.
4. Copia `hooks/guard.py` en `.claude/hooks/guard.py` y `scripts/start-agent.sh` en `.devcontainer/`.
5. Escribe la versión usada en `.agent-standards-version`.

El pipeline de seguridad (tarea 7) comprobará que las copias no se desvían de la versión declarada.

## Tests del guardarraíl

```bash
python3 -m pytest agent-standards/hooks -q
```
