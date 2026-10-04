#!/usr/bin/env bash
# Arranca Claude Code con la identidad de la GitHub App del agente (agent-standards v1.0.0).
#
# Lo ejecuta un HUMANO, nunca el agente: lee la clave privada de la App,
# obtiene un token de instalación que caduca en 1 hora y limitado a un solo repo,
# y lanza `claude` con ese token y la identidad del bot en git.
# La clave y la configuración global de git no cambian.
#
# Variables (normalmente las define el devcontainer):
#   AGENT_APP_ID     ID de la GitHub App
#   AGENT_APP_SLUG   nombre de la App, p. ej. almagentic-agent
#   AGENT_REPO       owner/repo donde trabajará el agente
#   AGENT_KEY_FILE   ruta a la clave .pem (por defecto /run/secrets/agent/agent.pem)
set -euo pipefail

: "${AGENT_APP_ID:?Define AGENT_APP_ID}"
: "${AGENT_APP_SLUG:?Define AGENT_APP_SLUG}"
: "${AGENT_REPO:?Define AGENT_REPO (owner/repo)}"
KEY_FILE="${AGENT_KEY_FILE:-/run/secrets/agent/agent.pem}"
API="https://api.github.com"

if [[ ! -f "$KEY_FILE" || ! -r "$KEY_FILE" ]]; then
  echo "No encuentro la clave de la App en $KEY_FILE." >&2
  echo "Ponla en la carpeta .config/almagentic/agent/ de tu usuario, con el nombre agent.pem:" >&2
  echo "  - repo abierto desde Windows o desde /mnt/c en WSL: %USERPROFILE%\\.config\\almagentic\\agent\\agent.pem" >&2
  echo "  - repo dentro de WSL, Linux o macOS:                ~/.config/almagentic/agent/agent.pem" >&2
  echo "La carpeta se monta en vivo: no hace falta reconstruir el contenedor." >&2
  exit 1
fi
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Aviso: ANTHROPIC_API_KEY está definida; Claude Code la usará en lugar de tu suscripción." >&2
fi

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

now=$(date +%s)
header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$AGENT_APP_ID" | b64url)
signature=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$KEY_FILE" -binary | b64url)
jwt="$header.$payload.$signature"

gh_api() { curl -fsS -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "$@"; }

installation_id=$(gh_api -H "Authorization: Bearer $jwt" "$API/repos/$AGENT_REPO/installation" | jq -r .id)
token_json=$(gh_api -X POST -H "Authorization: Bearer $jwt" \
  "$API/app/installations/$installation_id/access_tokens" \
  -d "{\"repositories\":[\"${AGENT_REPO#*/}\"]}")
token=$(jq -r .token <<<"$token_json")
expires=$(jq -r .expires_at <<<"$token_json")
bot_id=$(gh_api "$API/users/${AGENT_APP_SLUG}%5Bbot%5D" | jq -r .id)
unset jwt

bot_name="${AGENT_APP_SLUG}[bot]"
bot_email="${bot_id}+${AGENT_APP_SLUG}[bot]@users.noreply.github.com"

echo "Agente: $bot_name · repo: $AGENT_REPO · token válido hasta $expires"

# El agente no hereda ninguna credencial del humano. VS Code reenvía al contenedor
# el helper de credenciales de git, su askpass y el agente SSH del host: con ellos
# el agente podría hacer push con TU identidad (y tu bypass de administrador).
unset SSH_AUTH_SOCK GIT_ASKPASS SSH_ASKPASS VSCODE_GIT_ASKPASS_MAIN VSCODE_GIT_ASKPASS_NODE \
      VSCODE_GIT_ASKPASS_EXTRA_ARGS VSCODE_GIT_IPC_HANDLE GITHUB_TOKEN
export GIT_SSH_COMMAND="false"   # sin SSH: solo HTTPS con el token del bot
export GIT_TERMINAL_PROMPT=0

export GH_TOKEN="$token"
export GIT_AUTHOR_NAME="$bot_name" GIT_COMMITTER_NAME="$bot_name"
export GIT_AUTHOR_EMAIL="$bot_email" GIT_COMMITTER_EMAIL="$bot_email"
# Credenciales de git solo para este proceso: se vacía la lista de helpers
# (incluido el de VS Code) y se añade uno que devuelve el token del bot.
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0="credential.helper" GIT_CONFIG_VALUE_0=""
export GIT_CONFIG_KEY_1="credential.https://github.com.helper"
export GIT_CONFIG_VALUE_1='!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'

exec claude "$@"
