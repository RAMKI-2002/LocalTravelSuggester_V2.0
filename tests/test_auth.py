"""Tests for authentication endpoints: register, login, me."""

from __future__ import annotations


def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_register_duplicate_email_returns_409(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "password123"}
    resp1 = client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    # Second registration with same email — different username
    resp2 = client.post("/auth/register", json={
        "username": "bob2",
        "email": "bob@example.com",
        "password": "password123",
    })
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_register_duplicate_username_returns_409(client):
    client.post("/auth/register", json={
        "username": "charlie", "email": "charlie@example.com", "password": "password123"
    })
    resp = client.post("/auth/register", json={
        "username": "charlie", "email": "charlie2@example.com", "password": "password123"
    })
    assert resp.status_code == 409


def test_register_short_password_returns_422(client):
    resp = client.post("/auth/register", json={
        "username": "dave", "email": "dave@example.com", "password": "short",
    })
    assert resp.status_code == 422


def test_register_invalid_email_returns_422(client):
    resp = client.post("/auth/register", json={
        "username": "eve", "email": "not-an-email", "password": "password123",
    })
    assert resp.status_code == 422


def test_login_success(client, registered_user):
    resp = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client, registered_user):
    resp = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


def test_login_unknown_email_returns_401(client):
    resp = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert resp.status_code == 401


def test_me_with_valid_token_returns_user(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # never expose password hash


def test_me_without_token_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
