# SCRUM-120 — Implementation plan: offline link checker (`python -m linkcheck`)

## Context

SCRUM-120 adds a standard-library-only Python package `linkcheck/` at the root of `ophirgal/test-repo-for-halo`, run as `python -m linkcheck <dir> [--json FILE] [--markdown FILE] [--ignore PATTERN ...]`. It crawls every `.html` page under `<dir>`, extracts `href`/`src` from `a`, `link`, `img` and `script`, and reports `empty-link`, `missing-target`, `missing-anchor`, `outside-root` and `decode-error` findings. It writes them as terminal lines, sets an exit code (0/1/2) and can write deterministic JSON and Markdown reports. External links are listed and never fetched. The 17 acceptance criteria (AC1–AC17) are in `spec.md` §5. The work lands on the work branch `halo/feat/scrum-120-20261123-173828`, which was cut from `main`. `spec.md`, `hld.md` and `work-items.md` sit beside this file in `stories/SCRUM-120/`. The design (`hld.md` §5–§6) and the three work items t1 → t2 → t3 are what this plan executes.

## Research findings

**Repository state (checkout at `cc67937`):**
- Root files are `README.md`, `serve.py`, `smoke_test.py`, `hello_world.sh`, `hello_world.txt` and `test_hello_world.sh`, plus the folders `docs/` and `stories/`. There is no `linkcheck/`, `tests/`, `.github/`, `.factory/`, `CLAUDE.md`, `AGENTS.md`, `Makefile`, `pyproject.toml`, `setup.cfg`, `pytest.ini` or `requirements.txt`. Everything this story builds is new, except `README.md`.
- `docs/index.html` (19 lines) and `docs/jungle.html` (115 lines) contain 0 `href`/`src` attributes (`grep -c`). `docs/plans/_.txt` is a non-HTML file, and the crawl ignores it. So `python -m linkcheck docs/` must report 2 pages, 0 links and exit 0 (AC13).
- `serve.py:38` defines `ROUTES = {"/": INDEX, "/jungle": JUNGLE}`, which is a fixed route table and not a directory server. The design follows spec D1: `/x` resolves against the scanned root as a filesystem path (`hld.md` §1).
- `smoke_test.py` and `serve.py` import only the standard library. `smoke_test.py:382`/`:403` use a `main()` that returns an exit code and call `sys.exit(main())`. `linkcheck/cli.py` follows the same idiom.
- `README.md` has one section, `## Hello World script` (lines 3–17), with fenced `bash` examples. The new section follows that style and is appended after it.
- Other `.html` files exist under `stories/*/design/`. The checker never scans them, because it only crawls the `<dir>` it is given. Tests must not point the checker at the repository root.

**Runtime facts (verified with the pod's Python 3.12.15):**
- `html.parser.HTMLParser` lower-cases tag and attribute names, delivers attribute values already entity-unescaped, and gives a valueless attribute as `None`. `getpos()[0]` is the 1-based line where the tag starts. `<script>`/`<style>` bodies are CDATA, so markup inside them and CSS `url()` are never seen as tags. AC14 needs no extra code for this.
- `UnicodeDecodeError.start` from `bytes.decode("utf-8-sig")` is relative to the data **after** the BOM. `b'\xef\xbb\xbfab\n\xff'` gives `3`, while the real byte offset is `6`. The decoder must strip a leading `b'\xef\xbb\xbf'` by hand, decode with strict `"utf-8"`, and add the BOM length to the offset. The line of the first bad byte is the count of `b"\n"` before the offset, plus 1.

**Contracts (fixed by `spec.md` and `hld.md` §5):**
- Public names: `extract_links(path)`; `Link` with `target` (str), `line` (int) and `kind` in {`anchor`, `image`, `stylesheet`, `script`}; `PageDecodeError` (path, byte offset, line); `check_site(root)`, with ignore patterns as an optional argument.
- Stdout line format: `path:line: kind: target`. Paths are relative to the root and use `/` separators.
- JSON keys, in order: `pages, links, ignored, external, findings`. Finding keys are `path, line, kind, target`. External keys are `path, line, target`. Output uses 2-space indent and UTF-8, ends with a trailing newline, and is sorted by path, line, kind, target.
- Markdown has a summary table with the rows Pages, Links, External, Ignored and Findings. It has one `##` section per page with findings, escapes `|` and backticks, and says "No findings" on a clean run.
- Finding targets (`hld.md` §5): for `missing-target`, the resolved path relative to the root. For `missing-anchor`, that path plus `#fragment`. For `outside-root`, the link as written. For `empty-link`, `""`. For `decode-error`, `byte <offset>`.

**Gate:** the only gate is the story's: `python -m unittest discover -s tests`, run from the repository root. There is no `tests/__init__.py`. The root is on `sys.path` because of `python -m`, and `discover -s tests` adds `tests/`. The existing checks `python3 smoke_test.py` and `bash test_hello_world.sh` must keep passing. There is no provider CI. `dev-toolkit`'s `run-tests-gate.sh` resolves its command from `DEV_TOOLKIT_TEST_CMD`, then from `.factory/testing.md`'s `local-test-gate:`, then by discovery (`make test`, `npm test`, `go test ./...`, `pytest` with a config). None of these exist here. Unless the platform configures `DEV_TOOLKIT_TEST_CMD`, its run records `not_declared` (see Risks).

**External data:** none. There are no other systems of record and no network access.

**Unknowns remaining:** epic traceability (spec O1). This does not block the plan.

## Locked decisions and assumptions

**Locked decisions**
- Standard library only, no network access, tests under `tests/`, run with `python -m unittest discover -s tests` (`spec.md` §6).
- The only existing file that changes is `README.md`. `docs/`, `serve.py`, `smoke_test.py`, `hello_world.sh` and `test_hello_world.sh` stay unchanged (`spec.md` §2 Non-Goals).
- D1: `/x` resolves against the scanned root. A `file:` URL resolves as a filesystem path and gives `outside-root` when it leaves the root (`spec.md` §8, AC15).
- D2: an undecodable page gives `decode-error` at the line of its first bad byte, with target `byte <offset>`. It counts in `pages`, its links go unchecked, and the run exits 1 (AC16).
- D3: JSON shape with `ignored`, sorted lists, and an Ignored row in the Markdown (AC10, AC12).
- D5: no CI workflow file. `README.md` shows a CI example instead.
- D6: the real-site run of 2 pages and 0 links is accepted (AC13).
- D7: `href="#"` is not a finding (AC17).
- Module layout and ownership: t1 owns `linkcheck/__init__.py` and `linkcheck/extract.py`. t2 owns `linkcheck/check.py`. t3 owns `linkcheck/__main__.py`, `linkcheck/cli.py`, `linkcheck/report.py` and `README.md`. Each owner also writes its own `tests/test_*.py` (`hld.md` §2, `work-items.md`).
- Design edge rules (`hld.md` §6):
  - A valueless or whitespace-only attribute is `empty-link`, and the first of duplicate attributes counts.
  - `//host/x` is external.
  - Ignore runs first, as case-sensitive `fnmatch.fnmatchcase` on the target as extracted, and empty links are not ignorable.
  - The query string is stripped and the path percent-decoded.
  - Containment uses `os.path.realpath` before any read.
  - A trailing `/`, or a path to an existing directory, resolves to that directory's `index.html`.
  - A fragment is checked only on an `.html` page that decodes.
  - The crawl collects files with a case-insensitive `.html` suffix, in sorted order, and skips symlinks that escape the root.
  - An I/O error exits 2 and names the path. `argparse` handles usage errors.

**Assumptions**
- A-BOM: the byte offset counts from the start of the file, BOM included. Evidence: AC3 says "byte offset" of the file, and the Python codec behaviour is shown above. If this is wrong, a BOM-prefixed bad page reports an offset 3 bytes higher than a reviewer expects. The only effect is a test expectation.
- A-Exit2-before-write: argument and directory validation happen before any page is read or any report is opened. Report files are written only after the check completes, to a temporary file in the same directory that is then renamed with `os.replace`. A report-write failure therefore exits 2 and leaves no partial file. Evidence: `hld.md` §5 says "On exit 2 no report is written". If this is wrong, a failed run could leave a truncated report.
- A-Offline-test: AC14's "no network" is proven in a subprocess that disables `socket.socket` (and `socket.create_connection`) before it runs the module through `runpy.run_module("linkcheck", run_name="__main__")` under `python -c`. Evidence: `hld.md` §7, "socket creation patched to fail". If this is wrong, a test that only asserts output would not prove that nothing is fetched.
- A-Sentinel: the tests prove that an `outside-root` target is never read by creating a sentinel file outside the root and patching `builtins.open`/`pathlib.Path.read_bytes`. A test that calls `check_site` in-process asserts the sentinel path is never passed to them. If this is wrong, AC7 and AC15 lose their "never read" proof.

## Solution proposal

Build three layered modules, each importing only the one below it: `extract` ← `check` ← `cli`/`report`. They match the three work items, so each work item builds and tests on its own.

1. **`linkcheck/extract.py` (t1).** Read the file as bytes. Strip a leading UTF-8 BOM by hand, decode with strict `"utf-8"`, and on `UnicodeDecodeError` raise `PageDecodeError(path, offset, line)`. Its message names the path and `byte <offset>`, and the offset includes the BOM length. Feed the text to a private `HTMLParser` subclass. In `handle_starttag`, and in `handle_startendtag` for `<img/>`/`<link/>`, map the tag to its attribute: `a`→`href`/`anchor`, `img`→`src`/`image`, `link`→`href`/`stylesheet`, `script`→`src`/`script`. Take the first occurrence of that attribute. If the value is `None` or empty after `.strip()`, record an empty-link line; otherwise append `Link(target, line, kind)`. On every start tag, collect `id` into the anchor set, and collect `name` when the tag is `a`. Expose two entry points:
   - `parse_page(path)`, which returns a small `Page` result (frozen dataclass or `NamedTuple`) with `links`, `empty_lines` and `anchors`, and is what t2 consumes.
   - `extract_links(path)`, which returns `parse_page(path).links`. This is the spec contract.
   `Link` is a frozen `dataclass` or `NamedTuple`. Re-export `extract_links`, `Link` and `PageDecodeError` from `linkcheck/__init__.py`.

2. **`linkcheck/check.py` (t2).** `check_site(root, ignore=())` returns a `SiteResult` with `pages`, `links`, `ignored`, `external` (a list of `(path, line, target)`) and `findings` (a list of `Finding(path, line, kind, target)`), all sorted.
   - **Crawl:** walk with `os.walk(followlinks=False)`, sorting `dirnames` and `filenames` in place. Keep a file when its `realpath` is inside `realpath(root)`. Use `os.path.commonpath` for that test, not a string prefix.
   - **Per link, in this order:**
     - Apply ignore.
     - Split with `urllib.parse.urlsplit` and lower-case the scheme.
     - Treat a scheme other than `""`/`file`, or `netloc` with no scheme, as external.
     - Treat a `file:` URL whose netloc is not `""`/`localhost` as `outside-root`.
     - Build the candidate path: an empty path means the same page, a leading `/` means root-relative, `file:` means an absolute filesystem path, and anything else is relative to the page's directory. Use `unquote` on the path.
     - Run the containment test on `realpath` **before** any `isdir`/`exists`/read.
     - Map a directory or a trailing `/` to `index.html`.
     - Check existence, then check the fragment against the target's anchor set. An empty fragment (`#`) is skipped.
   - **Caches:** cache parsed pages by real path, so each page is parsed once. A cached decode failure suppresses the fragment check.
   - **Errors:** an `OSError` while reading a page is raised as `LinkcheckIOError(path)`, a new exception in `check.py`.
   Re-export `check_site` from `linkcheck/__init__.py`.

3. **`linkcheck/cli.py` + `report.py` + `__main__.py` (t3).**
   - `cli.main(argv=None) -> int` uses `argparse` with a positional `dir`, `--json`, `--markdown` and `--ignore` (`action="append"`). If `dir` is not a directory, it calls `parser.error`, which exits 2.
   - It then runs `check_site`, prints `path:line: kind: target` for each sorted finding, and writes the reports through `report.to_json(result)` / `report.to_markdown(result)`, which are pure functions returning `str`. The files are written atomically.
   - It returns 1 if there are findings and 0 otherwise. `LinkcheckIOError` or `OSError` on a report write prints to stderr and returns 2.
   - `__main__.py` does `sys.exit(main())`.
   - JSON is built from dicts in key order with `json.dumps(..., indent=2, ensure_ascii=False) + "\n"`, encoded as UTF-8.

**Key decisions:**
- `html.parser` over regex. A regex is wrong on comments, script bodies and line numbers (`hld.md` §6).
- A separate `parse_page` lets t2 get links, empty links and anchors from one parse, while `extract_links` keeps the exact spec signature.
- Containment by `realpath` and `commonpath` before any filesystem probe of the target covers `../`, `file:` and symlink escapes with one check.
- The report renderers are pure functions. This makes byte-identity testable without the filesystem.

**Rejected alternatives:**
- Mimicking `serve.py` routing. It is a fixed two-route table (`serve.py:38`).
- A third-party HTML parser. It is forbidden.
- Making `extract_links` return a tuple of links, empty links and anchors. That breaks the AC1 contract.
- `utf-8-sig` decoding. It reports the wrong byte offset after a BOM.

## Ordered implementation steps

**t1 — extractor**
1. Create `linkcheck/__init__.py` (new) with a module docstring and re-exports of `extract_links`, `Link` and `PageDecodeError`. AC1, AC3. Test layer: unittest, `tests/test_extract.py`, through an import test.
2. Create `linkcheck/extract.py` (new) with:
   - `Link`, `Page` and `PageDecodeError(path, offset, line)`, whose message includes the path and `byte <offset>`.
   - BOM stripping and strict UTF-8 decoding, with offset and line computed from the raw bytes.
   - The `HTMLParser` subclass that collects links in document order, empty-link lines and anchors.
   - `parse_page(path)` and `extract_links(path)`.
   AC1, AC2, AC3, AC14 (no links inside `<script>`/`<style>` bodies or CSS `url()`). Test layer: unittest.
3. Create `tests/test_extract.py` (new). Build fixtures with `tempfile.TemporaryDirectory`. Cover:
   - Five links (3 `a`, 1 `img`, 1 `link`) in order, with lines and kinds, plus `script src` with kind `script` (AC1).
   - Whitespace and `&amp;` targets. Empty, whitespace-only and valueless `href`/`src` become empty-link lines and are not links (AC2).
   - Upper-case tags and attributes. A duplicate attribute uses the first value. An inline `<script>` yields nothing.
   - Markup inside a `<script>` or `<style>` body and CSS `url()` are not links (AC14).
   - The anchor set holds `id` on any element and `name` only on `a`.
   - An invalid byte on line 3 gives `PageDecodeError` with the correct offset, line and path in its message. The same with a BOM gives an offset that includes 3 BOM bytes. A BOM-only valid page parses (AC3).
   - Imports from both `linkcheck` and `linkcheck.extract` work.

**t2 — checker**
4. Create `linkcheck/check.py` (new) with `Finding`, `SiteResult` and `LinkcheckIOError`, the sorted, containment-filtered crawl, link classification (ignore, then external, then internal), resolution, the `realpath` containment check before any probe, mapping directories to `index.html`, the existence and fragment checks, the page-parse cache, and the conversion of `decode-error` and `empty-link` into findings. AC4–AC8, AC15, AC16, AC17, FR15. Test layer: unittest, `tests/test_check.py`.
5. Add the `check_site` re-export to `linkcheck/__init__.py` (the handoff allowed by t2). AC4. Test layer: unittest.
6. Create `tests/test_check.py` (new) with temp-dir sites. Cover:
   - A clean site gives no findings and correct `pages`/`links`/`external` counts (AC4).
   - `missing.html` gives `missing-target` with the root-relative resolved path, from a subfolder page too (AC5).
   - `other.html#nope` gives `missing-anchor` with target `other.html#nope`. `#top` is checked on the same page, with both the passing and failing cases. `a name` satisfies the check. `#` gives no finding (AC6, AC17).
   - `../../etc/passwd`, `file:///<sentinel>`, `file://otherhost/x` and a symlink escaping the root all give `outside-root`, with the link as written as the target. The sentinel file outside the root is never opened: patch `builtins.open` and `os.stat` with spies that fail when the sentinel path is opened or probed (AC7, AC15).
   - `guide/` and `guide` (an existing directory) resolve to `guide/index.html`, and are broken only when `index.html` is missing (AC8).
   - `/other.html` from `sub/page.html` resolves against the root, with both the present and missing cases (AC15).
   - `https:`, `mailto:`, `javascript:`, `data:` and `//host/x` are external, are not findings, and are counted (AC14, FR6).
   - `?q=1` is stripped, `%20` is decoded, and a fragment on `.png` or on an undecodable target is not checked.
   - An `empty-link` finding has target `""` (AC2 at site level).
   - An undecodable page counts in `pages`, gives one `decode-error` with `byte <offset>` and its line, and none of its links are checked (AC16).
   - Ignore patterns: an ignored link counts only in `ignored`, an ignored external link is not in `external`, matching is case-sensitive, and empty links are not ignorable (FR15).
   - Two runs give equal results, in sorted order. A `.HTML` suffix is crawled and `.htm` is not. A page is parsed at most once (patch `parse_page` with a counting spy).
   - An unreadable page raises `LinkcheckIOError`. Use a `chmod 000` file and skip with a stated reason when running as root, because root ignores the permission.

**t3 — CLI, reports, README**
7. Create `linkcheck/report.py` (new) with `to_json(result) -> str` and `to_markdown(result) -> str` (the summary table, per-page sections, `|`/backtick escaping and "No findings"). AC10, AC11, AC12. Test layer: unittest, `tests/test_cli.py`.
8. Create `linkcheck/cli.py` (new) with `main(argv=None) -> int`: `argparse`, directory validation (exit 2 through `parser.error`), the stdout finding lines, atomic report writes (temporary file plus `os.replace`), and exit codes 0/1/2. Create `linkcheck/__main__.py` (new) calling `sys.exit(main())`. AC9, AC10, AC11, AC12. Test layer: unittest.
9. Create `tests/test_cli.py` (new). Most cases use `subprocess.run([sys.executable, "-m", "linkcheck", ...], cwd=<repo root>)`, where the repo root is the parent of `tests/`. Cover:
   - Exit codes 0, 1 and 2: a missing directory, a file passed as the directory, an unknown option and `--json` with no value. On exit 2 no report file exists. Stdout holds exactly the sorted finding lines (AC9).
   - The JSON key order, shapes and sort, and two runs that are byte-identical (AC10).
   - The Markdown summary rows, per-page sections, "No findings" on a clean run, `|` escaping, and byte-identity (AC11).
   - Repeated `--ignore`, counted in `ignored` and in the Ignored row (AC12).
   - `--json` and `--markdown` combined in one run.
   - A report path in a missing directory exits 2 and names the path.
   - `decode-error`, `outside-root` and `missing-target` lines (AC16, AC7, AC5).
   - AC14 in a subprocess with sockets disabled (assumption A-Offline-test): `https://example.com/x` is in `external`, and CSS `url()` and a script-built link are not counted. Exit is 0.
   - `python -m linkcheck docs/` from the repo root exits 0 with empty stdout (AC13).
10. Append a section to `README.md` after `## Hello World script`, for example `## Link checker (linkcheck)`. Document the usage line, `--json`, `--markdown` and repeatable `--ignore`, the five finding kinds, exit codes 0/1/2, offline behaviour, `python -m unittest discover -s tests`, and a CI example as a shell snippet. The snippet runs `python -m linkcheck docs/ --markdown linkcheck.md`, appends `linkcheck.md` to `"$GITHUB_STEP_SUMMARY"` whatever the exit code, and keeps the job failing when the exit code is not 0. Do not change the existing lines. Add no workflow file. AC13, FR16. Test layer: none for prose. AC13's exit-0 half is covered in step 9.

**Invariants across steps:**
- **Security boundary:** containment runs before every filesystem probe of a target, and the tests prove it.
- **No network:** no module imports `urllib.request`, `http.client` or `socket`.
- **Determinism:** walks are sorted, output is sorted with the full tie-break, and output holds no timestamps or absolute paths.
- **Validation and error paths:** exit 2 happens before any write, and report writes are atomic.
- **Authorization, tenancy and concurrency:** not applicable. This is a single-process local CLI.
- **Dependencies:** none to acquire, only the standard library on Python 3.12.
- **Generated deliverables:** none, and no binaries.

## Work-item mapping

| Step | Work item |
|---|---|
| 1, 2, 3 | t1 — linkcheck HTML link extractor (extract_links, Link, PageDecodeError) |
| 4, 5, 6 | t2 — linkcheck site checker (check_site): resolution, root boundary, anchors, ignore |
| 7, 8, 9, 10 | t3 — python -m linkcheck CLI with exit codes, JSON and Markdown reports, README |

Every work item has steps. Each one builds and passes `python -m unittest discover -s tests` on its own: t1's tests need only `extract.py`, and t2's need only t1 and `check.py`.

## Verification and CI gate

- **Canonical gate (the story's, in order):**
  1. `python -m unittest discover -s tests` from the repository root.
  2. `python3 smoke_test.py`.
  3. `bash test_hello_world.sh`.
  All three run in a pod. They use only the standard library, Bash and localhost; `smoke_test.py` binds an ephemeral port on 127.0.0.1. There is no provider CI in the repository (no `.github/`), so no provider check runs at the head. Adding a workflow is out of scope (D5).
- **The one local run** is `run-tests-gate.sh --run` on the committed SHA. The repository declares no `local-test-gate:` and has nothing the script can discover. Unless the platform sets `DEV_TOOLKIT_TEST_CMD` (to `python -m unittest discover -s tests`), it records `not_declared`. That record must be reported as is: it is not a pass. No second manual run of the canonical command sits beside it, and there is no second worktree.
- **Test layer:** one layer, `unittest`, under `tests/` (new; no `tests/__init__.py`). It holds unit tests in-process and end-to-end CLI tests through `subprocess` with `sys.executable`. No other layer exists or is invented.
- **`.factory/testing.md` / `.factory/delivery-assets`:** neither exists. No binary deliverable, so no delivery-assets entry.
- **Done means:**
  - All `tests/test_extract.py`, `tests/test_check.py` and `tests/test_cli.py` tests pass, with at least one test per AC1–AC17.
  - The only skip allowed is the `chmod 000` case under root, and it states its reason.
  - `python -m linkcheck docs/` exits 0 with empty stdout.
  - `smoke_test.py` and `test_hello_world.sh` still pass.
  - `git diff main --stat` shows only new files under `linkcheck/` and `tests/`, plus `README.md`.

## Risks and scope guards

**Risks**
- **Root-escape bug (security).** Mitigation: a single `realpath`/`commonpath` containment check before any probe, and sentinel-spy tests for `../`, `file:` and a symlink.
- **BOM offset off by 3.** Mitigation: manual BOM stripping and strict `utf-8`, with a dedicated test.
- **Silent network use.** Mitigation: no network imports, and the AC14 subprocess test with sockets disabled.
- **Non-deterministic reports.** Mitigation: sorted walk, sorted output with the full tie-break, `json.dumps` with fixed key order, and byte-identity tests.
- **Permission test under root.** `chmod 000` does not block root, so the test detects `os.geteuid() == 0` and skips with a reason. The `OSError` path is also covered by patching `open` to raise.
- **The local gate records `not_declared`**, because the repository has no `local-test-gate:` and nothing discoverable. Adding `.factory/testing.md` is outside every work item's "Owns" list and outside the story, so it is not planned. The implementer reports the record as is.
- **AC13 is trivial** (0 links), as accepted by D6.

**Scope guards: the implement phase must NOT**
- Edit `docs/*.html`, `serve.py`, `smoke_test.py`, `hello_world.sh`, `hello_world.txt`, `test_hello_world.sh` or anything under `stories/`, apart from what the platform writes.
- Change the existing lines of `README.md`. Only append.
- Add a third-party dependency, `requirements.txt`, `pyproject.toml`, a CI workflow, `.factory/` files or `tests/__init__.py`.
- Fetch or validate external URLs, parse CSS `url()` or script-generated links, or check attributes other than `href`/`src` on `a`/`link`/`img`/`script`.
- Run the checker against the repository root, or crawl `.htm`/non-HTML files.
- Print anything on stdout other than finding lines, or print absolute paths.
- Skip, delete or weaken any test, `smoke_test.py` or `test_hello_world.sh` to get green. A failing check is reported as blocked.

## Clarification outcomes

None. The developer delegated all open decisions to the intake (`spec.md` §8, D1–D7), and research found no conflict between the locked sources and the repository that needs a developer answer.
