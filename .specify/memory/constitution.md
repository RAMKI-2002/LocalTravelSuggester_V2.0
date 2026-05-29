# Project Constitution — Local Travel Suggester

## Governing Principles

This is the non-negotiable governing document for the Local Travel Suggester project.
The AI reads this before every session. All agents, skills, and commands follow these principles.

## Project Identity

**Name:** Local Travel Suggester v2.0  
**Domain:** AI-powered travel recommendations  
**Stack:** FastAPI (Python 3.11+) + React (JS) + SQLAlchemy + AWS Bedrock  
**Purpose:** Deliver weather-aware, intent-driven trip suggestions with user authentication and history

## Core Principles

### 1. API-First
Every feature starts with an API contract. The Pydantic `response_model` is defined before implementation begins.
No endpoint ships without a declared response schema.

### 2. Test-First (TDD)
No implementation ships without tests written first.
Tests are written in RED state, then implementation turns them GREEN.
Backend API coverage must stay ≥70%.

### 3. Security by Default
All endpoints require authentication unless explicitly marked public.
Passwords are hashed with bcrypt. Never returned in any response.
All secrets loaded from environment variables. Never hardcoded.

### 4. Simplicity Over Cleverness
If a simpler implementation satisfies the requirement, choose the simpler implementation.
Fewer files, explicit code, clear naming.
Every architectural decision must be explainable in 60 seconds.

### 5. Observability
Every endpoint emits structured JSON logs with request_id, user_id, and duration.
Health endpoints must accurately reflect dependency status.
Errors are logged with full context, never silently swallowed.

## Scope

**In scope:**
- User authentication (register, login, JWT)
- Weather-aware trip recommendations (OpenWeatherMap + Foursquare/Overpass)
- Intent parsing (rule-based + optional AWS Bedrock LLM)
- Per-user trip history
- Interactive map display (Leaflet)

**Out of scope (unless added via OpenSpec change):**
- Social features (sharing, ratings)
- Mobile app
- Real-time updates / WebSockets
- Payment or booking integration

## Quality Standards

- Backend test coverage: ≥70%
- API response time P50: <2s (mock LLM) / <8s (real Bedrock)
- All code must pass `pytest` and `ruff` before commit
- All security findings at HIGH/CRITICAL must be resolved before any PR

## Change Management

All new features or API contract changes go through OpenSpec (`/opsx:propose`).
No ad-hoc changes to existing endpoints without a proposal.md.
