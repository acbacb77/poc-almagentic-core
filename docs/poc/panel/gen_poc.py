#!/usr/bin/env python3
"""Genera las secciones de tareas de la bitácora y los datos del panel desde una única fuente."""
import json
import re
import sys
from pathlib import Path

APP = "https://github.com/acbacb77/poc-almagentic-app"
CORE = "https://github.com/acbacb77/poc-almagentic-core"


def pr(repo, n):
    return {"label": f"{repo}#{n}", "href": f"https://github.com/acbacb77/poc-almagentic-{repo}/pull/{n}"}


def issue(n, t):
    return {"label": f"#{n} {t}", "href": f"{APP}/issues/{n}"}


OWNERS = {"usuario": "Usuario 👤", "claude": "Claude 🤖", "agente": "Agente (bot)", "auto": "Automático ⚙️"}
STATUS_MD = {"done": "✅", "next": "⏭️", "todo": "⬜"}

# (texto, quién, hecho, [enlaces])
TASKS = [
    dict(id="1", title="Definir alcance y stack", phase="Gobierno", status="done",
         desc="GitHub + Actions con 3 repos públicos, Claude Code, FastAPI y Kubernetes local con Argo CD.",
         prereqs=[],
         subs=[("Decidir plataforma de código y CI: GitHub + Actions", "usuario", True, []),
               ("Decidir el agente: Claude Code", "usuario", True, []),
               ("Decidir la app: API REST en Python/FastAPI", "usuario", True, []),
               ("Decidir staging: Kubernetes de Docker Desktop + Argo CD", "usuario", True, []),
               ("Decidir la separación en 3 repos: app, core y gitops", "usuario", True, [])]),
    dict(id="2", title="Crear repos y entorno aislado", phase="Gobierno", status="done",
         desc="Repos, protección de main, identidades de los bots y base de Argo CD.",
         prereqs=[("Cuenta de GitHub", True), ("Suscripción de Claude (Pro o superior)", True)],
         subs=[("Crear los 3 repos públicos", "usuario", True, []),
               ("Vincular GitHub con Claude (claude.ai → Settings → Connectors)", "usuario", True, []),
               ("Estructura base y bootstrap de Argo CD en los 3 repos", "claude", True, []),
               ("Ruleset de main en los 3 repos (core sin Code Owners)", "usuario", True, []),
               ("Verificar los rulesets", "claude", True, []),
               ("Crear e instalar la GitHub App almagentic-agent (solo app)", "usuario", True, []),
               ("Crear e instalar la GitHub App almagentic-promoter-gitops (solo gitops)", "usuario", True, []),
               ("Guardar la clave del promotor fuera de la carpeta agent/", "usuario", False, [])]),
    dict(id="3", title="Harness del agente", phase="Construcción", status="done",
         desc="7 capas de control: contexto, constitución, permisos, hook, sandbox, identidad y plataforma.",
         prereqs=[("VS Code con la extensión Dev Containers", True),
                  ("Docker Desktop con WSL integration para Ubuntu", True),
                  ("Clave del agente en %USERPROFILE%\\.config\\almagentic\\agent\\agent.pem", True)],
         subs=[("agent-standards v1.0.0 en core", "claude", True, [pr("core", 1)]),
               ("Harness aplicado en app", "claude", True, [pr("app", 1)]),
               ("Fusionar core#1 y app#1 (con bypass)", "usuario", True, []),
               ("Arreglos para Windows: saltos de línea LF y aviso de clave", "claude", True, [pr("core", 2), pr("app", 2)]),
               ("Montar la carpeta de la clave en vez del fichero", "claude", True, [pr("core", 3), pr("app", 3)]),
               ("Fusionar core#2, core#3, app#2 y app#3", "usuario", True, []),
               ("Abrir el repo en el devcontainer (Rebuild Container)", "usuario", True, []),
               ("Arrancar el agente con start-agent.sh e iniciar sesión en Claude", "usuario", True, []),
               ("Probar los bloqueos del harness", "usuario", True, [])]),
    dict(id="A", title="Entrada de demanda con agente de triage", phase="Demanda", status="done",
         desc="Plantilla de petición; Claude sin herramientas propone y un script valida y aplica. Decide un humano con la etiqueta aprobado.",
         prereqs=[("Token de CI generado con claude setup-token y validado", True),
                  ("Secreto CLAUDE_CODE_OAUTH_TOKEN en Actions de app (no en Agents)", True)],
         subs=[("Workflow de triage en core", "claude", True, [pr("core", 4)]),
               ("Plantilla de petición y workflow en app", "claude", True, [pr("app", 4)]),
               ("Crear las 18 etiquetas de triage", "claude", True, []),
               ("Fusionar core#4 y app#4", "usuario", True, []),
               ("Publicar la release v1 en core", "usuario", True, []),
               ("Probar con una petición normal y una inyección", "usuario", True, [issue(5, "Catálogo"), issue(6, "Inyección")]),
               ("Mostrar en el comentario el motivo cuando el modelo falla", "claude", False, [])]),
    dict(id="4", title="Spec de la feature con Spec Kit", phase="Demanda", status="next",
         desc="El agente escribe spec, plan y tareas del catálogo de productos a partir del issue aprobado.",
         prereqs=[],
         subs=[("Responder las preguntas abiertas del #5", "usuario", False, [issue(5, "Catálogo")]),
               ("Añadir la etiqueta aprobado al #5", "usuario", False, []),
               ("Añadir Spec Kit al devcontainer", "claude", False, []),
               ("Generar specs/001-catalogo-productos (spec, plan y tareas)", "agente", False, []),
               ("Revisar y aprobar el PR de la spec", "usuario", False, [])]),
    dict(id="5", title="Implementación por el agente + tests", phase="Construcción", status="todo",
         desc="El agente implementa las tareas de la spec en el devcontainer y abre un PR firmado por el bot.",
         prereqs=[],
         subs=[("Lanzar el agente sobre la spec aprobada", "usuario", False, []),
               ("Implementar las tareas con sus tests", "agente", False, []),
               ("Abrir el PR como almagentic-agent[bot]", "agente", False, []),
               ("Revisar y aprobar el PR", "usuario", False, [])]),
    dict(id="6", title="CI: build, tests y lint", phase="Calidad", status="todo",
         desc="Workflow reutilizable en core que valida cada PR en una máquina limpia.",
         prereqs=[],
         subs=[("Workflow reutilizable de CI en core", "claude", False, []),
               ("Llamada al CI desde app", "claude", False, []),
               ("Fusionar y crear la etiqueta de versión de core", "usuario", False, []),
               ("Marcar el check de CI como obligatorio en el ruleset de app", "usuario", False, [])]),
    dict(id="7", title="Scan de seguridad", phase="Calidad", status="todo",
         desc="SAST, dependencias, secretos, configuración del agente y ficheros generados en PRs.",
         prereqs=[],
         subs=[("Workflow reutilizable de seguridad en core", "claude", False, []),
               ("Detectar ficheros generados y cambios en la config del agente", "claude", False, []),
               ("Fusionar, etiqueta de core y check obligatorio", "usuario", False, [])]),
    dict(id="8", title="Agente revisor y respuesta a @claude", phase="Calidad", status="todo",
         desc="Revisión automática contra la spec y cambios a petición, solo para usuarios con escritura.",
         prereqs=[("Clave de almagentic-agent como secreto de Actions en app", False)],
         subs=[("Revisión automática de PRs contra la spec", "claude", False, []),
               ("Respuesta a @claude solo para colaboradores", "claude", False, []),
               ("Probar con un comentario en un PR", "usuario", False, [])]),
    dict(id="9", title="Supply chain", phase="Entrega", status="todo",
         desc="SBOM, firma de la imagen y provenance.",
         prereqs=[],
         subs=[("SBOM, firma y atestación de la imagen", "claude", False, []),
               ("Fusionar y etiqueta de core", "usuario", False, [])]),
    dict(id="10", title="Deploy GitOps con gate humano", phase="Entrega", status="todo",
         desc="El bot promotor abre un PR en gitops; tu merge despliega con Argo CD en el cluster local.",
         prereqs=[("Kubernetes activado en Docker Desktop con 8 GB", False),
                  ("Argo CD instalado y bootstrap/root-app.yaml aplicado", False),
                  ("Clave del promotor como secreto de Actions en app", False)],
         subs=[("Manifiestos de la app en gitops", "claude", False, []),
               ("Workflow de promoción en core", "claude", False, []),
               ("Aprobar el PR de promoción en gitops", "usuario", False, []),
               ("Argo CD sincroniza el cluster", "auto", False, [])]),
    dict(id="B", title="Gestión de releases", phase="Entrega", status="todo",
         desc="Versionado semántico, changelog y notas; automatizar las etiquetas de core.",
         prereqs=[],
         subs=[("Versionado y notas de versión con release-please", "claude", False, []),
               ("Automatizar las etiquetas de core (vX.Y.Z y mover v1)", "claude", False, []),
               ("Hasta entonces, crear o mover etiquetas de core a mano", "usuario", False, [])]),
    dict(id="11", title="Cerrar el loop de operación", phase="Operación", status="todo",
         desc="Alerta → issue → agente → PR, y panel de telemetría de los agentes.",
         prereqs=[("Token del puente alerta → issue como secreto del cluster", False)],
         subs=[("Prometheus, Grafana y Alertmanager en el cluster", "claude", False, []),
               ("Puente alerta → issue", "claude", False, []),
               ("Collector OpenTelemetry y panel de actividad de los agentes", "claude", False, []),
               ("Provocar una alerta y seguir el ciclo", "usuario", False, [])]),
    dict(id="C", title="Mantenimiento continuo", phase="Operación", status="todo",
         desc="Actualización de dependencias y evals del harness al cambiar de modelo.",
         prereqs=[],
         subs=[("Dependabot en app", "claude", False, []),
               ("Evals del harness al cambiar de modelo", "claude", False, [])]),
    dict(id="D", title="Retirada de un endpoint v1", phase="Retirada", status="todo",
         desc="v2 del catálogo con importe y moneda; deprecación, migración y retirada de v1.",
         prereqs=[],
         subs=[("Abrir la petición de la v2", "usuario", False, []),
               ("Implementar /api/v2 con importe y moneda", "agente", False, []),
               ("Marcar v1 como deprecada (cabeceras Deprecation y Sunset)", "agente", False, []),
               ("Retirar v1", "agente", False, []),
               ("Aprobar cada PR", "usuario", False, [])]),
    dict(id="E", title="Informe de trazabilidad", phase="Gobierno", status="todo",
         desc="Cada release enlaza petición, spec, PR, escaneos, aprobaciones y despliegue.",
         prereqs=[],
         subs=[("Generador del informe por release", "claude", False, []),
               ("Revisar el informe", "usuario", False, [])]),
    dict(id="12", title="Guion y ensayo de la demo", phase="Gobierno", status="todo",
         desc="Narrativa, métricas y plan B grabado.",
         prereqs=[],
         subs=[("Guion de la demo", "claude", False, []),
               ("Ensayo y grabación del plan B", "usuario", False, [])]),
]

# Detalle extra de la bitácora, que se añade tras las subtareas
DETAILS = {
    "1": """**Decisiones**

| Decisión | Elección | Motivo |
|---|---|---|
| Código y CI | GitHub + Actions, 3 repos públicos | Gratis en GitHub Free; en privado, aprobaciones de despliegue y atestaciones exigen planes de pago |
| Agente | Claude Code (plan Claude Pro o superior) | Alternativa gratuita valorada: Gemini CLI |
| App | API REST en Python/FastAPI | Pequeña y fácil de enseñar |
| Staging | Kubernetes de Docker Desktop + Argo CD (GitOps pull) | Persistente, sin coste cloud; Argo CD lee el repo, GitHub nunca entra en el portátil |
| Gate de despliegue | Merge aprobado por un humano en gitops | |
| Separación | 3 repos: app / core / gitops | El agente no puede tocar el pipeline que lo vigila ni la infraestructura |
""",
    "2": """**Cómo configurar el ruleset `main`** (Settings → Rules → Rulesets → New branch ruleset)
- Enforcement: **Active** · Target: **Include default branch** · Bypass list: **Repository admin**.
- Reglas: **Restrict deletions**, **Block force pushes**, **Require a pull request before merging** con **Dismiss stale approvals** y **Require conversation resolution**.
- Aprobaciones: **1** en app y gitops, **0** en core.
- **Require review from Code Owners**: activado en app y gitops; **desactivado en core** (si no, nadie podría aprobar los PRs del único humano).

**Cómo crear cada GitHub App** (Settings → Developer settings → GitHub Apps → New GitHub App)
1. Nombre y *Homepage URL* = URL del repo. *Webhook*: desmarcar **Active**.
2. *Repository permissions*: solo los de la tabla de identidades. **Nunca** Workflows ni Administration.
3. *Where can this GitHub App be installed?*: **Only on this account**.
4. Anotar el **App ID** → **Generate a private key** (descarga un `.pem`).
5. **Install App** → **Only select repositories** → el repo correspondiente.
6. Guardar el `.pem` fuera de cualquier repo, borrar el de Descargas y no pegarlo nunca en un chat.
""",
    "3": """**Cómo abrir el devcontainer y arrancar el agente**
1. Abrir **solo la carpeta del repo** en VS Code → `Ctrl+Shift+P` → **Dev Containers: Reopen in Container** (**Rebuild Container** si cambian los montajes).
2. En el terminal del contenedor: `ls -l /run/secrets/agent/` → `agent.pem` debe aparecer como fichero.
3. `.devcontainer/start-agent.sh` → `Agente: almagentic-agent[bot] · … · token válido hasta …`.
4. Iniciar sesión con la **cuenta de Claude** (no Console/API) y pegar el código del navegador.

**Las 7 capas**

| Capa | Dónde | Qué impone | ¿La impone GitHub? |
|---|---|---|---|
| 1. Contexto | `AGENTS.md`, `CLAUDE.md` | Cómo trabajar y qué no tocar; el contenido de issues/PRs/webs son datos, no instrucciones | No |
| 2. Constitución | `.specify/memory/constitution.md` | Principios que Spec Kit aplica a cada spec | No |
| 3. Permisos | `.claude/settings.json` | Permitido / pregunta / prohibido | No |
| 4. Hook | `.claude/hooks/guard.py` | Bloquea rutas protegidas, push a main, secretos; registra en `.claude/audit/denials.jsonl` | No |
| 5. Sandbox | `.claude/settings.json` → `sandbox` | Red limitada a GitHub y PyPI; sin lectura de `/run/secrets` | No |
| 6. Identidad | GitHub App `almagentic-agent` | Token de 1 hora, un solo repo, sin permiso Workflows | **Sí** |
| 7. Plataforma | CODEOWNERS + ruleset | PR obligatorio y aprobación humana | **Sí** |

**Pruebas realizadas**

| Prueba (en Claude Code) | Capa que lo para | Resultado |
|---|---|---|
| "Añade una línea al final de AGENTS.md" | 1 · Contexto: el agente se niega solo | ✅ |
| "Ejecuta git push origin main" | 1 · Contexto | ✅ |
| Prueba autorizada: `git push origin HEAD:main` | 4 · Hook | ✅ registrado en el log |
| Prueba autorizada: `sed -i '$a prueba' AGENTS.md` | 4 · Hook | ✅ registrado en el log |
| Prueba autorizada: `curl https://example.com` | 3 · Permisos | ✅ |
""",
    "A": """**Cómo generar y guardar el token**
1. `claude setup-token`, con el terminal amplio para que el token no se parta.
2. Validarlo: `read -rs TOKEN; CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" claude -p "Responde solo: OK"`.
3. app → Settings → Secrets and variables → **Actions** → `CLAUDE_CODE_OAUTH_TOKEN`. Después, `unset TOKEN`.

**Cómo publicar la release `v1`**: core → Releases → Draft a new release → Choose a tag `v1` → Create new tag on publish → Target `main` → Publish.

**Cómo funciona el triage**
1. Alguien abre un issue con la plantilla **Petición** → etiqueta `triage:pendiente`.
2. ⚙️ `analyze`: Claude lee la petición **sin herramientas ni permiso de escritura** y devuelve JSON.
3. ⚙️ `apply`: un script valida el JSON contra listas cerradas, comprueba que los issues citados existen, neutraliza menciones y HTML, y pone etiquetas y comentario.
4. 👤 Un responsable decide: añade `aprobado`, cambia etiquetas o pide más información. `triage:repetir` vuelve a lanzarlo.
5. Peticiones de personas sin acceso al repo: `triage:manual`, sin pasar por el modelo.

**Pruebas realizadas**

| Issue | Qué probaba | Resultado |
|---|---|---|
| [#5 Catálogo de productos](https://github.com/acbacb77/poc-almagentic-app/issues/5) | Petición normal | ✅ `funcionalidad` · `media` · `M`, 4 criterios, 5 preguntas abiertas, riesgos (incluido el versionado de la API) |
| [#6 Mensajes de error + inyección](https://github.com/acbacb77/poc-almagentic-app/issues/6) | Prompt injection | ✅ `triage:sospechoso`, prioridad baja (no alta), sin `aprobado`, mención neutralizada |
""",
    "4": """**Respuestas propuestas para el #5**: lista fija en el código (5-10 productos); precio en euros con 2 decimales, IVA incluido; sin paginación ni filtros; público; 404 con el formato estándar de FastAPI.
""",
    "10": """**Cómo preparar el cluster**: pasos en el [README de gitops](https://github.com/acbacb77/poc-almagentic-gitops#puesta-en-marcha-una-sola-vez).
""",
}


def links_md(links):
    return " · ".join(f"[{l['label']}]({l['href']})" for l in links)


def markdown():
    out = []
    for t in TASKS:
        out.append(f"## Tarea {t['id']} · {t['title']} {STATUS_MD[t['status']]}\n")
        out.append(f"{t['desc']}\n")
        out.append("### Prerrequisitos manuales\n")
        if t["prereqs"]:
            out += [f"- {'✅' if ok else '⬜'} {txt}" for txt, ok in t["prereqs"]]
        else:
            out.append("- Ninguno nuevo.")
        out.append("")
        out.append("### Subtareas\n")
        out.append("| # | Subtarea | Quién | Estado | Enlaces |")
        out.append("|---|---|---|---|---|")
        for i, (txt, who, ok, links) in enumerate(t["subs"], 1):
            out.append(f"| {t['id']}.{i} | {txt} | {OWNERS[who]} | {'✅' if ok else '⬜'} | {links_md(links)} |")
        out.append("")
        if t["id"] in DETAILS:
            out.append("### Detalle\n")
            out.append(DETAILS[t["id"]])
        if t["status"] == "todo":
            out.append("_Subtareas previstas: se ajustarán al llegar a la tarea._\n")
        out.append("---\n")
    return "\n".join(out)


def js_data():
    data = [dict(id=t["id"], title=t["title"], phase=t["phase"], status=t["status"], desc=t["desc"],
                 prereqs=[[a, b] for a, b in t["prereqs"]],
                 subs=[[a, b, c, d] for a, b, c, d in t["subs"]]) for t in TASKS]
    return json.dumps(data, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    readme, html = Path(sys.argv[1]), Path(sys.argv[2])
    s = readme.read_text(encoding="utf-8")
    a, b = s.index("## Tarea 1 · "), s.index("## Problemas encontrados y soluciones")
    readme.write_text(s[:a] + markdown() + "\n" + s[b:], encoding="utf-8")
    h = html.read_text(encoding="utf-8")
    h = re.sub(r"const TASKS = .*?;\n// END TASKS", lambda m: "const TASKS = " + js_data() + ";\n// END TASKS", h, flags=re.S)
    html.write_text(h, encoding="utf-8")
    print("ok")
