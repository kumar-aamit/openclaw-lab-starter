import logging
import re
from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from pydantic import BaseModel
from starlette.datastructures import UploadFile

from . import __version__
from .appspec import ICON_DIR, AppSpec, AppSpecError, load_app_spec
from .config import Settings
from .files import extract_text
from .health import CheckResult, run_checks
from .hookrunner import HookError
from .runner import RunError, RunResult, Runtime, load_runtime, run_screen
from .screens import ScreenError
from .start import bold, preview, steps_done, use_cases

HERE = Path(__file__).parent
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
log = logging.getLogger("baseapp")


@lru_cache(maxsize=None)
def _icon_svg(name: str) -> str:
    svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    return re.sub(r'class="[^"]*"', 'class="icon" aria-hidden="true"', svg, count=1)


def icon(name: str) -> Markup:
    return Markup(_icon_svg(name))


class RunRequest(BaseModel):
    inputs: dict[str, str] = {}
    example: int | None = None


def _load(settings: Settings) -> tuple[AppSpec, Runtime | None, str | None]:
    try:
        rt = load_runtime(settings)
        return rt.spec, rt, None
    except (AppSpecError, ScreenError, HookError) as exc:
        log.error("%s", exc)
        try:
            spec = load_app_spec(settings.app_dir)
        except AppSpecError:
            spec = AppSpec()
        return AppSpec(name=spec.name, mark=spec.mark, brand=spec.brand, site=spec.site), None, str(exc)


def _source_label(result: RunResult, ref: str) -> str | None:
    match = re.search(r"\d+", ref or "")
    if not match or not 1 <= int(match.group()) <= len(result.sources):
        return None
    p = result.sources[int(match.group()) - 1]
    return f"{p.source} › {p.heading}" if p.heading else p.source


def create_app(settings: Settings) -> FastAPI:
    spec, rt, config_error = _load(settings)
    site = spec.site or settings.site_name

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        client = getattr(app.state, "http", None)
        if client is not None:
            await client.aclose()

    app = FastAPI(title=spec.name, version=__version__, docs_url=None, redoc_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.globals["icon"] = icon
    templates.env.filters["bold"] = bold

    def http_client() -> httpx.AsyncClient:
        if getattr(app.state, "http", None) is None:
            app.state.http = httpx.AsyncClient()
        return app.state.http

    def page_context(**extra) -> dict:
        screens = list(rt.screens.values()) if rt else []
        return {"spec": spec, "site": site, "config_error": config_error, "commit": settings.commit,
                "platform_version": __version__, "screens": screens, "lab_user": settings.lab_user, **extra}

    def start_page(request: Request, case_id: str = "", step: str = ""):
        cases = use_cases()
        case = next((c for c in cases if c.id == case_id), cases[0])
        done = steps_done(case, list(rt.screens.values()) if rt else [])
        last = len(case.steps) - 1
        view = int(step) - 1 if step.isdigit() and 1 <= int(step) <= last + 1 else min(done, last)
        return templates.TemplateResponse(request, "start.html", page_context(
            cases=cases, case=case, done=done, view=view, step=case.steps[view],
            blocks=preview(case, view)))

    def screen_or_404(name: str):
        if rt is None or name not in rt.screens:
            raise HTTPException(status_code=404, detail=f"no screen named {name}")
        return rt.screens[name]

    async def form_inputs(request: Request, screen) -> tuple[dict[str, str], int | None]:
        form = await request.form()
        inputs = {}
        for field in screen.inputs:
            value = form.get(field.name)
            if isinstance(value, UploadFile):
                data = await value.read(MAX_UPLOAD_BYTES + 1)
                if not data:
                    continue
                if len(data) > MAX_UPLOAD_BYTES:
                    raise RunError(f"{field.label}: the file is larger than 2 MB")
                try:
                    inputs[field.name] = extract_text(value.filename or "upload.txt", data)
                except ValueError as exc:
                    raise RunError(f"{field.label}: {exc}") from None
            elif value is not None:
                inputs[field.name] = str(value)
        example = form.get("example")
        return inputs, (int(example) if isinstance(example, str) and example.isdigit() else None)

    @app.get("/health")
    @app.get("/healthz")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/version")
    async def version() -> dict:
        return {"commit": settings.commit, "platform": __version__, "app": spec.name, "config_error": config_error}

    @app.get("/api/checks")
    async def checks(request: Request):
        rows = [CheckResult("App", True, f"running {settings.commit[:7]}", None)]
        rows += await run_checks(settings, http_client())
        if request.headers.get("hx-request"):
            partial = "status" if request.query_params.get("view") == "status" else "checks"
            return templates.TemplateResponse(request, f"partials/{partial}.html", {"rows": rows})
        return [asdict(r) for r in rows]

    @app.get("/api/screens")
    async def screens() -> list[dict]:
        return [{"name": s.name, "title": s.title, "examples": [e.label for e in s.examples]}
                for s in (rt.screens.values() if rt else [])]

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if rt and rt.screens:
            return RedirectResponse(f"/s/{next(iter(rt.screens))}", status_code=303)
        return start_page(request)

    @app.get("/start", response_class=HTMLResponse)
    async def start(request: Request, case: str = "", step: str = ""):
        return start_page(request, case, step)

    @app.get("/s/{name}", response_class=HTMLResponse)
    async def screen_page(request: Request, name: str):
        screen = screen_or_404(name)
        return templates.TemplateResponse(request, f"layouts/{screen.layout}.html",
                                          page_context(screen=screen, current=name))

    @app.post("/s/{name}/run", response_class=HTMLResponse)
    async def screen_run(request: Request, name: str):
        screen = screen_or_404(name)
        try:
            inputs, example = await form_inputs(request, screen)
            result = await run_screen(rt, screen, inputs, example, http_client())
        except RunError as exc:
            return templates.TemplateResponse(request, "partials/run_error.html", {"message": str(exc)})
        return templates.TemplateResponse(request, "partials/answer.html", {
            "screen": screen, "r": result, "site": site,
            "cite": lambda ref: _source_label(result, ref)})

    @app.post("/api/screens/{name}/run")
    async def api_run(name: str, body: RunRequest):
        screen = screen_or_404(name)
        try:
            result = await run_screen(rt, screen, body.inputs, body.example, http_client())
        except RunError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        return {
            "answer": result.answer,
            "sources": [{"n": i, "source": p.source, "heading": p.heading} for i, p in enumerate(result.sources, 1)],
            "timings": {"total_ms": result.total_ms, "model_ms": result.model_ms},
            "model": result.model_name, "tier": result.tier, "mocked": result.mocked,
        }

    return app


app = create_app(Settings.from_env())
