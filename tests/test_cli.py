import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from linkcheck import cli
from linkcheck.check import External, Finding, SiteResult
from linkcheck.report import to_json, to_markdown

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_linkcheck(*args, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, "-m", "linkcheck", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONPATH": REPO_ROOT},
    )


class CliTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        self.site = os.path.join(self.base, "site")
        os.mkdir(self.site)

    def write(self, rel, content="<p>x</p>"):
        path = os.path.join(self.site, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def out(self, name):
        return os.path.join(self.base, name)

    def read(self, path):
        with open(path, "rb") as fh:
            return fh.read()

    def broken_site(self):
        self.write("index.html", '<a href="guide/">g</a>\n<a href="https://example.com/x">e</a>\n<a href="#nope">n</a>')
        self.write("guide/intro.html", '<p>\n<a href="setup.html">s</a>\n<a href="../../../etc/passwd">p</a>')
        self.write("bad.html", b"<p>ok</p>\n\xff")


class ExitCodeTest(CliTestCase):
    def test_clean_exit_0_no_output(self):
        self.write("index.html", '<a href="other.html">o</a>')
        self.write("other.html")
        proc = run_linkcheck(self.site)
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))

    def test_findings_exit_1_sorted_lines_only(self):
        self.broken_site()
        proc = run_linkcheck(self.site)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(
            proc.stdout.splitlines(),
            [
                "bad.html:2: decode-error: byte 10",
                "guide/intro.html:2: missing-target: guide/setup.html",
                "guide/intro.html:3: outside-root: ../../../etc/passwd",
                "index.html:1: missing-target: guide/index.html",
                "index.html:3: missing-anchor: index.html#nope",
            ],
        )

    def test_usage_errors_exit_2_and_write_no_report(self):
        self.write("index.html")
        a_file = self.write("file.html")
        report = self.out("r.json")
        cases = [
            [os.path.join(self.base, "missing"), "--json", report],
            [a_file, "--json", report],
            [self.site, "--bogus", "--json", report],
            [self.site, "--markdown", report, "--json"],
            [],
        ]
        for args in cases:
            with self.subTest(args=args):
                proc = run_linkcheck(*args)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertIn("usage:", proc.stderr)
                self.assertFalse(os.path.exists(report))

    def test_unwritable_report_exits_2_naming_path(self):
        self.write("index.html", '<a href="missing.html">m</a>')
        bad = os.path.join(self.base, "no-such-dir", "r.json")
        md = self.out("r.md")
        proc = run_linkcheck(self.site, "--markdown", md, "--json", bad)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(bad, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertFalse(os.path.exists(md))
        self.assertEqual([n for n in os.listdir(self.base) if n.startswith(".linkcheck-")], [])

    def test_unreadable_page_exits_2_naming_path(self):
        self.write("sub/locked.html")
        real_open = open

        def failing_open(path, *a, **k):
            if os.fspath(path).endswith("locked.html"):
                raise PermissionError(13, "Permission denied", path)
            return real_open(path, *a, **k)

        report = self.out("r.json")
        with mock.patch("builtins.open", failing_open), mock.patch("sys.stderr") as err:
            code = cli.main([self.site, "--json", report])
        self.assertEqual(code, 2)
        self.assertIn("sub/locked.html", "".join(c.args[0] for c in err.write.call_args_list))
        self.assertFalse(os.path.exists(report))


class JsonReportTest(CliTestCase):
    def test_shape_order_and_determinism(self):
        self.broken_site()
        self.write("a.html", '<a href="mailto:x@y.z">m</a><a href="https://b">b</a>')
        first, second = self.out("1.json"), self.out("2.json")
        self.assertEqual(run_linkcheck(self.site, "--json", first).returncode, 1)
        self.assertEqual(run_linkcheck(self.site, "--json", second).returncode, 1)
        raw = self.read(first)
        self.assertEqual(raw, self.read(second))
        self.assertTrue(raw.endswith(b"}\n"))
        self.assertIn(b'\n  "pages": 4,', raw)  # 2-space indent
        doc = json.loads(raw.decode("utf-8"))
        self.assertEqual(list(doc), ["pages", "links", "ignored", "external", "findings"])
        self.assertEqual((doc["pages"], doc["links"], doc["ignored"]), (4, 7, 0))
        self.assertEqual(
            doc["external"],
            [
                {"path": "a.html", "line": 1, "target": "https://b"},
                {"path": "a.html", "line": 1, "target": "mailto:x@y.z"},
                {"path": "index.html", "line": 2, "target": "https://example.com/x"},
            ],
        )
        self.assertEqual(len(doc["findings"]), 5)
        for f in doc["findings"]:
            self.assertEqual(list(f), ["path", "line", "kind", "target"])
        keys = [(f["path"], f["line"], f["kind"], f["target"]) for f in doc["findings"]]
        self.assertEqual(keys, sorted(keys))

    def test_non_ascii_written_as_utf8(self):
        self.write("index.html", '<a href="café.html">c</a>')
        out = self.out("r.json")
        run_linkcheck(self.site, "--json", out)
        self.assertIn("café.html".encode("utf-8"), self.read(out))

    def test_renderer_sorts_unsorted_input(self):
        result = SiteResult(
            1, 2, 0,
            (External("b", 1, "x"), External("a", 9, "y")),
            (Finding("b", 1, "k", "t"), Finding("a", 2, "k", "t"), Finding("a", 1, "z", "t")),
        )
        doc = json.loads(to_json(result))
        self.assertEqual([e["path"] for e in doc["external"]], ["a", "b"])
        self.assertEqual([(f["path"], f["line"]) for f in doc["findings"]], [("a", 1), ("a", 2), ("b", 1)])


class MarkdownReportTest(CliTestCase):
    def test_summary_and_sections(self):
        self.broken_site()
        self.write("pipe.html", '<a href="a|b`c.html">x</a>')
        first, second = self.out("1.md"), self.out("2.md")
        run_linkcheck(self.site, "--markdown", first, "--ignore", "nothing")
        run_linkcheck(self.site, "--markdown", second, "--ignore", "nothing")
        self.assertEqual(self.read(first), self.read(second))
        text = self.read(first).decode("utf-8")
        self.assertTrue(text.endswith("\n"))
        for row in ("| Pages | 4 |", "| Links | 6 |", "| External | 1 |", "| Ignored | 0 |", "| Findings | 6 |"):
            self.assertIn(row, text)
        headings = [l for l in text.splitlines() if l.startswith("## ")]
        self.assertEqual(headings, ["## bad.html", "## guide/intro.html", "## index.html", "## pipe.html"])
        self.assertIn("| 2 | decode-error | byte 10 |", text)
        self.assertIn("| 3 | missing-anchor | index.html#nope |", text)
        self.assertIn("| 1 | missing-target | a\\|b\\`c.html |", text)
        self.assertNotIn("No findings", text)

    def test_clean_run_says_no_findings(self):
        self.write("index.html")
        out = self.out("r.md")
        self.assertEqual(run_linkcheck(self.site, "--markdown", out).returncode, 0)
        text = self.read(out).decode("utf-8")
        self.assertIn("No findings.", text)
        self.assertIn("| Findings | 0 |", text)
        self.assertNotIn("## ", text)

    def test_renderer_exact_output(self):
        result = SiteResult(2, 3, 1, (External("a.html", 1, "https://x"),), (Finding("a.html", 4, "empty-link", ""),))
        self.assertEqual(
            to_markdown(result),
            textwrap.dedent(
                """\
                # Link check report

                | Metric | Count |
                | --- | ---: |
                | Pages | 2 |
                | Links | 3 |
                | External | 1 |
                | Ignored | 1 |
                | Findings | 1 |

                ## a.html

                | Line | Kind | Target |
                | ---: | --- | --- |
                | 4 | empty-link |  |
                """
            ),
        )

    def test_json_and_markdown_combined(self):
        self.write("index.html", '<a href="missing.html">m</a>')
        js, md = self.out("r.json"), self.out("r.md")
        proc = run_linkcheck(self.site, "--json", js, "--markdown", md)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(self.read(js))["findings"][0]["target"], "missing.html")
        self.assertIn("| 1 | missing-target | missing.html |", self.read(md).decode())


class IgnoreTest(CliTestCase):
    def test_repeatable_ignore_counted(self):
        self.write(
            "index.html",
            '<a href="drafts/a.html">1</a><a href="old/b.html">2</a><a href="https://e.com">3</a><a href="ok.html">4</a>',
        )
        self.write("ok.html")
        js, md = self.out("r.json"), self.out("r.md")
        proc = run_linkcheck(self.site, "--ignore", "drafts/*", "--ignore", "old/*", "--json", js, "--markdown", md)
        self.assertEqual(proc.returncode, 0)
        doc = json.loads(self.read(js))
        self.assertEqual((doc["links"], doc["ignored"], len(doc["external"])), (2, 2, 1))
        self.assertIn("| Ignored | 2 |", self.read(md).decode())
        self.assertEqual(run_linkcheck(self.site, "--ignore", "drafts/*").stdout, "index.html:1: missing-target: old/b.html\n")


class OfflineScopeTest(CliTestCase):
    def test_external_listed_css_and_script_links_ignored_no_network(self):
        self.write(
            "index.html",
            "<style>body { background: url('bg.png'); }</style>\n"
            "<div style=\"background: url(missing.png)\"></div>\n"
            "<script>var a = document.createElement('a'); a.href = 'gone.html';"
            " document.write('<a href=\"built.html\">x</a>');</script>\n"
            '<a href="https://example.com/x">ext</a>\n',
        )
        out = self.out("r.json")
        code = textwrap.dedent(
            """\
            import runpy, socket, sys
            def blocked(*a, **k):
                raise RuntimeError("network access attempted")
            socket.socket = blocked
            socket.create_connection = blocked
            socket.getaddrinfo = blocked
            sys.argv = ["linkcheck"] + sys.argv[1:]
            runpy.run_module("linkcheck", run_name="__main__", alter_sys=True)
            """
        )
        proc = subprocess.run(
            [sys.executable, "-c", code, self.site, "--json", out],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))
        doc = json.loads(self.read(out))
        self.assertEqual(doc["links"], 1)
        self.assertEqual(doc["external"], [{"path": "index.html", "line": 4, "target": "https://example.com/x"}])
        self.assertEqual(doc["findings"], [])


class RealSiteTest(unittest.TestCase):
    def test_repo_docs_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "r.json")
            # /newsletter is a serve.py route (SCRUM-103), not a file under docs/.
            proc = run_linkcheck("docs/", "--json", out, "--ignore", "/newsletter")
            self.assertEqual((proc.returncode, proc.stdout), (0, ""))
            with open(out, encoding="utf-8") as fh:
                doc = json.load(fh)
        self.assertEqual((doc["pages"], doc["links"], doc["ignored"], doc["findings"]), (2, 0, 1, []))

    def test_readme_documents_command(self):
        with open(os.path.join(REPO_ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in ("python -m linkcheck docs/", "--json", "--markdown", "--ignore", "GITHUB_STEP_SUMMARY",
                       "empty-link", "missing-target", "missing-anchor", "outside-root", "decode-error"):
            self.assertIn(needle, readme)


if __name__ == "__main__":
    unittest.main()
