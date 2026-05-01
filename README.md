# Agent skills test

Version-controlled skill bundles for agent workflows (inbox / agent / outbox layout) and a small **marketing intern** web app (FastAPI) on OpenShift.

## Repository layout

| Path | Purpose |
|------|--------|
| `backend/app/` | Python API (`main.py`, `k8s_pi_job.py`), `requirements.txt` |
| `frontend/` | React UI (Vite): `src/App.jsx` + four panels under `src/components/` → built to `frontend/dist/` |
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

**Frontend dev** (API on port 8080): `cd frontend && npm install && npm run dev` — Vite proxies `/api` to the backend.

The container image builds the UI with a Node stage (`docker.io/library/node:20-alpine`). Clusters that cannot pull Docker Hub need a mirrored Node base or a pre-built `frontend/dist/` baked in separately.

## Chat (Qwen) vs Run agent (OpenAI)

Two separate integrations:

| Step | Model / API | Env vars | What it does |
|------|-------------|----------|----------------|
| **Chat** | **Qwen** (OpenShift AI or any OpenAI-compatible `POST …/v1/chat/completions`) | **`CHAT_*` only** — never `OPENAI_*` | Converses with the user and **writes into `inbox/*.md`** via JSON patches from the model. |
| **Run agent** | **OpenAI API** | **`OPENAI_API_KEY`** / **`OPENAI_K8S_SECRET_NAME`** | Runs the pi-agent Job with the inbox + skills you prepared in chat. |

Chat does **not** read or send your OpenAI key. Configure Qwen with **`CHAT_COMPLETIONS_URL`**, **`CHAT_MODEL`**, and **`CHAT_API_KEY`** (or **`CHAT_ALLOW_NO_AUTH=1`** when allowed).

**Qwen / chat wiring**

1. **URL** — HTTPS Route to your inference service + **`/v1/chat/completions`** (confirm with your OpenShift AI / KServe docs).
2. **Env** (see `openshift/deployment.yaml`):
   - **`CHAT_COMPLETIONS_URL`**, **`CHAT_MODEL`**, optional **`CHAT_API_KEY`**, or **`CHAT_ALLOW_NO_AUTH=1`**.

After changing env vars, apply the Deployment and roll the pod.

**If `oc apply -f openshift/deployment.yaml` errors on `spec.selector` immutable:** the Deployment on the cluster was likely created with **`oc apply -k openshift/`**, which adds extra labels to the selector. Either use **`oc apply -k openshift/`** (recommended), or update env without touching the Deployment object:

```bash
oc set env deployment/marketing-intern -n marketing-intern \
  CHAT_COMPLETIONS_URL='https://YOUR_ROUTE/v1/chat/completions' \
  CHAT_MODEL='qwen3-8b'
```

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
