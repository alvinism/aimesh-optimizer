# aimesh-optimizer

A tiny LAN-only HTTP service that triggers the **Asus AiMesh "优化 / Optimize"**
button programmatically. Designed for one-tap iOS Shortcuts on family members'
phones — they tap an icon when AirPlay misbehaves, the router rebuilds its
mesh topology, and Wi-Fi heals.

Built on [`asusrouter`](https://github.com/Vaskivskyi/asusrouter), FastAPI,
and uvicorn. Single endpoint, source-IP gated, debounced.

## What it does

`POST /optimize` (or `GET /optimize` for iOS Shortcuts) calls
`AsusSystem.AIMESH_REBUILD` on your router — the same `re_reconnect`
action the web UI fires. Concurrent requests get `423`; requests within the
cooldown window get `429`; non-LAN sources get `403`.

## Install on the Pi

```sh
git clone <this-repo> /opt/aimesh-optimizer
cd /opt/aimesh-optimizer
sudo bash deploy/install.sh
sudo -e /opt/aimesh-optimizer/.env       # set ASUS_PASS, optionally adjust LAN_CIDRS
sudo systemctl restart aimesh-optimizer
```

Verify:
```sh
curl -sf http://127.0.0.1:8080/health
curl -sf http://127.0.0.1:8080/optimize
journalctl -u aimesh-optimizer -f
```

## Update later

```sh
cd /opt/aimesh-optimizer
git pull
.venv/bin/pip install -e .
sudo systemctl restart aimesh-optimizer
```

## Configuration

All via environment variables (typically loaded from `.env`):

| Var | Default | Purpose |
|---|---|---|
| `ASUS_HOST` | `192.168.50.1` | Router admin address |
| `ASUS_USER` | `admin` | Router admin user |
| `ASUS_PASS` | *(required)* | Router admin password |
| `ASUS_USE_SSL` | `true` | Use HTTPS to admin UI |
| `ASUS_VERIFY_SSL` | `false` | Verify the router's self-signed cert |
| `LAN_CIDRS` | `192.168.50.0/24` | Comma-separated CIDRs allowed to call the API |
| `COOLDOWN_SECONDS` | `300` | Seconds to lock out after a successful trigger |
| `LISTEN_HOST` | `0.0.0.0` | HTTP bind address |
| `LISTEN_PORT` | `8080` | HTTP bind port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Endpoints

### `GET|POST /optimize`

| Status | Meaning |
|---|---|
| `200` | Triggered. Body: `{"status":"ok","triggered_at":"<ISO8601>"}` |
| `429` | Cooldown active. Body has `retry_after_seconds`; also sent as `Retry-After` header |
| `423` | Another optimize is currently in flight |
| `403` | Caller IP is not in `LAN_CIDRS` |
| `502` | Router error (auth fail, unreachable, etc). Cooldown is NOT updated |

### `GET /health`
Returns `{"status":"ok","version":"...","cooldown_remaining_seconds":N,"in_flight":bool}`.

## iOS Shortcut for parents

1. Shortcuts app → **+** new shortcut.
2. Action: **Get Contents of URL** → `http://192.168.50.222:8080/optimize`
   (replace with your Pi's LAN IP).
3. Action: **Show Notification** → set body to "Wi-Fi 已修复 / Wi-Fi fixed".
4. Tap shortcut name → **Add to Home Screen** with a friendly icon.

If the shortcut is tapped within the cooldown window the response body says
`"cooldown"` — the notification will surface that, telling them to wait.

## Development

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Run locally:
```sh
cp .env.example .env  # edit
python -m aimesh_optimizer
```

## Security notes

- LAN-only by source IP. There is **no auth token**; the assumption is your
  LAN is trusted. If you ever expose this via tailscale, add tailscale's
  `100.64.0.0/10` to `LAN_CIDRS` and consider adding a bearer token.
- `.env` is gitignored and is `chmod 600` after `install.sh`. Don't commit it.
- The systemd unit runs as the unprivileged user that ran `install.sh`,
  with `ProtectSystem=strict`, `NoNewPrivileges=true`, `ProtectHome=true`,
  `PrivateTmp=true`, and a narrow `RestrictAddressFamilies` allow-list.

## License

MIT.
