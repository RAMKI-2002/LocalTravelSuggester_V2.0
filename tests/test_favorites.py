"""Tests for user favorites endpoints."""

from __future__ import annotations

import pytest

SAMPLE_PLACE = {
    "name": "Hussain Sagar Lake",
    "description": "A large heart-shaped lake.",
    "categories": ["lake", "park"],
    "reasoning": "Perfect for a peaceful evening.",
    "coords": {"lat": 17.42, "lng": 78.47},
    "distance_km": 12.3,
    "score": 0.82,
    "website": None,
    "address": "Hyderabad, India",
}

SAMPLE_PLACE_2 = {
    **SAMPLE_PLACE,
    "name": "Charminar",
    "coords": {"lat": 17.36, "lng": 78.47},
    "reasoning": "Historic monument worth visiting.",
}

OTHER_PLACE = {
    **SAMPLE_PLACE,
    "name": "Golconda Fort",
    "coords": {"lat": 17.38, "lng": 78.40},
}


def _favorite_payload(place: dict | None = None, city: str = "Hyderabad") -> dict:
    return {"place": place if place is not None else SAMPLE_PLACE, "city": city}


def _register_second_user(client) -> dict:
    client.post(
        "/auth/register",
        json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "user2@example.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_favorite(client, headers, place: dict | None = None, city: str = "Hyderabad") -> dict:
    resp = client.post("/favorites", json=_favorite_payload(place, city), headers=headers)
    assert resp.status_code == 201, resp.json()
    return resp.json()


# --- Auth (401) ---


def test_post_favorite_without_auth_returns_401(client):
    resp = client.post("/favorites", json=_favorite_payload())
    assert resp.status_code == 401


def test_get_favorites_without_auth_returns_401(client):
    resp = client.get("/favorites")
    assert resp.status_code == 401


def test_delete_favorite_without_auth_returns_401(client):
    resp = client.delete("/favorites/1")
    assert resp.status_code == 401


# --- POST happy path / validation ---


def test_post_favorite_saves_and_returns_201(client, auth_headers):
    resp = client.post("/favorites", json=_favorite_payload(), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    for key in (
        "id",
        "place_name",
        "city",
        "lat",
        "lng",
        "categories",
        "reasoning",
        "created_at",
    ):
        assert key in data, f"missing key: {key}"
    assert data["place_name"] == SAMPLE_PLACE["name"]
    assert data["city"] == "Hyderabad"
    assert data["lat"] == pytest.approx(SAMPLE_PLACE["coords"]["lat"])
    assert data["lng"] == pytest.approx(SAMPLE_PLACE["coords"]["lng"])
    assert data["categories"] == SAMPLE_PLACE["categories"]
    assert data["reasoning"] == SAMPLE_PLACE["reasoning"]


def test_post_favorite_invalid_payload_returns_422(client, auth_headers):
    resp = client.post("/favorites", json={"city": "Hyderabad"}, headers=auth_headers)
    assert resp.status_code == 422

    resp2 = client.post(
        "/favorites",
        json={"place": {"name": "", "reasoning": "x", "coords": {}}, "city": "Hyderabad"},
        headers=auth_headers,
    )
    assert resp2.status_code == 422


def test_post_duplicate_favorite_returns_409(client, auth_headers):
    _create_favorite(client, auth_headers)
    resp = client.post("/favorites", json=_favorite_payload(), headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Place already saved"


# --- GET list / isolation ---


def test_get_favorites_empty_list_returns_200(client, auth_headers):
    resp = client.get("/favorites", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_get_favorites_returns_only_current_user_items(client, auth_headers):
    _create_favorite(client, auth_headers, SAMPLE_PLACE)
    _create_favorite(client, auth_headers, SAMPLE_PLACE_2)

    headers2 = _register_second_user(client)
    _create_favorite(client, headers2, OTHER_PLACE)

    resp1 = client.get("/favorites", headers=auth_headers)
    assert resp1.status_code == 200
    assert resp1.json()["count"] == 2

    resp2 = client.get("/favorites", headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 1
    assert resp2.json()["items"][0]["place_name"] == OTHER_PLACE["name"]


# --- DELETE / 404 not 403 ---


def test_user_b_cannot_delete_user_a_favorite_returns_404(client, auth_headers):
    created = _create_favorite(client, auth_headers)
    headers2 = _register_second_user(client)

    resp = client.delete(f"/favorites/{created['id']}", headers=headers2)
    assert resp.status_code == 404
    assert resp.status_code != 403

    still_there = client.get("/favorites", headers=auth_headers)
    assert still_there.json()["count"] == 1
    assert still_there.json()["items"][0]["id"] == created["id"]


def test_delete_own_favorite_returns_204(client, auth_headers):
    created = _create_favorite(client, auth_headers)
    resp = client.delete(f"/favorites/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    listing = client.get("/favorites", headers=auth_headers)
    assert listing.json()["count"] == 0
    assert all(item["id"] != created["id"] for item in listing.json()["items"])


def test_delete_nonexistent_favorite_returns_404(client, auth_headers):
    resp = client.delete("/favorites/99999", headers=auth_headers)
    assert resp.status_code == 404
