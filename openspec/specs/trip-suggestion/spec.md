# trip-suggestion Specification

## Purpose

Defines the contract for trip suggestion results: what each place in `POST /suggest-trip` responses includes, what upstream place normalization must exclude, and what the dashboard displays. Per-place budget estimation was removed — see archived change `openspec/changes/archive/2026-06-02-remove-budget-estimation/`.

## Requirements
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

