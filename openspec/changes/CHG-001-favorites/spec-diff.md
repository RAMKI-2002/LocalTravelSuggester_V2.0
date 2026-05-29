# CHG-001 — Spec Diff

Changes to `specs/local-travel-suggester/spec.md`

---

## Sections Modified

### User Stories — ADDITIONS

```diff
+ **US-13** As a logged-in user, I want to save a specific place suggestion to my
+           favorites so I can refer back to it later without repeating the search.
+
+ **US-14** As a logged-in user, I want to view all my saved favorite places in one
+           list so I can plan future visits.
+
+ **US-15** As a logged-in user, I want to remove a place from my favorites when
+           I am no longer interested in it.
```

### Acceptance Criteria — ADDITIONS

```diff
+ ### AC-08: Favorites
+ - POST /favorites requires authentication
+ - Request includes: place_name, city, lat, lng (optional), categories (optional), reasoning (optional)
+ - Returns: the created favorite with id and created_at
+ - GET /favorites returns all saved favorites for the authenticated user
+ - DELETE /favorites/{id} removes the favorite; returns 404 if not found or owned by another user
+ - A place can be favorited multiple times (no uniqueness constraint — user decides)
```

### Scope Boundaries — MODIFIED

```diff
- Out of Scope: Social features (sharing trips, ratings, comments)
+ Out of Scope: Social features (sharing favorites, public favorites lists)
+
+ In Scope (added): Personal favorites (save/list/delete place suggestions)
```

### Data Model — ADDITION (for plan.md)

```diff
+ ### 3.5 `user_favorites` Table
+
+ | Column | Type | Notes |
+ |--------|------|-------|
+ | `id` | Integer PK | |
+ | `user_id` | Integer FK | → `users.id`, CASCADE delete |
+ | `place_name` | String(256) | |
+ | `city` | String(128) | Indexed |
+ | `lat` | Float | Nullable |
+ | `lng` | Float | Nullable |
+ | `categories` | JSON | list[str] |
+ | `reasoning` | Text | Nullable |
+ | `created_at` | DateTime | server_default=now() |
```
