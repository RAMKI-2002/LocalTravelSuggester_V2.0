"""Tests for trip suggestion and history endpoints."""

from __future__ import annotations

import httpx
import respx


WEATHER_MOCK = {
    "name": "Hyderabad",
    "main": {"temp": 28.5, "feels_like": 27.0, "humidity": 60},
    "weather": [{"main": "Clear", "description": "clear sky"}],
    "wind": {"speed": 3.5},
}

OVERPASS_MOCK = {
    "elements": [
        {
            "type": "node", "id": 1, "lat": 17.385, "lon": 78.486,
            "tags": {"name": "Hussain Sagar", "tourism": "attraction"},
        },
        {
            "type": "node", "id": 2, "lat": 17.360, "lon": 78.474,
            "tags": {"name": "Charminar", "historic": "monument"},
        },
        {
            "type": "node", "id": 3, "lat": 17.410, "lon": 78.450,
            "tags": {"name": "Birla Mandir", "amenity": "place_of_worship", "religion": "hindu"},
        },
    ]
}

NOMINATIM_MOCK = [{"lat": "17.385", "lon": "78.486", "display_name": "Hyderabad, India"}]


def test_suggest_trip_without_auth_returns_401(client):
    resp = client.post("/suggest-trip", json={"city": "Hyderabad"})
    assert resp.status_code == 401


def test_suggest_trip_missing_city_returns_422(client, auth_headers):
    resp = client.post("/suggest-trip", json={}, headers=auth_headers)
    assert resp.status_code == 422


def test_suggest_trip_city_too_short_returns_422(client, auth_headers):
    resp = client.post("/suggest-trip", json={"city": "X"}, headers=auth_headers)
    assert resp.status_code == 422


@respx.mock
def test_suggest_trip_happy_path(client, auth_headers):
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_MOCK)
    )
    respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
        return_value=httpx.Response(200, json=WEATHER_MOCK)
    )
    # Overpass uses POST
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]:
        respx.post(url).mock(return_value=httpx.Response(200, json=OVERPASS_MOCK))

    resp = client.post(
        "/suggest-trip",
        json={"city": "Hyderabad", "preference": "peaceful temples", "max_results": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Hyderabad"
    assert "weather" in data
    assert "suggestions" in data
    assert "meta" in data
    assert isinstance(data["suggestions"], list)
    assert data["meta"]["elapsed_ms"] > 0
    # LLM mock should always produce curated results
    for s in data["suggestions"]:
        assert "name" in s
        assert "reasoning" in s
        assert "coords" in s


@respx.mock
def test_suggest_trip_weather_failure_degrades_gracefully(client, auth_headers):
    """When weather API fails and no cache exists, weather should be empty but suggestions still returned."""
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_MOCK)
    )
    respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
        return_value=httpx.Response(500, text="Server Error")
    )
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]:
        respx.post(url).mock(return_value=httpx.Response(200, json=OVERPASS_MOCK))

    resp = client.post("/suggest-trip", json={"city": "Hyderabad"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "weather" in data
    assert "weather" in data["meta"]["degraded"]


def test_history_without_auth_returns_401(client):
    resp = client.get("/history")
    assert resp.status_code == 401


@respx.mock
def test_history_returns_user_scoped_results(client, auth_headers):
    """History should only contain the authenticated user's queries."""
    # Make a trip suggestion first
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=NOMINATIM_MOCK)
    )
    respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
        return_value=httpx.Response(200, json=WEATHER_MOCK)
    )
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]:
        respx.post(url).mock(return_value=httpx.Response(200, json=OVERPASS_MOCK))

    client.post("/suggest-trip", json={"city": "Hyderabad"}, headers=auth_headers)

    # Register a second user
    client.post("/auth/register", json={
        "username": "user2", "email": "user2@example.com", "password": "password123"
    })
    login2 = client.post("/auth/login", json={"email": "user2@example.com", "password": "password123"})
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    # User 2 should see 0 history items
    resp2 = client.get("/history", headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 0

    # User 1 should see 1 history item
    resp1 = client.get("/history", headers=auth_headers)
    assert resp1.status_code == 200
    assert resp1.json()["count"] == 1
    assert resp1.json()["items"][0]["city"] == "Hyderabad"


def test_history_default_limit(client, auth_headers):
    resp = client.get("/history", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
