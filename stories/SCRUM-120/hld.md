# SCRUM-120 — High-Level Design: offline link checker (`python -m linkcheck`)

## 1. System Overview

- **What:** a new standard-library-only Python package `linkcheck/` at the repository root, run as `python -m linkcheck <dir>`. It crawls every `.html` file under `<dir>`, extracts `href`/`src` from `a`, `link`, `img` and `script`, and reports `empty-link`, `missing-target`, `missing-anchor`, `outside-root` and `decode-error` findings as terminal lines, an exit code (0/1/2) and optional `--json` / `--markdown` reports. External links are listed, never fetched.
- **Problem:** broken links in `docs/` are found only by readers; the check must run offline.
- **Responsibilities:** parse pages (t1), resolve and check links under a root boundary (t2), CLI + reports + README (t3).
- **Grounding (verified at `449e144`):** `docs/index.html` and `docs/jungle.html` hold no `href`/`src` (grep count 0), so the real-site run checks 2 pages, 0 links. No `linkcheck/`, `tests/`, `.github/`, `CLAUDE.md`, `AGENTS.md` or `.factory/` exist. `serve.py` and `smoke_test.py` are stdlib-only. Runtime verified: Python 3.12.
- **Code vs spec note:** the spec says `/page.html` resolves "the way `serve.py` serves `docs/` at `/`". `serve.py` (`ROUTES`, lines ~37-38) actually serves only two fixed routes (`/` → `docs/index.html`, `/jungle` → `docs/jungle.html`), not the directory. The design follows the spec's decision D1 (root-relative resolves against the scanned root as a filesystem path); it does not mimic `serve.py`'s route table.

## 2. Architecture Overview

Single repo (`ophirgal/test-repo-for-halo`), one package, three layered modules; each layer only imports the one below.

| Module | Owner | Role |
|---|---|---|
| `linkcheck/__init__.py`, `linkcheck/extract.py` | t1 | HTML parsing: links, empty links, page anchors (ids / `a name`), decode errors |
| `linkcheck/check.py` | t2 | Crawl root, classify (external / ignored / internal), resolve, root-boundary check, anchor check, counts |
| `linkcheck/__main__.py`, `linkcheck/cli.py`, `linkcheck/report.py` | t3 | Argument parsing, terminal lines, exit codes, JSON and Markdown renderers |
| `tests/test_extract.py` / `tests/test_check.py` / `tests/test_cli.py` | t1 / t2 / t3 | unittest suites, fixtures built in temp dirs |
| `README.md` | t3 | The only existing file changed |

External dependencies: none (stdlib `html.parser`, `urllib.parse`, `pathlib`/`os`, `fnmatch`, `argparse`, `json`, `tempfile`, `unittest`).

## 3. Data Flow Design

Synchronous, single process, no I/O beyond reading files under the root and writing the requested report files.

1. `cli` validates arguments (exit 2 on usage error, before anything is read or written).
2. `check.check_site(root, ignore patterns)` walks the root in sorted order, collecting every `*.html` file (each counts in `pages`).
3. For each page, `extract` decodes UTF-8 and parses: links (target, line, kind), empty-link occurrences, and the page's anchor names. A decode failure becomes a `decode-error` finding; that page's links are not checked.
4. Each link: ignored (fnmatch) → counted in `ignored`, dropped. External scheme → appended to `external`. Otherwise resolved to a path, contained in the root (else `outside-root`, never read), existence checked (`missing-target`), fragment checked against the target page's anchors (`missing-anchor`; target pages parsed once and cached).
5. `cli` prints sorted findings, writes `--json` / `--markdown` via `report`, exits 0 or 1.

## 4. Component Breakdown

- **Extractor** (`linkcheck/extract.py`, t1). In: a file path. Out: links in document order (`Link` with `target`, `line`, `kind`), empty-link occurrences with their line, and the set of anchor names (`id` on any element, `name` on `a`). Raises `PageDecodeError` (path, byte offset, line of first bad byte). Repo: `ophirgal/test-repo-for-halo`.
- **Checker** (`linkcheck/check.py`, t2). In: root directory, ignore patterns. Out: result with findings (path, line, kind, target), external entries (path, line, target) and counts `pages`, `links`, `ignored`. Repo: same.
- **CLI + reports** (`linkcheck/__main__.py`, `linkcheck/cli.py`, `linkcheck/report.py`, t3). In: argv. Out: stdout lines, exit code, JSON / Markdown files. Repo: same.

## 5. Interface Contracts

Named by the spec (fixed): `extract_links(path)`, `Link` (`target`, `line`, `kind`), `PageDecodeError`, `check_site(root)`. Everything else internal is the implementer's choice.

- **t1 → t2:** t1 additionally exposes, from the same parse, the page's empty-link lines and its anchor-name set (shape chosen by t1; t2 consumes what t1 commits). `check_site` accepts the ignore patterns as an optional argument (default none), so `check_site(root)` still works.
- **CLI:** `python -m linkcheck <dir> [--json FILE] [--markdown FILE] [--ignore PATTERN ...]`. Stdout: one `path:line: kind: target` line per finding, nothing else. Errors/usage: stderr.
- **Exit codes:** 0 clean; 1 one or more findings; 2 usage error (missing/non-directory `<dir>`, unknown option, option without value) or a report file that cannot be written. On exit 2 no report is written.
- **Paths everywhere** (terminal, JSON, Markdown): relative to the scanned root, `/` separators.
- **Finding targets:** `missing-target` → resolved path relative to root (e.g. `guide/setup.html`; for a directory link `guide/index.html`); `missing-anchor` → resolved path + `#fragment`; `outside-root` → the link as written in the page (the resolved outside path is never shown or read); `empty-link` → empty string; `decode-error` → `byte <offset>`.
- **JSON:** keys in order `pages, links, ignored, external, findings`; finding keys `path, line, kind, target`; external keys `path, line, target`; 2-space indent, UTF-8, trailing newline. Sorted by path, then line, then kind, then target (tie-break added for byte-determinism). `links` = non-empty links that were not ignored (external included); `ignored` = links dropped by `--ignore`.
- **Markdown:** a summary table (Pages, Links, External, Ignored, Findings), then one `##` section per page with findings (pages sorted) listing line, kind and target in a table; `|` and backticks in targets escaped; a clean run states "No findings". Deterministic bytes.

## 6. Key Technical Decisions

Behaviour verified by running Python 3.12's `html.parser` / `urllib.parse` against edge inputs; each settled case is an acceptance criterion of its owning work item.

**Parsing (t1)**
- `html.parser.HTMLParser`: tags/attributes are lower-cased, attribute values arrive already entity-unescaped (`&amp;` → `&`), `getpos()` gives the 1-based line of the tag start. Script and style bodies are not parsed as markup, so a `<a href>` inside a `<script>` string and CSS `url()` are never links (criterion 14) — no extra code needed.
- A valueless attribute (`<a href>`) or whitespace-only value is an `empty-link`, same as `href=""`; this applies to `src` too.
- Duplicate attribute (`href="a" href="b"`): the first one counts (browser behaviour).
- `script` without `src`, `link`/`img`/`a` without the attribute: no link.
- Decoding is strict UTF-8 on raw bytes; offset = `UnicodeDecodeError.start`; line = newlines before offset + 1. A leading UTF-8 BOM is accepted.

**Classification and resolution (t2)**
- Scheme from `urlsplit` (lower-cased). Any scheme other than none / `file` → external (`http`, `https`, `mailto`, `javascript`, `data`, `tel`, …). A scheme-relative `//host/x` (no scheme, has host) is also external — it names another host.
- Ignore is applied first, on the target as extracted, with case-sensitive `fnmatch.fnmatchcase`; an ignored external link counts only in `ignored`. Empty links are not subject to ignore.
- Query string stripped; path percent-decoded before resolution. `#` alone, `?x` alone, and an empty path with a fragment refer to the page itself.
- Relative → against the page's directory; `/x` → against the root; `file:` with empty or `localhost` host → its path as an absolute filesystem path (a relative `file:` path resolves like a relative link); `file:` with another host → `outside-root`.
- Containment: the candidate is normalised and symlink-resolved (`realpath`) and must be inside the realpath of the root; otherwise `outside-root` and no read, stat of contents or parse happens beyond resolving the path.
- Trailing `/`, or a target that is an existing directory → that directory's `index.html`.
- Fragment checked only when the resolved target is an `.html` page that decodes; fragment compared percent-decoded and case-sensitively. A fragment pointing at an undecodable page is not a second finding (the page already has its `decode-error`).
- Crawl: `.html` files (case-insensitive suffix), sorted, recursive, including dot-directories; files/dirs that resolve outside the root via symlink are skipped (never read).

**CLI (t3):** `argparse` (its own exit 2 on bad options). The directory is checked before any work.

**Alternatives considered:** a regex extractor (rejected: wrong on comments/scripts/line numbers); depending on `serve.py` routing (rejected: fixed two-route table, not a directory server).

## 7. Risks & Constraints

- **Security:** the root boundary is the security property (FR10/FR11). Risk: a symlink or `file:` link escaping the root; mitigated by realpath containment before any read, with tests that use a sentinel file outside the root and prove it is never opened.
- **Offline:** no module imports or calls network code; criterion 14 is tested with socket creation patched to fail.
- **Scale:** each page is read and parsed once (target pages cached); memory is linear in links. Adequate for a docs site; no concurrency needed.
- **Determinism:** sorted walk and sorted output with a full tie-break; JSON/Markdown produced without timestamps or absolute paths.
- **Unreadable page (permissions/IO error):** not in the spec; treated as a fatal error naming the path, exit 2 (assumption A4).
- **Real-site check is trivial:** `docs/` has 0 links today (spec D6, accepted).

## 8. Assumptions

- **A1** — Only `.html` files are crawled; query strings are stripped; a fragment on a non-HTML target is not checked (spec §8 assumptions, adopted). Risk if wrong: `.htm` pages or anchors in other formats go unchecked.
- **A2** — `//host/x` is external. Risk: none offline; it is never fetched.
- **A3** — An existing directory linked without a trailing `/` resolves to its `index.html`. Risk: a site server that does not redirect would 404 where we pass.
- **A4** — An I/O error reading a page exits 2 naming the path. Risk: a CI job sees a usage-style failure instead of a finding; it still fails loudly.
- **A5** — Paths are reported relative to the scanned root (spec example). Risk: the developer must prefix the root to open the file.
- **A6** — The epic's requirement IDs (spec O1) were not available; no traceability labels are invented.

## 9. Repository Gates

No `CLAUDE.md`, `AGENTS.md`, `.factory/` or CI workflow exists, so the only gate is the story's: `python -m unittest discover -s tests` passes from the repository root (no `tests/__init__.py`; `python -m` puts the root on `sys.path`), and the existing `python3 smoke_test.py` and `bash test_hello_world.sh` still pass untouched.
