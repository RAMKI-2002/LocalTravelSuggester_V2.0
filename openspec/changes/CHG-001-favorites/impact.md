# CHG-001 — Impact Analysis

## Backward Compatibility

| Component | Impact | Notes |
|-----------|--------|-------|
| Existing API endpoints | None | New routes only; nothing changed |
| Database schema | Additive | New `user_favorites` table; no existing table modified |
| Frontend | Additive | New page + button; existing pages unchanged |
| Auth system | None | Reuses existing `get_current_user` dependency |
| Tests | Additive | New test file; existing tests unchanged |

**Risk level: LOW** — purely additive change, no modifications to existing behavior.

## Database Migration

`init_db()` with `Base.metadata.create_all()` will create the new `user_favorites` table on next startup. No data migration needed. No existing records affected.

If using Alembic, a single migration would be: `alembic revision --autogenerate -m "add_user_favorites"`.

## Performance Impact

- GET /favorites: simple indexed query on `user_id`. At 1000 favorites per user, negligible. At 100,000 favorites, add a composite index on (user_id, created_at).
- POST /favorites: single INSERT. No LLM call. Response time < 50ms.
- No impact on existing /suggest-trip pipeline.

## Security Considerations

- All favorites endpoints require JWT authentication
- DELETE checks `user_id == current_user.id` before deleting — returns 404 (not 403) to prevent enumeration
- No user can discover or modify another user's favorites

## Test Coverage Impact

New test file adds ~8 tests. Expected coverage change:
- `routes_favorites.py`: targeting 100%
- `db/models.py (UserFavorite)`: targeting 100% (model is declarative, no logic)
- Overall coverage: +1-2% (net positive)
