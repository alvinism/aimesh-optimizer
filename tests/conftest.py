"""Stub `asusrouter` for tests so the suite runs without the real library installed.

Only kicks in when `asusrouter` is not already importable; in a venv where
`pip install -e .` has installed the real library, this is a no-op.
"""

from __future__ import annotations

import sys
import types
from importlib.util import find_spec


def _install_asusrouter_stub() -> None:
    if find_spec("asusrouter") is not None:
        # Real library is installed — let imports go through it.
        return

    asusrouter = types.ModuleType("asusrouter")
    connection_config = types.ModuleType("asusrouter.connection_config")
    modules_pkg = types.ModuleType("asusrouter.modules")
    system = types.ModuleType("asusrouter.modules.system")

    class _AsusRouter:
        def __init__(self, **_): ...

        async def async_connect(self): ...

        async def async_run_service(self, *_, **__): ...

        async def async_set_state(self, *_, **__): ...

        async def async_disconnect(self): ...

        async def async_del_connection(self): ...

    class _ARConnectionConfigKey:
        VERIFY_SSL = "verify_ssl"

    class _AsusSystem:
        AIMESH_REBUILD = "re_reconnect"

    asusrouter.AsusRouter = _AsusRouter
    connection_config.ARConnectionConfigKey = _ARConnectionConfigKey
    system.AsusSystem = _AsusSystem
    asusrouter.connection_config = connection_config
    asusrouter.modules = modules_pkg
    modules_pkg.system = system

    sys.modules["asusrouter"] = asusrouter
    sys.modules["asusrouter.connection_config"] = connection_config
    sys.modules["asusrouter.modules"] = modules_pkg
    sys.modules["asusrouter.modules.system"] = system


_install_asusrouter_stub()
