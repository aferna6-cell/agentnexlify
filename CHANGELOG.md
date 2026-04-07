# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- POST endpoint for appointment slots (`/api/v1/appointments/slots/{id}`) to avoid API key exposure in URLs
- 15-second fetch timeouts on all widget API calls with AbortController
- Password strength validator (10+ chars, uppercase, lowercase, number)
- Timing attack prevention on login endpoint (dummy bcrypt hashing)
- Frontend test suite with Vitest and @testing-library
- Canonical database schema reference (`docs/dev-knowledge/canonical-schema.md`)
- Migration 094 to reconcile 8 ad-hoc columns on `leads` table that existed in production but had no migration files

### Changed
- Bcrypt rounds increased from 12 to 14 (OWASP 2024+ recommendation)
- Widget file upload and appointment slot booking now send API keys in request body instead of URL query params
- Widget files in `frontend/public/widget/` are now symlinks to `widget/` (prevents drift)
- `AGENTS.md` updated to reference canonical schema and symlink approach

### Fixed
- Null checks added to all DOM element access in widget (prevents crashes on missing elements)
- Message counter now resets correctly on session reset
- Frontend test for API client 401 redirect behavior

### Security
- API keys no longer appear in server logs, browser history, or CDN logs
- Login endpoint response time is consistent whether email exists or not (prevents user enumeration)
- Stronger password requirements for new accounts

---

## [0.1.0] — 2026-04-07

Initial versioned release (pre-production beta).

### What exists
- Multi-tenant SaaS platform with FastAPI backend
- React/Vite frontend dashboard
- Embeddable JavaScript chat widget with lead capture and appointment booking
- Stripe billing integration (free/growth/professional/autopilot/enterprise plans)
- Supabase database with Row Level Security
- AI-powered lead qualification using Anthropic Claude
- Marketing campaigns, email sequences, social media scheduling
- Team member management with role-based access
- Local SEO, review management, CSAT surveys
- Pipeline automation and smart lists
- 94 database migrations
- 305+ backend tests
- 13 frontend tests

### Notes
- This version tag is retrospective. The project has been under active development since March 2026.
- First tag applied after 586+ commits to establish versioning discipline going forward.
