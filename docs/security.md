# Security Analysis

**Project:** Local Travel Suggester v2.0  
**Date:** 2026-05-25  
**Standard:** OWASP Top 10 2021  
**Method:** AI-assisted review + static code analysis  

---

## 1. Executive Summary

The rebuilt application addresses the most critical security gaps from v1.0 (no authentication, no user isolation). The new system uses JWT authentication, bcrypt password hashing, user-scoped data access, and structured input validation. Several low-risk issues and production hardening items are noted below.

**Risk Level: LOW** for the demo scope. Additional hardening is needed for production deployment.

---

## 2. OWASP Top 10 Assessment

### A01 — Broken Access Control

**Status: MITIGATED**

- `/suggest-trip` requires `get_current_user` dependency → unauthenticated requests return 401
- `/history` filters by `current_user.id` → users cannot see each other's history
- DELETE /favorites (proposed) returns 404 for other users' resources to prevent enumeration

**Remaining gap:**
- `/health/detailed` is unauthenticated — it exposes which external services are available. Acceptable for a demo. In production, restrict to internal network or add an admin token check.

---

### A02 — Cryptographic Failures

**Status: MITIGATED**

| Mechanism | Implementation | Assessment |
|-----------|---------------|------------|
| Password hashing | `bcrypt` with `gensalt()` (work factor 12) | ✅ Correct — adaptive, salted |
| JWT signing | HS256 with `SECRET_KEY` from env | ✅ Correct — not hardcoded |
| Token expiry | 24 hours (`ACCESS_TOKEN_EXPIRE_HOURS`) | ✅ Bounded — not forever |
| Transport | HTTPS assumed in production | ⚠️ App doesn't enforce; depends on reverse proxy |

**Finding:** The default `SECRET_KEY` in `config.py` is `"dev-secret-key-change-in-production"`. If deployed without setting this env var, tokens are signed with a known key — any attacker could forge JWTs.

**Fix:** Add a startup check:
```python
if settings.secret_key == "dev-secret-key-change-in-production":
    import sys
    sys.exit("ERROR: SECRET_KEY must be changed for production. Refusing to start.")
```
Or use `pydantic.Field(min_length=32)` to reject weak secrets.

---

### A03 — Injection

**Status: MITIGATED**

- All DB queries use SQLAlchemy ORM with parameterized queries. No raw SQL string interpolation.
- External API inputs (city, preference) are validated by Pydantic (`str`, `Field(max_length=...)`) before use.
- User input is never interpolated into shell commands.

**Low risk:** The `city` field is passed verbatim to Nominatim and OpenWeatherMap as a URL query parameter via `httpx`. `httpx` URL-encodes parameters automatically. No SSRF risk (target hosts are hardcoded constants).

---

### A04 — Insecure Design

**Status: PARTIALLY MITIGATED**

**Good:**
- Separation of concerns: routes don't contain business logic
- Auth state validated on every request via `get_current_user` dependency
- Error messages are generic (no stack traces in 4xx/5xx responses by default)

**Gap:** No rate limiting on `/auth/register` or `/auth/login`. An attacker can:
- Submit unlimited registration attempts (fills the `users` table)
- Brute-force passwords at ~3 req/sec (bcrypt is slow, but not infinite)

**Fix for production:** Add `slowapi` or Nginx rate limiting:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
@limiter.limit("5/minute")
async def login(...): ...
```

---

### A05 — Security Misconfiguration

**Status: PARTIALLY MITIGATED**

| Item | Status | Notes |
|------|--------|-------|
| CORS | ⚠️ Review | `allow_origins=["http://localhost:5173", "http://localhost:3000"]` — correct for dev. Change to exact production domain. |
| CORS `allow_credentials=True` | ⚠️ Review | Needed for the Bearer token flow? No — Bearer is sent in headers, not cookies. `allow_credentials` can be `False`. |
| Debug mode | ✅ Off | FastAPI debug defaults to False in production |
| `/docs` (Swagger UI) | ⚠️ Consider | Exposes full API schema. Disable in production: `FastAPI(docs_url=None)` |
| Error detail exposure | ✅ Generic | 422 Pydantic errors don't expose internal state |

**Note on `allow_credentials`:** Setting this to `True` with `allow_origins=["*"]` would be a security misconfiguration (browsers block it). Since specific origins are listed, it's technically valid — but unnecessary. Set to `False` to be explicit.

---

### A06 — Vulnerable and Outdated Components

**Status: ACCEPTABLE (demo)**

Key dependencies:
- `fastapi` — actively maintained, rapid security patches
- `python-jose[cryptography]` — maintained; HS256 is standard
- `bcrypt>=4.0` — actively maintained; work factor is configurable
- `sqlalchemy>=2.0` — actively maintained
- `httpx` — actively maintained

**Action for production:** Pin to exact versions in `requirements.txt` and run `pip-audit` in CI:
```bash
pip install pip-audit && pip-audit -r requirements.txt
```

---

### A07 — Identification and Authentication Failures

**Status: MITIGATED**

- Passwords hashed with bcrypt (not MD5/SHA-1)
- JWT tokens expire in 24 hours
- Failed login returns generic "Invalid credentials" (does not distinguish "user not found" from "wrong password")
- No plaintext password logging (only username is logged)

**Gap:** No "forgot password" flow — out of scope for demo.

**Gap:** No email verification on registration — a registered user can use any email string.

---

### A08 — Software and Data Integrity Failures

**Status: ACCEPTABLE**

- No deserialization of untrusted data
- LLM responses are validated with `json.loads()` + `try/except` — malformed LLM output raises `ValueError`, not executed
- `respx` mocks in tests prevent CI from hitting real external services

---

### A09 — Security Logging and Monitoring Failures

**Status: PARTIALLY MITIGATED**

**Good:**
- Structured JSON logging with `request_id` on every request
- Auth events logged: `user_registered`, `user_logged_in`
- `latency_ms` stored per trip query for anomaly detection

**Gap:**
- Failed login attempts are not specifically logged (the 401 will appear in request logs, but no aggregation)
- No alerting on repeated 401s from the same IP

**Fix for production:** Log authentication failures explicitly:
```python
logger.warning("login_failed: username=%r ip=%r", username, request.client.host)
```

---

### A10 — Server-Side Request Forgery (SSRF)

**Status: MITIGATED**

All outbound HTTP calls go to hardcoded, constant URLs:
- `api.openweathermap.org`
- `api.foursquare.com`
- `nominatim.openstreetmap.org`
- `overpass-api.de`
- AWS Bedrock (via boto3 SDK)

No user-supplied URL is ever fetched directly. SSRF is not applicable.

---

## 3. Sensitive Data Handling

| Data | Storage | Transmission | Assessment |
|------|---------|-------------|------------|
| Passwords | bcrypt hash only | Never transmitted after registration | ✅ |
| JWT tokens | localStorage (frontend) | Bearer header (HTTPS in prod) | ⚠️ localStorage is XSS-vulnerable; see below |
| API keys (OpenWeather, Foursquare) | `.env` file | Never exposed to frontend or users | ✅ |
| AWS credentials | `.env` file / IAM role | Never in code | ✅ |

**JWT in localStorage:** The `AuthContext.jsx` stores the JWT in `localStorage`. This means an XSS attack could steal the token. The more secure alternative is `httpOnly` cookies, which JavaScript cannot access.

For this demo scope, `localStorage` is acceptable. For production: use `httpOnly`, `Secure`, `SameSite=Strict` cookies.

---

## 4. API Key Exposure Risk

All external API keys are loaded from environment variables via `Settings`. The `.env` file is in `.gitignore` (should be verified). The `.env.example` file contains placeholder values only.

**Check:** Ensure `.env` is in `.gitignore`:
```bash
grep ".env" .gitignore  # should show .env
```

---

## 5. Security Hardening Checklist (Production)

| Item | Current State | Action |
|------|-------------|--------|
| SECRET_KEY validation | Weak default exists | Add startup check or Field(min_length=32) |
| Rate limiting | None | Add slowapi or Nginx |
| HTTPS enforcement | Not in app | Use nginx/caddy in front of uvicorn |
| Disable /docs in prod | Enabled | FastAPI(docs_url=None) |
| JWT in httpOnly cookie | localStorage | Refactor AuthContext to use cookies |
| pip-audit in CI | Not set up | Add to GitHub Actions |
| Failed login logging | Not specific | Log auth failures explicitly |
| CORS allow_credentials | True | Set to False (not needed for Bearer) |
