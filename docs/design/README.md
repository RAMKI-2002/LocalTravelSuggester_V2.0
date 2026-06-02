# UI / Interaction Design

**Stage:** Bonus Stage (optional)  
**Status:** Sketched (no hi-fi prototype generated)

---

## Why This Stage Was Not Done with a UI Tool

This project was built with a focus on the AI-assisted backend engineering workflow. The frontend was implemented directly in React (Vite + Tailwind) as part of Stage 4, using the API contracts already defined in `specs/local-travel-suggester/plan.md`.

A dedicated UI generation tool (v0.dev, Bolt.new) was not used because:
- The frontend is 4 pages (Login, Dashboard, History, Favorites) — simple enough to implement directly
- The API contracts were already well-defined in the technical plan before frontend work began
- The project prioritizes backend engineering quality; the frontend is intentionally minimal (four pages)

---

## Sketched Information Architecture

### Page 1 — Login / Register (`/`)

```
┌─────────────────────────────────────┐
│        Local Travel Suggester        │
│  ┌─────────────┐ ┌───────────────┐  │
│  │    Login    │ │   Register    │  │
│  └─────────────┘ └───────────────┘  │
│                                     │
│  Username: [___________________]    │
│  Password: [___________________]    │
│                                     │
│  [        Login / Register        ] │
└─────────────────────────────────────┘
```

**API calls:** `POST /auth/login`, `POST /auth/register`

---

### Page 2 — Dashboard (`/dashboard`)

```
┌─────────────────────────────────────┐
│  Nav: [Dashboard] [History] [Favorites] [Logout] │
├────────────────────────┬────────────┤
│  City: [__________]    │            │
│  Pref: [__________]    │  Leaflet   │
│  [  Get Suggestions  ] │    Map     │
│                        │            │
│  ┌──────────────────┐  │  [Markers] │
│  │ Suggestion Card  │  │            │
│  │ Name, Category   │  │            │
│  │ AI Reasoning     │  │            │
│  │ Distance: X km   │  │            │
│  │ [♥ Save]         │  │            │
│  └──────────────────┘  │            │
└────────────────────────┴────────────┘
```

**API calls:** `POST /suggest-trip`

---

### Page 3 — History (`/history`)

```
┌─────────────────────────────────────┐
│  Nav: [Dashboard] [History] [Favorites] [Logout] │
├─────────────────────────────────────┤
│  Your Trip History                  │
│                                     │
│  [City: Mumbai]  [Parks, Outdoor]   │
│  5 suggestions · 2.3s · 2026-05-20  │
│                                     │
│  [City: Hyderabad] [Food, Biryani]  │
│  3 suggestions · 1.8s · 2026-05-18  │
└─────────────────────────────────────┘
```

**API calls:** `GET /history`

---

### Page 4 — Favorites (`/favorites`)

```
┌─────────────────────────────────────┐
│  Nav: [Dashboard] [History] [Favorites] [Logout] │
├─────────────────────────────────────┤
│  Saved Places                       │
│                                     │
│  ♥ Hussain Sagar Lake  [Remove]     │
│  Hyderabad · lake, park             │
│  Perfect for a peaceful evening…    │
│                                     │
│  (empty state: save from Dashboard) │
└─────────────────────────────────────┘
```

**API calls:** `GET /favorites`, `DELETE /favorites/{id}`

---

## API Contracts Implied by the UI

These contracts were derived from UI needs and are fully implemented:

| UI Action | API Call | Response Fields |
|-----------|----------|----------------|
| Login form submit | `POST /auth/login` | `access_token`, `token_type` |
| Register form submit | `POST /auth/register` | `id`, `username`, `email` |
| Dashboard form submit | `POST /suggest-trip` | `suggestions[]`, `weather`, `meta` |
| History page load | `GET /history` | `items[]`, `count` |
| Save place from card | `POST /favorites` | `id`, `place_name`, `city`, … |
| Favorites page load | `GET /favorites` | `items[]`, `count` |
| Remove favorite | `DELETE /favorites/{id}` | 204 No Content |
| Nav: current user | `GET /auth/me` | `id`, `username`, `email` |

---

## If Using v0.dev (Bonus Implementation Guide)

To complete this stage with a real UI tool:

```
Prompt for v0.dev:

Create a React dashboard page for a travel suggestion app that:
- Has a form with "City" and "Preference" inputs
- Calls POST /suggest-trip with { city, preference, max_results: 5 }
- Shows a Leaflet map with markers at each suggestion's coordinates
- Shows suggestion cards with: name, categories, AI reasoning, distance_km
- Shows a loading spinner during the API call
- Shows an error message if the call fails
- Uses Tailwind CSS for styling
Show the component code and the exact API response shape it expects.
```

Save the generated component to `docs/design/dashboard-mockup.jsx`.
