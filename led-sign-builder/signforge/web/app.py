"""Local web UI. Self-host trust model: parsing happens in-process, no auth,
no outbound network calls. Uploaded files are referenced by server-side tokens
only — client-supplied font_path/art_path are ignored. Basic guardrails
(per-IP rate limits, upload/job caps with eviction) keep a shared LAN box
healthy; this is still not hardened multi-tenant hosting.
"""

from __future__ import annotations

import secrets
import shutil
import tempfile
import threading
import time
import traceback
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..ingest.fonts import default_font_path
from ..params import PRESET_PARAMS, SignParams
from ..verify import BuildError

app = FastAPI(title="LED Sign Builder")

STATIC = Path(__file__).parent / "static"
WORK = Path(tempfile.mkdtemp(prefix="signforge-web-"))
UPLOADS: "OrderedDict[str, Path]" = OrderedDict()
JOBS: "OrderedDict[str, dict]" = OrderedDict()
_pool = ThreadPoolExecutor(max_workers=2)
_lock = threading.Lock()

FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}
ART_EXT = {".svg", ".dxf", ".png", ".jpg", ".jpeg"}
FONT_CAP = 5 * 1024 * 1024
ART_CAP = 20 * 1024 * 1024

MAX_UPLOADS = 50           # stored upload files (oldest evicted)
MAX_JOBS_KEPT = 20         # finished jobs retained on disk (oldest evicted)
MAX_ACTIVE_JOBS = 4        # queued+running ceiling
RATE_WINDOW_S = 600.0
RATE_LIMITS = {"build": 12, "upload": 30}   # per IP per window
_rate: dict[tuple[str, str], deque] = {}


def _throttle(request: Request, kind: str) -> None:
    ip = request.client.host if request.client else "?"
    q = _rate.setdefault((kind, ip), deque())
    now = time.monotonic()
    while q and now - q[0] > RATE_WINDOW_S:
        q.popleft()
    if len(q) >= RATE_LIMITS[kind]:
        raise HTTPException(
            429, f"rate limit: {RATE_LIMITS[kind]} {kind}s per {RATE_WINDOW_S / 60:.0f} min"
        )
    q.append(now)


def _evict() -> None:
    """Bound disk usage: oldest uploads and finished job dirs go first."""
    with _lock:
        while len(UPLOADS) > MAX_UPLOADS:
            _tok, path = UPLOADS.popitem(last=False)
            path.unlink(missing_ok=True)
        finished = [k for k, j in JOBS.items() if j.get("status") in ("done", "error")]
        while len(finished) > MAX_JOBS_KEPT:
            k = finished.pop(0)
            job = JOBS.pop(k, None)
            if job and job.get("outdir"):
                shutil.rmtree(job["outdir"], ignore_errors=True)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text()


@app.get("/static/{name}")
def static_file(name: str):
    p = STATIC / Path(name).name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/presets")
def presets():
    return {
        "presets": PRESET_PARAMS,
        "defaults": SignParams().model_dump(),
        "printers": sorted(
            __import__("signforge.params", fromlist=["PRINTER_PRESETS"]).PRINTER_PRESETS
        ),
    }


@app.post("/api/upload")
async def upload(kind: str, file: UploadFile, request: Request):
    _throttle(request, "upload")
    ext = Path(file.filename or "").suffix.lower()
    if kind == "font" and ext not in FONT_EXT:
        raise HTTPException(400, f"font must be one of {sorted(FONT_EXT)}")
    if kind == "art" and ext not in ART_EXT:
        raise HTTPException(400, f"art must be one of {sorted(ART_EXT)}")
    data = await file.read()
    cap = FONT_CAP if kind == "font" else ART_CAP
    if len(data) > cap:
        raise HTTPException(413, f"{kind} exceeds {cap // 1024 // 1024} MB cap")
    if kind == "font":
        # reject broken fonts at the door, not at build time
        try:
            from ..ingest.fonts import load_font

            font = load_font(data)
            font.getBestCmap()
        except Exception:
            raise HTTPException(400, "could not parse that font file (TTF/OTF/WOFF/WOFF2)")
    if kind == "art" and ext in (".png", ".jpg", ".jpeg"):
        magic_ok = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
        if not magic_ok:
            raise HTTPException(400, "file does not look like a PNG/JPEG")
    token = f"{kind}-{secrets.token_hex(8)}"
    path = WORK / f"{token}{ext}"
    path.write_bytes(data)
    UPLOADS[token] = path
    _evict()
    return {"token": token, "filename": file.filename}


def _resolve_params(payload: dict) -> SignParams:
    raw = dict(payload.get("params") or {})
    content = dict(raw.get("content") or {})
    content.pop("font_path", None)      # tokens only — never client paths
    content.pop("art_path", None)
    ft = payload.get("font_token")
    at = payload.get("art_token")
    if ft:
        if ft not in UPLOADS:
            raise HTTPException(400, "unknown font token")
        content["font_path"] = str(UPLOADS[ft])
    else:
        content["font_path"] = default_font_path()
    if at:
        if at not in UPLOADS:
            raise HTTPException(400, "unknown art token")
        content["art_path"] = str(UPLOADS[at])
        content["mode"] = "art"
    raw["content"] = content
    try:
        return SignParams.model_validate(raw)
    except Exception as e:
        raise HTTPException(422, f"invalid params: {e}") from e


@app.post("/api/preview2d")
def preview2d(payload: dict):
    from ..pipeline import quick_plan
    from ..preview.html import render_preview

    params = _resolve_params(payload)
    try:
        layout, ledplan, pieces, warnings = quick_plan(params)
    except BuildError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    x0, y0, x1, y1 = layout.bbox
    stats = {
        "sign_mm": [round(x1 - x0, 1), round(y1 - y0, 1)],
        "bodies": {},
        "pixels": len(ledplan.pixels) if ledplan else 0,
        "pieces": len(pieces),
        "source": "",
        "pieces_detail": [],
    }
    html = render_preview(layout, pieces, ledplan, stats, params, body_notes=warnings)
    svg = html[html.index("<svg") : html.index("</svg>") + 6]
    return {
        "svg": svg,
        "sign_mm": stats["sign_mm"],
        "pixels": stats["pixels"],
        "pieces": stats["pieces"],
        "watts": round(ledplan.power.watts, 1) if ledplan else 0,
        "psu": ledplan.power.psu_watts if ledplan else 0,
        "warnings": warnings + (ledplan.audits if ledplan else []),
    }


def _run_job(job_id: str, params: SignParams) -> None:
    from ..pipeline import build

    job = JOBS[job_id]

    def progress(msg: str) -> None:
        job["progress"].append(msg)

    try:
        job["status"] = "running"
        outdir = WORK / job_id
        result = build(params, outdir, progress=progress)
        with _lock:
            job.update(
                status="done",
                stats=result.stats,
                warnings=result.warnings,
                outdir=str(outdir),
                zip=next((f for f in result.files if f.endswith(".zip")), None),
            )
    except BuildError as e:
        with _lock:
            job.update(status="error", error=str(e))
    except Exception as e:  # pragma: no cover - defensive
        with _lock:
            job.update(status="error", error=f"internal: {e}\n{traceback.format_exc()}")


@app.post("/api/build")
def start_build(payload: dict, request: Request):
    _throttle(request, "build")
    active = sum(1 for j in JOBS.values() if j.get("status") in ("queued", "running"))
    if active >= MAX_ACTIVE_JOBS:
        raise HTTPException(429, f"{active} builds already active — try again shortly")
    params = _resolve_params(payload)
    job_id = f"job-{secrets.token_hex(6)}"
    JOBS[job_id] = {"status": "queued", "progress": [], "name": params.name}
    _pool.submit(_run_job, job_id, params)
    _evict()
    return {"job": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404)
    return {k: v for k, v in job.items() if k != "outdir"}


def _job_file(job_id: str, rel: str) -> FileResponse:
    job = JOBS.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404)
    p = (Path(job["outdir"]) / rel).resolve()
    if not str(p).startswith(str(Path(job["outdir"]).resolve())) or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/jobs/{job_id}/download")
def job_download(job_id: str):
    job = JOBS.get(job_id)
    if not job or not job.get("zip"):
        raise HTTPException(404)
    return FileResponse(job["zip"], filename=Path(job["zip"]).name)


@app.get("/api/jobs/{job_id}/viewer")
def job_viewer(job_id: str):
    return _job_file(job_id, "preview/viewer.html")


@app.get("/api/jobs/{job_id}/preview")
def job_preview(job_id: str):
    return _job_file(job_id, "preview/index.html")
