# Agent skills test

Version-controlled skill bundles for agent workflows (inbox / agent / outbox layout) and a small **marketing intern** web app (FastAPI) on OpenShift.

## Repository layout

| Path | Purpose |
|------|--------|
| `backend/app/` | Python API (`main.py`, `k8s_pi_job.py`), `requirements.txt` |
| `frontend/` | Web UI (`index.html` loaded at startup — edit here for layout/CSS/JS) |
| `skills/marketing-intern/` | Default bundle: `agent/`, `inbox/`, `outbox/` markdown for the demo agent |
| `skills/pi-test/` | Sample pi-style bundle + optional pi-agent `Containerfile` |
| `openshift/` | Deployment, Service, Route, RBAC samples |
| `scripts/` | Helpers (`rebuild-marketing-intern-openshift.sh`, Quay mirror, etc.) |

## Marketing intern — build image

From the **repository root**:

```bash
podman build -f backend/Containerfile -t marketing-intern:latest .
```

### Run locally

```bash
podman run --rm -p 8080:8080 marketing-intern:latest
```

Open http://localhost:8080 — health: http://localhost:8080/health

## OpenShift binary build + rollout

After changing `backend/`, `frontend/`, or `skills/marketing-intern/`, use:

```bash
./scripts/rebuild-marketing-intern-openshift.sh
```

The BuildConfig must build with **`dockerfilePath: backend/Containerfile`** (not `deploy/…`). If your cluster still points at the old path, patch once:

```bash
oc patch bc marketing-intern -n marketing-intern --type=json \
  -p '[{"op":"replace","path":"/spec/strategy/dockerStrategy/dockerfilePath","value":"backend/Containerfile"}]'
```

Then apply manifests as needed:

```bash
oc apply -k openshift/
```

Route: `oc get route marketing-intern -n marketing-intern`

## pi-agent image (optional)

From repo root:

```bash
podman build -t pi-agent:latest -f skills/pi-test/Containerfile .
```

Or from `skills/pi-test/` using that directory as context (see comments in `skills/pi-test/Containerfile`).
