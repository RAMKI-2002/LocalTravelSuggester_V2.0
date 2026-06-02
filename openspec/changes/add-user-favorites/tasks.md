## 1. Tests (TDD — red first)

Reference: `openspec/changes/add-user-favorites/specs/user-favorites/spec.md` and `docs/superpowers/specs/2026-06-03-user-favorites-design.md`.

Use `client`, `auth_headers`, and two-user setup pattern from `tests/test_trip.py`. Add a shared `SAMPLE_PLACE` fixture dict matching `PlaceSuggestion` shape. DB-only — no `respx` mocks.

- [x] 1.1 Create `tests/test_favorites.py` with all test cases:
  - **Auth (401):**
    - `test_post_favorite_without_auth_returns_401`
    - `test_get_favorites_without_auth_returns_401`
    - `test_delete_favorite_without_auth_returns_401`
  - **POST happy path / validation:**
    - `test_post_favorite_saves_and_returns_201` — assert response includes `id`, `place_name`, `city`, `lat`, `lng`, `categories`, `reasoning`, `created_at`
    - `test_post_favorite_invalid_payload_returns_422` — missing `place` or empty `place.name`
    - `test_post_duplicate_favorite_returns_409` — assert `detail == "Place already saved"`
  - **GET list / isolation:**
    - `test_get_favorites_empty_list_returns_200` — new user, no saves → `{ count: 0, items: [] }`
    - `test_get_favorites_returns_only_current_user_items` — User A saves 2, User B saves 1; each GET returns own count only
  - **DELETE / 404 not 403:**
    - `test_user_b_cannot_delete_user_a_favorite_returns_404` — assert status is 404 **not** 403; User A's GET still shows the item
    - `test_delete_own_favorite_returns_204` — subsequent GET excludes deleted id
    - `test_delete_nonexistent_favorite_returns_404`
- [x] 1.2 Run `pytest tests/test_favorites.py -v` and confirm all tests FAIL (endpoints not registered yet)

## 2. Backend — model

- [x] 2.1 Add `UserFavorite` model to `backend/app/db/models.py`: `id`, `user_id` (FK → `users.id`, indexed, `ON DELETE CASCADE`), `place_name`, `city`, `lat`, `lng`, `categories` (JSON), `reasoning`, `created_at`; unique constraint on `(user_id, place_name)`; add `User.favorites` relationship with `cascade="all, delete-orphan"`

## 3. Backend — schemas

- [x] 3.1 Create `backend/app/schemas/favorites.py`: `FavoriteCreate` (`place: PlaceSuggestion`, `city: str`), `FavoriteItem`, `FavoriteListResponse` (`count`, `items`)

## 4. Backend — service

- [x] 4.1 Create `backend/app/services/favorites_service.py`: `create_favorite(db, user_id, place, city)` flattens `PlaceSuggestion` to columns; `list_favorites(db, user_id, limit)` ordered by `created_at DESC`; `delete_favorite(db, user_id, favorite_id)` returns bool (deleted or not); raise `ValueError("Place already saved")` on duplicate

## 5. Backend — routes

- [x] 5.1 Create `backend/app/api/routes_favorites.py`:
  - `POST /favorites` → 201 / 409 (`ValueError`) / 422 (Pydantic)
  - `GET /favorites?limit=20` → 200 `{ count, items }`, scoped to `current_user.id`, limit 1–50
  - `DELETE /favorites/{id}` → 204 / 404 (missing **or** other user's row — never 403)
  - All endpoints: `Depends(get_current_user)`

## 6. Backend — register router

- [x] 6.1 Register favorites router in `backend/app/main.py` (`from app.api import routes_favorites`; `app.include_router(routes_favorites.router)`)

## 7. Backend — verification

- [x] 7.1 Run `pytest tests/test_favorites.py -v` and confirm all tests PASS
- [x] 7.2 Run `pytest tests/ -v` and confirm no regressions

## 8. Frontend — API layer

- [x] 8.1 Add to `frontend/src/api.js`:
  - `addFavorite(place, city)` — POST; return response on 201; throw on other errors (caller handles 409)
  - `getFavorites(limit = 20)` — GET
  - `deleteFavorite(id)` — DELETE; expect 204
- [x] 8.2 Add `/favorites` proxy to `frontend/vite.config.js`

## 9. Frontend — UI and navigation

- [x] 9.1 Add heart/save control to `SuggestionCard` in `frontend/src/pages/DashboardPage.jsx`
- [x] 9.2 Create `frontend/src/pages/FavoritesPage.jsx`
- [x] 9.3 Update `frontend/src/App.jsx`

## 10. Documentation

- [x] 10.1 Update `README.md`
- [x] 10.2 Update `docs/architecture.md`
- [x] 10.3 Update `docs/security.md`
- [x] 10.4 Update `docs/current-state.md`
- [x] 10.5 Update `docs/design/README.md`
- [x] 10.6 Update `docs/performance.md`
- [x] 10.7 Doc grep audit

## 11. Post-ship OpenSpec (after feat commit — not during apply)

- [ ] 11.1 Run `/opsx-archive add-user-favorites` after implementation is committed
- [ ] 11.2 Verify `openspec/specs/user-favorites/spec.md` has a filled **Purpose** (not TBD) describing user-scoped place bookmarks from trip suggestions
- [ ] 11.3 Commit archive move: `chore: archive OpenSpec change add-user-favorites`
