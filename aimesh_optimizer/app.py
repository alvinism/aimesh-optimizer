import logging
from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from . import __version__
from .client import RouterCreds, RouterError, trigger_aimesh_optimize
from .config import Settings, get_settings
from .lock import CooldownActive, CooldownLock, InFlight

logger = logging.getLogger(__name__)


def _is_lan_source(host: str | None, settings: Settings) -> bool:
    if not host:
        return False
    try:
        addr = ip_address(host)
    except ValueError:
        return False
    return any(addr in net for net in settings.lan_cidrs)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    cooldown = CooldownLock(settings.cooldown_seconds)
    creds = RouterCreds(
        host=settings.asus_host,
        user=settings.asus_user,
        password=settings.asus_pass,
        use_ssl=settings.asus_use_ssl,
        verify_ssl=settings.asus_verify_ssl,
    )

    app = FastAPI(title="aimesh-optimizer", version=__version__)

    @app.middleware("http")
    async def lan_only(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        client_host = request.client.host if request.client else None
        if not _is_lan_source(client_host, settings):
            logger.warning("rejecting non-LAN request from %s %s", client_host, request.url.path)
            return JSONResponse(status_code=403, content={"status": "forbidden"})
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict:
        s = cooldown.state()
        return {
            "status": "ok",
            "version": __version__,
            "cooldown_remaining_seconds": round(s.cooldown_remaining_seconds, 1),
            "in_flight": s.in_flight,
        }

    async def _do_optimize() -> Response:
        try:
            async with cooldown.acquire():
                await trigger_aimesh_optimize(creds)
        except CooldownActive as exc:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "cooldown",
                    "retry_after_seconds": round(exc.retry_after_seconds, 1),
                },
                headers={"Retry-After": str(int(exc.retry_after_seconds) + 1)},
            )
        except InFlight:
            return JSONResponse(status_code=423, content={"status": "in_flight"})
        except RouterError as exc:
            logger.exception("router call failed")
            return JSONResponse(
                status_code=502,
                content={"status": "router_error", "message": str(exc)},
            )
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.get("/optimize")
    async def optimize_get() -> Response:
        return await _do_optimize()

    @app.post("/optimize")
    async def optimize_post() -> Response:
        return await _do_optimize()

    return app


app = create_app()
