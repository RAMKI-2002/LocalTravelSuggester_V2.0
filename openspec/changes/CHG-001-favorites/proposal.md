# CHG-001 — Add User Favorites Feature

**Change ID:** CHG-001
**Type:** Feature Addition
**Status:** Proposed
**Date:** 2026-05-25
**Requestor:** Product / Stage 5 (change management)

---

## 1. Problem Statement

Users frequently revisit the same city or return to places they've saved mentally. Currently:
- There is no way to save a suggestion for later
- The history endpoint shows past queries but not specifically liked places
- Users have to re-run the same search to find a place again

A "favorites" feature lets users pin specific place suggestions to a personal list, enabling retrieval without re-running the full AI pipeline.

---

## 2. Proposed Change

Add a `favorites` system allowing users to save and retrieve specific place suggestions.

### New Endpoints:
- `POST /favorites` — save a place to the user's favorites
- `GET /favorites` — list the user's saved favorites
- `DELETE /favorites/{id}` — remove a favorite

### New DB Table: `user_favorites`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `user_id` | Integer FK | → `users.id` |
| `place_name` | String(256) | |
| `city` | String(128) | |
| `lat` | Float | nullable |
| `lng` | Float | nullable |
| `categories` | JSON | list of strings |
| `reasoning` | Text | LLM reasoning at the time of save |
| `created_at` | DateTime | server_default=now() |

### Frontend Changes:
- Add a ♥ button on each suggestion card in DashboardPage
- Add a Favorites tab/link in the navigation
- New `FavoritesPage.jsx` with the saved list

---

## 3. Why This Approach

**Why a separate table (not extending query_history)?**
History records an entire query. A favorite is a specific place from a query. They have different schemas and different access patterns (history: ordered by time; favorites: user curated). Mixing them would complicate both.

**Why not use localStorage?**
localStorage is browser-specific, not synced across devices, and lost on clear. A DB-backed favorites list follows the same auth-scoped pattern as history.

---

## 4. Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Embed favorites in query_history as a field | Different access patterns; forces loading full query to check favorites |
| Use a third-party bookmarking service | External dependency; overkill for a demo |
| localStorage only | Not persistent across devices or browser sessions |

---

## 5. Impact Analysis

See `impact.md` in this directory.
