# Agent skills test

Version-controlled skill bundles for agent workflows (inbox / agent / outbox layout).

## Layout

- `marketing-intern/` — campaign and event marketing materials agent
- `pi-test/` — sample pi.dev-style agent layout with `Containerfile`

## Marketing intern — OpenShift

The `deploy/` directory builds a small read-only web UI that lists and serves the `marketing-intern` markdown bundle (for demos and internal review).

### Build image

From this repository root:

```bash
podman build -f deploy/Containerfile -t marketing-intern:latest .
```

### Run locally

```bash
podman run --rm -p 8080:8080 marketing-intern:latest
```

Open http://localhost:8080 — health check: http://localhost:8080/health

### Deploy on OpenShift

1. Create a project (namespace), e.g. `marketing-intern`.
2. Push the image to your cluster registry (or use `oc new-build --binary` with the same `Containerfile`).
3. Apply manifests from `openshift/` after setting the image reference in `deployment.yaml` to your image pull spec.

```bash
oc apply -k openshift/
```

If you do not use Kustomize, apply files individually:

```bash
oc apply -f openshift/deployment.yaml -f openshift/service.yaml -f openshift/route.yaml
```

Adjust `Route` host or TLS as required by your cluster.
