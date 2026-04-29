"""Serve the marketing-intern skill bundle as static files with a simple index."""
from __future__ import annotations

import html
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

BASE = Path(__file__).resolve().parent / "marketing-intern"


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    rows: list[str] = []
    for f in sorted(BASE.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(BASE)
        href = f"/file/{rel.as_posix()}"
        rows.append(f'<li><a href="{html.escape(href)}">{html.escape(rel.as_posix())}</a></li>')
    ul = "<ul>\n" + "\n".join(rows) + "\n</ul>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"/><title>Marketing intern bundle</title></head>
<body>
<h1>Marketing intern</h1>
<p>Read-only view of the version-controlled skill bundle (<code>agent/</code>, <code>inbox/</code>, <code>outbox/</code>).</p>
{ul}
</body>
</html>"""


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
