"""HTTP-layer tests using FastAPI's TestClient.

The router call is monkeypatched so these tests run without `asusrouter`
talking to a real device.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aimesh_optimizer import app as app_module
from aimesh_optimizer.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        asus_host="192.168.50.1",
        asus_user="admin",
        asus_pass="x",
        lan_cidrs="127.0.0.0/8",  # TestClient calls from 127.0.0.1
        cooldown_seconds=300,
    )


@pytest.fixture
def successful_router(monkeypatch):
    calls: list[None] = []

    async def fake_trigger(_creds):
        calls.append(None)

    monkeypatch.setattr(app_module, "trigger_aimesh_optimize", fake_trigger)
    return calls


@pytest.fixture
def failing_router(monkeypatch):
    async def fake_trigger(_creds):
        raise app_module.RouterError("boom")

    monkeypatch.setattr(app_module, "trigger_aimesh_optimize", fake_trigger)


def test_health_ok(settings, successful_router):
    client = TestClient(app_module.create_app(settings), client=("127.0.0.1", 0))
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["in_flight"] is False
    assert body["cooldown_remaining_seconds"] == 0.0


def test_optimize_get_succeeds(settings, successful_router):
    client = TestClient(app_module.create_app(settings), client=("127.0.0.1", 0))
    r = client.get("/optimize")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert len(successful_router) == 1


def test_optimize_post_succeeds(settings, successful_router):
    client = TestClient(app_module.create_app(settings), client=("127.0.0.1", 0))
    r = client.post("/optimize")
    assert r.status_code == 200
    assert len(successful_router) == 1


def test_cooldown_returns_429(settings, successful_router):
    client = TestClient(app_module.create_app(settings), client=("127.0.0.1", 0))
    assert client.get("/optimize").status_code == 200
    r = client.get("/optimize")
    assert r.status_code == 429
    body = r.json()
    assert body["status"] == "cooldown"
    assert body["retry_after_seconds"] > 0
    assert "Retry-After" in r.headers


def test_router_error_is_502_and_does_not_start_cooldown(settings, failing_router):
    client = TestClient(app_module.create_app(settings), client=("127.0.0.1", 0))
    r = client.get("/optimize")
    assert r.status_code == 502
    assert r.json()["status"] == "router_error"
    # Cooldown was not stamped — health says 0 remaining
    h = client.get("/health").json()
    assert h["cooldown_remaining_seconds"] == 0.0


def test_non_lan_source_is_403(successful_router):
    settings = Settings(
        asus_host="192.168.50.1",
        asus_user="admin",
        asus_pass="x",
        lan_cidrs="192.168.50.0/24",  # client below is on a different subnet
        cooldown_seconds=300,
    )
    client = TestClient(app_module.create_app(settings), client=("203.0.113.5", 0))
    r = client.get("/optimize")
    assert r.status_code == 403
    assert r.json()["status"] == "forbidden"


