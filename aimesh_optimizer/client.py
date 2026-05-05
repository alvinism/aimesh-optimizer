import logging
from dataclasses import dataclass

from asusrouter import AsusRouter
from asusrouter.connection_config import ARConnectionConfigKey
from asusrouter.modules.system import AsusSystem

logger = logging.getLogger(__name__)


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
        logger.info("connected to router %s; firing AIMESH_REBUILD", creds.host)
        await router.async_run_service(AsusSystem.AIMESH_REBUILD)
        logger.info("AIMESH_REBUILD dispatched")
    except Exception as exc:  # noqa: BLE001 — we want to wrap any underlying error
        raise RouterError(str(exc)) from exc
    finally:
        try:
            await router.async_disconnect()
        except Exception:  # noqa: BLE001
            logger.warning("router disconnect raised; ignoring", exc_info=True)
