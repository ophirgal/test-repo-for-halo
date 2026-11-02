# Implementation Plan — HALO-93: Jungle page at `/jungle`

## Context

HALO-93 adds a second static page at `/jungle`. It shows a single yellow `<h1>` reading "Hello World!" on a deep-green background, framed by original inline-SVG leaves, vines and bushes. It is built to the approved HALO-92 design. `/` stays byte-identical, and every other path stays a 404 with no listing. The acceptance criteria in brief:
- AC1: desktop render matches the design.
- AC2: at 375px the heading wraps "Hello" / "World!", with no horizontal scroll and no overlap.
- AC3: contrast of at least 3:1, and the page is static.
- AC4: `/`, the existing smoke test and other paths' 404s are unchanged.
- AC5: no external requests, no secrets.
- AC6: original graphics and the system font only.
- AC7: the product owner's visual approval.
- AC8: PR traceability, and merge only on a green smoke test.

The change lands in `ophirgal/test-repo-for-halo` on branch `halo/feat/halo-93`. `spec.md`, `hld.md` and `work-items.md` sit beside this file in `stories/HALO-93/`. The design source is `stories/HALO-92/design/screens/`.

## Research findings

**Repository state (fact).**
- Files: `serve.py`, `smoke_test.py`, `docs/index.html`, `docs/.nojekyll`, `README.md`, `hello_world.txt`, plus `stories/` and `docs/plans/_.txt`.
- No `AGENTS.md`, `CLAUDE.md`, `.factory/`, manifest, linter or CI configuration.
- The local interpreter is Python 3.13.1. No version is declared, so the HLD's 3.11 ceiling applies.
- `python3 smoke_test.py` currently prints `OK: 28 checks passed`.

**Change surface.**
- `serve.py:2-7`: the module docstring says "Root-only HTTP server" and "Serves exactly one document". Both must change. The usage block at `serve.py:9-15` holds `python3 serve.py`, `PORT=` and `HOST=`, which `smoke_test.py:96-102` asserts.
- `serve.py:32`: `INDEX = Path(__file__).resolve().parent / "docs" / "index.html"`, a fixed path.
- `serve.py:35-66`: `RootOnlyHandler(http.server.BaseHTTPRequestHandler)`.
  - `_is_root()` (`:45-46`) compares `urllib.parse.urlsplit(self.path).path == "/"`.
  - `_send_index_headers(body)` (`:48-52`) sends 200, `Content-Type: text/html; charset=utf-8` and `Content-Length`.
  - `do_GET` (`:54-60`) and `do_HEAD` (`:62-66`) call `send_error(404)` on a miss.
  - The class docstring (`:36-41`) says "Answer `/` … everything else with 404".
- `serve.py:69`: `make_server(host=DEFAULT_HOST, port=DEFAULT_PORT, handler=RootOnlyHandler)`.
- `serve.py:92`: the start-up message prints only the root URL. It is cosmetic and needs no change.

**Contracts consumed by `smoke_test.py` (must stay stable).**
- `serve.DEFAULT_HOST`, `serve.DEFAULT_PORT`, `serve._resolve_port`, `serve.__doc__`, `RootOnlyHandler` and `make_server` (`smoke_test.py:19-20, 74-102, 201`).
- `NON_ROOT_PATHS` (`smoke_test.py:22-28`).
- Helpers: `get(base, path)` returns decoded text (`:61-67`), `head(base, path)` returns the status (`:51-58`), and the `Checks` collector (`:37-48`).

**Width regex hazard (fact).**
- The width check at `smoke_test.py:152-158` uses `r"(?:\bmin-)?width\s*[:=]\s*\"?(\d+(?:\.\d+)?)\s*(px|pt)"`. The pattern has no leading word boundary on `width`.
- So `max-width:640px` in a media query matches and fails (640 > 375).
- The design's `width:375px` on `.frame--mobile` passes, but it is review chrome that is being dropped anyway.
- Unitless SVG attributes such as `width="1440"` and `stroke-width="4"` do not match.
- Consequence: the jungle page's breakpoint must be written in `em`/`rem` (for example `@media (max-width: 40em)`). Any px value must be 375 or less.

**Design source (fact).**
- `stories/HALO-92/design/screens/jungle-page.default.html` and `.mobile.html` carry byte-identical inline SVGs. There are five: `deco-tl`, `deco-tr`, `deco-vl`, `deco-vr` and `deco-bush` (`jungle-page.default.html:14-50`).
- Each SVG is `aria-hidden="true"`, has no `xmlns` and no `<text>`, and uses only the nine FR6 hex values as literal `fill`/`stroke`.
- The heading markup is `<h1 class="hello"><span>Hello</span> <span>World!</span></h1>` (`:52`).
- The page CSS is `tokens.css:56-80`: `.frame`, `.stage`, `h1.hello`, `.deco`, and the `--desktop`/`--mobile` modifiers in `cqw`.
- The background is `radial-gradient(ellipse 60% 55% at 50% 50%, #155239 0%, #0F3D2E 100%)`.
- Review chrome to drop: `<link rel="stylesheet" href="tokens.css">` and the `<a>` pills at `:3-8`, captions and notes, `rgba(...)` box-shadows, `border-radius`, and the fixed `375px`×`720px` and 16:9 frames.
- HALO-92 approvals (structure, prototype, screens) are recorded in `stories/HALO-92/design/approval.json`.

**What must be created:** `docs/jungle.html`. **What must change:** the routing and docstrings in `serve.py`, plus additive checks and one helper in `smoke_test.py`.

**External data:** none. **Remaining unknowns:** none that block the build. Pixel fidelity, the 375px render and the product owner's approval can only be checked manually (no browser automation; adding one would be a new dependency).

## Locked decisions and assumptions

**Locked decisions**
- Exact-match route table of fixed paths: `/` → `docs/index.html` and `/jungle` → `docs/jungle.html`. The query string is ignored, GET and HEAD route identically, and no path is ever built from the request (hld.md §2, §6; spec §7).
- `/jungle/`, `/jungle2`, `/jungles`, `/other`, `/jungle.html` and `/docs/jungle.html` return 404 (hld.md OQ1 and §5; work-items.md t1).
- Keep the `RootOnlyHandler` name, the `make_server` signature, the `NON_ROOT_PATHS` list and all 28 existing assertions (work-items.md "Must not change").
- Do not touch `docs/index.html`, `README.md` or `hello_world.txt` (spec FR2; work-items.md).
- A single self-contained page:
  - All CSS is inline, with no second URL such as `/jungle.css`.
  - It has `lang="en"`, the viewport meta tag and the title `Hello World! · Jungle`.
  - It contains none of the forbidden tokens listed in t1.
  - (hld.md §2, §6; spec FR5, FR9.)
- Palette allow-list: `#0F3D2E`, `#155239`, `#1B5E3A`, `#3E8E41`, `#6DBE45`, `#6B4423`, `#4A2F1A`, `#F2C230`, `#E8772E` (spec FR6).
- Layout values: desktop heading at 9vw on one line, corners 21vw, vines 4vw with a 1.5vw inset, bushes 13vw, about 16vw side and 12vw bottom clearance. Mobile: heading at 19vw split into two lines, corners 34vw, bushes 24vw, vines hidden, 16px side padding (spec §4; hld.md §6).
- The page grows to fit its content instead of letting decorations overlap on short or tall windows (hld.md OQ3).
- `/jungle` hosting via GitHub Pages is out of scope (hld.md OQ2).
- The gate is `python3 smoke_test.py`, and the repo has no CI (hld.md §7).

**Assumptions**
- *Breakpoint unit is `em`.* Evidence: the width regex at `smoke_test.py:155` matches `max-width:<n>px`. If a px breakpoint over 375 is used, the new width check on the jungle body fails. The existing check on `/` would be unaffected.
- *`cqw` vs `vw`.* Use `vw` on a full-window page, or `cqw` on a full-width `container-type:inline-size` wrapper; either matches the design. Evidence: the HLD leaves the choice to the implementer. If wrong, there is only a visual difference: `vw` includes the scrollbar width on desktop, at most about 1%.
- *Byte-identical root check.* Compare the raw GET bytes against `serve.INDEX.read_bytes()` through a new byte-returning helper. The existing `get()` decodes with `"replace"`, so it cannot prove byte equality. If wrong, the check is weaker but still detects any content change.
- *A route table as a module constant* (new name `ROUTES`, a dict of `str` → `Path`) lets a smoke check assert that the only servable files are `INDEX` and `JUNGLE`. `ROUTES` and `JUNGLE` are new names; none exist today. If a reviewer prefers another name, it is a cosmetic rename.

## Solution proposal

**Approach.** Extend the existing stdlib server; do not replace it.
- In `serve.py`, add a constant `JUNGLE` next to `INDEX` and a module-level `ROUTES = {"/": INDEX, "/jungle": JUNGLE}`.
- Replace `_is_root()` with a lookup that returns `ROUTES.get(urllib.parse.urlsplit(self.path).path)`.
- `do_GET`/`do_HEAD` keep their shape: on a miss they call `send_error(404)`; on a hit they read the constant file and reuse the existing 200 header helper. Renaming `_send_index_headers` is optional.
- Rewrite the docstrings to describe "two fixed pages" while keeping the usage block verbatim.

`docs/jungle.html` is one HTML document built from the HALO-92 screens:
- the five SVGs copied verbatim, with no recolouring;
- the heading markup from `:52`;
- an inline `<style>` adapted from `tokens.css:56-80` to a real window.

The window adaptation:
- `body` is the frame: the radial gradient, `min-height:100vh` then `100dvh`, `overflow-x:hidden`, `position:relative`, the system font stack. Font-stack names are not colours.
- The stage is a flex-centred block in normal flow. Its padding equals the decoration footprint (top ≥ corner height, sides ≥ 16vw, bottom ≥ 12vw on desktop), so the page grows rather than letting decorations overlap the heading.
- Decorations are `position:absolute`, `z-index:1` and `pointer-events:none`. The heading is `z-index:2`.
- Vine height is computed from the page height (`top` and `bottom` insets, not `calc(100% - 28cqw)` against a 16:9 frame).
- One `@media (max-width: 40em)` block switches to the mobile values. It also sets `h1 span{display:block}` and hides `.deco-vl`/`.deco-vr`.
- The only declared colours are the FR6 hex values. Use no `rgba()`, no named colours, and no `transition`, `animation` or `:hover`.

`smoke_test.py` only gains checks. They append to `run_checks` after the existing ones, which stay byte-for-byte unchanged, plus one helper that returns raw bytes.

**Key decisions.**
- Exact match over prefix or folder serving: it keeps the existing no-path-from-request guarantee (RK5).
- Inline CSS over a stylesheet route: a second URL would widen the route surface and break FR9's self-containment.
- Copy the SVGs verbatim: the approved palette and shapes are preserved, and licensing stays "original" (AC6).
- `em` breakpoint: compatible with the reused width regex.

**Rejected alternatives.**
- `SimpleHTTPRequestHandler` over `docs/`: exposes `/jungle.html`, `/index.html` and listings.
- `startswith("/jungle")`: opens `/jungle2`.
- Serving `tokens.css` as-is: carries the chrome, `rgba`, `:hover` and fixed px frames.
- Browser-based visual tests: a new dependency and a new test layer.

## Ordered implementation steps

1. **Create `docs/jungle.html` (new)** — AC1, AC2, AC3, AC5, AC6. Covered by the new smoke checks (step 4) and the manual browser check (step 6).
   - `<!DOCTYPE html>`, `<html lang="en">`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<title>Hello World! · Jungle</title>`.
   - One inline `<style>` as described in the Solution proposal.
   - `<body>` holds the five SVGs, copied from `stories/HALO-92/design/screens/jungle-page.default.html:14-50`, keeping `aria-hidden="true"`, `viewBox` and `preserveAspectRatio`. After them comes the stage holding `<h1><span>Hello</span> <span>World!</span></h1>`.
   - No other text node, and no `xmlns`, `<a>`, `<link>`, `<script>` or `url(`.
2. **Route `/jungle` in `serve.py`** — AC1, AC4. Covered by the smoke test (step 4).
   - Add `JUNGLE = Path(__file__).resolve().parent / "docs" / "jungle.html"` and `ROUTES` after `serve.py:32`.
   - Replace `_is_root` (`:45-46`) with a target lookup through `ROUTES`. Update `do_GET`/`do_HEAD` (`:54-66`) to serve the looked-up constant path and keep `send_error(404)` on a miss.
   - Do not call `Path(...)`, `os.path` or `open` with any part of `self.path`.
   - Validation and error path: unknown paths, trailing slashes, `..` sequences and look-alikes all miss the exact match and return 404. There is no authorisation, tenancy or shared mutable state. Each request only reads a constant file, so `ThreadingHTTPServer` concurrency is safe.
3. **Update the `serve.py` docstrings** (`:2-7`, `:36-41`) — AC4 and t1's docstring criterion. Covered by the existing check at `smoke_test.py:96-102` (usage block kept) and a new check (step 4).
   - Remove "Root-only" and "exactly one document". Describe `/` and `/jungle` as the two fixed pages, with 404 for everything else.
   - Keep lines `:9-20` (usage) unchanged.
4. **Extend `smoke_test.py` with additive checks** — AC1–AC5, AC8. Layer: the existing stdlib HTTP smoke test, the repo's only test layer.
   - Add `get_bytes(base, path)`, a raw-bytes sibling of `get()`. Then append the following to `run_checks` before `return checks`; do not edit lines `:1-195` except to add new code.
   - **Routes:**
     - `GET /jungle`, `GET /jungle?x=1` and `HEAD /jungle` return 200.
     - `Content-Type == "text/html; charset=utf-8"` on GET `/jungle`.
     - The GET `/jungle` body equals `serve.JUNGLE.read_bytes()`.
     - The GET `/` raw body equals `serve.INDEX.read_bytes()`. It contains `Hello World`, not `Hello World!`, and not `/jungle`.
     - Set `serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE}`.
   - **Look-alikes:** a new list, `JUNGLE_LOOKALIKE_PATHS = ["/jungle/", "/jungle2", "/jungles", "/other", "/jungle.html", "/docs/jungle.html"]`. For it and `NON_ROOT_PATHS`, GET returns 404 with no `Directory listing`, and HEAD returns 404.
   - **Page content (on the jungle body):**
     - `<html lang="en">` is present, along with `name="viewport"` and `width=device-width`.
     - The `<title>` text equals `Hello World! · Jungle`.
     - Exactly one `<h[1-6]\b` match, and it is `<h1`. Its inner text, with tags stripped and whitespace collapsed, is `Hello World!`.
     - No forbidden token, matched case-insensitively with tag patterns anchored (`<a[\s>]`, `<button\b`, `<form\b`, `<input\b`, `<script\b`, `<link\b`, `<img\b`, `<iframe\b`, `<audio\b`, `<video\b`, `@import`, `url(`, `@keyframes`, `animation`, `transition`, `:hover`, `http://`, `https://`, `xmlns`).
     - Every `<svg` opening tag contains `aria-hidden="true"`, and there is no `<text`.
     - The visible-text check: after removing `<style>`, `<svg>…</svg>` and `<title>` blocks and stripping tags, the remaining text is exactly `Hello World!`.
     - Every `#[0-9A-Fa-f]{3,8}` hex value is in the FR6 allow-list (case-insensitive). There is no `rgb(`/`rgba(`/`hsl(`.
     - `#F2C230`, `#0F3D2E` and `#155239` are all present.
     - The existing width regex finds nothing over 375px on the jungle body. Reuse the same pattern; copy it, do not alter the original.
     - A no-secrets heuristic: no `password`, `api_key`/`apikey`, `secret` or `token=`, case-insensitive.
   - **Docstrings:** `serve.__doc__` contains neither `Root-only` nor `exactly one document` (case-insensitive).
   - Dependencies: stdlib only (`re`, `urllib`), with nothing to install and no cache assumed.
5. **Run the gate** — AC4, AC8. Layer: the smoke test.
   - Run `python3 smoke_test.py` once on the committed SHA. It must print `OK: <n> checks passed` with n > 28 and exit 0.
   - Confirm 3.11 compatibility by inspection: no `match`, PEP 695 or 3.12+ APIs. Run with a `python3.11` interpreter if the pod has one.
6. **Manual browser check, recorded in the PR body** — AC1, AC2, AC3, AC5, AC6, AC7. There is no automated layer (pixel layout), so this is stated, not invented.
   - Run `python3 serve.py` and open `/jungle` at 375px, about 768px, 1024px and 1440px, and on a short landscape window (about 800×400).
   - Confirm no letter is covered or cut, there is no horizontal scroll, the desktop heading is on one line and the mobile heading is on two lines, the vines are hidden on mobile, and the page renders with the network blocked.
   - Contrast is about 7.3:1 on `#0F3D2E` and about 5.4:1 on `#155239` (hld.md §7).
7. **PR description** — AC6, AC7, AC8. No test layer applies; it is reviewed by a human.
   - Name HALO-93, epic HALO-91 and the Epic PRD (Confluence page 24707073, v2).
   - State that all graphics are original inline SVG and the font is the system font, with no non-MIT/BSD/Apache components.
   - Include the step 6 results.
   - Request the product owner's visual approval on desktop and at 375px.
   - The PR merges only on a green smoke test.

## Work-item mapping

| Step | Work item |
|---|---|
| 1–7 | t1 — HALO-93: Serve the jungle page at /jungle (self-contained page, fixed route, smoke checks) |

`work-items.md` has one work item, t1, and every step belongs to it. There is no planning gap.

## Verification and CI gate

- **Canonical gate:** `python3 smoke_test.py`. It is the repo's only check; there is no build, linter, formatter or CI pipeline. Run it once locally on the committed SHA.
- **Pass condition:**
  - exit 0 and `OK: <n> checks passed`, with all 28 original checks among them and unmodified;
  - every new check from step 4 passes;
  - no `FAIL:` line.
- **Pod compatibility:** the gate runs fully in a pod. It needs only localhost on an ephemeral port and no network.
- **Manual layer (not runnable in a pod):** the visual and responsive review from step 6 and the product owner's approval (AC7). They need a real browser and a human, so they are recorded in the PR, not automated.
- **Not applicable:**
  - Provider CI: none exists, and this story creates none.
  - `.factory/testing.md`: absent.
  - `.factory/delivery-assets`: not needed. The only new file is a small text file, well under 1 MiB.

## Risks and scope guards

**Risks**
- **Route widening or regression (RK5).** Mitigation: exact-match `ROUTES`, look-alike 404 checks on GET and HEAD, a byte-identical `/` check, and the `ROUTES` contents check.
- **Decorations covering the heading at in-between or odd sizes (RK1).** Mitigation: the stage padding is at least the decoration footprint, the page grows with `min-height` instead of a fixed aspect ratio, and the manual five-size check runs.
- **The width regex tripping on the breakpoint.** Mitigation: an `em` breakpoint, and no px width over 375.
- **Forbidden-token false positives.** `transform` is fine, but `transition` is not. Font names in the font stack are fine. Do not leave `href`/`http` anywhere, including comments.
- **Copying chrome from the screens.** Mitigation: copy only the SVGs, the heading markup and the `.frame`/`.stage`/`.deco`/`h1.hello` rules. Drop `rgba` box-shadows, `border-radius`, the fixed frames, `<link>` and the pills.
- **Hex check catching non-colour `#` tokens.** The page has no anchors or IDs that need `#`. Do not add any.

**Scope guards — the implement phase must NOT:**
- edit `docs/index.html`, `README.md`, `hello_world.txt`, `docs/.nojekyll` or anything under `stories/` (including the HALO-92 design and this plan folder's `spec.md`, `hld.md` and `work-items.md`);
- add a link to `/jungle` from `/`;
- change, reorder, weaken or delete any of the 28 existing smoke checks, or edit `NON_ROOT_PATHS`, `get()`, `head()` or `Checks`;
- rename `RootOnlyHandler`, change the `make_server` signature, or change `DEFAULT_HOST`, `DEFAULT_PORT`, `_resolve_port` or the usage block;
- switch to `SimpleHTTPRequestHandler`, prefix or regex routing, or serve `/jungle/`, `/jungle.html` or a CSS or asset route;
- add dependencies, `requirements.txt`, CI configuration, a test framework, browser automation, web fonts, images, animals, animation or extra text;
- recolour or redesign the decorations, because visual changes need a new HALO-92 approval;
- make the gate green by skipping, deleting or loosening a check. A failing check is reported as blocked.

## Clarification outcomes

None.
