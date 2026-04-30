#!/usr/bin/env bash
# Mirror marketing-intern image from OpenShift integrated registry to Quay.
# Prerequisites: oc logged in; podman/skopeo optional; Quay robot token or password.
#
# Usage:
#   export QUAY_USER='rh-ee-gsiyu+YOUR_ROBOT'
#   export QUAY_TOKEN='...robot token...'
#   ./scripts/mirror-to-quay.sh
#
# Dest repo must exist on Quay (or org allows auto-create).

set -euo pipefail

SRC_REGISTRY="${SRC_REGISTRY:-127.0.0.1:5000}"
SRC_IMAGE="${SRC_IMAGE:-marketing-intern/marketing-intern:latest}"
DEST="${DEST:-docker://quay.io/rh-ee-gsiyu/agent-skills:latest}"

if [[ -z "${QUAY_TOKEN:-}" ]]; then
  echo "Set QUAY_TOKEN (and QUAY_USER if not using docker login cache)." >&2
  exit 1
fi

PF_PID=""
cleanup() { [[ -n "${PF_PID}" ]] && kill "${PF_PID}" 2>/dev/null || true; }
trap cleanup EXIT

echo "Port-forwarding integrated registry to localhost:5000..."
oc -n openshift-image-registry port-forward svc/image-registry 5000:5000 &
PF_PID=$!
sleep 2

TOKEN=$(oc whoami -t)
USER_OCP=$(oc whoami)

echo "Copying image to Quay (${DEST})..."
skopeo copy \
  --src-creds="${USER_OCP}:${TOKEN}" \
  --src-tls-verify=false \
  --dest-creds "${QUAY_USER:?set QUAY_USER to quay robot username}:$QUAY_TOKEN" \
  --dest-tls-verify=true \
  "docker://${SRC_REGISTRY}/${SRC_IMAGE}" \
  "${DEST}"

echo "Done. Update Deployment: PI_AGENT_IMAGE=quay.io/rh-ee-gsiyu/agent-skills:latest"
echo "And ensure pull Secret is linked to serviceaccount marketing-intern-pi."
