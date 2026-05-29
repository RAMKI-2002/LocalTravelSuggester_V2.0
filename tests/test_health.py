"""Tests for health endpoints."""

from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_health_detailed_returns_200(client):
    resp = client.get("/health/detailed")
    assert resp.status_code == 200


def test_health_detailed_has_required_structure(client):
    resp = client.get("/health/detailed")
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "elapsed_ms" in data
    assert "config" in data
    assert "stats" in data


def test_health_detailed_checks_database(client):
    resp = client.get("/health/detailed")
    data = resp.json()
    assert "database" in data["checks"]
    assert data["checks"]["database"]["status"] == "ok"


def test_health_detailed_checks_llm(client):
    resp = client.get("/health/detailed")
    data = resp.json()
    assert "llm" in data["checks"]
    # In test mode LLM_MOCK=true, so it should be ok with a mock note
    assert data["checks"]["llm"]["status"] == "ok"


def test_health_detailed_config_shows_mock(client):
    resp = client.get("/health/detailed")
    data = resp.json()
    assert data["config"]["llm_mock"] is True


def test_api_root_returns_version(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "docs" in data
