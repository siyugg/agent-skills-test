#!/usr/bin/env bash
# Rebuild the marketing-intern app image on OpenShift (binary Docker build) and
# roll the Deployment so the running pods pick up the new image.
#
# Use this after changing backend/app, frontend/, or skills/ and you need a new
# image on the cluster. The BuildConfig must use dockerfilePath: backend/Containerfile
# (see README). The cluster does not always replace pods when :latest moves;
# this script always runs a rollout restart after a successful build.
#
# Prerequisites:
#   - oc logged in to the right cluster
#   - BuildConfig "marketing-intern" and Deployment in the target namespace
#
# Usage (from anywhere):
#   ./scripts/rebuild-marketing-intern-openshift.sh
#
# Optional environment:
#   NAMESPACE   — OpenShift project (default: marketing-intern)
#   BC_NAME     — BuildConfig name (default: marketing-intern)
#   DEPLOYMENT  — Deployment name (default: marketing-intern)
#   NO_ROLLOUT  — if set to 1, skip rollout restart (only build)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

NAMESPACE="${NAMESPACE:-marketing-intern}"
BC_NAME="${BC_NAME:-marketing-intern}"
DEPLOYMENT="${DEPLOYMENT:-marketing-intern}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

cd "${REPO_ROOT}"

if ! command -v oc >/dev/null 2>&1; then
  echo "oc not found in PATH." >&2
  exit 1
fi

if ! oc whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: oc login …" >&2
  exit 1
fi

echo "Repository root: ${REPO_ROOT}"
echo "Starting binary build ${BC_NAME} in namespace ${NAMESPACE}…"

oc start-build "${BC_NAME}" \
  --from-dir=. \
  --follow \
  -n "${NAMESPACE}"

if [[ "${NO_ROLLOUT:-0}" == "1" ]]; then
  echo "NO_ROLLOUT=1 — skipping rollout restart."
  exit 0
fi

echo "Restarting deployment/${DEPLOYMENT} so pods use the new image…"
oc rollout restart "deployment/${DEPLOYMENT}" -n "${NAMESPACE}"
oc rollout status "deployment/${DEPLOYMENT}" -n "${NAMESPACE}" --timeout="${ROLLOUT_TIMEOUT}"

echo "Done. Open your Route or run: oc get route -n ${NAMESPACE}"
