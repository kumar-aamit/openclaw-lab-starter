import asyncio
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
from .llm import ModelError, complete_text
from .runner import RunError, RunResult, Runtime, load_runtime, run_screen
from .screens import ScreenError
from .status import ASKS, LOAD_PROMPT, LOAD_REQUESTS, Stats, chips, tiles

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

    def http_client() -> httpx.AsyncClient:
        if getattr(app.state, "http", None) is None:
            app.state.http = httpx.AsyncClient()
        return app.state.http

    stats = Stats()
    app.state.stats = stats
    indexes = rt.indexes if rt else {}

    def page_context(**extra) -> dict:
        screens = list(rt.screens.values()) if rt else []
        return {"spec": spec, "site": site, "config_error": config_error, "commit": settings.commit,
                "version": settings.version, "deployed": stats.deployed, "platform_version": __version__,
                "screens": screens, "lab_user": settings.lab_user, **extra}

    def status_page(request: Request):
        return templates.TemplateResponse(request, "status.html", page_context(
            on_status=True, tiles=tiles(settings, site, stats, indexes), asks=ASKS, load_requests=LOAD_REQUESTS))

    def screen_chips(screen):
        return chips(screen, settings, site, stats, indexes.get(screen.name) if screen.knowledge else None)

    async def model_checks() -> dict[str, CheckResult]:
        return {r.name: r for r in await run_checks(settings, http_client())}

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
        return {"commit": settings.commit, "version": settings.version, "platform": __version__,
                "app": spec.name, "config_error": config_error}

    @app.get("/api/checks")
    async def checks(request: Request):
        rows = [CheckResult("App", True, f"running {settings.commit[:7]}", None)]
        rows += await run_checks(settings, http_client())
        if request.headers.get("hx-request"):
            if request.query_params.get("view") == "dot":
                state = "fail" if any(r.ok is False for r in rows) else "ok"
                return HTMLResponse(f'<span class="dot dot-{state}" aria-hidden="true"></span>')
            return templates.TemplateResponse(request, "partials/checks.html", {"rows": rows})
        return [asdict(r) for r in rows]

    @app.get("/status/tiles", response_class=HTMLResponse)
    async def status_tiles(request: Request):
        return templates.TemplateResponse(request, "partials/tiles.html", {
            "tiles": tiles(settings, site, stats, indexes, await model_checks())})

    @app.post("/status/ask/{tier}", response_class=HTMLResponse)
    async def status_ask(request: Request, tier: str):
        if tier not in ASKS:
            raise HTTPException(status_code=404, detail=f"no model tier named {tier}")
        endpoint = settings.smart if tier == "smart" else settings.fast
        ctx = {"tier": tier, "endpoint": endpoint, "site": site, "mocked": settings.mock}
        if settings.mock:
            ctx.update(text=ASKS[tier]["mock"], ms=None, tokens=None)
        else:
            try:
                text, ms, tokens = await complete_text(
                    http_client(), endpoint, settings.api_key,
                    [{"role": "user", "content": ASKS[tier]["prompt"]}], tier=tier, max_tokens=160)
            except ModelError as exc:
                return templates.TemplateResponse(request, "partials/run_error.html", {"message": str(exc)})
            stats.tokens += tokens
            ctx.update(text=text, ms=ms, tokens=tokens)
        return templates.TemplateResponse(request, "partials/ask.html", ctx)

    @app.post("/status/load", response_class=HTMLResponse)
    async def status_load(request: Request):
        ctx = {"mocked": settings.mock, "endpoint": settings.fast, "n": LOAD_REQUESTS}
        if not settings.mock:
            async def one():
                return await complete_text(http_client(), settings.fast, settings.api_key,
                                           [{"role": "user", "content": LOAD_PROMPT}], tier="fast", max_tokens=8)
            results = await asyncio.gather(*(one() for _ in range(LOAD_REQUESTS)), return_exceptions=True)
            done = [r for r in results if not isinstance(r, BaseException)]
            errors = [str(r) for r in results if isinstance(r, ModelError)]
            if not done:
                return templates.TemplateResponse(request, "partials/run_error.html",
                                                  {"message": errors[0] if errors else "no request answered"})
            times = sorted(ms for _, ms, _ in done)
            stats.load_ms = times
            stats.tokens += sum(t for _, _, t in done)
            ctx.update(times=times, slowest=max(times), median=stats.load_median, failed=len(results) - len(done))
        return templates.TemplateResponse(request, "partials/load.html", ctx)

    @app.get("/api/screens")
    async def screens() -> list[dict]:
        return [{"name": s.name, "title": s.title, "examples": [e.label for e in s.examples]}
                for s in (rt.screens.values() if rt else [])]

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if rt and rt.screens:
            return RedirectResponse(f"/s/{next(iter(rt.screens))}", status_code=303)
        return status_page(request)

    @app.get("/status", response_class=HTMLResponse)
    async def status(request: Request):
        return status_page(request)

    @app.get("/s/{name}", response_class=HTMLResponse)
    async def screen_page(request: Request, name: str):
        screen = screen_or_404(name)
        return templates.TemplateResponse(request, f"layouts/{screen.layout}.html",
                                          page_context(screen=screen, current=name, chips=screen_chips(screen)))

    @app.post("/s/{name}/run", response_class=HTMLResponse)
    async def screen_run(request: Request, name: str):
        screen = screen_or_404(name)
        try:
            inputs, example = await form_inputs(request, screen)
            result = await run_screen(rt, screen, inputs, example, http_client())
        except RunError as exc:
            return templates.TemplateResponse(request, "partials/run_error.html", {"message": str(exc)})
        stats.record_run(name, result.total_ms, result.tokens)
        return templates.TemplateResponse(request, "partials/answer.html", {
            "screen": screen, "r": result, "site": site, "chips": screen_chips(screen),
            "cite": lambda ref: _source_label(result, ref)})

    @app.post("/api/screens/{name}/run")
    async def api_run(name: str, body: RunRequest):
        screen = screen_or_404(name)
        try:
            result = await run_screen(rt, screen, body.inputs, body.example, http_client())
        except RunError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        stats.record_run(name, result.total_ms, result.tokens)
        return {
            "answer": result.answer,
            "sources": [{"n": i, "source": p.source, "heading": p.heading} for i, p in enumerate(result.sources, 1)],
            "timings": {"total_ms": result.total_ms, "model_ms": result.model_ms},
            "model": result.model_name, "tier": result.tier, "mocked": result.mocked, "tokens": result.tokens,
        }

    return app


app = create_app(Settings.from_env())
