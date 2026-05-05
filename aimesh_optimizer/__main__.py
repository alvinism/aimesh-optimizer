import logging

import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(
        "aimesh_optimizer.app:app",
        host=settings.listen_host,
        port=settings.listen_port,
        log_level=settings.log_level.lower(),
        access_log=True,
        # We're not behind a reverse proxy; never trust X-Forwarded-For,
        # otherwise a LAN client could spoof its source IP and bypass the
        # LAN_CIDRS middleware check.
        proxy_headers=False,
        forwarded_allow_ips=[],
    )


if __name__ == "__main__":
    main()
