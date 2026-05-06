import logging
from dataclasses import dataclass

from asusrouter import AsusRouter
from asusrouter.connection_config import ARConnectionConfigKey

logger = logging.getLogger(__name__)

# The web UI's "Optimize / 优化" button on the AiMesh topology page sends:
#     POST /applyapp.cgi
#     body: action_mode=re_reconnect
# This goes through httpd's action_mode dispatcher, which iterates AiMesh
# nodes and tears down their WDS backhauls — the actual mesh rebuild.
#
# AsusSystem.AIMESH_REBUILD has the same string value ("re_reconnect"), BUT
# the library's set_state/run_service helpers wrap it as
#     POST /apply.cgi  body: action_mode=apply&rc_service=re_reconnect
# That hits a *different* httpd code path: notify_rc re_reconnect → client
# roaming only, no WDS tear-down. To match the button we have to bypass the
# enum and call run_service with service=None + the action_mode argument,
# which is the same shape the library uses for AIMESH_REBOOT.
_OPTIMIZE_ACTION = {"action_mode": "re_reconnect"}


@dataclass(frozen=True)
class RouterCreds:
    host: str
    user: str
    password: str
    use_ssl: bool = True
    verify_ssl: bool = False


class RouterError(Exception):
    """Wraps any error from the underlying asusrouter client."""


async def trigger_aimesh_optimize(creds: RouterCreds) -> None:
    """Connect to the router, fire AiMesh optimize, disconnect.

    A fresh client per call is intentional: cheap, avoids stale-session bugs,
    and the operation is rare enough that the connect overhead doesn't matter.
    """
    router = AsusRouter(
        hostname=creds.host,
        username=creds.user,
        password=creds.password,
        use_ssl=creds.use_ssl,
        connection_config={ARConnectionConfigKey.VERIFY_SSL: creds.verify_ssl},
    )
    try:
        await router.async_connect()
        logger.info("connected to router %s; firing AiMesh global optimize", creds.host)
        await router.async_run_service(
            service=None,
            arguments=_OPTIMIZE_ACTION,
            apply=False,
            expect_modify=False,
        )
        logger.info("AiMesh optimize dispatched (action_mode=re_reconnect)")
    except Exception as exc:  # noqa: BLE001 — we want to wrap any underlying error
        raise RouterError(str(exc)) from exc
    finally:
        try:
            # async_del_connection logs out AND closes the underlying aiohttp
            # session; async_disconnect alone leaves the ClientSession dangling
            # which triggers asyncio's "Unclosed client session" warning.
            await router.async_del_connection()
        except Exception:  # noqa: BLE001
            logger.warning("router cleanup raised; ignoring", exc_info=True)
