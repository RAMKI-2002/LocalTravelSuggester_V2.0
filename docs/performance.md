# Performance Analysis

**Project:** Local Travel Suggester v2.0  
**Date:** 2026-05-25  
**Method:** AI-assisted review + static analysis + design-time estimation  

---

## 1. Overview

This document identifies the performance characteristics of the rebuilt application: where time is spent per request, what the current bottlenecks are, and what optimizations are appropriate at this project's scale.

---

## 2. Request Timing Breakdown

### POST /suggest-trip (happy path, no cache)

| Step | Typical Latency | Notes |
|------|----------------|-------|
| 1. Geocode city via Nominatim | 300–800ms | External HTTP, no auth, rate-limited to 1 req/s |
| 2. Fetch weather (OpenWeatherMap) | 200–500ms | External HTTP, JSON response ~1 KB |
| 3. Fetch places (Foursquare) | 300–700ms | External HTTP, up to 20 results |
| 3a. Fallback: Overpass query | 500–2000ms | Only if Foursquare disabled/fails; OSM query heavier |
| 4. Parse intent (rule-based + optional LLM) | <10ms (rule) / 800–2500ms (LLM) | LLM path: AWS Bedrock invoke latency |
| 5. Rank places | <5ms | Pure Python, O(n log n), n≤20 |
| 6. LLM reasoning per suggestion | 800–3000ms | Bedrock; dominates total latency |
| 7. DB write (QueryHistory) | 5–30ms | SQLite: sync; PostgreSQL: similar for single row |
| **Total (mock LLM)** | **~1–2s** | Steps 4+6 use fast in-memory mock |
| **Total (real Bedrock LLM)** | **~4–8s** | Dominated by two Bedrock calls |

### GET /history (10 rows)

| Step | Typical Latency | Notes |
|------|----------------|-------|
| JWT decode | <1ms | In-process, no network |
| DB query (indexed on user_id) | 5–20ms | SQLite: sync; trivial for ≤50 rows |
| JSON serialization | <5ms | Pydantic + dict construction |
| **Total** | **~10–30ms** | Dominated by DB (negligible) |

### POST /auth/login

| Step | Typical Latency | Notes |
|------|----------------|-------|
| DB lookup by username | 5–20ms | |
| bcrypt verify (work factor 12) | 100–300ms | Intentionally slow (brute-force protection) |
| JWT encode | <1ms | |
| **Total** | **~120–320ms** | bcrypt dominates; expected and acceptable |

---

## 3. P50 / P95 / P99 Estimates

These are design-time estimates based on typical external API behavior. Not measured from live load tests.

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| POST /suggest-trip (mock LLM) | 1.2s | 2.5s | 4s |
| POST /suggest-trip (real LLM) | 5s | 9s | 15s |
| GET /history | 25ms | 80ms | 200ms |
| POST /auth/login | 200ms | 400ms | 600ms |
| POST /auth/register | 250ms | 500ms | 700ms |
| GET /health | <10ms | 20ms | 50ms |

**Note:** P99 values for /suggest-trip are dominated by cold-start Bedrock latency and Nominatim rate limiting, not application code.

---

## 4. Caching Strategy

### Current Implementation

| Cache | Storage | TTL | Key |
|-------|---------|-----|-----|
| Weather | `WeatherLog` DB row | 30 minutes | `(city, normalized_city)` |
| Places | `PlaceCache` DB row | 24 hours | `(city, category, source)` |

**Impact:** On cache hit for both weather and places:
- POST /suggest-trip skips steps 2 and 3 (saves ~500ms–1.3s)
- LLM calls are NOT cached — reasoning is regenerated each time

**Why LLM responses aren't cached:**
- Intent varies with preference string
- User expects fresh, personalized reasoning each call
- Bedrock latency (2–3s) is acceptable for a travel planning context

### Optimization Opportunity: LLM Response Cache

If performance becomes critical:
```python
cache_key = f"llm:{city}:{effective_pref}:{','.join(sorted(place_names))}"
```
Cache the JSON reasoning output (TTL: 1 hour). Estimated savings: 2–3s on cache hit. Adds complexity — acceptable only if P95 > 10s under load.

---

## 5. Bottleneck Analysis

### Primary Bottleneck: AWS Bedrock Latency

Two serial LLM calls per request:
1. `reason_trip` — generates per-place reasoning text
2. `curate_places` — optionally re-ranks by AI judgment

**Risk:** 5–8s P50 is high for a web UI. Most users tolerate ≤3s.

**Mitigation options:**
1. **Mock mode for development:** `LLM_MOCK=true` → <10ms per call. Already implemented.
2. **Merge to one LLM call:** Combine reasoning + curation into a single prompt. Reduces latency by 40–50%.
3. **Streaming responses:** Stream Bedrock output to frontend progressively. Requires `asyncio` + SSE or WebSocket.
4. **Async parallel calls:** `asyncio.gather()` for weather + places + geocode (already parallel). LLM calls are sequential by design (curation needs reasoning output).

### Secondary Bottleneck: Nominatim Rate Limit

Nominatim enforces 1 request/second for anonymous users. Under concurrent load, requests queue.

**Mitigation:** Cache geocode results in `PlaceCache` (or a separate `GeoCache` table) with a long TTL (7 days). Cities don't move.

### Acceptable: bcrypt Login Time

300ms login time is intentional. This is not a bug — it's brute-force protection. Only optimize (reduce work factor) if login becomes a UX complaint.

---

## 6. Database Performance

### Current Schema Indexes

| Table | Indexed Columns | Query Pattern |
|-------|----------------|---------------|
| `users` | `username` (unique) | lookup on login |
| `users` | `email` (unique) | lookup on register |
| `query_history` | `user_id` | history endpoint filter |
| `place_cache` | `(city, category, source)` | cache lookup |
| `weather_log` | `(city, logged_at)` | TTL-aware lookup |

**Assessment:** Index coverage is adequate for the current query patterns.

### Scale Thresholds

| Scenario | Impact |
|----------|--------|
| 10,000 users, 50 queries each | 500,000 query_history rows — still fast with user_id index |
| 1,000 place cache entries | Negligible — PlaceCache is read-heavy |
| Concurrent /suggest-trip requests | Blocked by external API rate limits before DB becomes a bottleneck |

**Recommendation:** At 100,000+ users, add PostgreSQL connection pooling (PgBouncer). For the demo scope, SQLite/PostgreSQL without pooling is fine.

---

## 7. Observability

### Current Instrumentation

- **Structured JSON logs:** every request has a `request_id`, method, path, status, duration via `RequestIdMiddleware`
- **`latency_ms` in query_history:** every trip query duration is persisted — enables historical P50/P95 analysis from the DB
- **`/health/detailed`:** concurrent dependency checks with response time reporting

### What's Missing

- No distributed tracing (OpenTelemetry) — acceptable for a demo
- No Prometheus metrics endpoint — would add `prometheus-fastapi-instrumentator` in production
- No per-step timing within the trip pipeline — add `time.perf_counter()` around each client call if latency profiling is needed

### Quick Latency Profiling

To measure actual P50/P95 without load testing infrastructure:
```python
import time
t0 = time.perf_counter()
# ... step ...
logger.info("step=geocode latency_ms=%.0f", (time.perf_counter()-t0)*1000)
```
Add this around each step in `trip_service.py`. Logs are structured JSON — easily queried.

---

## 8. Optimization Priority Matrix

| Optimization | Effort | Impact | Priority |
|-------------|--------|--------|---------|
| Merge two LLM calls into one | Medium | High (−40% latency) | High |
| Cache geocode results | Low | Medium (occasional) | Medium |
| Add Prometheus metrics | Medium | High (observability) | Medium |
| Stream Bedrock response | High | High (UX feel) | Low (demo scope) |
| Connection pooling (PgBouncer) | High | Low (demo scale) | Low |
| Async Bedrock SDK calls | Medium | Medium | Low |
