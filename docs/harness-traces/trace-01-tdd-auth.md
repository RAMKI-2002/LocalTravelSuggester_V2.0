# Harness Trace 01 — TDD: Auth System

**Task:** B-01 Write auth tests + B-04 Security module + B-05 Auth service + routes
**Date:** 2026-05-25
**Agent Role:** Test Writer → Code Agent → Code Reviewer

---

## Brainstorm Phase

**Prompt used:**
```
What are the ways to implement JWT authentication in a FastAPI app?
Project rules: see .cursor/rules/fastapi-rules.mdc
Preference: simplest approach that satisfies requirements.
```

**Options presented by AI:**
1. `python-jose` + `passlib[bcrypt]` + `OAuth2PasswordBearer` — standard FastAPI approach
2. `PyJWT` + manual bcrypt — more direct, fewer abstractions
3. Cookie-based sessions — simpler but not stateless

**Decision:** Option 2 modified: use `python-jose` for JWT (better FastAPI ecosystem fit) + `bcrypt` directly (avoids passlib compatibility issues with bcrypt 4.x). OAuth2PasswordBearer used for Swagger UI integration.

**Why not sessions:** Requirements need a React frontend on a different port. Sessions require CORS for cookies which is more complex than bearer token headers.

---

## Plan Phase (Tests Written First)

Tests written in `tests/test_auth.py` **before any implementation existed**:
- `test_register_success` → expected 201 + access_token
- `test_register_duplicate_email_returns_409` → expected 409
- `test_register_short_password_returns_422` → expected 422 (Pydantic validation)
- `test_login_success` → expected 200 + access_token
- `test_login_wrong_password_returns_401` → expected 401
- `test_me_with_valid_token_returns_user` → expected 200 + user data
- `test_me_without_token_returns_401` → expected 401

**Test run (before implementation):** 9 failures, 0 passes. ✓ TDD validated.

---

## Implement Phase

**Prompt:**
```
Implement the auth system so that tests/test_auth.py passes.
File: backend/app/core/security.py (JWT + hashing)
File: backend/app/services/auth_service.py (register_user, login_user)
File: backend/app/api/routes_auth.py (POST /auth/register, POST /auth/login, GET /auth/me)
Rules: .cursor/rules/fastapi-rules.mdc — routes do only HTTP, business logic in service.
```

**AI-generated output reviewed for:**
- ✓ Business logic in auth_service.py, not in routes
- ✓ No hardcoded secrets — SECRET_KEY from config
- ✓ 409 for duplicate email (not 400)
- ✓ Same 401 error for both "user not found" and "wrong password" (prevents enumeration)

**Issue caught during review:** AI generated `passlib.CryptContext` which fails with bcrypt 4.x. Rejected. Used `bcrypt.hashpw()` directly.

---

## Verify Phase

```bash
cd LocalTravelSuggester
$env:PYTHONPATH = "backend"
python -m pytest tests/test_auth.py -v
```

**Result:** 12/12 passed.
**Coverage for auth_service.py:** 100%
**Coverage for routes_auth.py:** 100%
**Coverage for core/security.py:** 95% (2 lines: edge cases in token decode)

---

## AI Error Caught

**What AI did wrong:** Generated `CryptContext(schemes=["bcrypt"])` using passlib. This fails with `ValueError: password cannot be longer than 72 bytes` due to a passlib 1.7.x + bcrypt 4.x incompatibility. The error message is misleading (it appears even for short passwords when passlib can't read the bcrypt version).

**How it was caught:** Running the tests immediately after implementation revealed the error. The test `test_register_success` failed with a server error rather than a 201.

**Fix:** Replaced passlib entirely with direct `bcrypt.hashpw()` / `bcrypt.checkpw()` calls. Simpler, fewer dependencies, no compatibility issues.

**Lesson:** AI generates what works in training data — which may be passlib 1.7.4 + bcrypt 3.x. The actual environment (bcrypt 4.x) is different. Always run tests before trusting AI output.
