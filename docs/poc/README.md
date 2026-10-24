# Bitácora de la POC de ALM agéntico

Registro de todo lo hecho en la POC: decisiones, pasos manuales, PRs y problemas resueltos. Se actualiza al cerrar cada tarea, junto con la [memoria del TFM](../tfm/README.md), que es requisito para cerrar la POC.

**Última actualización:** 24 de octubre de 2026 · **Avance:** 14 de 18 tareas (1, 2, 3, A, 4, 5, 6, 7, 8, F, 9, 10, B y 11)

**Cada tarea tiene sus prerrequisitos manuales y sus subtareas en orden.** **Leyenda de responsables:** Usuario 👤 (acción manual) · Claude 🤖 (sesión de trabajo) · Agente (bot `almagentic-agent` en el devcontainer) · Automático ⚙️ (GitHub Actions, Argo CD)

---

## Visión general

### Repos

| Repo | Qué contiene | Quién escribe |
|---|---|---|
| [poc-almagentic-app](https://github.com/acbacb77/poc-almagentic-app) | API FastAPI, specs y harness del agente | El agente (`almagentic-agent[bot]`) vía PR revisado |
| [poc-almagentic-core](https://github.com/acbacb77/poc-almagentic-core) | Workflows reutilizables, estándares de agentes y esta bitácora | Solo humanos |
| [poc-almagentic-gitops](https://github.com/acbacb77/poc-almagentic-gitops) | Estado deseado del cluster (Argo CD) | Bot promotor abre PRs, humano aprueba |

### Identidades no humanas

| Identidad | Tipo | Instalada en | Permisos | Para qué |
|---|---|---|---|---|
| `almagentic-agent` (App ID 5179760) | GitHub App | solo app | Contents, Pull requests, Issues: RW. **Sin Workflows** | Agente de código (Claude Code en el devcontainer) |
| `almagentic-promoter-gitops` (App ID 5179780) | GitHub App | solo gitops | Contents, Pull requests: RW | Abrir PRs de promoción (tarea 10) |
| `github-actions[bot]` | Token del workflow | app | Según cada job | Triage (lectura / escritura separadas) |

### Secretos y claves

| Secreto | Tarea | Dónde vive | Quién lo crea | Para qué |
|---|---|---|---|---|
| Clave de `almagentic-agent` | 2 (crear) · 3 (usar) | `%USERPROFILE%\.config\almagentic\agent\agent.pem` (o `~/.config/almagentic/agent/agent.pem` si el repo está dentro de WSL). **Nunca en un repo** | 👤 | Firmar el token de 1 hora del agente |
| Clave de `almagentic-promoter-gitops` | 2 (crear) · 10 (usar) | En el equipo, **fuera** de la carpeta `agent/`. En GitHub: app → Settings → Environments → **gitops-staging** → `PROMOTER_APP_PRIVATE_KEY` (solo rama `main`; nunca como secreto del repositorio) | 👤 | Token de una hora del promotor para abrir PRs en gitops |
| `CLAUDE_CODE_OAUTH_TOKEN` | A | app → Settings → Secrets and variables → **Actions** | 👤 (`claude setup-token`) | Que el triage, el revisor y el agente en Actions usen la suscripción de Claude. Caduca al año |
| `AGENT_APP_PRIVATE_KEY` | 8 · F | app → Settings → Secrets and variables → **Actions** (contenido completo del `.pem` del agente) | 👤 | Que el job `publish` de la respuesta a `@claude` pida el token de 1 hora de `almagentic-agent` |

### Versiones de core

| Etiqueta | Apunta a | Creada por | Notas |
|---|---|---|---|
| `v1` | `8a472a2` (core#25) | ⚙️ workflow `release` | Etiqueta móvil que usan app y gitops. **Desde la tarea B se mueve sola** en cada merge publicable |
| `v1.8.0` | `8a472a2` (core#25) | ⚙️ | Versiones automáticas de core y versiones de app a demanda |
| `v1.7.2` | `8f0ad27` (core#23) | 👤 (la última a mano) | Clave del promotor pasada explícitamente |
| `v1.7.1` | `1264008` (core#22) | 👤 | Comprobación de la clave del promotor |
| `v1.7.0` | `dc1165e` (core#21) | 👤 | Promoción a gitops y check de imágenes |
| `v1.6.0` | `89832cf` (core#19) | 👤 | Commits del agente verificados |
| `v1.5.1` | `3d44a36` (core#18) | 👤 | Arreglo de permisos de la publicación |
| `v1.5.0` | `25d79a9` (core#17) | 👤 | Cadena de suministro de la imagen |
| `v1.4.0` | `60dd1cc` (core#14) | 👤 | Agente autónomo de features (extensión F) |
| `v1.3.0` | `34d18ef` (core#12) | 👤 | Agente revisor y respuesta a `@claude` |
| `v1.2.0` | `e6076fa` (core#10) | 👤 | Escaneo de seguridad |
| `v1.1.0` | `d66db38` (core#8) | 👤 | CI reutilizable |

---

## Estado de las tareas

Las tareas con letra son **extensiones ALM**: se añadieron al plan original y se ejecutan entre dos tareas principales.

| # | Tarea | Tipo | Estado |
|---|---|---|---|
| **1** | Definir alcance y stack | Principal | ✅ Hecha |
| **2** | Crear repos y entorno aislado | Principal | ✅ Hecha |
| **3** | Harness del agente | Principal | ✅ Hecha |
| ↳ A | Entrada de demanda con agente de triage | Extensión ALM (entre 3 y 4) | ✅ Hecha |
| **4** | Spec de la feature con Spec Kit | Principal | ✅ Hecha |
| **5** | Implementación por el agente + tests | Principal | ✅ Hecha |
| **6** | CI: build, tests y lint | Principal | ✅ Hecha |
| **7** | Scan de seguridad | Principal | ✅ Hecha |
| **8** | Agente revisor y respuesta a @claude | Principal | ✅ Hecha |
| ↳ F | Agente autónomo en Actions | Extensión ALM (entre 8 y 9) | ✅ Hecha |
| **9** | Supply chain | Principal | ✅ Hecha |
| **10** | Deploy GitOps con gate humano | Principal | ✅ Hecha |
| ↳ B | Gestión de releases | Extensión ALM (entre 10 y 11) | ✅ Hecha |
| **11** | Cerrar el loop de operación | Principal | ✅ Hecha |
| ↳ C | Mantenimiento continuo | Extensión ALM (entre 11 y 12) | ⏭️ Siguiente |
| ↳ D | Retirada de un endpoint v1 | Extensión ALM (entre 11 y 12) | Pendiente |
| ↳ E | Informe de trazabilidad | Extensión ALM (entre 11 y 12) | Pendiente |
| **12** | Guion y ensayo de la demo | Principal | Pendiente |

---

## Tarea 1 · Definir alcance y stack ✅

GitHub + Actions con 3 repos públicos, Claude Code, FastAPI y Kubernetes local con Argo CD.

### Prerrequisitos manuales

- Ninguno nuevo.

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 1.1 | Decidir plataforma de código y CI: GitHub + Actions | Usuario 👤 | ✅ |  |
| 1.2 | Decidir el agente: Claude Code | Usuario 👤 | ✅ |  |
| 1.3 | Decidir la app: API REST en Python/FastAPI | Usuario 👤 | ✅ |  |
| 1.4 | Decidir staging: Kubernetes de Docker Desktop + Argo CD | Usuario 👤 | ✅ |  |
| 1.5 | Decidir la separación en 3 repos: app, core y gitops | Usuario 👤 | ✅ |  |

### Detalle

**Decisiones**

| Decisión | Elección | Motivo |
|---|---|---|
| Código y CI | GitHub + Actions, 3 repos públicos | Gratis en GitHub Free; en privado, aprobaciones de despliegue y atestaciones exigen planes de pago |
| Agente | Claude Code (plan Claude Pro o superior) | Alternativa gratuita valorada: Gemini CLI |
| App | API REST en Python/FastAPI | Pequeña y fácil de enseñar |
| Staging | Kubernetes de Docker Desktop + Argo CD (GitOps pull) | Persistente, sin coste cloud; Argo CD lee el repo, GitHub nunca entra en el portátil |
| Gate de despliegue | Merge aprobado por un humano en gitops | |
| Separación | 3 repos: app / core / gitops | El agente no puede tocar el pipeline que lo vigila ni la infraestructura |

---

## Tarea 2 · Crear repos y entorno aislado ✅

Repos, protección de main, identidades de los bots y base de Argo CD.

### Prerrequisitos manuales

- ✅ Cuenta de GitHub
- ✅ Suscripción de Claude (Pro o superior)

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 2.1 | Crear los 3 repos públicos | Usuario 👤 | ✅ |  |
| 2.2 | Vincular GitHub con Claude (claude.ai → Settings → Connectors) | Usuario 👤 | ✅ |  |
| 2.3 | Estructura base y bootstrap de Argo CD en los 3 repos | Claude 🤖 | ✅ |  |
| 2.4 | Ruleset de main en los 3 repos (core sin Code Owners) | Usuario 👤 | ✅ |  |
| 2.5 | Verificar los rulesets | Claude 🤖 | ✅ |  |
| 2.6 | Crear e instalar la GitHub App almagentic-agent (solo app) | Usuario 👤 | ✅ |  |
| 2.7 | Crear e instalar la GitHub App almagentic-promoter-gitops (solo gitops) | Usuario 👤 | ✅ |  |
| 2.8 | Guardar la clave del promotor fuera de la carpeta agent/ | Usuario 👤 | ⬜ |  |

### Detalle

**Cómo configurar el ruleset `main`** (Settings → Rules → Rulesets → New branch ruleset)
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

---

## Tarea 3 · Harness del agente ✅

7 capas de control: contexto, constitución, permisos, hook, sandbox, identidad y plataforma.

### Prerrequisitos manuales

- ✅ VS Code con la extensión Dev Containers
- ✅ Docker Desktop con WSL integration para Ubuntu
- ✅ Clave del agente en %USERPROFILE%\.config\almagentic\agent\agent.pem

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 3.1 | agent-standards v1.0.0 en core | Claude 🤖 | ✅ | [core#1](https://github.com/acbacb77/poc-almagentic-core/pull/1) |
| 3.2 | Harness aplicado en app | Claude 🤖 | ✅ | [app#1](https://github.com/acbacb77/poc-almagentic-app/pull/1) |
| 3.3 | Fusionar core#1 y app#1 (con bypass) | Usuario 👤 | ✅ |  |
| 3.4 | Arreglos para Windows: saltos de línea LF y aviso de clave | Claude 🤖 | ✅ | [core#2](https://github.com/acbacb77/poc-almagentic-core/pull/2) · [app#2](https://github.com/acbacb77/poc-almagentic-app/pull/2) |
| 3.5 | Montar la carpeta de la clave en vez del fichero | Claude 🤖 | ✅ | [core#3](https://github.com/acbacb77/poc-almagentic-core/pull/3) · [app#3](https://github.com/acbacb77/poc-almagentic-app/pull/3) |
| 3.6 | Fusionar core#2, core#3, app#2 y app#3 | Usuario 👤 | ✅ |  |
| 3.7 | Abrir el repo en el devcontainer (Rebuild Container) | Usuario 👤 | ✅ |  |
| 3.8 | Arrancar el agente con start-agent.sh e iniciar sesión en Claude | Usuario 👤 | ✅ |  |
| 3.9 | Probar los bloqueos del harness | Usuario 👤 | ✅ |  |

### Detalle

**Cómo abrir el devcontainer y arrancar el agente**
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

---

> ## ↳ Tarea A · Entrada de demanda con agente de triage ✅
>
> **Extensión ALM** · se ejecuta entre la tarea 3 y la 4.
>
> Plantilla de petición; Claude sin herramientas propone y un script valida y aplica. Decide un humano con la etiqueta aprobado.
>
> ### Prerrequisitos manuales
>
> - ✅ Token de CI generado con claude setup-token y validado
> - ✅ Secreto CLAUDE_CODE_OAUTH_TOKEN en Actions de app (no en Agents)
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | A.1 | Workflow de triage en core | Claude 🤖 | ✅ | [core#4](https://github.com/acbacb77/poc-almagentic-core/pull/4) |
> | A.2 | Plantilla de petición y workflow en app | Claude 🤖 | ✅ | [app#4](https://github.com/acbacb77/poc-almagentic-app/pull/4) |
> | A.3 | Crear las 18 etiquetas de triage | Claude 🤖 | ✅ |  |
> | A.4 | Fusionar core#4 y app#4 | Usuario 👤 | ✅ |  |
> | A.5 | Publicar la release v1 en core | Usuario 👤 | ✅ |  |
> | A.6 | Probar con una petición normal y una inyección | Usuario 👤 | ✅ | [#5 Catálogo](https://github.com/acbacb77/poc-almagentic-app/issues/5) · [#6 Inyección](https://github.com/acbacb77/poc-almagentic-app/issues/6) |
> | A.7 | Mostrar en el comentario el motivo cuando el modelo falla | Claude 🤖 | ⬜ |  |
>
> ### Detalle
>
> **Cómo generar y guardar el token**
> 1. `claude setup-token`, con el terminal amplio para que el token no se parta.
> 2. Validarlo: `read -rs TOKEN; CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" claude -p "Responde solo: OK"`.
> 3. app → Settings → Secrets and variables → **Actions** → `CLAUDE_CODE_OAUTH_TOKEN`. Después, `unset TOKEN`.
>
> **Cómo publicar la release `v1`**: core → Releases → Draft a new release → Choose a tag `v1` → Create new tag on publish → Target `main` → Publish.
>
> **Cómo funciona el triage**
> 1. Alguien abre un issue con la plantilla **Petición** → etiqueta `triage:pendiente`.
> 2. ⚙️ `analyze`: Claude lee la petición **sin herramientas ni permiso de escritura** y devuelve JSON.
> 3. ⚙️ `apply`: un script valida el JSON contra listas cerradas, comprueba que los issues citados existen, neutraliza menciones y HTML, y pone etiquetas y comentario.
> 4. 👤 Un responsable decide: añade `aprobado`, cambia etiquetas o pide más información. `triage:repetir` vuelve a lanzarlo.
> 5. Peticiones de personas sin acceso al repo: `triage:manual`, sin pasar por el modelo.
>
> **Pruebas realizadas**
>
> | Issue | Qué probaba | Resultado |
> |---|---|---|
> | [#5 Catálogo de productos](https://github.com/acbacb77/poc-almagentic-app/issues/5) | Petición normal | ✅ `funcionalidad` · `media` · `M`, 4 criterios, 5 preguntas abiertas, riesgos (incluido el versionado de la API) |
> | [#6 Mensajes de error + inyección](https://github.com/acbacb77/poc-almagentic-app/issues/6) | Prompt injection | ✅ `triage:sospechoso`, prioridad baja (no alta), sin `aprobado`, mención neutralizada |

---

## Tarea 4 · Spec de la feature con Spec Kit ✅

El agente escribe la spec del catálogo de productos con /speckit-specify a partir del issue aprobado; un humano la revisa y la aprueba en un PR propio.

### Prerrequisitos manuales

- ✅ Preguntas abiertas del #5 respondidas en un comentario (rutas bajo /api/v1)
- ✅ Etiqueta aprobado en el #5
- ✅ Devcontainer reconstruido tras app#8 (sandbox operativo)

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 4.1 | Añadir Spec Kit v1.1.0 al repo (skills, plantillas y permisos) | Claude 🤖 | ✅ | [app#7](https://github.com/acbacb77/poc-almagentic-app/pull/7) |
| 4.2 | Fusionar app#7 | Usuario 👤 | ✅ |  |
| 4.3 | Arreglar el sandbox del devcontainer (seccomp y user namespaces) | Claude 🤖 | ✅ | [app#8](https://github.com/acbacb77/poc-almagentic-app/pull/8) |
| 4.4 | Fusionar app#8 y reconstruir el contenedor | Usuario 👤 | ✅ |  |
| 4.5 | Generar specs/001-catalogo-productos con /speckit-specify | Agente (bot) | ✅ | [app#9](https://github.com/acbacb77/poc-almagentic-app/pull/9) |
| 4.6 | Revisar, aprobar y fusionar el PR de la spec | Usuario 👤 | ✅ |  |

### Detalle

**Decisiones**: rutas bajo `/api/v1` (convención de `AGENTS.md`); el criterio "precio al momento" pasa a "tras el despliegue"; el esqueleto de la aplicación lo crea el PR de la tarea 5. Spec Kit se instala desde la etiqueta v1.1.0 de GitHub (PyPI va por detrás) y sus ficheros se versionan en el repo.

**Incidencia**: el sandbox de Claude Code no arrancaba en el devcontainer (`bwrap: No permissions to create a new namespace`). Con `failIfUnavailable` el agente se quedó sin shell y no buscó rodeos. Solución: `--security-opt seccomp=unconfined` en `runArgs` (app#8). Comprobación: `bwrap --ro-bind / / --dev /dev --unshare-user --unshare-net true && echo "sandbox OK"`.

---

## Tarea 5 · Implementación por el agente + tests ✅

El agente genera plan y tareas con Spec Kit, crea el esqueleto de la aplicación e implementa el catálogo con 55 tests; un humano lo prueba, lo aprueba y lo fusiona.

### Prerrequisitos manuales

- ✅ Spec fusionada (app#9) y devcontainer actualizado con git pull

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 5.1 | Lanzar el agente sobre la spec aprobada (rama feat/5-catalogo-productos) | Usuario 👤 | ✅ |  |
| 5.2 | Generar plan y tareas con /speckit-plan y /speckit-tasks | Agente (bot) | ✅ |  |
| 5.3 | Crear el esqueleto (pyproject, src/app/main.py con /health, tests) | Agente (bot) | ✅ |  |
| 5.4 | Implementar las tareas con sus tests (/speckit-implement) | Agente (bot) | ✅ |  |
| 5.5 | Abrir el PR como almagentic-agent[bot] con Closes #5 | Agente (bot) | ✅ | [app#10](https://github.com/acbacb77/poc-almagentic-app/pull/10) |
| 5.6 | Probar la API a mano y revisar las decisiones del agente | Claude 🤖 | ✅ |  |
| 5.7 | Aprobar y fusionar el PR (cierra el #5) | Usuario 👤 | ✅ |  |

### Detalle

**Decisiones del agente aprobadas**: precio serializado como texto (`"4.95"`) para garantizar 2 decimales; identificador como slug; `GET /metrics` público hasta la tarea 10; rutas con barras reciben el 404 genérico de FastAPI.

**Pendientes derivados**: `httpx2` (bloqueado por permisos, va a la tarea C); `guard.py` no pasa ruff (arreglar en core); licencias sin contrastar (tarea 7); cabecera `Cache-Control: no-store` opcional (primera prueba de `@claude` en la tarea 8).

**Problema típico**: `start-agent.sh: AGENT_APP_ID: Define AGENT_APP_ID` significa que la terminal no está dentro del contenedor. Reabrir con *Dev Containers: Reopen in Container* y comprobar con `echo "$AGENT_APP_ID"`.

---

## Tarea 6 · CI: build, tests y lint ✅

Workflow reutilizable en core que valida cada PR de app en una máquina limpia (uv.lock exacto, pytest, ruff y mypy). Es un check obligatorio para fusionar en main.

### Prerrequisitos manuales

- ✅ Login de git con 2FA en WSL (gh auth login + gh auth setup-git) o mover etiquetas desde la web

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 6.1 | Workflow reutilizable de CI en core y CI propio de core (57 tests) | Claude 🤖 | ✅ | [core#8](https://github.com/acbacb77/poc-almagentic-core/pull/8) |
| 6.2 | Llamada al CI desde app (ci / checks) | Claude 🤖 | ✅ | [app#11](https://github.com/acbacb77/poc-almagentic-app/pull/11) |
| 6.3 | Fusionar core#8 y mover la etiqueta v1 de core (y crear v1.1.0) | Usuario 👤 | ✅ |  |
| 6.4 | Fusionar app#11 | Usuario 👤 | ✅ |  |
| 6.5 | Marcar ci / checks como obligatorio en el ruleset de main de app | Usuario 👤 | ✅ |  |
| 6.6 | Probar que un PR con el CI en rojo queda bloqueado | Claude 🤖 | ✅ | [app#12](https://github.com/acbacb77/poc-almagentic-app/pull/12) |
| 6.7 | Borrar la rama test/ci-rojo de app (botón Delete branch en app#12) | Usuario 👤 | ✅ |  |

### Detalle

**Cómo mover la etiqueta v1 de core** (repo `poc-almagentic-core`). Desde la web: *Releases* → borrar la release `v1` → *Tags* → borrar `v1` → *Draft a new release* con la etiqueta nueva `v1` y destino `main`. Desde WSL, en un clon de core y con `gh auth login` + `gh auth setup-git` hechos: `git fetch origin --tags && git tag -f v1 origin/main && git push -f origin v1`.

**Check obligatorio** (repo `poc-almagentic-app`): *Settings → Rules → Rulesets* → ruleset de `main` → *Require status checks to pass* → *Add checks* → `ci / checks`.

**Problema típico**: una ejecución que falla porque el workflow reutilizable no existe en la etiqueta no se puede relanzar con *Re-run*; hay que hacer un push nuevo a la rama del PR (por ejemplo, un commit vacío).

---

## Tarea 7 · Scan de seguridad ✅

Workflow reutilizable en core con cuatro escaneos (bandit, pip-audit y licencias, gitleaks y cambios del agente en lo que lo gobierna) y un check resumen obligatorio.

### Prerrequisitos manuales

- Ninguno nuevo.

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 7.1 | Workflow reutilizable de seguridad en core (security / result) | Claude 🤖 | ✅ | [core#10](https://github.com/acbacb77/poc-almagentic-core/pull/10) |
| 7.2 | Detectar ficheros generados y cambios del agente en .github/, .claude/, .specify/ y la configuración de pyproject | Claude 🤖 | ✅ | [core#10](https://github.com/acbacb77/poc-almagentic-core/pull/10) |
| 7.3 | Llamada al escaneo desde app | Claude 🤖 | ✅ | [app#13](https://github.com/acbacb77/poc-almagentic-app/pull/13) |
| 7.4 | Fusionar core#10, mover v1 de core, fusionar app#13 | Usuario 👤 | ✅ |  |
| 7.5 | Marcar security / result como obligatorio en el ruleset de main de app | Usuario 👤 | ✅ |  |
| 7.6 | Probar que un PR con un .pyc queda bloqueado | Claude 🤖 | ✅ | [app#14](https://github.com/acbacb77/poc-almagentic-app/pull/14) |
| 7.7 | Borrar las ramas de prueba de app (Delete branch en app#12 y app#14) | Usuario 👤 | ✅ |  |

### Detalle

**Escaneos** (repo `poc-almagentic-core`, `reusable-security.yml`): `sast` (bandit 1.9.4, ignora `# nosec`), `dependencies` (pip-audit 2.10.1 y licencias permitidas con pip-licenses 5.5.5), `secrets` (gitleaks 8.30.1 con checksum verificado), `governance` (`scripts/security/check_pr_files.py`, 21 tests) y `result`, que es el check obligatorio.

**Bandit y no Semgrep**: las reglas de Semgrep se descargan en cada ejecución; las de bandit van en la versión fijada y el resultado es reproducible.

**Hallazgo**: `governance` habría marcado app#10, donde el agente creó `[tool.ruff]` excluyendo `.claude/` y `.specify/`. Desde ahora ese cambio lo hace una persona.

---

## Tarea 8 · Agente revisor y respuesta a @claude ✅

Un revisor sin herramientas comenta cada PR contra la spec, y un comentario @claude de un colaborador lanza al agente de código en Actions, que sube su cambio al PR como almagentic-agent[bot].

### Prerrequisitos manuales

- ✅ Secreto AGENT_APP_PRIVATE_KEY (clave de almagentic-agent) en Actions de app
- ✅ CLAUDE_CODE_OAUTH_TOKEN en Actions de app (ya existía, de la extensión A)

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 8.1 | Workflows reutilizables en core: revisión (pensar/actuar) y respuesta a @claude (parche validado y subido por un script) | Claude 🤖 | ✅ | [core#12](https://github.com/acbacb77/poc-almagentic-core/pull/12) |
| 8.2 | Scripts de prompt, validación y publicación con 16 tests | Claude 🤖 | ✅ | [core#12](https://github.com/acbacb77/poc-almagentic-core/pull/12) |
| 8.3 | Llamadas desde app: agent-review y agent-respond | Claude 🤖 | ✅ | [app#15](https://github.com/acbacb77/poc-almagentic-app/pull/15) |
| 8.4 | Fusionar core#12, mover v1 de core (y crear v1.3.0), fusionar app#15 | Usuario 👤 | ✅ |  |
| 8.5 | PR de prueba con un test que falla (Cache-Control: no-store, FR-009) | Claude 🤖 | ✅ | [app#16](https://github.com/acbacb77/poc-almagentic-app/pull/16) |
| 8.6 | Comentar @claude en el PR de prueba | Usuario 👤 | ✅ | [app#16](https://github.com/acbacb77/poc-almagentic-app/pull/16) |
| 8.7 | Comprobar commit del bot, checks en verde, revisión y que el bot no se dispara a sí mismo | Claude 🤖 | ✅ | [app#16](https://github.com/acbacb77/poc-almagentic-app/pull/16) |
| 8.8 | Fusionar app#16 | Usuario 👤 | ✅ |  |

### Detalle

**Dos workflows** (repo `poc-almagentic-core`). `reusable-agent-review.yml`: el job `analyze` ejecuta Claude sin herramientas (`--tools ""`) desde una carpeta vacía y con salida JSON validada por esquema; el job `publish` (sin modelo) publica la revisión con `github.token` como comentario, nunca como aprobación. `reusable-agent-respond.yml`: el job `work` ejecuta Claude Code en la copia de app con el harness y el sandbox, sin token de GitHub, y empaqueta el cambio como parche; el job `publish` aplica el parche, pasa `check_pr_files.py`, hace el commit como `almagentic-agent[bot]` con un token de una hora y lo sube a la rama del PR.

**Quién puede disparar**: la revisión, PRs del mismo repo, no borrador, de colaboradores o del bot. La respuesta, comentarios con `@claude` de OWNER, MEMBER o COLLABORATOR; nunca PRs de forks ni ramas `main`.

**Prueba** (app#16): un test exigía `Cache-Control: no-store`. El comentario `@claude haz que pasen los tests de test_cache.py` produjo en ~75 s un commit del bot con un middleware y el ajuste de un test antiguo que contradecía FR-009; CI, seguridad y revisor pasaron, y el comentario del propio bot no volvió a lanzar al agente.

**Problema típico**: si `@claude` no hace nada, comprueba que `agent-respond.yml` ya está en `main` de app (el evento `issue_comment` solo lee los workflows de la rama por defecto).

---

> ## ↳ Tarea F · Agente autónomo en Actions ✅
>
> **Extensión ALM** · se ejecuta entre la tarea 8 y la 9.
>
> La etiqueta aprobado lanza al agente en Actions para escribir la spec, y el merge de la spec lanza el plan, las tareas y la implementación. Desaparecen los prompts manuales del devcontainer; las aprobaciones humanas no cambian.
>
> ### Prerrequisitos manuales
>
> - ✅ Clave de almagentic-agent como secreto de Actions en app (la misma de la tarea 8)
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | F.1 | Workflow reutilizable del agente en core: etiqueta aprobado → PR de la spec | Claude 🤖 | ✅ | [core#14](https://github.com/acbacb77/poc-almagentic-core/pull/14) |
> | F.2 | Disparador al fusionar una spec → PR de implementación con Closes #issue | Claude 🤖 | ✅ | [core#14](https://github.com/acbacb77/poc-almagentic-core/pull/14) · [app#17](https://github.com/acbacb77/poc-almagentic-app/pull/17) |
> | F.3 | Solo disparan usuarios con escritura; límite de turnos y de tiempo por ejecución | Claude 🤖 | ✅ | [core#14](https://github.com/acbacb77/poc-almagentic-core/pull/14) |
> | F.4 | Control de la red de salida del runner: sandbox del repo con dominios permitidos | Claude 🤖 | ✅ | [core#14](https://github.com/acbacb77/poc-almagentic-core/pull/14) |
> | F.5 | Fusionar core#14 y app#17, mover v1 (y crear v1.4.0) | Usuario 👤 | ✅ |  |
> | F.6 | Prueba real: petición #18 → spec (app#19) → implementación (app#20) | Usuario 👤 | ✅ | [#18 búsqueda por nombre](https://github.com/acbacb77/poc-almagentic-app/issues/18) · [app#19](https://github.com/acbacb77/poc-almagentic-app/pull/19) · [app#20](https://github.com/acbacb77/poc-almagentic-app/pull/20) |
> | F.7 | Título del PR sin el prefijo de la plantilla | Claude 🤖 | ✅ | [core#15](https://github.com/acbacb77/poc-almagentic-core/pull/15) |
>
> ### Detalle
>
> **Por qué**: sin esta extensión el desarrollador escribe dos prompts por feature en el devcontainer (spec e implementación). Con ella, el agente arranca con los mismos eventos en los que ya decide un humano: la etiqueta `aprobado` y el merge de la spec. El devcontainer se mantiene como modo interactivo.
>
> **Cómo** (repo `poc-almagentic-core`, `reusable-agent-feature.yml`): el job `work` comprueba permiso de escritura de quien dispara, issue abierto con `aprobado` y sin `triage:sospechoso`, y que no exista ya la rama; después ejecuta Claude Code con el harness y el sandbox del repo (red limitada a GitHub y PyPI), 40 o 150 turnos y 60 minutos, sin token de GitHub. El job `publish` decide la rama, rechaza en la fase spec todo lo que no esté en `specs/`, pasa `check_pr_files.py`, sube la rama, abre el PR como `almagentic-agent[bot]` y lo anuncia en el issue.
>
> **Prueba** (petición #18, búsqueda por nombre): 2 min de etiqueta a PR de spec (app#19); un `@claude` resolvió las dos dudas; 2 min de merge a PR de implementación (app#20, 103 tests); un segundo `@claude` corrigió la fuga del texto de `q` en el log de acceso que encontró el revisor. 25 minutos de issue a cierre, con cuatro decisiones humanas.

---

## Tarea 9 · Supply chain ✅

Imagen de la API probada, con SBOM, firmada con cosign y con atestaciones de procedencia SLSA y de SBOM verificadas contra el workflow de core. Los commits del agente salen verificados.

### Prerrequisitos manuales

- ✅ Paquete poc-almagentic-app público en GHCR

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 9.1 | Workflow reutilizable: bases por digest, build, prueba de humo y SBOM; en main, GHCR, cosign y atestaciones | Claude 🤖 | ✅ | [core#17](https://github.com/acbacb77/poc-almagentic-core/pull/17) |
| 9.2 | Dockerfile multietapa sin root y .dockerignore; el agente no puede tocarlos | Claude 🤖 | ✅ | [app#21](https://github.com/acbacb77/poc-almagentic-app/pull/21) |
| 9.3 | Fijar las imágenes base con los digests que dio el CI | Claude 🤖 | ✅ | [app#21](https://github.com/acbacb77/poc-almagentic-app/pull/21) |
| 9.4 | Arreglo: publish heredaba permissions: {} y no podía subir a GHCR | Claude 🤖 | ✅ | [core#18](https://github.com/acbacb77/poc-almagentic-core/pull/18) |
| 9.5 | Commits del agente por la API de GitHub (Verified) | Claude 🤖 | ✅ | [core#19](https://github.com/acbacb77/poc-almagentic-core/pull/19) · [app#22](https://github.com/acbacb77/poc-almagentic-app/pull/22) |
| 9.6 | Fusionar, mover v1 (v1.5.0, v1.5.1, v1.6.0) y relanzar la publicación | Usuario 👤 | ✅ |  |

### Detalle

**Imagen publicada**: `ghcr.io/acbacb77/poc-almagentic-app@sha256:02e89f6f…` (etiquetas `sha-<commit>` y `main`). Certificado de firma de Sigstore válido 10 minutos con identidad `…/poc-almagentic-core/.github/workflows/reusable-supply-chain.yml@refs/tags/v1`; entrada 3226607006 en Rekor.

**Verificar desde WSL**: `gh attestation verify oci://ghcr.io/acbacb77/poc-almagentic-app:main --owner acbacb77 --signer-workflow acbacb77/poc-almagentic-core/.github/workflows/reusable-supply-chain.yml`.

**Problemas típicos**: si `image / build` falla en «Imágenes base fijadas por digest», la anotación trae el digest que hay que poner en el `Dockerfile`. Un job de un workflow reutilizable sin `permissions` hereda el bloque del workflow, no el de quien llama.

---

## Tarea 10 · Deploy GitOps con gate humano ✅

Cada imagen firmada de main la verifica el bot promotor, que abre un PR en gitops con su digest y los commits que entran. Fusionar ese PR aprueba el despliegue y Argo CD sincroniza staging. Un check obligatorio impide desplegar imágenes no firmadas por core.

### Prerrequisitos manuales

- ✅ Kubernetes activado en Docker Desktop con 8 GB
- ✅ Argo CD v3.5.4 instalado y bootstrap/root-app.yaml aplicado
- ✅ Entorno gitops-staging en app (solo main) con PROMOTER_APP_PRIVATE_KEY
- ✅ verify / images obligatorio en el ruleset de main de gitops

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 10.1 | Promotor y check de imágenes en core (verificación de procedencia desde main, SBOM y firma) | Claude 🤖 | ✅ | [core#21](https://github.com/acbacb77/poc-almagentic-core/pull/21) |
| 10.2 | Manifiestos de la API por digest, aplicación de Argo CD y check en gitops | Claude 🤖 | ✅ | [gitops#1](https://github.com/acbacb77/poc-almagentic-gitops/pull/1) |
| 10.3 | Service como LoadBalancer en el puerto 8000 | Claude 🤖 | ✅ | [gitops#2](https://github.com/acbacb77/poc-almagentic-gitops/pull/2) |
| 10.4 | Job promote en app | Claude 🤖 | ✅ | [app#23](https://github.com/acbacb77/poc-almagentic-app/pull/23) |
| 10.5 | Arreglos: secreto del entorno pasado explícitamente y relanzar a mano | Claude 🤖 | ✅ | [core#22](https://github.com/acbacb77/poc-almagentic-core/pull/22) · [core#23](https://github.com/acbacb77/poc-almagentic-core/pull/23) · [app#24](https://github.com/acbacb77/poc-almagentic-app/pull/24) |
| 10.6 | Desbloqueo: certifi con vulnerabilidad nueva | Claude 🤖 | ✅ | [app#25](https://github.com/acbacb77/poc-almagentic-app/pull/25) |
| 10.7 | Aprobar el primer PR de promoción | Usuario 👤 | ✅ | [gitops#3](https://github.com/acbacb77/poc-almagentic-gitops/pull/3) |
| 10.8 | Argo CD sincroniza staging | Automático ⚙️ | ✅ |  |
| 10.9 | Prueba: imagen sin firma de core bloqueada | Claude 🤖 | ✅ | [gitops#4](https://github.com/acbacb77/poc-almagentic-gitops/pull/4) |

### Detalle

**Cómo preparar el cluster**: pasos en el [README de gitops](https://github.com/acbacb77/poc-almagentic-gitops#puesta-en-marcha-una-sola-vez). La API queda en `localhost:8000` (o `host.docker.internal:8000`).

**Flujo**: merge en app → imagen firmada → el promotor verifica procedencia desde main, SBOM y firma → PR en gitops con el digest y los commits → `verify / images` → **tu aprobación y merge** → Argo CD sincroniza staging. Para volver atrás, revertir el PR de promoción. Para relanzar: Actions → supply-chain → Run workflow (un *Re-run* repite la versión antigua de core).

**Problemas típicos**: sin `root-app.yaml` aplicado Argo CD no ve nada. La clave del promotor vive solo en el entorno `gitops-staging` y app tiene que pasarla explícitamente al workflow de core. «A JSON web token could not be decoded» = clave mal pegada.

---

> ## ↳ Tarea B · Gestión de releases ✅
>
> **Extensión ALM** · se ejecuta entre la tarea 10 y la 11.
>
> core se versiona solo en cada merge publicable (vX.Y.Z y mueve v1). La app publica versiones a demanda: semver por Conventional Commits, notas con los cambios del agente y la imagen firmada de main etiquetada sin reconstruir.
>
> ### Prerrequisitos manuales
>
> - Ninguno nuevo.
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | B.1 | Cálculo de versión y notas (release.py, 19 tests) | Claude 🤖 | ✅ | [core#25](https://github.com/acbacb77/poc-almagentic-core/pull/25) |
> | B.2 | Versiones de core automáticas: vX.Y.Z y mover v1 | Claude 🤖 | ✅ | [core#25](https://github.com/acbacb77/poc-almagentic-core/pull/25) |
> | B.3 | Versiones de la app con Run workflow, sin reconstruir la imagen | Claude 🤖 | ✅ | [core#25](https://github.com/acbacb77/poc-almagentic-core/pull/25) · [app#26](https://github.com/acbacb77/poc-almagentic-app/pull/26) |
> | B.4 | create-github-app-token: app-id → client-id | Claude 🤖 | ✅ | [core#25](https://github.com/acbacb77/poc-almagentic-core/pull/25) |
> | B.5 | Primera versión de la app: v1.0.0 | Usuario 👤 | ✅ |  |
> | B.6 | Desplegar v1.0.0 en staging | Usuario 👤 | ✅ | [gitops#6](https://github.com/acbacb77/poc-almagentic-gitops/pull/6) |
>
> ### Detalle
>
> **Versiones de core**: automáticas en cada merge a main con `feat`, `fix`, `ci`… (workflow `release` de core). Crea `vX.Y.Z` con su Release y mueve `v1`; un cambio incompatible crea `v2`. **Ya no se mueven etiquetas a mano.**
>
> **Versiones de la app** (repo `poc-almagentic-app`): *Actions → release → Run workflow* sobre `main`, después de que `supply-chain` termine para ese commit. Si falla con «Nada que publicar», desde la última versión solo hubo documentación o pruebas; con «Imagen no publicada», espera a `supply-chain`.
>
> **Primera versión**: `v1.0.0` = `ghcr.io/acbacb77/poc-almagentic-app@sha256:8ace64ae…` (commit `3898e7c`), desplegada con gitops#6.

---

## Tarea 11 · Cerrar el loop de operación ✅

Prometheus vigila la API en staging. Una alerta llega por Alertmanager a un puente que abre un issue en app con el formato de petición; sigue el camino normal (triage, decisión humana, agente, revisión, promoción). Grafana muestra la API y la actividad de los agentes, leída de la API de GitHub.

### Prerrequisitos manuales

- ✅ Token personal de grano fino (solo app: Issues escritura, Actions lectura) como Secret observabilidad-github
- ✅ Secret grafana-admin con la contraseña de Grafana

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 11.1 | /metrics en un puerto propio (9000) que el LoadBalancer no publica | Claude 🤖 | ✅ | [app#27](https://github.com/acbacb77/poc-almagentic-app/pull/27) |
| 11.2 | Prometheus, Alertmanager y Grafana; reglas BusquedasRechazadas y ApiSinRespuesta; puente alerta → issue; exportador de telemetría de los agentes; paneles | Claude 🤖 | ✅ | [gitops#7](https://github.com/acbacb77/poc-almagentic-gitops/pull/7) |
| 11.3 | Desplegar la imagen con métricas | Usuario 👤 | ✅ | [gitops#8](https://github.com/acbacb77/poc-almagentic-gitops/pull/8) |
| 11.4 | Alerta no prevista ApiSinRespuesta por el orden de despliegue: cerrada con la causa | Usuario 👤 | ✅ | [#28 ApiSinRespuesta](https://github.com/acbacb77/poc-almagentic-app/issues/28) |
| 11.5 | Provocar BusquedasRechazadas: el puente abre el issue y el triage lo clasifica | Usuario 👤 | ✅ | [#29 BusquedasRechazadas](https://github.com/acbacb77/poc-almagentic-app/issues/29) |
| 11.6 | Decisión: subir el máximo de q a 200 y añadir aprobado | Usuario 👤 | ✅ | [#29 BusquedasRechazadas](https://github.com/acbacb77/poc-almagentic-app/issues/29) |
| 11.7 | Arreglo: la fase spec puede retocar una spec existente | Claude 🤖 | ✅ | [core#27](https://github.com/acbacb77/poc-almagentic-core/pull/27) |
| 11.8 | El agente escribe la spec 003 y la implementación; un @claude corrige un E501 | Agente (bot) | ✅ | [app#30](https://github.com/acbacb77/poc-almagentic-app/pull/30) · [app#31](https://github.com/acbacb77/poc-almagentic-app/pull/31) |
| 11.9 | Arreglo: agente en ubuntu-24.04 y comprobación del sandbox (Ubuntu 26.04 lo rompía) | Claude 🤖 | ✅ | [core#28](https://github.com/acbacb77/poc-almagentic-core/pull/28) |
| 11.10 | Promoción del arreglo a staging | Usuario 👤 | ✅ | [gitops#11](https://github.com/acbacb77/poc-almagentic-gitops/pull/11) |
| 11.11 | Grafana estable: SQLite en WAL y liveness con margen | Claude 🤖 | ✅ | [gitops#9](https://github.com/acbacb77/poc-almagentic-gitops/pull/9) |
| 11.12 | Texto de la alerta con el nuevo máximo | Claude 🤖 | ✅ | [gitops#12](https://github.com/acbacb77/poc-almagentic-gitops/pull/12) |

### Detalle

**Secretos** (en WSL, una vez, nunca en git): `observabilidad-github` con un token personal de grano fino creado en *Settings de tu cuenta → Developer settings → Fine-grained tokens* (solo `poc-almagentic-app`; Issues lectura y escritura, Actions lectura; 90 días) y `grafana-admin`. Comandos en el [README de gitops](https://github.com/acbacb77/poc-almagentic-gitops#observabilidad-tarea-11).

**Direcciones**: Grafana `localhost:3000` (paneles «API del catálogo» y «Actividad de los agentes»), Prometheus `localhost:9090`. Las métricas de la API van por el puerto 9000 del pod, que el `Service` no publica.

**Ciclo probado** (25 min de la etiqueta al cierre, con dos fallos de la plataforma resueltos por el camino): alerta `BusquedasRechazadas` → issue app#29 abierto por el puente → triage → decisión en un comentario y `aprobado` → spec 003 (app#30) → implementación (app#31) y `@claude` para un E501 → promoción gitops#11 → q de 120 caracteres devuelve 200.

**Problemas típicos**: una alerta se puede disparar por el orden de despliegue (anotaciones antes que la imagen que las sirve): se cierra el issue con la causa y sin `aprobado`. Grafana 13 con SQLite en `emptyDir` se reiniciaba por el liveness (503 en `/api/health`): WAL y más margen (gitops#9). Si el agente dice que no pudo ejecutar comandos, mira el paso «Claude Code y dependencias del sandbox»: debe decir Ubuntu 24.04 y «Sandbox (bubblewrap) operativo».

---

> ## ↳ Tarea C · Mantenimiento continuo ⏭️
>
> **Extensión ALM** · se ejecuta entre la tarea 11 y la 12.
>
> Actualización de dependencias y evals del harness al cambiar de modelo.
>
> ### Prerrequisitos manuales
>
> - Ninguno nuevo.
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | C.1 | Dependabot en app | Claude 🤖 | ⬜ |  |
> | C.2 | Evals del harness al cambiar de modelo | Claude 🤖 | ⬜ |  |

---

> ## ↳ Tarea D · Retirada de un endpoint v1 ⬜
>
> **Extensión ALM** · se ejecuta entre la tarea 11 y la 12.
>
> v2 del catálogo con importe y moneda; deprecación, migración y retirada de v1.
>
> ### Prerrequisitos manuales
>
> - Ninguno nuevo.
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | D.1 | Abrir la petición de la v2 | Usuario 👤 | ⬜ |  |
> | D.2 | Implementar /api/v2 con importe y moneda | Agente (bot) | ⬜ |  |
> | D.3 | Marcar v1 como deprecada (cabeceras Deprecation y Sunset) | Agente (bot) | ⬜ |  |
> | D.4 | Retirar v1 | Agente (bot) | ⬜ |  |
> | D.5 | Aprobar cada PR | Usuario 👤 | ⬜ |  |
>
> _Subtareas previstas: se ajustarán al llegar a la tarea._

---

> ## ↳ Tarea E · Informe de trazabilidad ⬜
>
> **Extensión ALM** · se ejecuta entre la tarea 11 y la 12.
>
> Cada release enlaza petición, spec, PR, escaneos, aprobaciones y despliegue.
>
> ### Prerrequisitos manuales
>
> - Ninguno nuevo.
>
> ### Subtareas
>
> | # | Subtarea | Quién | Estado | Enlaces |
> |---|---|---|---|---|
> | E.1 | Generador del informe por release | Claude 🤖 | ⬜ |  |
> | E.2 | Revisar el informe | Usuario 👤 | ⬜ |  |
>
> _Subtareas previstas: se ajustarán al llegar a la tarea._

---

## Tarea 12 · Guion y ensayo de la demo ⬜

Narrativa, métricas, plan B grabado y cierre de la memoria del TFM (requisito para finalizar la POC).

### Prerrequisitos manuales

- Ninguno nuevo.

### Subtareas

| # | Subtarea | Quién | Estado | Enlaces |
|---|---|---|---|---|
| 12.1 | Guion de la demo | Claude 🤖 | ⬜ |  |
| 12.2 | Ensayo y grabación del plan B | Usuario 👤 | ⬜ |  |
| 12.3 | Completar la memoria del TFM con todas las tareas | Claude 🤖 | ⬜ |  |
| 12.4 | Revisión final de la memoria (15-45 páginas) y datos de portada | Usuario 👤 | ⬜ |  |

_Subtareas previstas: se ajustarán al llegar a la tarea._

---

## Problemas encontrados y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| Un `__pycache__/*.pyc` aparece en un PR de core | Core no tenía `.gitignore` | `.gitignore` en core; la tarea 7 detectará ficheros generados en PRs |
| No puedo aprobar un PR siendo admin | GitHub no deja aprobar PRs propios | PRs del harness: bypass (queda auditado en Rules → Insights). PRs del agente: los firma el bot y se aprueban normal |
| *"You need to first save your workspace in a folder containing all its workspace folders"* | VS Code tenía un workspace con varias carpetas | File → Close Workspace y abrir solo la carpeta del repo |
| `stat /run/guest-services/distro-services/ubuntu.sock: no such file or directory` | VS Code monta el socket Wayland de WSL y Docker Desktop no tenía integración con Ubuntu | Activar WSL integration para Ubuntu, o desmarcar *Dev › Containers: Mount Wayland Socket* |
| `/run/secrets/agent.pem` es un directorio (`total 0`) | Docker Desktop en Windows monta un fichero suelto como directorio | Se monta la carpeta `agent/` (core#3, app#3) y **Rebuild Container** |
| La clave se busca en `C:\Users\…` aunque abro desde WSL | El clon está en `/mnt/c/...`: Dev Containers usa rutas y variables de Windows | Poner la clave en la ruta de Windows o mover el clon dentro de WSL (`~/code`) |
| `start-agent.sh` falla con `$'\r'` o *bad interpreter* | Saltos de línea CRLF al clonar en Windows | `.gitattributes` con `eol=lf` (app#2) y volver a clonar |
| Triage: *"la respuesta no es JSON"*, `is_error: true`, coste 0 | `401 Invalid bearer token`: token mal copiado | Regenerar con `claude setup-token`, validarlo (A.5) y actualizar el secreto |
| No encuentro los artefactos de Actions | Están en la página de resumen, no en la del job | Ejecución → **Summary** → final de la página → **Artifacts** |
| ¿Secreto en *Actions* o en *Agents*? | *Agents* es para los agentes propios de GitHub | Siempre **Actions** para workflows |
| `git push` pide contraseña y falla tras activar 2FA | GitHub no acepta la contraseña por HTTPS con 2FA | Mover etiquetas desde la web (borrar release y etiqueta, recrearlas en `main`) o `gh auth login` + `gh auth setup-git` en WSL |
| No aparece *Re-run all jobs* | La ejecución falló al arrancar porque el workflow reutilizable no estaba en la etiqueta | Push nuevo a la rama del PR (p. ej. un commit vacío) |
| `@claude` no hace nada | `agent-respond.yml` aún no estaba en `main` de app; `issue_comment` solo lee la rama por defecto | Fusionar primero app#15 |
| El agente en Actions no puede usar `uv run` | La caché de uv del runner es de solo lectura dentro del sandbox | `UV_CACHE_DIR` dentro del proyecto y excluida de git (core#14) |
| El agente ve `.bashrc`, `.idea`, `.mcp.json`… sin seguimiento | El sandbox de Claude Code protege esos ficheros de la carpeta de trabajo mientras dura la sesión | No entran en el parche; el script solo publica lo que corresponde a la fase |
| El revisor dice que un test de Unicode descompuesto usa la forma precompuesta | El revisor solo ve texto y no distingue `á` de `a` + U+0301 | Falso positivo; se comprobaron los bytes |
| `image / build` falla en «Imágenes base fijadas por digest» | El `Dockerfile` usa una etiqueta sin digest | Copiar a `FROM` el digest que trae la anotación |
| `release / publish` falla al subir a GHCR | Con `permissions: {}` a nivel de workflow, el job reutilizable sin permisos propios hereda ese bloque vacío | Quitar el bloque (core#18) y *Re-run all jobs* |
| `image / publish` y `release` aparecen omitidos en un PR | La publicación solo corre en main | Es lo esperado |
| Argo CD no muestra ninguna aplicación ni existe `staging` | No se aplicó `bootstrap/root-app.yaml` | `kubectl apply -f …/bootstrap/root-app.yaml` |
| `read: -p: no coprocess` | La terminal es zsh | `printf 'Contraseña: '; read -s P; echo` |
| `promote` falla: la clave del promotor llega vacía | Un workflow reutilizable de otro repo no ve el secreto del entorno si app no se lo pasa | Declararlo en core y pasarlo explícitamente desde app (core#23, app#24) |
| *Re-run* no recoge un arreglo de core | Repite la versión de los workflows reutilizables de la ejecución original | Actions → supply-chain → **Run workflow** (app#24) |
| «A JSON web token could not be decoded» | Clave `.pem` mal pegada (saltos de línea o `BEGIN`/`END`) | Volver a pegarla entera, o subirla con `gh secret set … < fichero.pem` |
| `security / dependencies` falla en un PR que no toca dependencias | Vulnerabilidad nueva publicada en una dependencia (certifi, PYSEC-2026-4320) | Actualizarla en `uv.lock` (app#25); en la tarea C se automatiza |
| Mismo commit, digest distinto | La imagen no es reproducible byte a byte | Cerrar la promoción redundante; las versiones ya no reconstruyen (tarea B) |
| `release` de app falla con «Nada que publicar» | Desde la última versión solo hay `docs`, `test`, `chore` o `spec` | Es lo esperado; no hay versión nueva |
| `release` de app falla con «Imagen no publicada» | `supply-chain` aún no ha terminado para ese commit de main | Esperar y relanzar |
| Se abre un issue `ApiSinRespuesta` justo al desplegar la observabilidad | gitops#7 anotó el puerto 9000 antes de que la imagen que lo sirve (app#27) estuviera en staging | Cerrar el issue con la causa y sin `aprobado` (app#28); en adelante, desplegar primero la imagen y después las anotaciones |
| El pod de Grafana se reinicia cada ~20 min (exit 137, sin OOM) | Grafana 13 con SQLite en `emptyDir`: `/api/health` devuelve 503 mientras escribe y el liveness lo mata | SQLite en WAL, `busy_timeout`, liveness con más margen y más CPU (gitops#9) |
| Grafana parado a mano vuelve a arrancar | Argo CD (`selfHeal`) restaura el estado de git | Cambiarlo por PR en gitops |
| El agente rechaza su propia spec: «se esperaba una carpeta de spec nueva y hay 2» | La decisión pedía crear la spec 003 y retocar FR-009 de la 002; el guardarraíl contaba todas las carpetas tocadas | La carpeta nueva se busca solo entre los ficheros añadidos (core#27); quitar y volver a poner `aprobado` |
| El agente no puede ejecutar comandos (`apply-seccomp: write /proc/self/setgroups`) y llega un E501 al PR | `ubuntu-latest` pasó a Ubuntu 26.04 el 19-10-2026 y allí el sandbox no arranca | Jobs del agente en `ubuntu-24.04` y comprobación de bubblewrap antes del modelo (core#28) |
| Queda abierta una promoción antigua en gitops | El promotor no cierra las promociones a las que sustituye una más nueva | Cerrarla a mano sin fusionar (gitops#10) |

---

## Límites de la sesión de trabajo de Claude

| Puede | No puede (lo haces tú) |
|---|---|
| Subir ramas, abrir PRs, crear etiquetas de issues, leer issues y comentarios | Configurar rulesets, crear tags, leer logs/artefactos/secretos de Actions, aprobar o fusionar PRs |

---

## Pendientes menores

- Triage: mostrar en el comentario el motivo cuando el modelo devuelve un error (p. ej. el 401).
- Revisor (app#15): fijar por SHA los workflows reutilizables que reciben secretos (tarea B).
- Promotor: cerrar automáticamente las promociones sustituidas por una más nueva.
- Sandbox del agente en Ubuntu 26.04 (hoy fijado a `ubuntu-24.04`) y resto de workflows al pasar `ubuntu-latest` a 26.
- Grafana: si vuelve a reiniciarse, volumen persistente o base de datos externa.
- Promocionar sin reconstruir la imagen o construcción reproducible (digests distintos para el mismo commit).
- Argo CD: valorar verificación de firmas también dentro del clúster (Kyverno o policy-controller).
