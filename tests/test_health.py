from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    # Force in-memory DB and dry-run defaults before importing the app
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["DRY_RUN"] = "true"
    os.environ["TRADING_ENABLED"] = "false"
    os.environ.pop("OANDA_API_KEY", None)
    os.environ.pop("OANDA_ACCOUNT_ID", None)

    # Reset settings singleton so env overrides above take effect
    import app.config as cfg
    cfg._settings = None

    from app.main import create_app
    application = create_app()
    with TestClient(application, raise_server_exceptions=True) as c:
        yield c

    # Cleanup
    cfg._settings = None


def test_health_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_payload(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["dry_run"] is True
    assert data["trading_enabled"] is False
    assert "timestamp" in data
    assert data["version"] == "0.1.0"


def test_state_200(client: TestClient) -> None:
    resp = client.get("/state")
    assert resp.status_code == 200


def test_state_flags(client: TestClient) -> None:
    data = client.get("/state").json()
    assert data["dry_run"] is True
    assert data["trading_enabled"] is False
    assert data["worker_status"] in ("RUNNING", "PAUSED", "STOPPED")


def test_trades_empty(client: TestClient) -> None:
    resp = client.get("/trades")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trades"] == []
    assert data["count"] == 0


def test_control_pause(client: TestClient) -> None:
    resp = client.post("/control/pause")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["worker_status"] == "PAUSED"


def test_control_resume(client: TestClient) -> None:
    client.post("/control/pause")
    resp = client.post("/control/resume")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["worker_status"] == "RUNNING"
