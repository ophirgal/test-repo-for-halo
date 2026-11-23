# test-repo-for-halo

## Hello World script

Print the greeting from a Bash terminal (needs nothing beyond Bash; arguments are ignored):

```bash
bash hello_world.sh
# Hello, World!
```

Run its automated test:

```bash
bash test_hello_world.sh
# OK: 13 checks passed
```

## Link checker (linkcheck)

Check every HTML page of the docs site for broken internal links and missing
anchors, offline (standard library only, Python 3; nothing is ever fetched):

```bash
python -m linkcheck docs/
# no output and exit code 0 when every link resolves
```

Usage:

```bash
python -m linkcheck <dir> [--json FILE] [--markdown FILE] [--ignore PATTERN ...]
```

- `<dir>` — the directory to crawl; every `.html` file under it is checked.
  Only `href`/`src` on `a`, `link`, `img` and `script` count. A link starting
  with `/` resolves against `<dir>`; `guide/` resolves to `guide/index.html`.
- `--json FILE` — write a report `{"pages", "links", "ignored", "external", "findings"}`,
  sorted by path then line, byte-identical across runs.
- `--markdown FILE` — write a summary table and one section per page with
  findings, ready for a CI job summary.
- `--ignore PATTERN` — skip links whose target matches the `fnmatch` pattern
  (case-sensitive, repeatable, e.g. `--ignore 'drafts/*'`); they are counted as ignored.

Each finding is printed on its own line as `path:line: kind: target`, with the
path relative to `<dir>`:

```text
guide/intro.html:12: missing-target: guide/setup.html
```

| Kind | Meaning |
| --- | --- |
| `empty-link` | `href`/`src` is empty |
| `missing-target` | the linked file does not exist (target is its path relative to `<dir>`) |
| `missing-anchor` | the linked page has no element with that `id` (or `a` with that `name`) |
| `outside-root` | the link resolves outside `<dir>` (never read) |
| `decode-error` | the page is not valid UTF-8 (target is `byte <offset>`) |

External links (`https:`, `mailto:`, `//host/...` and any other scheme except
`file:`) are listed in the JSON report but never fetched and never a finding.

Exit codes: `0` no findings, `1` one or more findings, `2` usage error (missing
or non-directory `<dir>`, bad option), an unreadable page, or a report that
cannot be written.

In CI (for example a GitHub Actions `run:` step), keep the job failing on
broken links while always publishing the report to the job summary:

```bash
status=0
python -m linkcheck docs/ --markdown linkcheck.md || status=$?
cat linkcheck.md >> "$GITHUB_STEP_SUMMARY"
exit $status
```

Run the link checker's tests:

```bash
python -m unittest discover -s tests
```
