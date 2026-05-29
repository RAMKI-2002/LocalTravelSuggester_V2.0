# Feature Spec — Local Travel Suggester

**Stage:** 1 — Requirements Definition
**Date:** 2026-05-25
**Method:** Spec Kit `/specify` equivalent

> This document answers only **WHAT** the system does and **WHY**. No implementation choices are made here.

---

## 1. Problem Statement

Travellers visiting an unfamiliar city (or exploring their own city) struggle to find relevant places to visit because:

- Generic "top 10" lists ignore current weather conditions
- Search engines return the same popular spots regardless of personal preference
- Results are not anchored to the user's locality, so travel distances are impractical
- There is no personalised reasoning explaining *why* a place suits the user right now

---

## 2. Target Users

| User Type | Description |
|-----------|-------------|
| **Local Explorer** | A resident who wants to discover places in their own city based on mood or activity preference |
| **Visitor / Tourist** | Someone visiting a city for business or leisure who wants quick, relevant suggestions |
| **Weekend Planner** | Someone planning a day trip from their locality within the city |

---

## 3. User Stories

### Authentication

**US-01** As a new user, I want to register with a username, email, and password so that I can access the system and have my history saved against my account.

**US-02** As a returning user, I want to log in with my email and password so that I can access my personal trip history.

**US-03** As a logged-in user, I want to see my profile information so that I can confirm which account I am using.

### Trip Suggestions

**US-04** As a user, I want to enter a city name and receive a list of place suggestions so that I can find things to do.

**US-05** As a user, I want to describe what I am looking for in plain English (e.g., "I want somewhere peaceful", "hungry for street food") so that suggestions match my mood, not just a category dropdown.

**US-06** As a user, I want to optionally provide my locality (neighbourhood) within the city so that suggestions are close to where I am.

**US-07** As a user, I want to see current weather for the city alongside suggestions so that I know whether outdoor places are practical.

**US-08** As a user, I want each suggestion to include a one-sentence AI-generated reason explaining why it fits my preference and the current weather.

**US-09** As a user, I want to see the approximate distance from my locality to each suggestion so that I can plan travel time.

**US-10** As a user, I want to see a map showing pin locations for all suggestions so that I can understand the geographic spread.

### Trip History

**US-11** As a logged-in user, I want my past trip queries to be automatically saved so that I can review what I searched for before.

**US-12** As a logged-in user, I want to view my past queries with the suggestions returned at the time so that I can revisit recommendations.

---

## 4. Acceptance Criteria

### AC-01: Registration
- Accepts: username (3–50 chars), email (valid format), password (min 8 chars)
- Returns: access token on success
- Rejects duplicate email with 409 Conflict
- Passwords are never stored in plain text

### AC-02: Login
- Accepts: email + password
- Returns: JWT access token valid for 24 hours
- Returns 401 for invalid credentials

### AC-03: Trip Suggestion
- Required input: `city` (string, 2–128 chars)
- Optional input: `preference` (string, max 500 chars), `locality` (string), `max_results` (int 1–10, default 5)
- Returns: weather snapshot, list of place suggestions, metadata
- Each suggestion includes: name, description, categories, AI reasoning, coordinates, distance (if locality provided)
- Response time target: ≤8 seconds (P95)
- If upstream place APIs fail, system degrades gracefully and returns partial results

### AC-04: Weather Integration
- Live weather data is fetched for the requested city
- Weather influences which places are ranked higher (rainy → indoor preferred; sunny → outdoor preferred)
- Cached for 30 minutes to avoid hitting API rate limits

### AC-05: Intent Understanding
- System extracts structured intent (category, keywords, mood) from free-text preference
- Different preferences for the same city return meaningfully different place sets
- Rule-based extraction used for common prompts; LLM used for ambiguous ones

### AC-06: Trip History
- Each successful trip query is saved linked to the requesting user
- GET /history returns the last N queries for the authenticated user
- History is scoped per user — users cannot see each other's history

### AC-07: Map Display
- Frontend displays a Leaflet map with numbered pins for each suggestion
- User's locality is shown as a separate marker when provided

---

## 5. Scope Boundaries

### In Scope
- User registration and login (JWT auth)
- Trip suggestion with weather + LLM reasoning
- Trip history per user
- Map visualisation of suggestions
- Health check endpoint for all integrations

### Out of Scope (v1)
- Social features (sharing trips, ratings, comments)
- Email verification
- Push notifications
- Mobile app
- Booking integrations
- Offline mode
- Admin panel

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | P95 response time for `/suggest-trip` ≤ 8 seconds |
| **Availability** | Graceful degradation when any single upstream (weather, places, LLM) fails |
| **Security** | Passwords hashed (bcrypt), tokens use signed JWT, all user endpoints require authentication |
| **Test Coverage** | Backend API test coverage ≥ 70% |
| **Observability** | Structured JSON logs with request-id, health endpoint per dependency |
| **Maintainability** | Code readable by a new developer in under 30 minutes; no unexplained abstractions |
| **Portability** | Runs locally with SQLite; targets PostgreSQL in production; same code, no branching |

---

## 7. Core Business Features (3 required by assessment)

| # | Feature | Description |
|---|---------|-------------|
| 1 | **AI-Curated Trip Suggestions** | Weather-aware, intent-driven place recommendations with LLM reasoning |
| 2 | **User Authentication System** | JWT-based register/login/profile; user-scoped data |
| 3 | **Trip History** | Per-user query log; view past suggestions |

---

## 8. External Integrations (1 required by assessment)

| # | Integration | Purpose |
|---|-------------|---------|
| 1 | **AWS Bedrock (Nova Lite)** | LLM: intent extraction, place curation, reasoning |
| 2 | **OpenWeatherMap** | Current weather for the requested city |
| 3 | **Foursquare Places API** | Primary place data source |
| 4 | **OSM Overpass API** | Fallback place data source (free, no key needed) |
| 5 | **Nominatim (OSM)** | Geocoding city/locality names to lat/lng |

The primary LLM integration (AWS Bedrock) satisfies the assessment's "1 external API or LLM" requirement. All others are supporting integrations.
