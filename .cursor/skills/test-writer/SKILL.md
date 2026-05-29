# Skill: Test Writer

## Purpose
Generate pytest tests for a given FastAPI route or service function, following the project's TDD conventions and mocking requirements.

## When to Use
- Before implementing a new route or service function
- When adding a new test scenario to an existing test file
- When coverage drops below 70%

## Instructions

When activated, follow these steps:

### Step 1: Identify the Target
Ask the user: "Which route or service function do you want tests for?"

If it is a route:
- Check `backend/app/api/routes_*.py` for the route signature
- Check `backend/app/schemas/` for request/response models
- Note which dependencies it uses (`get_db`, `get_current_user`)

If it is a service:
- Check `backend/app/services/` for the function signature
- Note all parameters and return types

### Step 2: Identify Required Mocks
For route tests:
- List all external HTTP calls made in the pipeline (look in `clients/`)
- Each one needs a `respx.mock` decorator with the URL
- Note if the route requires auth (needs `auth_headers` fixture)

For service tests:
- No mocks needed unless the service calls a client
- Clients should be replaced with mock objects if needed

### Step 3: Generate Tests
Generate tests following this template:

```python
"""Tests for <target>."""
import pytest
import respx
import httpx
from fastapi.testclient import TestClient


# Happy path
def test_<what>_success(<fixtures>):
    ...
    assert resp.status_code == 200
    assert "expected_field" in resp.json()

# Auth failure (if route is protected)
def test_<what>_no_auth_returns_401(client):
    resp = client.post("/route", json={...})
    assert resp.status_code == 401

# Input validation
def test_<what>_missing_required_field_returns_422(client, auth_headers):
    resp = client.post("/route", json={}, headers=auth_headers)
    assert resp.status_code == 422

# Edge cases specific to the feature
def test_<what>_<edge_case>(...):
    ...
```

### Step 4: Verify
After generating tests:
1. Confirm the test file matches the naming convention `test_<module>.py`
2. Confirm fixtures are imported from `conftest.py`, not redefined inline
3. Confirm all external HTTP calls are mocked
4. Confirm `LLM_MOCK=true` is active for any test involving the trip pipeline

## Output Location
Tests go in `tests/` for route tests or `tests/services/` for service unit tests.

## Example Activation Prompt
"Use the test-writer skill to generate tests for POST /auth/register"
