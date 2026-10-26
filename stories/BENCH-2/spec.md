# In-Progress Ticket Draft — BENCH-2

## Status: NOT READY — Blocked on P0 questions

## Story

**Title:** Last-login line on the user profile page

**As a** signed-in user of the customer portal viewing my profile page,
**I want** to see the date and time of my previous sign-in,
**so that** I can notice unexpected account access at a glance.

## Scope (as stated)

**In scope:** Displaying the previous sign-in timestamp formatted per the user's locale and time zone; displaying "Last login: first sign-in" for first-time users.

**Out of scope:** Login history lists, alerts, admin views, changes to the sign-in flow, new API endpoints.

## Pre-conditions (as stated — ALL UNMET)

- [ ] The sign-in audit table records every successful sign-in with a timestamp — **DOES NOT EXIST**
- [ ] The user's locale and time zone are available from the existing profile or session data — **DOES NOT EXIST**
- [ ] A user profile page showing the user's name — **DOES NOT EXIST**
- [ ] Authentication and session management — **DOES NOT EXIST**

## Acceptance Criteria (well-formed but unverifiable against current codebase)

1. **Happy path: returning user** — Given a signed-in user with ≥2 audit records, when viewing profile, then "Last login" line shows previous sign-in timestamp formatted per user locale/TZ.
2. **Edge case: first-time user** — Given a signed-in user with only the current session record, when viewing profile, then line reads "Last login: first sign-in".
3. **Edge case: missing locale/TZ** — Given a user without locale/TZ preferences, when viewing profile, then timestamp uses portal-wide defaults.
4. **Boundary: all signed-in users** — The line is visible regardless of account age, role, or locale.
5. **Boundary: no sign-in flow change** — Sign-in steps, duration, and behavior are identical before and after deployment.

## Blocking Questions

See P0-1, P0-2, P0-3 in the message above. These must be resolved before a specification can be produced.
