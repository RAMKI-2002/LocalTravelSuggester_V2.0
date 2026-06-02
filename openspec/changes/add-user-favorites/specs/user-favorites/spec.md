## ADDED Requirements

### Requirement: Authenticated favorites API

The system SHALL expose `POST /favorites`, `GET /favorites`, and `DELETE /favorites/{id}`. All three endpoints MUST require a valid JWT via `get_current_user`. Unauthenticated requests SHALL receive HTTP 401.

#### Scenario: Unauthenticated POST rejected

- **WHEN** a client calls `POST /favorites` without an `Authorization` header
- **THEN** the response status is 401

#### Scenario: Unauthenticated GET rejected

- **WHEN** a client calls `GET /favorites` without an `Authorization` header
- **THEN** the response status is 401

#### Scenario: Unauthenticated DELETE rejected

- **WHEN** a client calls `DELETE /favorites/{id}` without an `Authorization` header
- **THEN** the response status is 401

### Requirement: Persist favorite with flat place columns

The system SHALL store favorites in a `user_favorites` table with columns: `id`, `user_id` (FK → `users.id`, indexed, ON DELETE CASCADE), `place_name`, `city`, `lat`, `lng`, `categories` (JSON), `reasoning`, and `created_at`.

`POST /favorites` SHALL accept a body containing a `place` object (validated as `PlaceSuggestion`) and a `city` string (trip source city). The service SHALL flatten `place.name` → `place_name`, `place.coords.lat`/`lng` → `lat`/`lng`, and `place.categories`/`place.reasoning` into their respective columns.

#### Scenario: Successful save returns 201

- **WHEN** an authenticated user POSTs a valid place payload they have not saved before
- **THEN** the response status is 201
- **AND** the response body includes `id`, `place_name`, `city`, `lat`, `lng`, `categories`, `reasoning`, and `created_at`

#### Scenario: Duplicate save returns 409

- **WHEN** an authenticated user POSTs a place whose `place.name` matches an existing favorite for that user
- **THEN** the response status is 409
- **AND** the response detail is `"Place already saved"`

### Requirement: List favorites scoped to current user

`GET /favorites` SHALL accept an optional `limit` query parameter (default 20, range 1–50). The response SHALL include only rows where `user_id` equals the authenticated user's id, ordered by `created_at` descending.

#### Scenario: User sees only own favorites

- **WHEN** User A has saved 2 places and User B has saved 1 place
- **THEN** User A's `GET /favorites` returns `count` 2
- **AND** User B's `GET /favorites` returns `count` 1

### Requirement: Delete favorite with enumeration-safe 404

`DELETE /favorites/{id}` SHALL delete the row only when both `id` matches and `user_id` equals the authenticated user's id. If no such row exists — whether the id is invalid or belongs to another user — the response SHALL be HTTP 404 Not Found (not 403).

#### Scenario: Owner deletes successfully

- **WHEN** an authenticated user DELETEs a favorite they own
- **THEN** the response status is 204
- **AND** a subsequent `GET /favorites` no longer includes that favorite

#### Scenario: Cross-user delete returns 404

- **WHEN** User B DELETEs a favorite id belonging to User A
- **THEN** the response status is 404
- **AND** User A's favorite remains in User A's `GET /favorites` results

#### Scenario: Nonexistent id returns 404

- **WHEN** an authenticated user DELETEs an id that does not exist for them
- **THEN** the response status is 404

### Requirement: Dashboard save affordance

The dashboard suggestion card UI SHALL include a control to save the place via `POST /favorites`. On success (201) the UI SHALL indicate the place is saved. On 409 the UI SHALL show an "Already saved" message without treating it as a fatal error.

#### Scenario: Save from suggestion card

- **WHEN** the user clicks save on a suggestion card after a successful trip result
- **THEN** the client POSTs the suggestion as `place` and the trip `city` from the result
- **AND** on 201 the save control reflects saved state

### Requirement: Favorites page

The application SHALL provide a protected `/favorites` route that lists saved places via `GET /favorites` and allows removal via `DELETE /favorites/{id}`. Navigation SHALL include a link to this page alongside Dashboard and History.

#### Scenario: Empty favorites state

- **WHEN** an authenticated user with no saved places visits `/favorites`
- **THEN** the page shows guidance to save places from the Dashboard

#### Scenario: Remove from favorites page

- **WHEN** the user removes a favorite from `/favorites`
- **THEN** the client calls `DELETE /favorites/{id}`
- **AND** the item is removed from the list on 204
