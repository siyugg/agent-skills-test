"""Create an OpenShift/Kubernetes Job per pi-agent run; collect outbox via exec tar."""
from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import tarfile
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

CONTAINER_OUTBOX = "/opt/app-root/src/outbox"

_CM_KEY_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _namespace() -> str:
    p = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return os.environ.get("POD_NAMESPACE", os.environ.get("NAMESPACE", "default"))


def _load_k8s() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _sanitize_cm_key(filename: str) -> str:
    s = filename.replace("/", "__").replace("\\", "__")
    s = _CM_KEY_RE.sub("_", s)
    if not s or not (s[0].isalnum() or s[0] in "._"):
        s = "f_" + s
    return s[:253]


def _dir_to_configmap_payload(src: Path) -> tuple[dict[str, str], dict[str, str]]:
    data: dict[str, str] = {}
    binary_data: dict[str, str] = {}
    if not src.is_dir():
        return data, binary_data
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src).as_posix()
        key = _sanitize_cm_key(rel)
        raw = f.read_bytes()
        try:
            text = raw.decode("utf-8")
            if "\x00" in text:
                binary_data[key] = base64.b64encode(raw).decode("ascii")
            else:
                data[key] = text
        except UnicodeDecodeError:
            binary_data[key] = base64.b64encode(raw).decode("ascii")
    return data, binary_data


def _mime_for_suffix(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"


def _files_from_tar_bytes(raw: bytes) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not raw.strip():
        return files
    try:
        tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
    except tarfile.TarError:
        return files
    with tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name.lstrip("./")
            if not name or name.endswith("/"):
                continue
            fobj = tf.extractfile(m)
            if fobj is None:
                continue
            blob = fobj.read()
            lower = name.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                files.append(
                    {
                        "name": name,
                        "kind": "image",
                        "mime": _mime_for_suffix(name),
                        "base64": base64.b64encode(blob).decode("ascii"),
                        "content": "",
                    }
                )
            else:
                try:
                    text = blob.decode("utf-8")
                except UnicodeDecodeError:
                    text = blob.decode("utf-8", errors="replace")
                files.append({"name": name, "kind": "text", "content": text, "base64": "", "mime": ""})
    files.sort(key=lambda x: x["name"])
    return files


def _wait_job(
    batch_v1: client.BatchV1Api,
    namespace: str,
    job_name: str,
    timeout_sec: int,
) -> client.V1Job:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            job = batch_v1.read_namespaced_job_status(name=job_name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                time.sleep(1.0)
                continue
            raise
        st = job.status
        if st:
            succeeded = getattr(st, "succeeded", None)
            failed = getattr(st, "failed", None)
            if succeeded is not None and int(succeeded) >= 1:
                return job
            if failed is not None and int(failed) >= 1:
                raise HTTPException(
                    status_code=502,
                    detail=json.dumps(
                        {
                            "message": "pi-agent Job pod failed",
                            "job": job_name,
                        }
                    ),
                )
        time.sleep(2.0)
    raise HTTPException(status_code=504, detail=f"Job {job_name} timed out after {timeout_sec}s")


def _pod_for_job(core_v1: client.CoreV1Api, namespace: str, job_name: str) -> str:
    pods = core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"job-name={job_name}",
    )
    if not pods.items:
        raise HTTPException(status_code=502, detail=f"No pod found for job {job_name}")
    # Prefer succeeded pod
    for p in pods.items:
        if p.status and p.status.phase == "Succeeded":
            return p.metadata.name  # type: ignore[union-attr]
    return pods.items[0].metadata.name  # type: ignore[union-attr]


def _exec_tar_outbox(core_v1: client.CoreV1Api, namespace: str, pod_name: str) -> bytes:
    cmd = ["tar", "cf", "-", "-C", CONTAINER_OUTBOX, "."]
    ws = stream(
        core_v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=cmd,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
        _preload_content=False,
    )
    stdout = b""
    while ws.is_open():
        ws.update(timeout=120)
        if ws.peek_stdout():
            chunk = ws.read_stdout()
            if isinstance(chunk, str):
                stdout += chunk.encode("latin1", errors="replace")
            else:
                stdout += chunk
        if ws.peek_stderr():
            ws.read_stderr()
    return stdout


def _pod_logs(core_v1: client.CoreV1Api, namespace: str, pod_name: str) -> str:
    try:
        return core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
    except ApiException:
        return ""


def _openai_env_for_job() -> list[client.V1EnvVar]:
    secret_name = os.environ.get("OPENAI_K8S_SECRET_NAME", "").strip()
    secret_key = os.environ.get("OPENAI_K8S_SECRET_KEY", "OPENAI_API_KEY").strip()
    if secret_name:
        return [
            client.V1EnvVar(
                name="OPENAI_API_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(name=secret_name, key=secret_key)
                ),
            )
        ]
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        p = os.environ.get("OPENAI_API_KEY_FILE")
        if p and Path(p).is_file():
            key = Path(p).read_text(encoding="utf-8").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Set OPENAI_API_KEY on the API deployment or OPENAI_K8S_SECRET_NAME for the Job.",
        )
    return [client.V1EnvVar(name="OPENAI_API_KEY", value=key)]


def run_pi_agent_job(agent_dir: Path, inbox_dir: Path) -> dict[str, Any]:
    """Create ConfigMaps + Job, wait, tar outbox from the pod, delete resources."""
    _load_k8s()
    ns = _namespace()
    suffix = uuid.uuid4().hex[:12]
    job_name = f"mi-pi-{suffix}"
    cm_agent = f"mi-agent-{suffix}"
    cm_inbox = f"mi-inbox-{suffix}"
    image = os.environ.get("PI_AGENT_IMAGE", "localhost/pi-agent:v1")
    timeout_s = int(os.environ.get("PI_AGENT_TIMEOUT_SEC", "600"))
    ttl = int(os.environ.get("JOB_TTL_SECONDS_AFTER_FINISHED", "600"))

    core_v1 = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()

    agent_data, agent_bin = _dir_to_configmap_payload(agent_dir)
    inbox_data, inbox_bin = _dir_to_configmap_payload(inbox_dir)
    if not inbox_data and not inbox_bin:
        inbox_data = {".keep": "\n"}
    if not agent_data and not agent_bin:
        raise HTTPException(status_code=400, detail="Staged agent directory is empty")

    def _cm(meta: client.V1ObjectMeta, d: dict[str, str], b: dict[str, str]) -> client.V1ConfigMap:
        kw: dict[str, Any] = {"metadata": meta}
        if d:
            kw["data"] = d
        if b:
            kw["binary_data"] = b
        return client.V1ConfigMap(**kw)

    cm_body_a = _cm(client.V1ObjectMeta(name=cm_agent, namespace=ns), agent_data, agent_bin)
    cm_body_i = _cm(client.V1ObjectMeta(name=cm_inbox, namespace=ns), inbox_data, inbox_bin)

    job_body = client.V1Job(
        metadata=client.V1ObjectMeta(name=job_name, namespace=ns, labels={"app": "mi-pi-agent", "run": suffix}),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=ttl,
            backoff_limit=0,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "mi-pi-agent"}),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    volumes=[
                        client.V1Volume(
                            name="agent",
                            config_map=client.V1ConfigMapVolumeSource(name=cm_agent),
                        ),
                        client.V1Volume(
                            name="inbox",
                            config_map=client.V1ConfigMapVolumeSource(name=cm_inbox),
                        ),
                        client.V1Volume(name="outbox", empty_dir=client.V1EmptyDirVolumeSource()),
                    ],
                    containers=[
                        client.V1Container(
                            name="pi-agent",
                            image=image,
                            image_pull_policy=os.environ.get("PI_AGENT_IMAGE_PULL_POLICY", "IfNotPresent"),
                            env=_openai_env_for_job(),
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="agent",
                                    mount_path="/opt/app-root/src/agent",
                                    read_only=True,
                                ),
                                client.V1VolumeMount(
                                    name="inbox",
                                    mount_path="/opt/app-root/src/inbox",
                                    read_only=True,
                                ),
                                client.V1VolumeMount(
                                    name="outbox",
                                    mount_path="/opt/app-root/src/outbox",
                                ),
                            ],
                            resources=client.V1ResourceRequirements(
                                limits={"memory": os.environ.get("PI_AGENT_MEMORY_LIMIT", "512Mi")},
                                requests={"cpu": os.environ.get("PI_AGENT_CPU_REQUEST", "100m"), "memory": "256Mi"},
                            ),
                        )
                    ],
                ),
            ),
        ),
    )

    try:
        core_v1.create_namespaced_config_map(namespace=ns, body=cm_body_a)
        core_v1.create_namespaced_config_map(namespace=ns, body=cm_body_i)
        batch_v1.create_namespaced_job(namespace=ns, body=job_body)
        _wait_job(batch_v1, ns, job_name, timeout_s)
        pod_name = _pod_for_job(core_v1, ns, job_name)
        tar_raw = _exec_tar_outbox(core_v1, ns, pod_name)
        files = _files_from_tar_bytes(tar_raw)
        logs = _pod_logs(core_v1, ns, pod_name)
        return {
            "files": files,
            "exit_code": 0,
            "stdout": logs or "",
            "stderr": "",
            "image": image,
            "exec_mode": "openshift-job",
            "job_name": job_name,
            "namespace": ns,
        }
    except HTTPException:
        raise
    except ApiException as e:
        raise HTTPException(status_code=502, detail=f"Kubernetes API error: {e.reason} — {e.body}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    finally:
        for name in (job_name,):
            try:
                batch_v1.delete_namespaced_job(
                    name=name,
                    namespace=ns,
                    propagation_policy="Background",
                )
            except ApiException:
                pass
        for cm in (cm_agent, cm_inbox):
            try:
                core_v1.delete_namespaced_config_map(name=cm, namespace=ns)
            except ApiException:
                pass


def openshift_job_available() -> bool:
    if not Path("/var/run/secrets/kubernetes.io/serviceaccount/token").is_file():
        return False
    try:
        _load_k8s()
        # Lightweight check; Role grants pods list (not serviceaccounts list).
        client.CoreV1Api().list_namespaced_pod(namespace=_namespace(), limit=1)
        return True
    except Exception:
        return False
