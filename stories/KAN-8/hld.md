# High-Level Design — Simple Hello World webpage (KAN-8)

## 1. System Overview
- **What:** a single static HTML page that greets the visitor with "Hello World", plus the minimal serving layer needed to return 200 for the root path and 404 for every other path.
- **Problem:** nothing is served today; the epic needs a verifiable proof of life.
- **Responsibilities:** render the greeting and title (FR1, FR2); render cleanly at 375px wide (FR3); root-only routing with 404 elsewhere (FR4); leave the KAN-6 files untouched.

## 2. Architecture Overview
- **Repository:** `ophirgal/test-repo-for-halo` (id `03b40291-ca08-4b8d-8c13-6389b0a66054`) — the only repo touched. Branch `halo/feat/kan-8`, matching the KAN-6 convention.
- **Components (all new, all in this repo):**
  - `docs/index.html` — the page. Lives in a dedicated subdirectory so the served tree never contains `README.md` or `hello_world.txt`. `docs/` is also one of the two folders GitHub Pages can be pointed at, so a later human-gated Pages enablement needs no file moves.
  - `docs/.nojekyll` — opts out of Jekyll processing if Pages is ever enabled (harmless otherwise).
  - `serve.py` — root-only HTTP server using only the Python 3 standard library. `GET /` → 200 with `docs/index.html`; any other path → 404. No other files are served, so there is no path-traversal surface and no directory listing.
  - `smoke_test.py` — dependency-free test that starts the server on an ephemeral port and asserts FR1, FR2 and FR4 over real HTTP.
- **Not modified:** `README.md`, `hello_world.txt` (spec non-goal). Run instructions live in a header comment of `serve.py`, not in the README.
- **External dependencies:** none. No package manifest, no framework, no CI.

## 3. Data Flow Design
- Synchronous request/response only: browser → `GET /` → server reads `docs/index.html` → 200 text/html. Browser → `GET /<anything else>` → 404.
- No state, no events, no async processing.

## 4. Component Breakdown
| Component | Responsibility | Inputs / Outputs | Repo |
| --- | --- | --- | --- |
| `docs/index.html` | Greeting page: `<title>` containing "Hello World", main content with "Hello World", viewport meta tag, text that wraps and no fixed widths wider than the viewport | — / HTML document | test-repo-for-halo |
| `serve.py` | Root-only routing, 200/404 split, configurable port, binds localhost by default | HTTP request / HTTP response | test-repo-for-halo |
| `smoke_test.py` | Automated verification of FR1, FR2, FR4 against a live local server | — / exit code 0 on pass, non-zero with a message on failure | test-repo-for-halo |

## 5. Interface Contracts
- `GET /` → `200`, `Content-Type: text/html`, body contains "Hello World" in the main content and in `<title>`.
- `GET /<any other path>` (including `/index.html`, `/hello_world.txt`, `/README.md`, `/docs/index.html`, `/foo`) → `404`. Body content unspecified (spec Open Question; status code is the contract).
- `GET /` after any 404s → still `200` with the greeting.
- Run contract: `python3 serve.py` starts the server (port configurable via argument or environment variable, documented in the file header); `python3 smoke_test.py` exits 0 on pass.

## 6. Key Technical Decisions
- **Static page + minimal stdlib server, not a static-directory host or a framework.** A "serve this folder" tool would return 200 for `/index.html` and for the KAN-6 files if run from the repo root, violating FR4 as written. Root-only routing is the smallest code that makes FR4 exactly true. Alternatives rejected: Node/Express or any package (adds a dependency footprint to an empty repo); `python3 -m http.server` (directory semantics, serves everything).
- **FR4 is implemented literally:** every non-root path is 404, including the pre-existing files and `/index.html`. This is the strictest reading and the safest for a smoke test to assert.
- **`docs/` as site root.** Keeps KAN-6 artifacts out of the served tree and is Pages-selectable if a human later enables Pages.
- **Python 3 stdlib** chosen over Node because it needs no manifest file; Python 3.11 is present on the implementation pod. This becomes the repo's first runtime convention.
- **FR3 by construction + manual check.** Viewport meta tag plus naturally wrapping text; no CSS framework. No browser automation is added (it would pull in Playwright or similar). The PR description records a manual 375px check.
- **Hosting / "reachable":** satisfied in this story by the locally runnable server. Enabling GitHub Pages is a repository-settings write outside the PR and is listed as an optional post-merge human step, not a deliverable.

## 7. Risks & Constraints
- **Technical:** FR3 has no automated browser check; the smoke test can only assert the viewport meta tag is present. Mitigation: manual check noted in the PR.
- **Integration:** if Pages is enabled later with source `/docs`, `/index.html` would return 200 under Pages (static hosts serve the file by name); this is outside this story's verified scope and noted for the human who enables it.
- **Operational:** no CI exists, so the smoke test runs locally in the PR workflow only. Server is for local/dev proof of life, not production hardening; it binds localhost by default and serves exactly one file.
- **Scope creep:** empty repo invites frameworks/CI; the deliverable is held to four small files and no README change.

## Build order
Single wave, single ticket. Post-merge optional human step (not a ticket): enable GitHub Pages from `main` / `docs` and confirm the live root returns 200 with the greeting and an unknown path returns 404.
