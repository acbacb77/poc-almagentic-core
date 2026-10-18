#!/usr/bin/env bash
# Verifica que una imagen se puede desplegar (tarea 10) e imprime el commit de app del que sale.
#
# Uso: verify_image.sh <imagen@sha256:...>
# Variables: SOURCE_REPO (owner/repo de la aplicación), SIGNER_WORKFLOW (workflow de core
# que firma), GH_TOKEN. Requiere gh y cosign.
#
# Comprueba, contra registros públicos (Sigstore/Rekor y la API de atestaciones):
#   1. procedencia SLSA firmada por SIGNER_WORKFLOW, construida desde SOURCE_REPO en main;
#   2. SBOM atestado por el mismo workflow;
#   3. firma de cosign con certificado del mismo workflow.
set -euo pipefail
ref="$1"
[[ "$ref" =~ @sha256:[0-9a-f]{64}$ ]] || { echo "::error::${ref} no está fijada por digest" >&2; exit 1; }
: "${SOURCE_REPO:?}" "${SIGNER_WORKFLOW:?}"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

gh attestation verify "oci://${ref}" --repo "$SOURCE_REPO" --signer-workflow "$SIGNER_WORKFLOW" \
  --source-ref refs/heads/main --deny-self-hosted-runners --format json > "$tmp/procedencia.json" \
  || { echo "::error title=Procedencia no válida::${ref}: no hay procedencia SLSA de ${SIGNER_WORKFLOW} construida desde main de ${SOURCE_REPO}" >&2; exit 1; }
gh attestation verify "oci://${ref}" --repo "$SOURCE_REPO" --signer-workflow "$SIGNER_WORKFLOW" \
  --predicate-type https://spdx.dev/Document/v2.3 > /dev/null \
  || { echo "::error title=SBOM no válido::${ref}: no hay SBOM atestado por ${SIGNER_WORKFLOW}" >&2; exit 1; }
cosign verify "$ref" --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp "^https://github.com/${SIGNER_WORKFLOW}@" > /dev/null 2>&1 \
  || { echo "::error title=Firma no válida::${ref}: no está firmada por ${SIGNER_WORKFLOW}" >&2; exit 1; }

jq -r '[.[].verificationResult.statement.predicate.buildDefinition.resolvedDependencies[]?.digest.gitCommit // empty][0] // ""' "$tmp/procedencia.json"
