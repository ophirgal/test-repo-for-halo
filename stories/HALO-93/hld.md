# HLD — HALO-93: Jungle page at `/jungle`

_Traceability: Story HALO-93 · Epic HALO-91 (Epic PRD, Confluence v2) · Design HALO-92 (approved 2026-11-02, `stories/HALO-92/design/`) · Repo ophirgal/test-repo-for-halo, branch `halo/feat/halo-93`._

## 1. System Overview
- **What we're building:** a second static page, `/jungle`. It shows the large yellow "Hello World!" heading on a deep-green background, framed by original inline-SVG plant decorations, built to the approved HALO-92 design.
- **Problem:** the site serves exactly one document at `/` and returns 404 for everything else. We need one new address, and nothing else may become reachable (RK5).
- **Responsibilities:**
  - serve `/jungle` (GET/HEAD, query string ignored) from a fixed file
  - keep `/` byte-identical
  - keep every other path a 404 with no directory listing
  - make the page fully self-contained (no external requests, no secrets, original graphics only)

## 2. Architecture Overview
- **`serve.py`** (stdlib `http.server`). The existing handler, `RootOnlyHandler`, gains an exact-match table from request path to a constant file path: `/` → `docs/index.html` (existing), `/jungle` → `docs/jungle.html` (new).
  - Paths are fixed when the module loads and are never derived from the request.
  - The class name and the `make_server` signature are unchanged, because `smoke_test.py` imports them.
- **`docs/jungle.html`** (new). One self-contained HTML document: `lang="en"`, viewport meta tag, title `Hello World! · Jungle`, inline `<style>`, inline `aria-hidden` SVG decorations copied from the HALO-92 screens, and a single `<h1>`.
  - No `<link>`, `<script>`, `<img>`, `@import`, `url(...)`, web font or external URL (and no SVG `xmlns`).
- **`smoke_test.py`.** Checks are only added. Existing checks and the `NON_ROOT_PATHS` list stay unchanged.
- **`docs/index.html`, `README.md`, `hello_world.txt`:** untouched.
- **External dependencies:** none. No new runtime or test dependency; the code stays valid on Python 3.11.

## 3. Data Flow
1. The browser sends `GET /jungle` (or HEAD, or `/jungle?x=1`).
2. The handler takes the path part of the URL and looks it up in the exact-match table.
3. On a hit, it reads the constant file and sends 200, `text/html; charset=utf-8`, `Content-Length`, and the body (GET only).
4. On a miss, it calls `send_error(404)` and returns the standard error page, with no listing.
5. The browser renders everything from the one response. Nothing else is requested.

There is no state, no persistence, and no asynchronous or event processing.

## 4. Component Breakdown
| Component | Responsibility | Inputs / Outputs | Repo |
|---|---|---|---|
| Route table in `serve.py` | Map `/` and `/jungle` to fixed files; 404 for everything else | HTTP request path → 200 with file, or 404 | ophirgal/test-repo-for-halo |
| `docs/jungle.html` | Jungle page: heading, palette, decorations, responsive layout | static file → rendered page | ophirgal/test-repo-for-halo |
| `smoke_test.py` additions | Automated checks for the new route, page content and boundaries, plus the root regression | runs server in-process → pass/fail | ophirgal/test-repo-for-halo |

## 5. Interface Contracts
- `GET /jungle` and `GET /jungle?<any>`: 200, `text/html; charset=utf-8`, body = `docs/jungle.html`.
- `HEAD /jungle`: 200, same headers, no body.
- `GET /`: unchanged; the body is byte-identical to `docs/index.html`.
- Any other path returns 404 and never a listing. That includes `/jungle/`, `/jungle2`, `/jungles`, `/other`, `/jungle.html`, `/docs/jungle.html` and the existing `NON_ROOT_PATHS`.
- Python surface: `serve.RootOnlyHandler`, `serve.make_server(host, port, handler=...)` and the `python3 serve.py` / `PORT=` / `HOST=` docstring text are all kept. The docstrings' "root-only" / "exactly one document" wording is updated to describe two fixed pages.

## 6. Key Technical Decisions
- **Exact-match table of constants**, not `SimpleHTTPRequestHandler`, prefix matching or folder serving. This keeps today's guarantee that no path is ever built from the request. _Alternatives rejected:_ serving `docs/` as a folder, and `startswith('/jungle')`. Both open new addresses (RK5).
- **Inline everything.** The HALO-92 note says "one stylesheet", but a second URL such as `/jungle.css` would break FR3. All CSS goes inline in the page. _Tradeoff:_ no caching. That's irrelevant for a demo page.
- **Translating the design's frames to a real window:**
  - Drop the review chrome (`.review-bar`, notes, captions, links) and the fixed 375×720 / 16:9 frames.
  - The page fills the window: at least one screen tall (`100vh`, with `100dvh` where supported). The heading is centred with flex.
  - Decorations are absolutely positioned in the corners, on the sides and along the bottom, below the heading in the stacking order, with `pointer-events:none`.
- **Units.** Use `vw` (or `cqw` on a full-width container; the implementer chooses) to reproduce the design's percentages. Desktop: heading 9vw on one line, corner leaves 21vw, vines 4vw at a 1.5vw inset, bushes 13vw, side clearance about 16vw, bottom clearance about 12vw. No fixed width over 375px in px or pt, so the existing width regex would also pass on this page.
- **One mobile breakpoint**, a max-width media query (implementer's choice, about 600–700px). It switches to: heading 19vw split into "Hello" / "World!", corner leaves 34vw, bushes 24vw, vines hidden, 16px side padding.
  - The heading always keeps its no-overlap clearance. It sits in a padded stage whose padding is at least the decoration footprint, so decorations stay in the margins.
- **Short or tall windows (OQ3).** The page grows to fit its content instead of letting decorations overlap the heading. Vines are sized against the page height, not a 16:9 assumption.
- **Accessibility.** The heading is split into two `<span>`s and is read as one "Hello World!". All SVGs are `aria-hidden="true"` and contain no `<text>`.
- **Palette:** only the FR6 hex values appear in the page's CSS and SVG. The smoke test enforces this with an allow-list.

## 7. Risks & Constraints
- **RK5, regression or route widening.** Mitigation: exact matching, plus new smoke checks for look-alike 404 paths and a byte-identical `/`.
- **RK1, decorations covering the heading at in-between or unusual sizes.** Mitigation: decorations stay in the padded margins, and the page is checked by hand at 375, about 768, 1024 and 1440 px and on a short landscape window. No browser automation (no new dependencies), so this check stays manual and is recorded in the PR.
- **RK2, contrast.** The yellow `#F2C230` is about 7.3:1 on `#0F3D2E` and about 5.4:1 on `#155239`, both above 3:1, and fixed by the palette.
- **Copying the screens as-is** would bring in links, captions and the relative `tokens.css` `<link>`. Only the SVGs, the heading markup and the `.frame` rules carry over.
- **No CI in the repo.** "Required checks" means `python3 smoke_test.py`, as for KAN-8. This story creates no CI.
- **Hosting (OQ2):** `serve.py` is the site. GitHub Pages behaviour for `/jungle` is out of scope.
- **Python:** no version is declared, so stay within 3.11 syntax and the standard library only.

## Resolved open questions (assumptions)
- **OQ1:** `/jungle/` → 404. Exact match, consistent with how `/` is handled today.
- **OQ2:** static hosting is out of scope.
- **OQ3:** the page grows to fit; no overlap at any proportions.

## Build order
One PR (t1). It owns `docs/jungle.html`, the route change in `serve.py` and the added smoke checks, merged together so `main` stays green.
