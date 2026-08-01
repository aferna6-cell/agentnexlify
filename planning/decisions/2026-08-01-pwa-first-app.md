# PWA-first downloadable app — reverses the mobile non-goal

**Date:** 2026-08-01
**Status:** Accepted (owner decision, this session)
**Supersedes:** the "iOS / native mobile app — desktop-first; mobile is 'much later'" non-goal in `specs/agent-os-overhaul_spec.md` (lines 42 + 344).

## Decision

Ship the "downloadable app" as an installable PWA on the existing `frontend/`
dashboard, not a native build. Capacitor (mobile) / Tauri (desktop) wrappers
are a later, optional packaging step if app-store presence becomes
commercially necessary. Native development only if a capability demands it.

## Context

Owner goal (2026-08-01): AgentNexLiFy as a personal-assistant app you can
download on computer and phone, with easier setup than self-hosted
alternatives. The server already does all monitoring (inbox poll, SMS agent,
social scheduler run server-side) — the client is a viewport plus a
notification surface, which is the workload PWAs handle best.

## What PWA-first means concretely

1. **Installable** on desktop (Chrome/Edge install prompt) and iOS
   (Add to Home Screen): `manifest.webmanifest` with square 192/512 icons
   (Chrome installability requirement — the old 675x426 logo entry never
   fired the prompt), standalone display, `/dashboard` start URL, existing
   apple-touch-icon + `apple-mobile-web-app-capable` meta.
2. **Push notifications** via the existing web-push stack
   (`backend/routers/push_subscriptions.py`, `os_push_notify.py`, `sw.js`):
   VAPID keys provisioned in Railway; OS approval pushes (pre-existing) plus
   escalation pushes (`escalations._notify_owner_async` push leg, added with
   this ADR). iOS supports web push for installed PWAs (16.4+).
3. **No offline caching** — `sw.js` stays push-only on purpose ("keep
   deploys boring"). The dashboard is useless without the API; an offline
   shell adds cache-invalidation risk for no real capability.

## Rejected alternatives

- **Native iOS/Android first**: weeks of build + app-store review for a
  client that is a thin viewport; blocks iteration speed.
- **Electron desktop**: heavyweight for a dashboard; PWA install covers it.
- **Do nothing (keep non-goal)**: owner explicitly reprioritized.

## Consequences

- `specs/agent-os-overhaul_spec.md` non-goal lines are superseded by this ADR.
- App-store distribution (if ever) wraps the same frontend via Capacitor —
  no second codebase.
- Push requires VAPID keys in the backend environment; without them the
  stack degrades gracefully (subscribe endpoint 404s, notifications simply
  don't fire).
