import os
import tempfile
import unittest

import linkcheck
from linkcheck import extract
from linkcheck.extract import Link, PageDecodeError, extract_links, parse_page


class ExtractTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write(self, content, name="page.html"):
        path = os.path.join(self._tmp.name, name)
        data = content.encode("utf-8") if isinstance(content, str) else content
        with open(path, "wb") as fh:
            fh.write(data)
        return path


class HappyPathTest(ExtractTestCase):
    def test_five_links_in_document_order(self):
        path = self.write(
            "<html>\n"
            "<head><link rel=stylesheet href=\"style.css\"></head>\n"
            "<body>\n"
            "<a href=\"one.html\">1</a>\n"
            "<img src=\"pic.png\" alt=\"\">\n"
            "<p><a href=\"two.html#x\">2</a> <a href=\"https://example.com/\">3</a></p>\n"
            "</body></html>\n"
        )
        self.assertEqual(
            extract_links(path),
            [
                Link("style.css", 2, "stylesheet"),
                Link("one.html", 4, "anchor"),
                Link("pic.png", 5, "image"),
                Link("two.html#x", 6, "anchor"),
                Link("https://example.com/", 6, "anchor"),
            ],
        )
        for link in extract_links(path):
            self.assertIsInstance(link.target, str)
            self.assertIsInstance(link.line, int)

    def test_script_src_kind(self):
        path = self.write('<script src="app.js"></script>')
        self.assertEqual(extract_links(path), [Link("app.js", 1, "script")])

    def test_self_closing_tags(self):
        path = self.write('<img src="a.png"/>\n<link href="s.css" />')
        self.assertEqual(
            extract_links(path),
            [Link("a.png", 1, "image"), Link("s.css", 2, "stylesheet")],
        )

    def test_line_is_line_of_tag_start(self):
        path = self.write('<p>x</p>\n\n<a\n  href="late.html">y</a>')
        self.assertEqual(extract_links(path), [Link("late.html", 3, "anchor")])


class BoundaryTest(ExtractTestCase):
    def test_unescaped_and_trimmed(self):
        path = self.write('<a href="  a.html?x=1&amp;y=2  ">a</a>\n<a href="\tb.html\n">b</a>')
        self.assertEqual(
            [l.target for l in extract_links(path)], ["a.html?x=1&y=2", "b.html"]
        )

    def test_empty_values_are_empty_links_not_links(self):
        path = self.write(
            '<a href="">e</a>\n'
            '<a href="   ">w</a>\n'
            "<a href>v</a>\n"
            '<img src="">\n'
            "<script src></script>\n"
            '<a href="ok.html">ok</a>\n'
        )
        page = parse_page(path)
        self.assertEqual(page.links, (Link("ok.html", 6, "anchor"),))
        self.assertEqual(page.empty_lines, (1, 2, 3, 4, 5))

    def test_case_insensitive_tags_and_attributes(self):
        path = self.write('<A HREF="up.html">x</A><IMG SRC="p.png">')
        self.assertEqual(
            extract_links(path),
            [Link("up.html", 1, "anchor"), Link("p.png", 1, "image")],
        )

    def test_duplicate_attribute_uses_first(self):
        path = self.write('<a href="first.html" href="second.html">x</a>')
        self.assertEqual(extract_links(path), [Link("first.html", 1, "anchor")])

    def test_duplicate_empty_first_is_empty_link(self):
        page = parse_page(self.write('<a href="" href="second.html">x</a>'))
        self.assertEqual(page.links, ())
        self.assertEqual(page.empty_lines, (1,))

    def test_elements_without_attribute_produce_nothing(self):
        page = parse_page(
            self.write("<script>var x = 1;</script><a name=top>t</a><img alt=x><link rel=icon>")
        )
        self.assertEqual(page.links, ())
        self.assertEqual(page.empty_lines, ())

    def test_other_elements_and_attributes_ignored(self):
        path = self.write(
            '<iframe src="f.html"></iframe><area href="m.html"><a data-href="d.html" title="t.html">x</a>'
            '<img srcset="s.png 2x">'
        )
        self.assertEqual(extract_links(path), [])

    def test_script_and_style_bodies_and_css_url_are_not_links(self):
        path = self.write(
            "<style>body { background: url('bg.png'); } a[href] {}</style>\n"
            "<script>document.write('<a href=\"built.html\">x</a>');"
            " var s = '<img src=\"x.png\">';</script>\n"
            '<div style="background: url(inline.png)">x</div>\n'
            "<!-- <a href=\"commented.html\">c</a> -->\n"
            '<a href="real.html">r</a>\n'
        )
        self.assertEqual(extract_links(path), [Link("real.html", 5, "anchor")])


class AnchorsTest(ExtractTestCase):
    def test_ids_on_any_element_and_names_only_on_a(self):
        page = parse_page(
            self.write(
                '<h1 id="top">t</h1><section id="s1"></section><a name="legacy">l</a>'
                '<input name="field"><img id="pic" src="p.png"><br id="br"/>'
            )
        )
        self.assertEqual(page.anchors, frozenset({"top", "s1", "legacy", "pic", "br"}))


class DecodeErrorTest(ExtractTestCase):
    def test_invalid_utf8_raises_with_path_offset_and_line(self):
        data = b"<p>ok</p>\n<p>fine</p>\nbad \xff here\n"
        path = self.write(data)
        self.assertEqual(data.index(b"\xff"), 26)
        with self.assertRaises(PageDecodeError) as ctx:
            extract_links(path)
        err = ctx.exception
        self.assertEqual(err.offset, 26)
        self.assertEqual(err.line, 3)
        self.assertEqual(err.path, path)
        self.assertIn(path, str(err))
        self.assertIn("byte 26", str(err))

    def test_offset_counts_bom_bytes(self):
        path = self.write(b"\xef\xbb\xbfab\n\xff")
        with self.assertRaises(PageDecodeError) as ctx:
            parse_page(path)
        self.assertEqual(ctx.exception.offset, 6)
        self.assertEqual(ctx.exception.line, 2)

    def test_leading_bom_accepted(self):
        path = self.write(b'\xef\xbb\xbf<a href="x.html">x</a>')
        self.assertEqual(extract_links(path), [Link("x.html", 1, "anchor")])

    def test_truncated_multibyte_sequence(self):
        path = self.write("<p>é</p>".encode("utf-8")[:4])
        with self.assertRaises(PageDecodeError) as ctx:
            extract_links(path)
        self.assertEqual(ctx.exception.offset, 3)


class ImportTest(unittest.TestCase):
    def test_public_names(self):
        for name in ("extract_links", "Link", "PageDecodeError"):
            self.assertIs(getattr(linkcheck, name), getattr(extract, name))


if __name__ == "__main__":
    unittest.main()
