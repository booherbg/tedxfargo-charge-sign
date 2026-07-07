"""Local web app. Self-host trust model with real accounts on top:

- accounts mode (default): register/login, sessions, free/premium tiers with
  size + daily-build + queue-depth enforcement, admin management, priority
  queue (premium first).
- open mode (--open / SIGNFORGE_OPEN=1): no auth, no tiers — solo self-host.

Uploads stay token-scoped (client paths ignored), rate-limited, validated at
the door. Not hardened multi-tenant hosting; guardrails for a shared box.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
import time
from collections import OrderedDict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..ingest.fonts import default_font_path
from ..params import PALETTES, PRESET_PARAMS, PRINTER_PRESETS, SignParams
from ..plaques import SHAPES
from ..verify import BuildError
from .jobqueue import JobQueue
from .users import OPEN_USER, TIERS, UserStore

STATIC = Path(__file__).parent / "static"

FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}
ART_EXT = {".svg", ".dxf", ".png", ".jpg", ".jpeg"}
FONT_CAP = 5 * 1024 * 1024
ART_CAP = 20 * 1024 * 1024
MAX_UPLOADS = 50
RATE_WINDOW_S = 600.0
RATE_LIMITS = {"build": 12, "upload": 30, "auth": 20}
COOKIE = "sf_session"


def create_app(
    open_mode: bool | None = None,
    db_path: str | None = None,
    workdir: str | None = None,
    workers: int = 2,
) -> FastAPI:
    app = FastAPI(title="LED Sign Builder")
    if open_mode is None:
        open_mode = os.environ.get("SIGNFORGE_OPEN", "0") == "1"
    work = Path(workdir or tempfile.mkdtemp(prefix="signforge-web-"))
    work.mkdir(parents=True, exist_ok=True)
    store = UserStore(db_path)
    admin_pw = None if open_mode else store.ensure_admin()
    if admin_pw:
        print(f"\n  ▚ first run: admin account 'admin@local' password: {admin_pw}\n")

    def on_job_change(job: dict) -> None:
        store.log_job(job["id"], job["user_id"], job["name"], job["status"],
                      job["params"].to_json() if hasattr(job["params"], "to_json") else "{}")

    queue = JobQueue(work, workers=workers, on_change=on_job_change)
    uploads: OrderedDict[str, Path] = OrderedDict()
    rate: dict[tuple[str, str], deque] = {}

    app.state.open_mode = open_mode
    app.state.store = store
    app.state.queue = queue

    # ---- plumbing -----------------------------------------------------------
    def throttle(request: Request, kind: str) -> None:
        ip = request.client.host if request.client else "?"
        q = rate.setdefault((kind, ip), deque())
        now = time.monotonic()
        while q and now - q[0] > RATE_WINDOW_S:
            q.popleft()
        if len(q) >= RATE_LIMITS[kind]:
            raise HTTPException(429, f"rate limit: {RATE_LIMITS[kind]} {kind}s per 10 min")
        q.append(now)

    def current_user(request: Request) -> dict | None:
        if open_mode:
            return dict(OPEN_USER)
        return store.get_session(request.cookies.get(COOKIE, ""))

    def require_user(request: Request) -> dict:
        user = current_user(request)
        if not user:
            raise HTTPException(401, "sign in required")
        return user

    def require_admin(request: Request) -> dict:
        user = require_user(request)
        if user.get("role") != "admin":
            raise HTTPException(403, "admin only")
        return user

    def evict_uploads() -> None:
        while len(uploads) > MAX_UPLOADS:
            _tok, p = uploads.popitem(last=False)
            p.unlink(missing_ok=True)

    # ---- static -------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (STATIC / "index.html").read_text()

    @app.get("/static/{name}")
    def static_file(name: str):
        p = STATIC / Path(name).name
        if not p.exists():
            raise HTTPException(404)
        return FileResponse(p)

    @app.get("/static/fonts/{name}")
    def static_font(name: str):
        p = Path(default_font_path()).parent / Path(name).name
        if not p.exists():
            raise HTTPException(404)
        return FileResponse(p)

    # ---- design library (bundled example artworks) ---------------------------
    def _library_dir() -> Path:
        from importlib import resources

        return Path(str(resources.files("signforge") / "assets" / "art"))

    @app.get("/api/library")
    def library():
        d = _library_dir()
        names = sorted(p.stem for p in d.glob("*.svg"))
        return {"art": [{"name": n, "url": f"/api/library/{n}.svg"} for n in names]}

    @app.get("/api/library/{name}")
    def library_file(name: str):
        p = _library_dir() / Path(name).name
        if p.suffix != ".svg" or not p.exists():
            raise HTTPException(404)
        return FileResponse(p, media_type="image/svg+xml")

    # ---- meta ---------------------------------------------------------------
    @app.get("/api/presets")
    def presets(request: Request):
        user = current_user(request)
        return {
            "presets": PRESET_PARAMS,
            "defaults": SignParams().model_dump(),
            "printers": {k: v for k, v in PRINTER_PRESETS.items()},
            "palettes": PALETTES,
            "plaques": list(SHAPES),
            "tiers": TIERS,
            "open_mode": open_mode,
            "user": {k: user[k] for k in ("email", "role", "tier")} if user else None,
        }

    # ---- auth ---------------------------------------------------------------
    @app.post("/api/auth/register")
    def register(payload: dict, request: Request, response: Response):
        throttle(request, "auth")
        if open_mode:
            raise HTTPException(400, "open mode: accounts are disabled")
        try:
            user = store.create_user(str(payload.get("email", "")), str(payload.get("password", "")))
        except ValueError as e:
            raise HTTPException(400, str(e))
        token = store.create_session(user["id"])
        response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
        return {"user": {k: user[k] for k in ("email", "role", "tier")}}

    @app.post("/api/auth/login")
    def login(payload: dict, request: Request, response: Response):
        throttle(request, "auth")
        if open_mode:
            raise HTTPException(400, "open mode: accounts are disabled")
        user = store.verify(str(payload.get("email", "")), str(payload.get("password", "")))
        if not user:
            raise HTTPException(401, "wrong email or password")
        token = store.create_session(user["id"])
        response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
        return {"user": {k: user[k] for k in ("email", "role", "tier")}}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response):
        store.delete_session(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(request: Request):
        user = current_user(request)
        if not user:
            return {"user": None, "open_mode": open_mode}
        limits = store.limits_for(user)
        return {
            "user": {k: user[k] for k in ("email", "role", "tier")},
            "limits": limits,
            "builds_today": store.builds_today(user["id"]) if user["id"] else 0,
            "open_mode": open_mode,
        }

    # ---- admin ---------------------------------------------------------------
    @app.get("/api/admin/users")
    def admin_users(user: dict = Depends(require_admin)):
        return {"users": store.list_users()}

    @app.post("/api/admin/users/{uid}")
    def admin_update(uid: int, payload: dict, user: dict = Depends(require_admin)):
        try:
            store.update_user(uid, tier=payload.get("tier"), role=payload.get("role"))
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"ok": True}

    @app.delete("/api/admin/users/{uid}")
    def admin_delete(uid: int, user: dict = Depends(require_admin)):
        if uid == user["id"]:
            raise HTTPException(400, "refusing to delete yourself")
        store.delete_user(uid)
        return {"ok": True}

    # ---- uploads --------------------------------------------------------------
    @app.post("/api/upload")
    async def upload(kind: str, file: UploadFile, request: Request,
                     user: dict = Depends(require_user)):
        throttle(request, "upload")
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
            try:
                from ..ingest.fonts import load_font

                load_font(data).getBestCmap()
            except Exception:
                raise HTTPException(400, "could not parse that font file (TTF/OTF/WOFF/WOFF2)")
        if kind == "art" and ext in (".png", ".jpg", ".jpeg"):
            if not (data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"):
                raise HTTPException(400, "file does not look like a PNG/JPEG")
        token = f"{kind}-{secrets.token_hex(8)}"
        path = work / f"{token}{ext}"
        path.write_bytes(data)
        uploads[token] = path
        evict_uploads()
        return {"token": token, "filename": file.filename}

    # ---- params + preview ------------------------------------------------------
    def resolve_params(payload: dict) -> SignParams:
        raw = dict(payload.get("params") or {})
        content = dict(raw.get("content") or {})
        content.pop("font_path", None)
        content.pop("art_path", None)
        ft, at = payload.get("font_token"), payload.get("art_token")
        lib = payload.get("library")
        if ft:
            if ft not in uploads:
                raise HTTPException(400, "unknown font token")
            content["font_path"] = str(uploads[ft])
        else:
            content["font_path"] = default_font_path()
        if at:
            if at not in uploads:
                raise HTTPException(400, "unknown art token")
            content["art_path"] = str(uploads[at])
            content["mode"] = "art"
        elif lib:
            p = _library_dir() / f"{Path(str(lib)).name}.svg"
            if not p.exists():
                raise HTTPException(400, "unknown library design")
            content["art_path"] = str(p)
            content["mode"] = "art"
        raw["content"] = content
        try:
            return SignParams.model_validate(raw)
        except Exception as e:
            raise HTTPException(422, f"invalid params: {e}")

    @app.post("/api/preview2d")
    def preview2d(payload: dict, request: Request, user: dict = Depends(require_user)):
        from ..pipeline import quick_plan
        from ..preview.html import render_preview

        params = resolve_params(payload)
        try:
            layout, ledplan, pieces, warnings = quick_plan(params)
        except BuildError as e:
            return JSONResponse({"error": str(e)}, status_code=422)
        x0, y0, x1, y1 = layout.bbox
        stats = {"sign_mm": [round(x1 - x0, 1), round(y1 - y0, 1)], "bodies": {},
                 "pixels": len(ledplan.pixels) if ledplan else 0, "pieces": len(pieces),
                 "pieces_detail": [], "source": ""}
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

    # ---- build queue ------------------------------------------------------------
    @app.post("/api/build")
    def start_build(payload: dict, request: Request, user: dict = Depends(require_user)):
        throttle(request, "build")
        params = resolve_params(payload)
        limits = store.limits_for(user)
        size = (
            params.content.art_target_height_mm
            if params.content.mode == "art"
            else params.content.cap_height_mm
        )
        if size > limits["max_cap_mm"]:
            raise HTTPException(
                403,
                f"{user.get('tier', 'free')} tier caps signs at {limits['max_cap_mm']:.0f} mm "
                f"(asked for {size:.0f}) — ask an admin for premium",
            )
        if user["id"] and store.builds_today(user["id"]) >= limits["builds_per_day"]:
            raise HTTPException(429, f"daily build quota reached ({limits['builds_per_day']})")
        if queue.active_count(user["id"]) >= limits["max_queued"]:
            raise HTTPException(429, f"you already have {limits['max_queued']} build(s) queued/running")
        job_id = f"job-{secrets.token_hex(6)}"
        queue.submit(job_id, params, user, limits["priority"])
        if user["id"]:
            store.record_build(user["id"])
        store.log_job(job_id, user["id"], params.name, "queued", params.to_json())
        return {"job": job_id, "position": queue.position(job_id)}

    def job_or_404(job_id: str, user: dict) -> dict:
        job = queue.jobs.get(job_id)
        if not job:
            raise HTTPException(404)
        if user.get("role") != "admin" and job["user_id"] != user["id"]:
            raise HTTPException(403, "not your build")
        return job

    @app.get("/api/jobs")
    def jobs_list(user: dict = Depends(require_user)):
        js = [
            queue.public(j)
            for j in queue.jobs.values()
            if user.get("role") == "admin" or j["user_id"] == user["id"]
        ]
        return {"jobs": js[-40:]}

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str, user: dict = Depends(require_user)):
        return queue.public(job_or_404(job_id, user))

    @app.delete("/api/jobs/{job_id}")
    def job_cancel(job_id: str, user: dict = Depends(require_user)):
        job_or_404(job_id, user)
        return {"cancelled": queue.cancel(job_id)}

    def job_file(job_id: str, rel: str, user: dict) -> FileResponse:
        job = job_or_404(job_id, user)
        if job.get("status") != "done" or not job.get("outdir"):
            raise HTTPException(404)
        p = (Path(job["outdir"]) / rel).resolve()
        if not str(p).startswith(str(Path(job["outdir"]).resolve())) or not p.exists():
            raise HTTPException(404)
        return FileResponse(p)

    @app.get("/api/jobs/{job_id}/download")
    def job_download(job_id: str, user: dict = Depends(require_user)):
        job = job_or_404(job_id, user)
        if not job.get("zip"):
            raise HTTPException(404)
        return FileResponse(job["zip"], filename=Path(job["zip"]).name)

    @app.get("/api/jobs/{job_id}/viewer")
    def job_viewer(job_id: str, user: dict = Depends(require_user)):
        return job_file(job_id, "preview/viewer.html", user)

    @app.get("/api/jobs/{job_id}/preview")
    def job_preview(job_id: str, user: dict = Depends(require_user)):
        return job_file(job_id, "preview/index.html", user)

    @app.get("/api/jobs/{job_id}/thumb.png")
    def job_thumb(job_id: str, user: dict = Depends(require_user)):
        return job_file(job_id, "preview/preview.png", user)

    return app
