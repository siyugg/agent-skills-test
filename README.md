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

1. **Project**

   ```bash
   oc new-project marketing-intern
   ```

2. **Image** — build the image, push it to a registry your cluster can pull from (often the OpenShift internal registry), then align `images.newName` / `images.newTag` in `openshift/kustomization.yaml` with that pull spec. Example:

   ```bash
   podman build -f deploy/Containerfile -t marketing-intern:latest .
   # oc registry login … ; podman tag … ; podman push …  (per your cluster docs)
   ```

3. **Apply**

   ```bash
   oc apply -k openshift/
   ```

   Without Kustomize:

   ```bash
   oc apply -f openshift/deployment.yaml -f openshift/service.yaml -f openshift/route.yaml -n marketing-intern
   ```

4. **Route** — `oc get route marketing-intern -n marketing-intern`, then open the HTTPS URL. Edge TLS is enabled in `openshift/route.yaml`; adjust `host` or TLS if your cluster requires it.
