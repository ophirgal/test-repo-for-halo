import builtins
import io
import os
import tempfile
import unittest
from unittest import mock

import linkcheck
from linkcheck import check as check_mod
from linkcheck.check import External, Finding, LinkcheckIOError, check_site


class SiteTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        self.root = os.path.join(self.base, "site")
        os.mkdir(self.root)

    def write(self, rel, content="<p>x</p>", base=None):
        path = os.path.join(base or self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = content.encode("utf-8") if isinstance(content, str) else content
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def findings(self, **kw):
        return list(check_site(self.root, **kw).findings)


class HappyPathTest(SiteTestCase):
    def test_clean_site_no_findings_and_counts(self):
        self.write(
            "index.html",
            '<link href="style.css"><a href="other.html#sec">o</a>\n'
            '<a href="guide/">g</a><img src="img/p.png"><a href="#top" id="top">t</a>\n'
            '<a href="https://example.com/">e</a><script src="app.js"></script>',
        )
        self.write("other.html", '<h2 id="sec">s</h2><a href="index.html">back</a>')
        self.write("guide/index.html", '<a href="../other.html">o</a>')
        self.write("style.css", "body{}")
        self.write("img/p.png", b"\x89PNG")
        self.write("app.js", "")
        result = check_site(self.root)
        self.assertEqual(result.findings, ())
        self.assertEqual(result.pages, 3)
        self.assertEqual(result.links, 9)
        self.assertEqual(result.ignored, 0)
        self.assertEqual(result.external, (External("index.html", 3, "https://example.com/"),))

    def test_check_site_reexported(self):
        self.assertIs(linkcheck.check_site, check_site)


class MissingTargetTest(SiteTestCase):
    def test_missing_file(self):
        self.write("index.html", '<p>\n<a href="missing.html">m</a>')
        self.assertEqual(self.findings(), [Finding("index.html", 2, "missing-target", "missing.html")])

    def test_missing_from_subfolder_is_root_relative(self):
        self.write("guide/intro.html", '<a href="setup.html">s</a><a href="../nope/x.html">n</a>')
        self.assertEqual(
            self.findings(),
            [
                Finding("guide/intro.html", 1, "missing-target", "guide/setup.html"),
                Finding("guide/intro.html", 1, "missing-target", "nope/x.html"),
            ],
        )

    def test_query_stripped_and_percent_decoded(self):
        self.write("my page.html")
        self.write("index.html", '<a href="my%20page.html?x=1">a</a><a href="other.html?x=1">b</a>')
        self.assertEqual(self.findings(), [Finding("index.html", 1, "missing-target", "other.html")])


class AnchorTest(SiteTestCase):
    def test_missing_anchor_in_other_page(self):
        self.write("other.html", '<h1 id="yes">y</h1><a name="named">n</a>')
        self.write(
            "index.html",
            '<a href="other.html#yes">1</a><a href="other.html#named">2</a>\n<a href="other.html#nope">3</a>',
        )
        self.assertEqual(self.findings(), [Finding("index.html", 2, "missing-anchor", "other.html#nope")])

    def test_bare_fragment_checked_against_same_page(self):
        self.write("sub/page.html", '<a href="#top">ok</a><div id="top"></div>\n<a href="#gone">x</a>')
        self.assertEqual(self.findings(), [Finding("sub/page.html", 2, "missing-anchor", "sub/page.html#gone")])

    def test_empty_fragment_is_no_finding(self):
        self.write("index.html", '<a href="#">top</a><a href="index.html#">self</a>')
        self.assertEqual(self.findings(), [])

    def test_anchor_is_case_sensitive_and_percent_decoded(self):
        self.write("index.html", '<p id="a b"></p><p id="Top"></p><a href="#a%20b">1</a><a href="#top">2</a>')
        self.assertEqual(self.findings(), [Finding("index.html", 1, "missing-anchor", "index.html#top")])

    def test_fragment_on_non_html_or_undecodable_target_not_checked(self):
        self.write("p.png", b"\x89PNG")
        self.write("bad.html", b"\xff")
        self.write("index.html", '<a href="p.png#x">1</a><a href="bad.html#x">2</a>')
        self.assertEqual(self.findings(), [Finding("bad.html", 1, "decode-error", "byte 0")])

    def test_directory_link_fragment_checked_in_index(self):
        self.write("guide/index.html", '<p id="here"></p>')
        self.write("index.html", '<a href="guide/#here">1</a><a href="guide/#not">2</a>')
        self.assertEqual(
            self.findings(), [Finding("index.html", 1, "missing-anchor", "guide/index.html#not")]
        )


class OutsideRootTest(SiteTestCase):
    def setUp(self):
        super().setUp()
        self.sentinel = self.write("secret.html", '<p id="x">secret</p>', base=self.base)
        os.makedirs(os.path.join(self.base, "outdir"))
        self.write("outdir/index.html", "<p>out</p>", base=self.base)

    def assert_never_touched(self, run):
        """Fail if the sentinel (or anything outside the root) is opened or stat'ed."""
        real_open, real_io_open, real_stat = builtins.open, io.open, os.stat
        outside = []

        def guard(path):
            p = os.fspath(path) if not isinstance(path, int) else ""
            if isinstance(p, str) and p and not os.path.abspath(p).startswith(self.root + os.sep):
                if os.path.abspath(p) != self.root:
                    outside.append(p)

        def spy_open(path, *a, **k):
            guard(path)
            return real_open(path, *a, **k)

        def spy_io_open(path, *a, **k):
            guard(path)
            return real_io_open(path, *a, **k)

        def spy_stat(path, *a, **k):
            guard(path)
            return real_stat(path, *a, **k)

        with mock.patch("builtins.open", spy_open), mock.patch("io.open", spy_io_open), mock.patch(
            "os.stat", spy_stat
        ):
            result = run()
        self.assertEqual(outside, [])
        return result

    def test_relative_escape(self):
        self.write("a/b/page.html", '<a href="../../../secret.html#x">s</a><a href="../../../../../../etc/passwd">p</a>')
        result = self.assert_never_touched(lambda: check_site(self.root))
        self.assertEqual(
            list(result.findings),
            [
                Finding("a/b/page.html", 1, "outside-root", "../../../../../../etc/passwd"),
                Finding("a/b/page.html", 1, "outside-root", "../../../secret.html#x"),
            ],
        )

    def test_file_urls(self):
        self.write("page.html", f'<a href="file://{self.sentinel}">1</a>\n<a href="file:///etc/passwd">2</a>\n'
                                '<a href="file://otherhost/x.html">3</a>\n'
                                f'<a href="file://localhost{self.root}/page.html">4</a>')
        result = self.assert_never_touched(lambda: check_site(self.root))
        self.assertEqual(
            list(result.findings),
            [
                Finding("page.html", 1, "outside-root", f"file://{self.sentinel}"),
                Finding("page.html", 2, "outside-root", "file:///etc/passwd"),
                Finding("page.html", 3, "outside-root", "file://otherhost/x.html"),
            ],
        )
        self.assertEqual(result.links, 4)

    def test_symlink_link_escaping_root(self):
        os.symlink(self.sentinel, os.path.join(self.root, "link.html"))
        os.symlink(os.path.join(self.base, "outdir"), os.path.join(self.root, "outlink"))
        self.write("page.html", '<a href="link.html#x">1</a><a href="outlink/">2</a><a href="outlink">3</a>')
        result = self.assert_never_touched(lambda: check_site(self.root))
        self.assertEqual(
            list(result.findings),
            [
                Finding("page.html", 1, "outside-root", "link.html#x"),
                Finding("page.html", 1, "outside-root", "outlink"),
                Finding("page.html", 1, "outside-root", "outlink/"),
            ],
        )
        # The escaping symlinked file and directory are not crawled either.
        self.assertEqual(result.pages, 1)

    def test_directory_index_symlink_escaping_root(self):
        os.makedirs(os.path.join(self.root, "guide"))
        os.symlink(self.sentinel, os.path.join(self.root, "guide", "index.html"))
        self.write("page.html", '<a href="guide/">g</a>')
        result = self.assert_never_touched(lambda: check_site(self.root))
        self.assertEqual(list(result.findings), [Finding("page.html", 1, "outside-root", "guide/")])

    def test_symlink_inside_root_is_followed(self):
        self.write("real.html", '<p id="a"></p>')
        os.symlink(os.path.join(self.root, "real.html"), os.path.join(self.root, "alias.html"))
        self.write("page.html", '<a href="alias.html#a">1</a>')
        self.assertEqual(self.findings(), [])


class DirectoryLinkTest(SiteTestCase):
    def test_trailing_slash_resolves_to_index(self):
        self.write("guide/index.html")
        self.write("index.html", '<a href="guide/">g</a><a href="guide">g2</a><a href="./guide/">g3</a>')
        self.assertEqual(self.findings(), [])

    def test_directory_without_index_is_missing(self):
        os.makedirs(os.path.join(self.root, "guide"))
        self.write("index.html", '<a href="guide/">g</a>\n<a href="guide">g2</a>\n<a href="nodir/">n</a>')
        self.assertEqual(
            self.findings(),
            [
                Finding("index.html", 1, "missing-target", "guide/index.html"),
                Finding("index.html", 2, "missing-target", "guide/index.html"),
                Finding("index.html", 3, "missing-target", "nodir/index.html"),
            ],
        )

    def test_root_slash_resolves_to_root_index(self):
        self.write("sub/page.html", '<a href="/">home</a>')
        self.assertEqual(self.findings(), [Finding("sub/page.html", 1, "missing-target", "index.html")])
        self.write("index.html")
        self.assertEqual(self.findings(), [])


class RootRelativeTest(SiteTestCase):
    def test_root_relative_from_subfolder(self):
        self.write("sub/page.html", '<a href="/other.html">o</a>')
        self.assertEqual(self.findings(), [Finding("sub/page.html", 1, "missing-target", "other.html")])
        self.write("other.html")
        self.assertEqual(self.findings(), [])

    def test_root_relative_cannot_escape(self):
        self.write("page.html", '<a href="/../secret.html">s</a>')
        self.write("secret.html", base=self.base)
        self.assertEqual(self.findings(), [Finding("page.html", 1, "outside-root", "/../secret.html")])


class ExternalTest(SiteTestCase):
    def test_external_schemes_listed_counted_not_findings(self):
        targets = [
            "https://example.com/x",
            "http://example.com",
            "HTTPS://EXAMPLE.COM",
            "mailto:a@b.c",
            "javascript:void(0)",
            "data:text/plain,hi",
            "tel:+123",
            "//cdn.example.com/x.js",
        ]
        self.write("index.html", "\n".join(f'<a href="{t}">x</a>' for t in targets))
        with mock.patch("socket.socket", side_effect=AssertionError("network used")):
            result = check_site(self.root)
        self.assertEqual(result.findings, ())
        self.assertEqual(result.links, len(targets))
        self.assertEqual(
            list(result.external), [External("index.html", i + 1, t) for i, t in enumerate(targets)]
        )

    def test_no_network_modules_imported(self):
        import ast

        pkg = os.path.dirname(check_mod.__file__)
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    mods = []
                    if isinstance(node, ast.Import):
                        mods = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        mods = [node.module or ""]
                    for mod in mods:
                        self.assertNotIn(mod.split(".")[0], {"socket", "http", "ssl"}, name)
                        self.assertNotEqual(mod, "urllib.request", name)


class EmptyAndDecodeTest(SiteTestCase):
    def test_empty_link_finding(self):
        self.write("index.html", '<a href="">e</a>\n<img src=" ">')
        result = check_site(self.root)
        self.assertEqual(
            list(result.findings),
            [Finding("index.html", 1, "empty-link", ""), Finding("index.html", 2, "empty-link", "")],
        )
        self.assertEqual(result.links, 0)

    def test_undecodable_page(self):
        self.write("bad.html", b'<a href="missing.html">x</a>\n<p>\xfe</p>')
        self.write("good.html")
        result = check_site(self.root)
        self.assertEqual(result.pages, 2)
        self.assertEqual(result.links, 0)
        self.assertEqual(list(result.findings), [Finding("bad.html", 2, "decode-error", "byte 32")])


class IgnoreTest(SiteTestCase):
    def test_ignored_links_dropped_and_counted(self):
        self.write(
            "index.html",
            '<a href="drafts/a.html">1</a><a href="drafts/b.html#x">2</a>'
            '<a href="https://example.com/x">3</a><a href="Drafts/c.html">4</a><a href="">5</a>',
        )
        result = check_site(self.root, ignore=["drafts/*", "https://example.com/*"])
        self.assertEqual(result.ignored, 3)
        self.assertEqual(result.links, 1)
        self.assertEqual(result.external, ())
        self.assertEqual(
            list(result.findings),
            [
                Finding("index.html", 1, "empty-link", ""),
                Finding("index.html", 1, "missing-target", "Drafts/c.html"),
            ],
        )


class CrawlTest(SiteTestCase):
    def test_suffixes_and_hidden_dirs(self):
        self.write("a.html")
        self.write("B.HTML")
        self.write("c.htm", '<a href="x.html">x</a>')
        self.write("notes.txt", '<a href="x.html">x</a>')
        self.write(".hidden/d.html")
        self.assertEqual(check_site(self.root).pages, 3)

    def test_deterministic_and_sorted(self):
        self.write("z.html", '<a href="m1.html">1</a>')
        self.write("a/b.html", '<a href="m2.html">2</a>\n<a href="#x">3</a>')
        self.write("a.html", '<a href="https://z">z</a><a href="https://a">a</a>')
        first, second = check_site(self.root), check_site(self.root)
        self.assertEqual(first, second)
        self.assertEqual([f.path for f in first.findings], ["a/b.html", "a/b.html", "z.html"])
        self.assertEqual(list(first.findings), sorted(first.findings))
        self.assertEqual([e.target for e in first.external], ["https://a", "https://z"])

    def test_each_page_parsed_once(self):
        self.write("index.html", '<a href="o.html#a">1</a><a href="o.html#b">2</a><a href="o.html">3</a>')
        self.write("o.html", '<p id="a"></p><a href="index.html#z">i</a>')
        calls = []
        real = check_mod.parse_page

        def spy(path):
            calls.append(path)
            return real(path)

        with mock.patch.object(check_mod, "parse_page", spy):
            result = check_site(self.root)
        self.assertEqual(sorted(calls), sorted(set(calls)))
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result.findings), 2)

    def test_not_a_directory(self):
        with self.assertRaises(NotADirectoryError):
            check_site(os.path.join(self.root, "nope"))


class IOErrorTest(SiteTestCase):
    def test_unreadable_page_raises_naming_path(self):
        self.write("sub/locked.html")
        real_open = builtins.open

        def failing_open(path, *a, **k):
            if os.fspath(path).endswith("locked.html"):
                raise PermissionError(13, "Permission denied", path)
            return real_open(path, *a, **k)

        with mock.patch("builtins.open", failing_open):
            with self.assertRaises(LinkcheckIOError) as ctx:
                check_site(self.root)
        self.assertEqual(ctx.exception.path, "sub/locked.html")
        self.assertIn("sub/locked.html", str(ctx.exception))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores file permissions")
    def test_chmod_000_page(self):
        path = self.write("locked.html")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        with self.assertRaises(LinkcheckIOError):
            check_site(self.root)


if __name__ == "__main__":
    unittest.main()
