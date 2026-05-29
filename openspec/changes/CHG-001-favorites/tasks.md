# CHG-001 — Implementation Tasks

## Backend Tasks

**CHG-001-B1** — Add `UserFavorite` ORM model to `backend/app/db/models.py` (1h)
- Columns: id, user_id (FK), place_name, city, lat, lng, categories (JSON), reasoning, created_at
- Relationship: User.favorites → list[UserFavorite]

**CHG-001-B2** — Add Pydantic schemas in `backend/app/schemas/` (0.5h)
- `FavoriteCreate`: place_name, city, lat (opt), lng (opt), categories (opt), reasoning (opt)
- `FavoriteResponse`: all fields + id + created_at

**CHG-001-B3** — Write tests first: `tests/test_favorites.py` (1h)
- test_add_favorite_success → 201
- test_list_favorites_returns_user_scoped_results → user isolation
- test_delete_favorite_success → 204
- test_delete_favorite_not_found → 404
- test_delete_other_users_favorite → 404 (not 403 — prevents enumeration)

**CHG-001-B4** — Implement routes in `backend/app/api/routes_favorites.py` (1h)
- POST /favorites → requires get_current_user
- GET /favorites → user-scoped query
- DELETE /favorites/{id} → check user_id matches

**CHG-001-B5** — Register router in `main.py` (0.1h)

## Frontend Tasks

**CHG-001-F1** — Add `addFavorite(place)` and `getFavorites()` calls to `api.js` (0.5h)

**CHG-001-F2** — Add ♥ button to `SuggestionCard` in `DashboardPage.jsx` (1h)
- Toggle state: filled ♥ / outline ♥
- On click: call addFavorite → show success toast

**CHG-001-F3** — Create `FavoritesPage.jsx` (1.5h)
- GET /favorites on mount
- Render card for each favorite (name, city, categories, reasoning)
- Delete button per card

**CHG-001-F4** — Add Favorites link to Nav in `App.jsx` (0.2h)

## Estimated Total: ~6 hours
