## ADDED Requirements

### Requirement: PlaceSuggestion response fields

Each item in `POST /suggest-trip` response `suggestions[]` SHALL include: `name`, `description`, `categories`, `reasoning`, `coords`, `distance_km`, `score`, `website`, and `address`. The response SHALL NOT include `estimated_budget` or any budget-related sub-fields.

#### Scenario: Successful trip suggestion omits budget

- **WHEN** an authenticated user submits a valid `POST /suggest-trip` request
- **THEN** each suggestion in the response contains `name`, `reasoning`, and `coords`
- **AND** each suggestion does not contain an `estimated_budget` field

#### Scenario: Distance remains available when user locality is geocoded

- **WHEN** an authenticated user submits a trip request with a geocodable `locality`
- **THEN** each suggestion with valid coordinates MAY include `distance_km` as the haversine distance from the user's location in kilometres
- **AND** `distance_km` is independent of any cost or pricing data

### Requirement: Place client normalization excludes pricing metadata

Normalized place dicts produced by `places_client.py` and `overpass_client.py` SHALL NOT include a `price_tier` key. The Foursquare places search request SHALL NOT request the `price` field.

#### Scenario: Foursquare normalization has no price_tier

- **WHEN** the places client normalizes a Foursquare search result
- **THEN** the returned dict does not contain `price_tier`
- **AND** the Foursquare API request does not include `price` in requested fields

#### Scenario: Overpass normalization has no price_tier

- **WHEN** the overpass client normalizes an OSM element
- **THEN** the returned dict does not contain `price_tier`

### Requirement: Dashboard suggestion cards omit budget display

The dashboard suggestion card UI SHALL display place name, categories, reasoning, distance, and score. It SHALL NOT display per-place budget or currency amounts.

#### Scenario: Suggestion card shows distance without budget

- **WHEN** the dashboard renders a trip suggestion result
- **THEN** each suggestion card MAY show distance in kilometres when `distance_km` is present
- **AND** the card does not show any ₹ amount or budget label

## REMOVED Requirements

### Requirement: Per-place budget estimation

**Reason:** Coarse budget estimates produce misleading ₹0 entry fees for Overpass-sourced places. Showing incorrect pricing is worse than showing nothing.

**Migration:** Remove `estimated_budget` from `PlaceSuggestion` schema. Delete `services/budget.py`. Remove budget enrichment from `trip_service.py` step `[7]`. Remove budget display from `DashboardPage.jsx`. Deploy backend and frontend together.

#### Scenario: Budget field no longer computed

- **WHEN** the trip service enriches final place candidates before building the response
- **THEN** the service does not call `estimate_budget` or attach `_budget` to place dicts

### Requirement: Budget schema model

**Reason:** The `Budget` Pydantic model exists solely to serialize `estimated_budget` on `PlaceSuggestion`.

**Migration:** Delete the `Budget` class from `schemas/trip.py` when removing `estimated_budget` from `PlaceSuggestion`.

#### Scenario: OpenAPI schema has no Budget type on suggestions

- **WHEN** the API schema for `PlaceSuggestion` is generated
- **THEN** `PlaceSuggestion` does not reference a `Budget` model or `estimated_budget` property
