"""Stub `asusrouter` for tests so the suite runs without the real library installed."""

from __future__ import annotations

import sys
import types


def _install_asusrouter_stub() -> None:
    if "asusrouter" in sys.modules:
        return
    stub = types.ModuleType("asusrouter")

    class _AsusRouter:
        def __init__(self, **_): ...

        async def async_connect(self): ...

        async def async_run_service(self, *_): ...

        async def async_disconnect(self): ...

    class _AsusSystem:
        AIMESH_REBUILD = "re_reconnect"

    stub.AsusRouter = _AsusRouter
    stub.AsusSystem = _AsusSystem
    sys.modules["asusrouter"] = stub


_install_asusrouter_stub()
