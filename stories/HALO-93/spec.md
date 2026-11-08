# Feature Specification Document — HALO-93: The jungle page at `/jungle` with a "Hello World!" heading in the jungle design

_Traceability: Story HALO-93 · Epic HALO-91, "Jungle-themed 'Hello World!' page" (Epic PRD, Confluence, version 2) · Depends on HALO-92, the jungle page design (approved: structure, prototype and screens, 2026-11-02) · Target repo: ophirgal/test-repo-for-halo, branch `halo/feat/halo-93`._

## 1. Feature Overview

**Summary.** Add one new, separate page to the site at `/jungle`. It shows a large "Hello World!" heading (with the exclamation mark) on a deep-green jungle background, surrounded by original plant decorations: leaves, vines and bushes. It is built exactly to the approved jungle page design (HALO-92). The existing greeting page at `/` and its smoke test do not change. Every other address keeps returning "page not found".

**Problem statement.** Today the site has one plain greeting page at the root: "Hello World" in a plain heading on white, with no colour or decoration. Every other path returns 404. The product owner wants a memorable, colourful demo page in which the greeting is always fully readable, on desktop and on mobile. The Epic PRD's hypothesis (section 2) says this is achieved by placing the decorations around the heading, not over it, and by choosing heading colours that stand out from the background.

**Target users / actors.**
- **Visitor** (primary): anyone who opens `/jungle` in a browser, on desktop or on a mobile phone. There is no sign-in and nothing to do; they only look.
- **Product owner ("Ally PO & DEV")**: owns the demo page. They visually approve the delivered page on desktop and mobile. That approval is the leading indicator (Epic PRD, section 2) and step 4 of the future flow (section 3).

## 2. Goals & Non-Goals

### Goals
- G1. `/jungle` shows the approved jungle design. "Hello World!" is the one dominant heading, in jungle colours, surrounded by plant decorations.
- G2. The heading is always whole and readable. No decoration covers any letter, the contrast is at least 3:1, and there is no horizontal scrolling at 375px width.
- G3. The rest of the site is unchanged: the root page, its smoke test and the 404 behaviour for all other paths.
- G4. The page works with no external services, and it complies with the organization's licence and no-secrets rules.

### Non-Goals (out of scope)
- Any change to the existing greeting page at `/`, including a link from it to `/jungle` (Epic PRD, section 8).
- Pages other than `/jungle`. Every other address keeps returning "page not found".
- Any content beyond the heading: no other text, links, menu, buttons or forms.
- Animation, sound, interaction, animals, a custom or web font, or a background image (R13; Epic PRD, sections 7 and 8).
- Translating the greeting. It stays in English.
- Visitor analytics or tracking of any kind. This is forbidden by R10.
- Redesigning anything. The look is fixed by the approved HALO-92 design, and any visual change needs a new design approval.

## 3. Functional Requirements

- **FR1 — New address (R12).** A GET request for `/jungle` returns the jungle page successfully as an HTML page. The page is a new, separate page; it does not replace the root.
- **FR2 — Root unchanged (R12, RK5).** `/` keeps serving the existing greeting page exactly as it is today. Its heading is "Hello World" with no exclamation mark, and it has no link to `/jungle`. The existing smoke test (`smoke_test.py`) passes without any of its existing checks being changed or weakened.
- **FR3 — Other addresses unchanged (R12, RK5).** Every path other than `/` and `/jungle` returns "page not found" (404) and never a directory listing. Examples are `/jungle2`, `/other`, `/index.html`, `/docs/index.html`, `/README.md` and `/foo/bar`. No file in the repo becomes reachable through a new address.
- **FR4 — Single main heading (R1, R2).** The page's only heading is the exact text `Hello World!`, including the exclamation mark. It is horizontally centred and is the largest element on the page.
- **FR5 — Tab title (R8).** The browser tab title includes "Hello World". The approved design specifies `Hello World! · Jungle`. The page declares English as its language.
- **FR6 — Jungle palette (R3).** The background, heading and decorations use only these colours from the approved design:
  - Deep green `#0F3D2E`: the background
  - Deep green glow `#155239`: a radial glow behind the heading
  - Forest green `#1B5E3A`, leaf green `#3E8E41` and light leaf green `#6DBE45`: the leaves and bushes
  - Earth brown `#6B4423`: the vine stems
  - Dark earth brown `#4A2F1A`: the ground strip
  - Yellow `#F2C230`: the heading and the flowers
  - Orange `#E8772E`: the berries and the flowers
- **FR7 — Plant decorations (R4).** The page has the approved decoration set: leaf clusters in the corners, side vines with leaves, and bushes along a ground strip, with yellow and orange flowers and berries. All of them are placed around the heading.
- **FR8 — Static page (R13).** No motion, sound or interaction. The page has no links, buttons, forms or visible text other than the heading. Decorative graphics add no visible text and are hidden from assistive technology as decoration.
- **FR9 — Self-contained (R11).** Everything the page needs to look as designed is delivered with it. Its colours, decorations and font come from the page itself: the system bold font and original inline graphics. The page makes no request to any other host.
- **FR10 — Compliance (R9, R10).** Every graphic and font is original, or the system font. Nothing in the page uses a non-permissive licence. The page has no keys, passwords, trackers or personal data.

**Inputs / outputs.** Input: the visitor's browser requests `/jungle`. Output: the rendered jungle page. There is no user input of any kind.

**Edge cases.**
- Narrow screen (375px): see section 4, "Mobile".
- Window widths between and beyond 375px and 1440px: the layout scales smoothly between the two reference designs. The heading stays whole and uncovered at every width (R5).
- A browser with no access to external hosts: the page renders fully (FR9).
- Similar-looking paths, such as `/jungle2` or `/jungles`: return 404 (FR3).

## 4. User Experience & Behavior

**Flow (Epic PRD, section 3, steps 1–3).**
1. The visitor opens `/jungle` on desktop or mobile.
2. The page appears: a deep-green background with the large yellow "Hello World!" heading in the middle, surrounded by plant decorations.
3. The visitor looks. There is nothing else to do.

There is one state: the page as rendered. There are no transitions.

**Look and feel. This is the approved HALO-92 design; each item is checkable.**
- **Background:** solid deep green `#0F3D2E`, with a soft radial glow in `#155239` behind the heading.
- **Heading:**
  - `Hello World!` in yellow `#F2C230`, in the system bold font. No custom font.
  - Weight 800, line height about 1.05, slightly tight letter spacing (-0.01em).
  - Centred, and clearly the largest element on the page.
- **Desktop (1440px reference):**
  - Heading size: about 130px at a 1440px-wide window, scaling with the width (9% of the width).
  - Heading layout: on one line.
  - Corner leaf clusters: about 21% of the width each.
  - Side vines: about 4% wide, inset about 1.5% from the edges.
  - Bushes: along the bottom, about 13% of the height, above the dark-brown ground strip.
  - Clear space around the heading: about 16% at the sides and 12% at the bottom.
- **Mobile (375px):**
  - Heading size: about 71px at 375px (19% of the width).
  - Heading layout: wraps onto two lines, "Hello" / "World!".
  - Corner leaves: shrink to about 34% of the width.
  - Bushes: shrink to about 24%.
  - Side vines: hidden.
  - Side padding: about 16px.
  - No horizontal scrolling, and the heading is never cut off.
- **Readability:** heading contrast is at least 3:1 against the background beneath it (R6). The approved colours give about 7.3:1 on `#0F3D2E` and about 5.4:1 on the glow `#155239`.
- **Decorations never cover any letter** of the heading at any width (R5, RK1).
- **Accessibility:** the page language is English. The heading is the only content exposed to assistive technology, and the decorations are marked as decorative.
- **Static:** no animation, transitions, hover effects or sound.

**Errors the user can see.** Any other address shows the existing "page not found" response, unchanged. There are no other user-facing errors.

## 5. Acceptance Criteria

Each criterion maps to the story's scenario of the same number (Hebrew story template, Given/When/Then).

- **AC1 — Desktop, normal path.**
  - Given a desktop browser, when it opens `/jungle`, the page loads successfully as HTML.
  - Its only heading is exactly `Hello World!`, centred and the largest element.
  - The background, heading colour, decorations and their placement match the approved HALO-92 desktop screen (`stories/HALO-92/design/screens/jungle-page.default.html`), with colours exactly as in FR6.
  - The tab title contains "Hello World" (designed as `Hello World! · Jungle`).
- **AC2 — Mobile 375px, edge case.**
  - Given a 375px-wide viewport, when it opens `/jungle`, "Hello World!" is shown whole, wrapped as "Hello" / "World!".
  - There is no horizontal scrolling.
  - No decoration overlaps any letter.
  - The corner leaves and bushes are reduced and the side vines are hidden, as in the approved mobile screen (`jungle-page.default.mobile.html`).
- **AC3 — Readability and static content.**
  - The heading-to-background contrast is at least 3:1, both on `#0F3D2E` and on the glow `#155239`.
  - The page contains no animation, sound, `<a>`, `<button>`, `<form>` or any visible text other than the heading.
- **AC4 — Scope boundary.**
  - `/` returns the existing greeting page byte-for-byte unchanged: "Hello World" with no exclamation mark and no link to `/jungle`.
  - `python3 smoke_test.py` passes with all of its existing assertions intact.
  - `/jungle2` and `/other` (and the existing 404 paths) return 404, with no directory listing.
- **AC5 — No external access, error case.**
  - With every host other than the site blocked, `/jungle` renders fully with the designed colours and decorations.
  - The page source references no external URL, font, script, stylesheet or image.
  - It contains no keys, passwords, trackers or personal data.
- **AC6 — Licensing.**
  - Every font and graphic on the page is original or the system font.
  - No component carries a licence other than MIT, BSD or Apache-2.0.
  - The PR states this.
- **AC7 — Product owner's visual approval (Epic PRD, section 2 and step 4).** The product owner confirms on desktop and at 375px that the page "looks like a jungle" and that the heading is readable.
- **AC8 — Traceability and gate (engineering requirements R3, R7).** The PR names HALO-93, epic HALO-91 and the Epic PRD. It merges only when the required checks are green; today that is the smoke test. Nothing is merged by hand.

**Verification.** STRUCTURE decides how much of AC1–AC5 the extended smoke test covers automatically: the route, the 200/404 results, the title, the single heading, no forbidden elements, and no external URLs. Pixel-level appearance, the 375px render and AC7 are checked manually in a browser.

## 6. Dependencies & Constraints (product-level)

- **Depends on:**
  - HALO-92, the jungle page design. It is approved, so this dependency is met. Its tokens, layout tables and screens are the visual source of truth.
  - The existing greeting page and its smoke test, which already work. They must stay untouched.
- **Affects:** nothing else. HALO-93 is the last story in the epic, and no story depends on it.
- **Organizational constraints** (Confluence, "Engineering requirements — infrastructure, security, compliance"):
  - Permissive licences only (MIT, BSD, Apache-2.0).
  - No new runtime dependency unless the PRD names it. The page should need none.
  - No secrets or personal data in the code, tests or commits.
  - CI gate: every required check green, and nothing merged by hand.
  - Every PR names its story and its PRD.
  - If Python is touched, it must keep the CPython version the project already declares.
- **Product constraints:**
  - The greeting stays in English.
  - Plants only: no animals.
  - No custom font and no background image.
  - The page is not linked from anywhere.

## 7. Technical Design (deferred to STRUCTURE)

The tech lead designs the solution from this spec. Constraints the product imposes, which STRUCTURE resolves:
- **Routing:** the server must serve `/jungle` without picking files from the request path. This keeps today's guarantee and keeps safe-file-handling requirement R5 out of play. Every other path must keep returning 404, with no listing.
- **Root page and test:** `docs/index.html` and the existing smoke-test assertions must not change. New checks may be added.
- **Adapting the design:** the HALO-92 screens show the page inside framed previews (16:9 desktop, 375×720 mobile) with review chrome around them. The delivered page must fill a real browser window without the chrome, and scale smoothly between the 375px and 1440px references.
- **No fixed widths:** avoid a fixed width wider than 375px, so the mobile no-scroll requirement and any reused width check hold.
- **Hosting:** whether `docs/` is also published as a static site (e.g. GitHub Pages), and whether `/jungle` must work there too.

## 8. Open Questions (non-blocking, for STRUCTURE)

- **OQ1.** `/jungle/` (trailing slash): should it serve the page or return 404? The story doesn't say. The spec only requires `/jungle` to work and look-alike paths such as `/jungle2` to return 404. A query string (`/jungle?x=1`) and HEAD requests are assumed to behave like `/jungle`, matching how the root behaves today.
- **OQ2.** Must `/jungle` also work on a static-hosting copy of `docs/` (there is a `.nojekyll` file)? The default assumption is that `serve.py` is the site.
- **OQ3.** How should the page behave in windows with unusual proportions (very tall or very short)? The design only fixes 1440 and 375 widths. Whatever the proportions, R5 (no letter covered) and R7 (no horizontal scroll at 375px) still apply.
