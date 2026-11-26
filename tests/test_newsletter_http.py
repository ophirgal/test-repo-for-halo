"""SCRUM-103 — the newsletter journey: pages, /newsletter routes in serve.py, footer link."""

import http.client
import json
import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

import newsletter
import serve
from newsletter import pages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'; "
       "base-uri 'none'; frame-ancestors 'none'")
PAGES = ("/newsletter", "/newsletter/signup", "/newsletter/thanks")
LOOK_ALIKES = ("/newsletter/", "/newsletter/export.csv", "/newsletter/thanks/", "/newsletters",
               "/Newsletter", "/newsletter/signup/", "/newsletter.html", "/newsletter/list", "/newsletter/form.js/")
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'


def text(body):
    return body.decode("utf-8") if isinstance(body, bytes) else body


def input_tag(page, field):
    return re.search(rf'<input [^>]*id="{field}"[^>]*>', text(page)).group(0)


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class PagesTest(unittest.TestCase):
    def test_welcome(self):
        page = text(newsletter.render_welcome())
        self.assertIn("<h1>Get our newsletter</h1>", page)
        self.assertIn("<p>News and updates from the site, sent to your inbox.</p>", page)
        self.assertIn('<a class="btn btn-block" href="/newsletter/signup">Subscribe</a>', page)
        self.assertIn('<a class="link-back" href="/">← Back to site</a>', page)
        self.assertIn('aria-label="Progress, step 1 of 3"', page)
        # focus order: Back to site, then Subscribe
        self.assertLess(page.index("← Back to site"), page.index(">Subscribe</a>"))

    def test_form_default(self):
        page = text(newsletter.render_form())
        self.assertIn("<h1>Subscribe to the newsletter</h1>", page)
        self.assertIn('aria-label="Progress, step 2 of 3"', page)
        self.assertIn('<a class="link-back" href="/newsletter">← Back</a>', page)
        self.assertIn('<form id="signup" action="/newsletter/signup" method="post" novalidate>', page)
        self.assertIn('<label for="name">Name</label>', page)
        self.assertIn('<label for="email">Email address</label>', page)
        name, email = input_tag(page, "name"), input_tag(page, "email")
        self.assertIn('maxlength="80"', name)
        self.assertIn('type="email"', email)
        for tag in (name, email):
            self.assertNotIn("aria-invalid", tag)
            self.assertNotIn("autofocus", tag)
        self.assertIn('<div class="hint" id="name-hint">Up to 80 characters.</div>', page)
        self.assertIn('<div class="hint" id="email-hint">For example, name@example.com. We only use it to send the '
                      "newsletter.</div>", page)
        self.assertIn('<button class="btn btn-block" type="submit"><span class="btn-label">Submit</span>', page)
        self.assertIn('<script src="/newsletter/form.js" defer></script>', page)
        self.assertNotIn("role=\"alert\"", page)
        # focus order: Back, Name, Email, Submit
        order = [page.index(s) for s in ("← Back", 'id="name"', 'id="email"', 'type="submit"')]
        self.assertEqual(order, sorted(order))

    def test_each_error_state(self):
        cases = {
            "name_empty": ({"name": newsletter.NAME_EMPTY}, "name", "Enter your name."),
            "name_too_long": ({"name": newsletter.NAME_TOO_LONG}, "name", "Enter a name of 80 characters or fewer."),
            "email_empty": ({"email": newsletter.EMAIL_EMPTY}, "email", "Enter your email address."),
            "email_malformed": ({"email": newsletter.EMAIL_MALFORMED}, "email",
                                "Enter an email address in the format name@example.com."),
        }
        for label, (errors, field, message) in cases.items():
            with self.subTest(label):
                page = text(newsletter.render_form({"name": "Maya", "email": "x"}, errors))
                tag = input_tag(page, field)
                self.assertIn('aria-invalid="true"', tag)
                self.assertIn(f'aria-describedby="{field}-error {field}-hint"', tag)
                self.assertIn("autofocus", tag)
                self.assertIn(f'<div class="error-msg" id="{field}-error">', page)
                self.assertIn(f'<span class="sr-only">Error: </span>{message}</span>', page)
                self.assertIn('class="field has-error"', page)

    def test_both_errors_autofocus_first_only(self):
        page = text(newsletter.render_form({"name": "", "email": "maya.levi@example"},
                                           {"name": newsletter.NAME_EMPTY, "email": newsletter.EMAIL_MALFORMED}))
        name, email = input_tag(page, "name"), input_tag(page, "email")
        self.assertIn('aria-invalid="true"', name)
        self.assertIn('aria-invalid="true"', email)
        self.assertIn("autofocus", name)
        self.assertNotIn("autofocus", email)
        self.assertEqual(page.count("autofocus"), 1)
        self.assertIn('value="maya.levi@example"', email)

    def test_values_escaped(self):
        xss = '"><script>alert(1)</script>'
        page = text(newsletter.render_form({"name": xss, "email": xss}, {"email": newsletter.EMAIL_MALFORMED}))
        self.assertNotIn("<script>alert", page)
        self.assertIn('value="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"', input_tag(page, "name"))

    def test_submission_failed(self):
        page = text(newsletter.render_form({"name": "Maya Levi", "email": "maya@example.com"}, failed=True))
        self.assertIn('<div class="alert" role="alert">', page)
        self.assertIn("<strong>Your signup didn’t go through</strong>", page)
        self.assertIn("We couldn’t reach the server.", page)
        self.assertIn('value="Maya Levi"', input_tag(page, "name"))
        self.assertIn('value="maya@example.com"', input_tag(page, "email"))

    def test_thanks_fixed_no_input(self):
        page = text(newsletter.render_thanks())
        self.assertEqual(newsletter.render_thanks(), newsletter.render_thanks())
        self.assertIn("<h1>You’re subscribed</h1>", page)
        self.assertIn('aria-label="Progress, step 3 of 3"', page)
        self.assertIn('<a class="btn btn-block" href="/">Back to site</a>', page)
        self.assertNotIn("<input", page)
        self.assertNotIn("<form", page)

    def test_every_page_responsive(self):
        for render in (newsletter.render_welcome, newsletter.render_form, newsletter.render_thanks):
            with self.subTest(render.__name__):
                page = text(render())
                self.assertIn(VIEWPORT, page)
                self.assertIn('<html lang="en">', page)
                for prop, value in re.findall(r"(?<![\w-])((?:min-|max-)?width):\s*(\d+)px", page):
                    self.assertLessEqual(int(value), 320, prop)
                self.assertIn("@media (max-width:40rem)", page)
                self.assertIn(".split{grid-template-columns:minmax(0,1fr)", page)
                self.assertNotRegex(page, r"<script>|\son\w+=")  # no inline script or handlers

    def test_contrast_meets_wcag_aa(self):
        t = pages.TOKENS
        text_pairs = [
            (t["text"], t["bg"]), (t["text"], t["surface"]), (t["text"], t["accent-bg"]),
            (t["muted"], t["surface"]), (t["muted"], t["accent-bg"]), (t["muted"], t["bg"]),
            (t["primary"], t["surface"]), (t["primary"], t["accent-bg"]),
            ("#ffffff", t["primary"]), ("#ffffff", t["primary-dark"]), ("#ffffff", t["disabled"]),
            (t["error"], t["surface"]), (t["error"], t["error-bg"]),
        ]
        for fg, bg in text_pairs:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast(fg, bg), 4.5)
        for bg in (t["bg"], t["surface"], t["accent-bg"]):
            with self.subTest(focus=bg):
                self.assertGreaterEqual(contrast(t["focus"], bg), 3.0)
        self.assertGreaterEqual(contrast(t["border"], t["surface"]), 3.0)  # input borders sit on the surface
        self.assertIn("outline:3px solid var(--c-focus)", pages.STYLE)

    def test_form_js(self):
        js = newsletter.FORM_JS.decode("utf-8")
        self.assertIn('getElementById("signup")', js)
        self.assertIn("button.disabled = on", js)
        self.assertIn("readOnly = on", js)
        self.assertIn('aria-busy', js)
        self.assertNotRegex(js, r"\beval\(|innerHTML|document\.write|new Function")
        page = text(newsletter.render_form())
        self.assertIn('<span class="btn-busy" hidden>', page)
        self.assertIn("Submitting…</span>", page)
        self.assertIn('id="signup-status"', page)


class QuietHandler(serve.RootOnlyHandler):
    def log_message(self, fmt, *args):
        pass


class NewsletterHTTPTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.nl_path = os.path.join(self.tmp.name, "newsletter.jsonl")
        self.use_env(KV_PATH=os.path.join(self.tmp.name, "kv.log"),
                     GUESTBOOK_PATH=os.path.join(self.tmp.name, "guestbook.jsonl"),
                     NEWSLETTER_PATH=self.nl_path)
        self.start()

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
        self.server = server

    def request(self, method, path, body=None, headers=None, port=None):
        conn = http.client.HTTPConnection("127.0.0.1", port or self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, resp.headers, resp.read()
        finally:
            conn.close()

    def post(self, name="Maya Levi", email="maya@example.com", raw=None, headers=FORM, path="/newsletter/signup"):
        body = raw if raw is not None else urllib.parse.urlencode({"name": name, "email": email})
        return self.request("POST", path, body=body, headers=headers)

    def records(self):
        if not os.path.exists(self.nl_path):
            return []
        with open(self.nl_path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh.read().splitlines()]

    def raw_send(self, data):
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
            sock.sendall(data)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks)


class RoutesTest(NewsletterHTTPTestCase):
    def test_get_and_head_pages(self):
        expected = {"/newsletter": newsletter.render_welcome(), "/newsletter/signup": newsletter.render_form(),
                    "/newsletter/thanks": newsletter.render_thanks()}
        for path, body in expected.items():
            with self.subTest(path=path):
                status, headers, got = self.request("GET", path)
                self.assertEqual((status, got), (200, body))
                self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(headers["Content-Security-Policy"], CSP)
                self.assertEqual(headers["Content-Length"], str(len(body)))
                h_status, h_headers, h_body = self.request("HEAD", path)
                self.assertEqual((h_status, h_body), (200, b""))
                self.assertEqual(h_headers["Content-Length"], str(len(body)))
                self.assertEqual(self.request("GET", path + "?utm=x&a=1")[2], body)  # query ignored

    def test_form_js(self):
        status, headers, body = self.request("GET", "/newsletter/form.js?v=1")
        self.assertEqual((status, body), (200, newsletter.FORM_JS))
        self.assertEqual(headers["Content-Type"], "text/javascript; charset=utf-8")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.request("HEAD", "/newsletter/form.js")[:3:2], (200, b""))

    def test_look_alikes_404(self):
        for path in LOOK_ALIKES:
            for method in ("GET", "HEAD"):
                with self.subTest(method=method, path=path):
                    self.assertEqual(self.request(method, path)[0], 404)

    def test_valid_signup_stored_and_redirected(self):  # scenario 1
        status, headers, body = self.post(" Maya\nLevi ", " Maya@Example.com ")
        self.assertEqual((status, headers["Location"], body), (303, "/newsletter/thanks", b""))
        [record] = self.records()
        self.assertEqual((record["n"], record["e"]), ("Maya Levi", "Maya@Example.com"))
        self.assertRegex(record["t"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(self.request("GET", headers["Location"])[2], newsletter.render_thanks())

    def test_repeated_address_same_answer_no_record(self):  # scenario 2
        first = self.post("Maya", "maya@example.com")
        for name, email in (("Other", "MAYA@example.com"), ("Maya", "  maya@example.com  ")):
            with self.subTest(email=email):
                again = self.post(name, email)
                self.assertEqual((again[0], again[1]["Location"], again[2]), (first[0], first[1]["Location"], first[2]))
                self.assertEqual(sorted(k for k in again[1].keys() if k != "Date"),
                                 sorted(k for k in first[1].keys() if k != "Date"))
        self.assertEqual([r["n"] for r in self.records()], ["Maya"])
        self.assertEqual(self.request("GET", "/newsletter/thanks")[2], newsletter.render_thanks())

    def test_invalid_input_400_nothing_stored(self):  # scenario 6
        cases = (
            ("", "maya@example.com", {"name": "Enter your name."}),
            ("Maya", "", {"email": "Enter your email address."}),
            ("Maya", "maya.levi@example", {"email": "Enter an email address in the format name@example.com."}),
            ("", "a@@b.co", {"name": "Enter your name.",
                             "email": "Enter an email address in the format name@example.com."}),
            ("", "", {"name": "Enter your name.", "email": "Enter your email address."}),
            ("ש" * 81, "a@b.co", {"name": "Enter a name of 80 characters or fewer."}),
        )
        for name, email, errors in cases:
            with self.subTest(name=name, email=email):
                status, headers, body = self.post(name, email)
                page = text(body)
                self.assertEqual(status, 400)
                self.assertEqual(headers["Content-Security-Policy"], CSP)
                for field, message in errors.items():
                    self.assertIn('aria-invalid="true"', input_tag(page, field))
                    self.assertIn(message, page)
                first = "name" if "name" in errors else "email"
                self.assertIn("autofocus", input_tag(page, first))
                self.assertEqual(page.count("autofocus"), 1)
                self.assertIn(f'value="{email}"', input_tag(page, "email"))
        self.assertEqual(self.records(), [])
        self.assertFalse(os.path.exists(self.nl_path))

    def test_invalid_values_kept_escaped(self):
        status, _, body = self.post('<script>"x"', "<b>@x")
        page = text(body)
        self.assertEqual(status, 400)
        self.assertNotIn("<script>", page.split("</head>")[1])
        self.assertIn('value="&lt;script&gt;&quot;x&quot;"', input_tag(page, "name"))
        self.assertIn('value="&lt;b&gt;@x"', input_tag(page, "email"))

    def test_missing_fields_are_empty(self):
        status, _, body = self.post(raw="other=1")
        self.assertEqual(status, 400)
        self.assertIn("Enter your name.", text(body))
        self.assertIn("Enter your email address.", text(body))

    def test_store_failure_500_failed_state(self):
        self.use_env(NEWSLETTER_PATH=os.path.join(self.tmp.name, "absent", "newsletter.jsonl"))
        logged = []
        patcher = mock.patch.object(QuietHandler, "log_message", lambda _self, fmt, *args: logged.append(fmt % args))
        patcher.start()
        self.addCleanup(patcher.stop)
        server = serve.make_server("127.0.0.1", 0, QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            body = urllib.parse.urlencode({"name": "Maya Levi", "email": "maya@example.com"})
            status, headers, page = self.request("POST", "/newsletter/signup", body=body, headers=FORM, port=port)
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
        page = text(page)
        self.assertEqual(status, 500)
        self.assertNotIn("Location", headers)
        self.assertIn("Your signup didn’t go through", page)
        self.assertIn('value="Maya Levi"', input_tag(page, "name"))
        self.assertIn('value="maya@example.com"', input_tag(page, "email"))
        self.assertNotIn("You’re subscribed", page)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "absent")))
        errors = [line for line in logged if line.startswith("newsletter store unavailable:")]
        self.assertEqual(len(errors), 1, logged)
        self.assertIn("No such file or directory", errors[0])
        self.assertNotIn("maya@example.com", errors[0])

    def test_post_body_errors(self):
        self.assertEqual(self.post(headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.post(headers={"Content-Type": "multipart/form-data; boundary=x"})[0], 415)
        self.assertEqual(self.post(raw=b"name=%FF&email=a%40b.co")[0], 400)
        self.assertEqual(self.post(headers={"Content-Type": FORM["Content-Type"] + "; charset=UTF-8"})[0], 303)
        self.assertEqual(len(self.records()), 1)
        for header in (b"", b"Content-Length: abc\r\n", b"Content-Length: 3\r\nContent-Length: 4\r\n"):
            with self.subTest(header=header):
                reply = self.raw_send(b"POST /newsletter/signup HTTP/1.1\r\nHost: x\r\n"
                                      b"Content-Type: application/x-www-form-urlencoded\r\n" + header
                                      + b"\r\nname=x&email=y%40z.co")
                self.assertTrue(reply.startswith(b"HTTP/1.0 400"), reply[:40])
        reply = self.raw_send(b"POST /newsletter/signup HTTP/1.1\r\nHost: x\r\n"
                              b"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: 65537\r\n\r\n")
        self.assertTrue(reply.startswith(b"HTTP/1.0 413"), reply[:40])
        self.assertEqual(len(self.records()), 1)

    def test_no_route_returns_signups(self):  # scenario 7
        name, email = "Zelda Unique-Name-7731", "zelda.unique7731@example.com"
        self.assertEqual(self.post(name, email)[0], 303)
        self.assertEqual(len(self.records()), 1)
        paths = PAGES + LOOK_ALIKES + ("/newsletter/form.js", "/", "/jungle", "/healthz", "/guestbook", "/kv/",
                                       "/newsletter?export=1", "/newsletter/signup?email=" + email)
        for path in paths:
            for method in ("GET", "HEAD", "POST", "PUT", "DELETE"):
                with self.subTest(method=method, path=path):
                    _, headers, body = self.request(method, path, body=b"" if method != "GET" else None,
                                                    headers=FORM if method == "POST" else None)
                    blob = body + str(headers).encode("utf-8")
                    self.assertNotIn(email.encode(), blob.lower())
                    self.assertNotIn(name.encode(), blob)


class RegressionTest(NewsletterHTTPTestCase):  # scenario 4
    def standard_501(self, method, path):
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
        cases = [(m, p) for m in ("PUT", "DELETE") for p in PAGES + ("/newsletter/form.js",)]
        cases += [("POST", p) for p in ("/newsletter", "/newsletter/thanks", "/newsletter/", "/newsletter/form.js",
                                       "/", "/jungle", "/healthz", "/newsletters")]
        for method, path in cases:
            with self.subTest(method=method, path=path):
                status, _, body = self.request(method, path, body=b"x")
                self.assertEqual(status, 501)
                self.assertEqual((status, body), self.standard_501(method, path))
        self.assertFalse(os.path.exists(self.nl_path))

    def test_existing_routes_unchanged(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual((status, body), (200, serve.INDEX.read_bytes()))
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b'<footer class="site-footer" aria-label="Site footer">', body)
        self.assertIn(b'<a href="/newsletter">Newsletter</a>', body)
        self.assertEqual(self.request("GET", "/jungle")[2], serve.JUNGLE.read_bytes())
        self.assertNotIn(b"newsletter", serve.JUNGLE.read_bytes().lower())
        self.assertEqual(self.request("GET", "/healthz")[:3:2], (200, b'{"status": "ok"}'))
        self.assertEqual(self.request("GET", "/guestbook")[0], 200)
        self.assertEqual(self.request("POST", "/guestbook", body="message=hi", headers=FORM)[0], 303)
        self.assertEqual(self.request("GET", "/kv/")[:3:2], (200, b"[]"))
        self.assertEqual(self.request("GET", "/nope")[0], 404)

    def test_routes_table_unchanged(self):
        self.assertEqual(serve.ROUTES, {"/": serve.INDEX, "/jungle": serve.JUNGLE})


class NewsletterSignupDocsTest(unittest.TestCase):
    def test_readme(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in ("## Newsletter signup (`/newsletter`)", "/newsletter/signup", "/newsletter/thanks",
                       "NEWSLETTER_PATH", "HOST=0.0.0.0", "no route", "## Newsletter export"):
            self.assertIn(needle, readme)

    def test_docstring(self):
        for needle in ("/newsletter", "/newsletter/signup", "/newsletter/thanks", "NEWSLETTER_PATH",
                       "./newsletter.jsonl", "python3 -m newsletter export"):
            self.assertIn(needle, serve.__doc__)


if __name__ == "__main__":
    unittest.main()
