"""SCRUM-126 — the /guestbook page: message rules, file store, page and HTTP route."""

import contextlib
import datetime
import http.client
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

import guestbook
import serve
from guestbook import store as gb_store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
LOOK_ALIKES = ("/guestbook/", "/guestbook.html", "/Guestbook", "/guestbookx")
UTC = datetime.timezone.utc
XSS = "<b>שלום</b><script>alert(1)</script>"


def at(minute):
    return datetime.datetime(2026, 11, 24, 8, minute, 0, tzinfo=UTC)


def local_text(when):
    return when.astimezone().strftime("%Y-%m-%d %H:%M")


def list_items(page):
    return re.findall(r'<li><span class="msg" dir="auto">(.*?)</span><time datetime="([^"]+)">([^<]+)</time></li>', page)


def field_value(page):
    return re.search(r'<input [^>]*value="([^"]*)"', page).group(1)


class MessageRulesTest(unittest.TestCase):  # C6, C7, C8, C9
    def test_200_with_spaces_accepted_trimmed(self):
        text, error, n = guestbook.check("   " + "a" * 200 + "  ")
        self.assertEqual((text, error, n), ("a" * 200, None, 200))

    def test_201_refused_not_cut(self):
        text, error, n = guestbook.check(" " + "a" * 201 + " ")
        self.assertEqual((error, n), (guestbook.TOO_LONG, 201))

    def test_empty_and_spaces_refused(self):
        for raw in ("", "   ", "\n", " \r\n\t "):
            with self.subTest(raw=raw):
                self.assertEqual(guestbook.check(raw)[1], guestbook.EMPTY)

    def test_line_breaks_become_one_space(self):
        for sep in ("\n", "\r\n", "\r", "\u2028", "\u2029", "\x85", "\v", "\f"):
            with self.subTest(sep=sep):
                self.assertEqual(guestbook.normalise(" a" + sep + "b "), "a b")

    def test_hebrew_counts_code_points(self):
        self.assertEqual(guestbook.check("ש" * 200)[1:], (None, 200))
        self.assertEqual(guestbook.check("ש" * 201)[1:], (guestbook.TOO_LONG, 201))


class StoreTest(unittest.TestCase):  # C3, C4, C11, C12
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "guestbook.jsonl")

    def lines(self):
        with open(self.path, encoding="utf-8") as fh:
            return fh.read().split("\n")

    def test_latest_20_newest_first(self):
        store = guestbook.GuestbookStore(self.path)
        for i in range(25):
            store.append(f"m{i}", now=at(i))
        latest = store.latest()
        self.assertEqual([r.text for r in latest], [f"m{i}" for i in range(24, 4, -1)])
        reloaded = guestbook.GuestbookStore(self.path).latest()
        self.assertEqual(reloaded, latest)

    def test_missing_file_empty_and_not_created(self):
        self.assertEqual(guestbook.GuestbookStore(self.path).latest(), [])
        self.assertFalse(os.path.exists(self.path))

    def test_record_format(self):
        guestbook.GuestbookStore(self.path).append("שלום", now=at(5))
        self.assertEqual(self.lines(), ['{"t":"2026-11-24T08:05:00Z","m":"שלום"}', ""])

    def test_bad_lines_skipped_with_warning(self):
        good = json.dumps({"t": "2026-11-24T08:00:00Z", "m": "ok"})
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join([good, "", "garbage", '{"t": 1, "m": "x"}', '{"t": "nope", "m": "x"}', good]) + "\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            latest = guestbook.GuestbookStore(self.path).latest()
        self.assertEqual([r.text for r in latest], ["ok", "ok"])
        warnings = err.getvalue().splitlines()
        self.assertEqual(len(warnings), 4)
        for lineno, line in zip((2, 3, 4, 5), warnings):
            self.assertIn(f"line {lineno}", line)

    def test_missing_trailing_newline_repaired(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"t":"2026-11-24T08:00:00Z","m":"a"}')
        guestbook.GuestbookStore(self.path).append("b", now=at(1))
        lines = self.lines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[1])["m"], "b")
        self.assertEqual([r.text for r in guestbook.GuestbookStore(self.path).latest()], ["b", "a"])

    def test_concurrent_appends_whole_lines(self):
        store = guestbook.GuestbookStore(self.path)
        threads = [threading.Thread(target=store.append, args=(f"t{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        lines = [json.loads(line) for line in self.lines() if line]
        self.assertEqual(sorted(r["m"] for r in lines), sorted(f"t{i}" for i in range(10)))

    def test_missing_directory_raises_and_not_created(self):
        path = os.path.join(self.tmp.name, "absent", "g.jsonl")
        store = guestbook.GuestbookStore(path)
        with self.assertRaises(OSError):
            store.append("x")
        self.assertEqual(store.latest(), [])
        self.assertFalse(os.path.exists(os.path.dirname(path)))


class PageTest(unittest.TestCase):  # C2, C3, C4, C7, C8, C10, C14, C15
    def render(self, records=(), **kw):
        return guestbook.render(list(records), **kw).decode("utf-8")

    def test_order_of_elements(self):
        page = self.render([gb_store.Record(at(1), "hi")])
        needles = ("<h1>Guestbook</h1>", ">Your message</label>", 'type="text"', 'placeholder="Write one line…"',
                   '<button type="submit">Send</button>', "One line, up to 200 characters.",
                   ">Latest messages</h2>", "<ol>")
        positions = [page.index(n) for n in needles]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('<form method="post" action="/guestbook">', page)
        self.assertEqual(page.count("<input"), 1)
        for banned in ("maxlength", "<script", 'href="/"', "/jungle", "<a "):
            self.assertNotIn(banned, page.lower())

    def test_times_and_direction(self):
        records = [gb_store.Record(at(30), "b"), gb_store.Record(at(1), "a")]
        items = list_items(self.render(records))
        self.assertEqual(items, [("b", "2026-11-24T08:30:00Z", local_text(at(30))),
                                 ("a", "2026-11-24T08:01:00Z", local_text(at(1)))])
        for _, _, shown in items:
            self.assertRegex(shown, r"^\d{4}-\d\d-\d\d \d\d:\d\d$")

    def test_empty_state(self):
        page = self.render()
        self.assertIn("No messages yet. Be the first to leave one.", page)
        self.assertNotIn("<ol", page)
        self.assertIn('<form method="post"', page)

    def test_error_empty(self):
        page = self.render(error=guestbook.EMPTY, value="   ")
        self.assertIn('aria-invalid="true" aria-describedby="message-error"', page)
        self.assertIn('id="message-error" role="alert"><strong>Message is empty.</strong> '
                      "Nothing was saved. Write at least one character and press Send.", page)
        self.assertNotIn("One line, up to 200 characters.", page)  # the error replaces the hint
        self.assertEqual(field_value(page), "   ")

    def test_error_too_long(self):
        page = self.render(error=guestbook.TOO_LONG, value="x" * 201, length=201)
        self.assertIn("Message is too long — 200 characters at most.", page)
        self.assertIn("Yours has 201. Nothing was saved or cut; shorten it and press Send.", page)
        self.assertEqual(field_value(page), "x" * 201)

    def test_escaping(self):
        page = self.render([gb_store.Record(at(1), XSS)], error=guestbook.EMPTY, value='"><script>x</script>')
        self.assertNotIn("<b>", page)
        self.assertNotIn("<script", page)
        self.assertIn("&lt;b&gt;שלום&lt;/b&gt;&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn('value="&quot;&gt;&lt;script&gt;x&lt;/script&gt;"', page)

    def test_mobile_markers(self):  # C14
        page = self.render([gb_store.Record(at(1), "h" * 200)])
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', page)
        self.assertRegex(page, r"\.msg \{[^}]*overflow-wrap: anywhere")
        self.assertRegex(page, r"\.row input \{[^}]*flex: 1; min-width: 0")
        self.assertIn("font-family: system-ui, sans-serif", page)
        for prop, value in re.findall(r"(?<![\w-])((?:min-|max-)?width):\s*(\d+)px", page):
            self.assertLessEqual(int(value), 360, prop)


class QuietHandler(serve.RootOnlyHandler):
    def log_message(self, fmt, *args):
        pass


class GuestbookHTTPTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kv_path = os.path.join(self.tmp.name, "kv.log")
        self.gb_path = os.path.join(self.tmp.name, "guestbook.jsonl")
        self.use_env(KV_PATH=self.kv_path, GUESTBOOK_PATH=self.gb_path)

    def use_env(self, **env):
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def start(self):
        server = serve.make_server("127.0.0.1", 0, QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

        self.addCleanup(stop)
        self.port = server.server_address[1]
        return server

    def request(self, method, path, body=None, headers=None, port=None):
        conn = http.client.HTTPConnection("127.0.0.1", port or self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, resp.headers, resp.read()
        finally:
            conn.close()

    def post(self, message=None, raw=None, headers=FORM):
        body = raw if raw is not None else urllib.parse.urlencode({"message": message})
        return self.request("POST", "/guestbook", body=body, headers=headers)

    def page(self):
        status, headers, body = self.request("GET", "/guestbook")
        self.assertEqual(status, 200, body)
        return body.decode("utf-8")

    def file_lines(self):
        if not os.path.exists(self.gb_path):
            return []
        with open(self.gb_path, encoding="utf-8") as fh:
            return fh.read().splitlines()

    def raw_send(self, data):
        """Send raw request bytes; return the status line and everything read."""
        import socket

        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
            sock.sendall(data)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks)


class GuestbookHTTPTest(GuestbookHTTPTestCase):
    def test_get_and_head(self):  # C1
        self.start()
        for path in ("/guestbook", "/guestbook?x=1"):
            status, headers, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            csp = headers["Content-Security-Policy"]
            self.assertIn("default-src 'none'", csp)
            self.assertNotIn("script-src", csp)
            self.assertEqual(int(headers["Content-Length"]), len(body))
            hstatus, hheaders, hbody = self.request("HEAD", path)
            self.assertEqual((hstatus, hbody), (200, b""))
            for name in ("Content-Type", "Content-Length", "X-Content-Type-Options", "Content-Security-Policy"):
                self.assertEqual(hheaders[name], headers[name])
        self.assertFalse(os.path.exists(self.gb_path))  # C4: a GET never creates the file

    def test_look_alikes_404(self):  # C1, AC 12
        self.start()
        for path in LOOK_ALIKES:
            for method in ("GET", "HEAD"):
                with self.subTest(path=path, method=method):
                    self.assertEqual(self.request(method, path)[0], 404)

    def test_empty_state(self):  # C4, AC 8
        self.start()
        self.assertIn("No messages yet. Be the first to leave one.", self.page())
        with open(self.gb_path, "w", encoding="utf-8") as fh:
            fh.write("garbage\n")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIn("No messages yet.", self.start_fresh_page())

    def start_fresh_page(self):
        self.start()
        return self.page()

    def test_post_redirect_get(self):  # C5, AC 1
        self.start()
        status, headers, body = self.post("שלום מכולם")
        self.assertEqual((status, headers["Location"], body), (303, "/guestbook", b""))
        self.assertEqual(len(self.file_lines()), 1)
        page = self.page()
        items = list_items(page)
        self.assertEqual(items[0][0], "שלום מכולם")
        self.assertRegex(items[0][2], r"^\d{4}-\d\d-\d\d \d\d:\d\d$")
        self.assertEqual(field_value(page), "")
        self.page()
        self.assertEqual(len(self.file_lines()), 1)  # a refresh adds nothing

    def test_latest_20(self):  # C3, AC 2
        store = guestbook.GuestbookStore(self.gb_path)
        for i in range(25):
            store.append(f"m{i}", now=at(i))
        self.start()
        items = list_items(self.page())
        self.assertEqual([i[0] for i in items], [f"m{i}" for i in range(24, 4, -1)])
        self.assertEqual([i[2] for i in items], [local_text(at(i)) for i in range(24, 4, -1)])

    def test_exactly_200_trimmed(self):  # C6, AC 4
        self.start()
        self.assertEqual(self.post("   " + "ש" * 200 + "   ")[0], 303)
        self.assertEqual(list_items(self.page())[0][0], "ש" * 200)

    def test_too_long_refused(self):  # C7, AC 3
        self.start()
        self.post("first")
        before = self.file_lines()
        status, headers, body = self.post(" " + "x" * 201 + " ")
        page = body.decode("utf-8")
        self.assertEqual(status, 400)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Message is too long — 200 characters at most.", page)
        self.assertIn("Yours has 201. Nothing was saved or cut; shorten it and press Send.", page)
        self.assertIn('aria-invalid="true" aria-describedby="message-error"', page)
        self.assertIn('role="alert"', page)
        self.assertEqual(field_value(page), " " + "x" * 201 + " ")
        self.assertEqual([i[0] for i in list_items(page)], ["first"])
        self.assertEqual(self.file_lines(), before)

    def test_empty_refused(self):  # C8, AC 5
        self.start()
        for raw in ("message=", "message=+++", "other=1", ""):
            with self.subTest(raw=raw):
                status, _, body = self.post(raw=raw)
                page = body.decode("utf-8")
                self.assertEqual(status, 400)
                self.assertIn("<strong>Message is empty.</strong> "
                              "Nothing was saved. Write at least one character and press Send.", page)
                self.assertIn("No messages yet.", page)
        self.assertEqual(field_value(self.post(raw="message=+++")[2].decode()), "   ")
        self.assertFalse(os.path.exists(self.gb_path))

    def test_line_breaks_one_item(self):  # C9, AC 6
        self.start()
        self.post("one\r\ntwo\nthree\u2028four")
        self.assertEqual(len(self.file_lines()), 1)
        self.assertEqual([i[0] for i in list_items(self.page())], ["one two three four"])

    def test_code_shown_as_text(self):  # C10, AC 7
        self.start()
        self.post(XSS)
        page = self.page()
        self.assertEqual(list_items(page)[0][0], "&lt;b&gt;שלום&lt;/b&gt;&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotIn("<b>", page)
        self.assertNotIn("<script", page)
        status, _, body = self.post('"' + "<script>" * 30)
        self.assertEqual(status, 400)
        self.assertNotIn("<script", body.decode())
        self.assertTrue(field_value(body.decode()).startswith("&quot;&lt;script&gt;"))

    def test_restart_keeps_order_and_times(self):  # C11, AC 9
        self.start()
        for text in ("a", "b", "c"):
            self.post(text)
        first = list_items(self.page())
        self.start()  # a second server on the same GUESTBOOK_PATH
        self.assertEqual(list_items(self.page()), first)
        self.assertEqual([i[0] for i in first], ["c", "b", "a"])
        for line in self.file_lines():
            self.assertRegex(json.loads(line)["t"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_default_path(self):  # C11
        os.environ.pop("GUESTBOOK_PATH")
        server = self.start()
        self.assertEqual(server.guestbook_store().path, "./guestbook.jsonl")

    def test_bad_line_page_still_renders(self):  # C12
        with open(self.gb_path, "w", encoding="utf-8") as fh:
            fh.write('{"t":"2026-11-24T08:00:00Z","m":"ok"}\n{bad\n')
        self.start()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            page = self.page()
        self.assertEqual([i[0] for i in list_items(page)], ["ok"])
        self.assertIn("line 2", err.getvalue())

    def test_concurrent_posts(self):  # C12
        self.start()
        results = []
        threads = [threading.Thread(target=lambda i=i: results.append(self.post(f"p{i}")[0])) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results, [303] * 10)
        self.assertEqual(sorted(json.loads(x)["m"] for x in self.file_lines()), sorted(f"p{i}" for i in range(10)))

    def test_unwritable_path_500(self):  # C12
        missing = os.path.join(self.tmp.name, "absent", "g.jsonl")
        self.use_env(GUESTBOOK_PATH=missing)
        self.start()
        self.assertEqual(self.post("hi")[0], 500)
        self.assertFalse(os.path.exists(os.path.dirname(missing)))
        self.assertIn("No messages yet.", self.page())

    def test_unreadable_file_500_others_fine(self):  # C12
        os.mkdir(self.gb_path)  # opening a directory fails, even as root
        self.start()
        self.assertEqual(self.request("GET", "/guestbook")[0], 500)
        self.assertEqual(self.request("HEAD", "/guestbook")[0], 500)
        self.assertEqual(self.post("hi")[0], 500)
        self.assertEqual(self.request("GET", "/")[2], serve.INDEX.read_bytes())
        self.assertEqual(self.request("GET", "/jungle")[2], serve.JUNGLE.read_bytes())
        self.assertEqual(self.request("GET", "/healthz")[0], 200)
        self.assertEqual(self.request("GET", "/kv/")[0], 200)

    def test_request_limits(self):  # C13
        self.start()
        self.assertEqual(self.post("x", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.post(raw="message=%FF")[0], 400)
        self.assertEqual(self.post("hi", headers={"Content-Type": FORM["Content-Type"] + "; charset=UTF-8"})[0], 303)
        for header in (b"", b"Content-Length: abc\r\n", b"Content-Length: 3\r\nContent-Length: 4\r\n"):
            with self.subTest(header=header):
                reply = self.raw_send(b"POST /guestbook HTTP/1.1\r\nHost: x\r\n"
                                      b"Content-Type: application/x-www-form-urlencoded\r\n" + header + b"\r\nmessage=x")
                self.assertTrue(reply.startswith(b"HTTP/1.0 400"), reply[:40])
                self.assertIn(b"Connection: close", reply)
        reply = self.raw_send(b"POST /guestbook HTTP/1.1\r\nHost: x\r\n"
                              b"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: 65537\r\n\r\n")
        self.assertTrue(reply.startswith(b"HTTP/1.0 413"), reply[:40])
        self.assertEqual([json.loads(x)["m"] for x in self.file_lines()], ["hi"])

    def test_repeated_message_uses_first(self):  # C13
        self.start()
        self.assertEqual(self.post(raw="message=first&message=second&x=1")[0], 303)
        self.assertEqual([i[0] for i in list_items(self.page())], ["first"])


class RegressionTest(GuestbookHTTPTestCase):  # C16, AC 11, AC 12
    def standard_501(self, method, path):
        """What the stock BaseHTTPRequestHandler answers for an unsupported method."""

        class Stock(serve.http.server.BaseHTTPRequestHandler):
            server_version = serve.RootOnlyHandler.server_version

            def log_message(self, *args):
                pass

        server = serve.http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stock)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, _, body = self.request(method, path, body=b"x", port=server.server_address[1])
            return status, body
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

    def test_other_methods_and_paths_stock_501(self):
        self.start()
        cases = (("PUT", "/guestbook"), ("DELETE", "/guestbook"), ("POST", "/"), ("POST", "/kv/x"),
                 ("POST", "/guestbook/"), ("POST", "/jungle"), ("POST", "/healthz"))
        for method, path in cases:
            with self.subTest(method=method, path=path):
                status, _, body = self.request(method, path, body=b"x")
                self.assertEqual(status, 501)
                self.assertEqual((status, body), self.standard_501(method, path))
        self.assertFalse(os.path.exists(self.gb_path))

    def test_existing_routes_unchanged(self):
        self.start()
        self.post("hello")
        self.assertEqual(self.request("GET", "/")[2], serve.INDEX.read_bytes())
        self.assertEqual(self.request("GET", "/jungle")[2], serve.JUNGLE.read_bytes())
        self.assertEqual(self.request("GET", "/healthz")[2], b'{"status": "ok"}')
        self.assertEqual(self.request("PUT", "/kv/a", body=b"1")[0], 204)
        self.assertEqual(self.request("GET", "/kv/")[2], b'["a"]')
        self.assertEqual(self.request("GET", "/nope")[0], 404)

    def test_routes_table_unchanged(self):
        self.assertEqual(serve.ROUTES, {"/": serve.INDEX, "/jungle": serve.JUNGLE})

    def test_smoke_test_creates_no_guestbook_file(self):
        missing = os.path.join(self.tmp.name, "absent", "guestbook.jsonl")
        env = dict(os.environ, GUESTBOOK_PATH=missing, KV_PATH=os.path.join(self.tmp.name, "absent", "kv.log"))
        result = subprocess.run([sys.executable, "smoke_test.py"], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(os.path.exists(os.path.dirname(missing)))


class GuestbookDocsTest(unittest.TestCase):  # C17
    def test_readme(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in ("## Guestbook (`/guestbook`)", "GUESTBOOK_PATH", "./guestbook.jsonl", "200 characters",
                       "latest 20", "remove its line", "restart", "HOST=0.0.0.0"):
            self.assertIn(needle, readme)

    def test_docstring(self):
        for needle in ("/guestbook", "GUESTBOOK_PATH", "./guestbook.jsonl"):
            self.assertIn(needle, serve.__doc__)

    def test_gitignore(self):
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("guestbook.jsonl", fh.read().split())


if __name__ == "__main__":
    unittest.main()
