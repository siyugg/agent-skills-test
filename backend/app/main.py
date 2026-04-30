"""Marketing intern harness: inbox/skills UI + pi-agent via OpenShift Job or podman."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from k8s_pi_job import openshift_job_available, run_pi_agent_job


def _repo_root() -> Path:
    """Directory containing ``skills/`` and ``frontend/`` (/app in the image, repo root when developing)."""
    here = Path(__file__).resolve().parent
    if (here / "skills" / "marketing-intern").is_dir():
        return here
    dev = here.parent.parent
    if (dev / "skills" / "marketing-intern").is_dir():
        return dev
    raise RuntimeError(
        f"Cannot find skills/marketing-intern (looked in {here}/skills and {dev}/skills)"
    )


def _load_index_html() -> str:
    p = _repo_root() / "frontend" / "index.html"
    if not p.is_file():
        raise RuntimeError(f"missing UI file: {p}")
    return p.read_text(encoding="utf-8")


_REPO_ROOT = _repo_root()
BASE = _REPO_ROOT / "skills" / "marketing-intern"

CONTAINER_AGENT = "/opt/app-root/src/agent"
CONTAINER_INBOX = "/opt/app-root/src/inbox"
CONTAINER_OUTBOX = "/opt/app-root/src/outbox"


def _read_api_key() -> str | None:
    path_env = os.environ.get("OPENAI_API_KEY_FILE")
    if path_env:
        p = Path(path_env)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()
    return None


def _openai_configured() -> bool:
    if os.environ.get("OPENAI_K8S_SECRET_NAME", "").strip():
        return True
    return bool(_read_api_key())


def _effective_exec_mode() -> str:
    raw = os.environ.get("AGENT_EXEC_MODE", "auto").strip().lower()
    if raw in ("openshift-job", "kubernetes-job", "k8s-job", "job"):
        return "openshift-job"
    if raw == "podman":
        return "podman"
    if openshift_job_available():
        return "openshift-job"
    return "podman"


def _generate_backend_ready() -> bool:
    mode = _effective_exec_mode()
    if mode == "openshift-job":
        return openshift_job_available()
    return _podman_available()


def _podman_bin() -> str:
    return os.environ.get("PODMAN_BIN", "podman")


def _pi_agent_image() -> str:
    return os.environ.get("PI_AGENT_IMAGE", "localhost/pi-agent:v1")


def _volume_suffix() -> str:
    return os.environ.get("PODMAN_VOLUME_SUFFIX", ",z")


def _podman_available() -> bool:
    return shutil.which(_podman_bin()) is not None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if not BASE.is_dir():
        raise RuntimeError(f"missing skill bundle directory: {BASE}")
    yield


app = FastAPI(title="Marketing intern — skill bundle", lifespan=lifespan)


def _safe_path(rel: str) -> Path:
    target = (BASE / rel).resolve()
    base = BASE.resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=403, detail="invalid path")
    return target


def _md_title_and_excerpt(text: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    title = "Untitled"
    rest_start = 0
    for i, line in enumerate(lines):
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            title = m.group(1).strip()
            rest_start = i + 1
            break
    body_lines: list[str] = []
    for line in lines[rest_start:]:
        if line.strip():
            body_lines.append(line)
            if len(body_lines) >= 8:
                break
    excerpt = "\n".join(body_lines).strip()
    if len(excerpt) > 400:
        excerpt = excerpt[:397] + "…"
    return title, excerpt


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    mode = _effective_exec_mode()
    return {
        "openai_configured": _openai_configured(),
        "podman_available": _podman_available(),
        "podman_bin": _podman_bin(),
        "pi_agent_image": _pi_agent_image(),
        "exec_mode": mode,
        "openshift_job_available": openshift_job_available(),
        "generate_backend_ready": _generate_backend_ready(),
        "chat_completions_configured": _chat_ready(),
        "chat_completion_url": _chat_completions_url() or None,
    }


@app.get("/api/skills")
def api_skills() -> JSONResponse:
    agent_dir = BASE / "agent"
    if not agent_dir.is_dir():
        return JSONResponse([])
    items: list[dict[str, Any]] = []
    # Every markdown file in agent/ is listed; only skill_*.md are toggles for staging (others always ship).
    for f in sorted(agent_dir.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        title, excerpt = _md_title_and_excerpt(raw)
        selectable = f.name.startswith("skill_")
        items.append(
            {
                "id": f.stem,
                "filename": f.name,
                "title": title,
                "excerpt": excerpt,
                "content": raw,
                "selectable": selectable,
            }
        )
    return JSONResponse(items)


def _folder_docs(folder: str) -> list[dict[str, str]]:
    d = BASE / folder
    if not d.is_dir():
        return []
    out: list[dict[str, str]] = []
    for f in sorted(d.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(BASE)
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            text = ""
        out.append(
            {
                "path": rel.as_posix(),
                "name": f.name,
                "content": text,
            }
        )
    return out


@app.get("/api/inbox")
def api_inbox() -> JSONResponse:
    return JSONResponse(_folder_docs("inbox"))


@app.get("/api/outbox")
def api_outbox() -> JSONResponse:
    return JSONResponse(_folder_docs("outbox"))


class InboxDocIn(BaseModel):
    name: str
    content: str


class GenerateBody(BaseModel):
    inbox: list[InboxDocIn] = Field(default_factory=list)
    selected_skill_ids: list[str] = Field(default_factory=list)


def _stage_agent(dest: Path, selected_skill_ids: list[str]) -> None:
    src = BASE / "agent"
    if not src.is_dir():
        raise HTTPException(status_code=500, detail="bundle agent/ missing")
    shutil.copytree(src, dest)
    if selected_skill_ids:
        keep_names = {f"{sid}.md" for sid in selected_skill_ids}
        for f in list(dest.glob("skill_*.md")):
            if f.name not in keep_names:
                f.unlink()


def _write_inbox_dir(inbox_root: Path, docs: list[InboxDocIn]) -> None:
    inbox_root.mkdir(parents=True, exist_ok=True)
    for existing in inbox_root.iterdir():
        if existing.is_file():
            existing.unlink()
    for doc in docs:
        name = doc.name.strip() or "unnamed.md"
        if "/" in name or "\\" in name or name.startswith(".."):
            raise HTTPException(status_code=400, detail=f"invalid inbox filename: {name}")
        (inbox_root / name).write_text(doc.content, encoding="utf-8")


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


def _read_outbox_files_structured(out_root: Path) -> list[dict[str, Any]]:
    if not out_root.is_dir():
        return []
    files: list[dict[str, Any]] = []
    for f in sorted(out_root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(out_root)
        rel_s = rel.as_posix()
        suffix = f.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            raw = f.read_bytes()
            files.append(
                {
                    "name": rel_s,
                    "kind": "image",
                    "mime": _mime_for_suffix(rel_s),
                    "base64": base64.b64encode(raw).decode("ascii"),
                    "content": "",
                }
            )
        else:
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                text = "[Could not read file]"
            files.append(
                {
                    "name": rel_s,
                    "kind": "text",
                    "mime": "",
                    "base64": "",
                    "content": text,
                }
            )
    return files


def _run_podman_staged(agent_dir: Path, inbox_dir: Path, outbox_dir: Path) -> dict[str, Any]:
    key = _read_api_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set for podman mode.",
        )
    if not _podman_available():
        raise HTTPException(
            status_code=503,
            detail=f"`{_podman_bin()}` not found on PATH.",
        )

    podman = _podman_bin()
    image = _pi_agent_image()
    vs = _volume_suffix()

    agent_abs = str(agent_dir.resolve())
    inbox_abs = str(inbox_dir.resolve())
    outbox_abs = str(outbox_dir.resolve())

    cmd = [
        podman,
        "run",
        "--rm",
        "-e",
        f"OPENAI_API_KEY={key}",
        "-v",
        f"{agent_abs}:{CONTAINER_AGENT}:ro{vs}",
        "-v",
        f"{inbox_abs}:{CONTAINER_INBOX}:ro{vs}",
        "-v",
        f"{outbox_abs}:{CONTAINER_OUTBOX}:rw{vs}",
        image,
    ]

    timeout_s = int(os.environ.get("PI_AGENT_TIMEOUT_SEC", "600"))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"podman run exceeded {timeout_s}s")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"executable not found: {podman}")

    files = _read_outbox_files_structured(outbox_dir)
    result = {
        "files": files,
        "exit_code": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "image": image,
        "exec_mode": "podman",
    }
    if proc.returncode != 0:
        detail = {
            "message": "pi-agent container exited non-zero",
            **result,
        }
        raise HTTPException(status_code=502, detail=json.dumps(detail))

    return result


def _run_generate(body: GenerateBody) -> dict[str, Any]:
    if not _openai_configured():
        raise HTTPException(
            status_code=503,
            detail="Configure OPENAI_API_KEY / OPENAI_API_KEY_FILE or OPENAI_K8S_SECRET_NAME.",
        )
    mode = _effective_exec_mode()
    if mode == "openshift-job" and not openshift_job_available():
        raise HTTPException(
            status_code=503,
            detail="AGENT_EXEC_MODE requests a Job but the API is not running in-cluster (no service account token).",
        )
    if mode == "podman" and not _podman_available():
        raise HTTPException(status_code=503, detail="Podman not available; set AGENT_EXEC_MODE=openshift-job on OpenShift.")

    with tempfile.TemporaryDirectory(prefix="mi-pi-agent-") as tmp:
        tmp_path = Path(tmp)
        agent_dir = tmp_path / "agent"
        inbox_dir = tmp_path / "inbox"
        outbox_dir = tmp_path / "outbox"
        _stage_agent(agent_dir, body.selected_skill_ids)
        _write_inbox_dir(inbox_dir, body.inbox)
        outbox_dir.mkdir(parents=True)

        if mode == "openshift-job":
            return run_pi_agent_job(agent_dir, inbox_dir)
        return _run_podman_staged(agent_dir, inbox_dir, outbox_dir)


@app.post("/api/generate")
async def api_generate(body: GenerateBody) -> JSONResponse:
    data = await asyncio.to_thread(_run_generate, body)
    return JSONResponse(data)


class ChatMessageIn(BaseModel):
    role: str = "user"
    content: str = ""


class ChatBody(BaseModel):
    message: str = ""
    history: list[ChatMessageIn] = Field(default_factory=list)


def _chat_completions_url() -> str:
    return os.environ.get("CHAT_COMPLETIONS_URL", "").strip()


def _chat_allow_no_auth() -> bool:
    return os.environ.get("CHAT_ALLOW_NO_AUTH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _chat_api_key() -> str | None:
    k = os.environ.get("CHAT_API_KEY", "").strip()
    if k:
        return k
    return _read_api_key()


def _chat_ready() -> bool:
    """True when chat can call the completions endpoint (URL + optional Bearer rules)."""
    if not _chat_completions_url():
        return False
    if _chat_api_key() or _chat_allow_no_auth():
        return True
    return False


def _inbox_filenames() -> list[str]:
    d = BASE / "inbox"
    if not d.is_dir():
        return []
    return sorted([f.name for f in d.iterdir() if f.is_file()])


def _call_openai_compatible_chat(messages: list[dict[str, str]]) -> str:
    import urllib.error
    import urllib.request

    url = _chat_completions_url()
    key = _chat_api_key()
    if not url:
        raise ValueError("CHAT_COMPLETIONS_URL is not set")
    if not key and not _chat_allow_no_auth():
        raise ValueError(
            "Set CHAT_API_KEY (or rely on OPENAI_API_KEY), or set CHAT_ALLOW_NO_AUTH=1 for endpoints that do not require a Bearer token"
        )
    model = os.environ.get("CHAT_MODEL", "qwen").strip()
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": float(os.environ.get("CHAT_TEMPERATURE", "0.3")),
        }
    ).encode()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:4000]
        raise ValueError(f"chat endpoint HTTP {e.code}: {err_body}") from e
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("empty choices from model")
    return str(choices[0].get("message", {}).get("content") or "")


def _parse_chat_json(raw: str) -> tuple[str, list[dict[str, Any]]]:
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```\w*\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        parsed = json.loads(t)
        reply = str(parsed.get("reply", raw))
        patches_raw = parsed.get("patches") or []
        patches: list[dict[str, Any]] = []
        for p in patches_raw:
            if isinstance(p, dict) and p.get("name"):
                patches.append({"name": str(p["name"]), "append": str(p.get("append", ""))})
        return reply, patches
    except json.JSONDecodeError:
        return raw, []


def _fallback_chat_response(user_msg: str, inbox_names: list[str]) -> tuple[str, list[dict[str, str]]]:
    reply = (
        "Configure **CHAT_COMPLETIONS_URL** (OpenAI-compatible `/v1/chat/completions` for Qwen on OpenShift AI) "
        "and **CHAT_API_KEY** (or rely on OPENAI_API_KEY). "
        "Until then, your message is appended to the primary inbox file as a demo."
    )
    target = ""
    if "campaign_brief.md" in inbox_names:
        target = "campaign_brief.md"
    elif inbox_names:
        target = inbox_names[0]
    patches: list[dict[str, str]] = []
    if target:
        patches.append({"name": target, "append": f"\n\n**[Chat]** {user_msg.strip()}"})
    return reply, patches


@app.post("/api/chat")
async def api_chat(body: ChatBody) -> JSONResponse:
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="empty message")
    inbox_names = _inbox_filenames()
    sys_prompt = (
        "You help organize marketing requirements. Inbox markdown files: "
        + ", ".join(inbox_names or ["(none)"])
        + ". Reply with a JSON object ONLY (no markdown code fences): "
        '{"reply":"<assistant message; ask a follow-up if information is insufficient>",'
        '"patches":[{"name":"exact-filename.md","append":"text to append to that file"}]}. '
        "Put facts in the best-matching file (e.g. dates in event_details.md). "
        "If unclear, ask in reply and use minimal patches."
    )
    messages_ch: list[dict[str, str]] = [{"role": "system", "content": sys_prompt}]
    for h in body.history[-16:]:
        role = h.role if h.role in ("user", "assistant") else "user"
        messages_ch.append({"role": role, "content": h.content})
    messages_ch.append({"role": "user", "content": msg})

    reply_text = ""
    patches: list[dict[str, Any]] = []

    if _chat_ready():
        try:
            raw = await asyncio.to_thread(_call_openai_compatible_chat, messages_ch)
            reply_text, patches = _parse_chat_json(raw)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)[:2000]) from e
    else:
        reply_text, plist = _fallback_chat_response(msg, inbox_names)
        patches = plist

    return JSONResponse({"reply": reply_text, "patches": patches})


_INDEX_HTML = _load_index_html()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX_HTML


@app.get("/file/{path:path}")
def get_file(path: str) -> Response:
    p = _safe_path(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="not found")
    body = p.read_bytes()
    lower = path.lower()
    if lower.endswith(".md"):
        media = "text/markdown; charset=utf-8"
    elif lower.endswith(".txt"):
        media = "text/plain; charset=utf-8"
    else:
        media = "application/octet-stream"
    return Response(content=body, media_type=media)
