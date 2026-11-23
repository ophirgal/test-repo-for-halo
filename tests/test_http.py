"""SCRUM-119 t4 — the /kv/ routes in serve.py, end to end (AC10-AC14, AC16-AC18)."""

import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import serve
from kvstore import KVStore, encode_record

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class QuietHandler(serve.RootOnlyHandler):
    def log_message(self, fmt, *args):
        pass


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kv_path = os.path.join(self.tmp.name, "kv.log")
        patcher = mock.patch.dict(os.environ, {"KV_PATH": self.kv_path})
        patcher.start()
        self.addCleanup(patcher.stop)

    def start(self, store=None):
        server = serve.make_server("127.0.0.1", 0, QuietHandler)
        if store is not None:
            server.kv_store = store
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

        self.addCleanup(stop)
        self.port = server.server_address[1]
        self.server = server
        self._stop = stop
        return server

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, resp.headers, resp.read()
        finally:
            conn.close()

    def put(self, path, value, raw=None):
        body = raw if raw is not None else json.dumps(value).encode("utf-8")
        return self.request("PUT", path, body=body)

    def assert_json_error(self, result, status):
        code, headers, body = result
        self.assertEqual(code, status, body)
        self.assertEqual(headers["Content-Type"], "application/json")
        payload = json.loads(body)
        self.assertEqual(set(payload), {"error"})
        self.assertIsInstance(payload["error"], str)
        return payload["error"]

    def read_log(self):
        with open(self.kv_path, "rb") as fh:
            return fh.read()


class RoutesTest(ServerTestCase):
    def test_put_get_delete_list(self):  # AC10
        self.start()
        status, _, body = self.put("/kv/b", {"x": [1, "é"]})
        self.assertEqual((status, body), (204, b""))
        self.assertEqual(self.put("/kv/a", 1)[0], 204)
        status, headers, body = self.request("GET", "/kv/b")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(body), {"x": [1, "é"]})
        status, headers, body = self.request("GET", "/kv/?anything=1")
        self.assertEqual((status, json.loads(body)), (200, ["a", "b"]))
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(self.request("DELETE", "/kv/b")[0], 204)
        self.assert_json_error(self.request("DELETE", "/kv/b"), 404)
        self.assert_json_error(self.request("GET", "/kv/b"), 404)
        self.assertEqual(json.loads(self.request("GET", "/kv/")[2]), ["a"])

    def test_head_mirrors_get(self):
        self.start()
        self.put("/kv/a", "hello")
        for path, status in (("/kv/a", 200), ("/kv/", 200), ("/kv/missing", 404), ("/kv/", 200)):
            with self.subTest(path=path):
                g_status, g_headers, g_body = self.request("GET", path)
                h_status, h_headers, h_body = self.request("HEAD", path)
                self.assertEqual((g_status, h_status), (status, status))
                self.assertEqual(h_body, b"")
                self.assertEqual(h_headers["Content-Type"], g_headers["Content-Type"])
                self.assertEqual(h_headers["Content-Length"], str(len(g_body)))

    def test_keys_with_slash_space_and_unicode(self):  # AC16
        self.start()
        self.assertEqual(self.put("/kv/app/config", 1)[0], 204)
        self.assertEqual(json.loads(self.request("GET", "/kv/app%2Fconfig")[2]), 1)
        self.assertEqual(self.put("/kv/my%20key", "spaced")[0], 204)
        self.assertEqual(self.put("/kv/%D7%A9%D7%9C%D7%95%D7%9D", "uni")[0], 204)
        self.assertEqual(json.loads(self.request("GET", "/kv/my%20key")[2]), "spaced")
        self.assertEqual(
            json.loads(self.request("GET", "/kv/")[2]), sorted(["app/config", "my key", "שלום"])
        )
        self._stop()
        with KVStore(self.kv_path) as store:
            self.assertEqual(store.get("my key"), "spaced")
            self.assertEqual(store.get("שלום"), "uni")
            self.assertEqual(store.get("app/config"), 1)

    def test_ttl_expiry(self):
        clock = FakeClock(1000.0)
        self.start(store=KVStore(self.kv_path, clock=clock))
        self.assertEqual(self.put("/kv/t?ttl=10", "temp")[0], 204)
        self.assertEqual(self.put("/kv/f?ttl=0.5&other=x", "frac")[0], 204)
        clock.now = 1009.9
        self.assertEqual(json.loads(self.request("GET", "/kv/t")[2]), "temp")
        clock.now = 1010
        self.assert_json_error(self.request("GET", "/kv/t"), 404)
        self.assertEqual(json.loads(self.request("GET", "/kv/")[2]), [])

    def test_restart_keeps_data(self):
        self.start()
        self.put("/kv/persist", {"n": 1})
        self._stop()
        self.start()
        self.assertEqual(json.loads(self.request("GET", "/kv/persist")[2]), {"n": 1})

    def test_one_store_shared_by_all_requests(self):
        server = self.start()
        errors = []

        def worker(n):
            try:
                for i in range(25):
                    status = self.put(f"/kv/w{n}-{i}", i)[0]
                    if status != 204:
                        errors.append(status)
            except Exception as err:
                errors.append(err)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(json.loads(self.request("GET", "/kv/")[2])), 100)
        self.assertIsInstance(server.kv_store, KVStore)

    def test_body_of_exactly_64_kib_is_accepted(self):  # AC11
        self.start()
        body = b'"' + b"x" * 65534 + b'"'
        self.assertEqual(len(body), 65536)
        self.assertEqual(self.put("/kv/big", None, raw=body)[0], 204)
        self.assertEqual(len(self.request("GET", "/kv/big")[2]), 65536)


class ErrorsTest(ServerTestCase):
    def test_invalid_bodies_are_400(self):  # AC11, AC17
        self.start()
        cases = {
            "not json": b"{not json",
            "empty": b"",
            "invalid utf-8": b'"\xff"',
            "bom": b'\xef\xbb\xbf"x"',
            "NaN": b"NaN",
            "Infinity": b"[Infinity]",
            "-Infinity": b"-Infinity",
            "1e400": b"1e400",
            "huge int": b"9" * 5000,
            "lone surrogate": b'"\\ud800"',
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                self.assert_json_error(self.put("/kv/k", None, raw=body), 400)
        self.assertEqual(self.read_log(), b"")

    def test_invalid_keys_are_400(self):  # AC11, AC16
        self.start()
        for path in ("/kv/" + "x" * 129, "/kv/a%00b", "/kv/tab%09", "/kv/%FF", "/kv/%E2%80%8B"):
            for method in ("GET", "PUT", "DELETE"):
                with self.subTest(path=path, method=method):
                    body = b"1" if method == "PUT" else None
                    message = self.assert_json_error(self.request(method, path, body=body), 400)
                    self.assertIn("key", message)
        for method in ("PUT", "DELETE"):
            with self.subTest(method=method, path="/kv/"):
                body = b"1" if method == "PUT" else None
                self.assert_json_error(self.request(method, "/kv/", body=body), 400)
        self.assertEqual(self.put("/kv/" + "x" * 128, 1)[0], 204)

    def test_invalid_ttl_is_400(self):  # AC17
        self.start()
        for query in ("ttl=0", "ttl=-1", "ttl=", "ttl=1&ttl=2", "ttl=abc", "ttl=nan", "ttl=inf", "ttl=-inf"):
            with self.subTest(query=query):
                message = self.assert_json_error(self.put(f"/kv/k?{query}", 1), 400)
                self.assertIn("ttl", message)
        self.assertEqual(self.read_log(), b"")

    def test_store_rejected_value_is_400(self):  # AC17
        self.start()
        # A 64,999-byte body whose value serializes to far more than 64 KiB:
        # each "1e15" is stored as 1000000000000000.0.
        body = ("[" + ",".join(["1e15"] * 13000) + "]").encode()
        self.assertLessEqual(len(body), 65536)
        message = self.assert_json_error(self.put("/kv/k", None, raw=body), 400)
        self.assertIn("value size", message)
        self.assertEqual(self.read_log(), b"")

    def test_missing_or_invalid_content_length_is_400(self):  # AC17
        self.start()
        for headers in ({}, {"Content-Length": "abc"}, {"Content-Length": "-1"}, {"Content-Length": "1.5"}):
            with self.subTest(headers=headers):
                with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
                    head = "PUT /kv/k HTTP/1.1\r\nHost: x\r\n"
                    head += "".join(f"{k}: {v}\r\n" for k, v in headers.items())
                    sock.sendall(head.encode() + b"\r\n")
                    response = self.read_all(sock)
                self.assertTrue(response.startswith(b"HTTP/1.0 400"), response[:60])
                self.assertIn(b"application/json", response)
                self.assertIn(b'"error"', response)

    @staticmethod
    def read_all(sock):
        chunks = []
        while True:
            try:
                chunk = sock.recv(65536)
            except ConnectionResetError:
                break
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)

    def test_oversized_body_is_413_without_reading(self):  # AC11
        self.start()
        for _ in range(20):
            with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
                sock.sendall(b"PUT /kv/k HTTP/1.1\r\nHost: x\r\nContent-Length: 100000\r\n\r\n\"small\"")
                started = time.monotonic()
                response = self.read_all(sock)  # times out (fails) if the server waits for the body
                self.assertLess(time.monotonic() - started, 5)
            self.assertTrue(response.startswith(b"HTTP/1.0 413"), response[:60])
            self.assertIn(b"Connection: close", response)
            payload = json.loads(response.split(b"\r\n\r\n", 1)[1])
            self.assertIn("65536", payload["error"])
        self.assertEqual(self.request("GET", "/kv/")[2], b"[]")
        status, _, _ = self.request("PUT", "/kv/k", body=b"1" * 65537)
        self.assertEqual(status, 413)


class CorruptLogTest(ServerTestCase):
    def test_corrupt_log_gives_503_and_pages_still_work(self):  # AC14
        data = encode_record("set", "a", 1) + b"garbage\n" + encode_record("set", "b", 2)
        with open(self.kv_path, "wb") as fh:
            fh.write(data)
        self.start()
        for method, path, body in (
            ("GET", "/kv/", None), ("GET", "/kv/a", None), ("HEAD", "/kv/a", None),
            ("PUT", "/kv/a", b"1"), ("DELETE", "/kv/a", None), ("GET", "/kv/%FF", None),
        ):
            with self.subTest(method=method, path=path):
                status, headers, raw = self.request(method, path, body=body)
                self.assertEqual(status, 503)
                self.assertEqual(headers["Content-Type"], "application/json")
                if method != "HEAD":
                    self.assertIn("line 2", json.loads(raw)["error"])
        for path in ("/", "/jungle"):
            self.assertEqual(self.request("GET", path)[0], 200)
        self.assertEqual(self.read_log(), data)


class RegressionTest(ServerTestCase):
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
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
            conn.request(method, path, body=b"x")
            resp = conn.getresponse()
            result = resp.status, resp.read()
            conn.close()
            return result
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

    def test_non_kv_paths_unchanged(self):  # AC12
        self.start()
        self.assertEqual(self.request("GET", "/")[2], serve.INDEX.read_bytes())
        self.assertEqual(self.request("GET", "/jungle")[2], serve.JUNGLE.read_bytes())
        for path in ("/kv", "/kv?x=1", "/foo/bar", "/jungle/", "/README.md", "/kvx/a", "/KV/a"):
            for method in ("GET", "HEAD"):
                with self.subTest(path=path, method=method):
                    status, headers, _ = self.request(method, path)
                    self.assertEqual(status, 404)
                    self.assertTrue(headers["Content-Type"].startswith("text/html"))
        for method, path in (("PUT", "/"), ("DELETE", "/foo"), ("PUT", "/kv"), ("POST", "/kv/x"), ("POST", "/")):
            with self.subTest(method=method, path=path):
                status, _, body = self.request(method, path, body=b"x")
                self.assertEqual((status, body), self.standard_501(method, path))
                self.assertEqual(status, 501)
        self.assertFalse(os.path.exists(self.kv_path))  # no /kv/ request, no store file

    def test_routes_table_unchanged(self):
        self.assertEqual(serve.ROUTES, {"/": serve.INDEX, "/jungle": serve.JUNGLE})

    def test_smoke_test_passes_and_creates_no_store(self):
        missing = os.path.join(self.tmp.name, "absent", "kv.log")
        env = dict(os.environ, KV_PATH=missing)
        result = subprocess.run(
            [sys.executable, "smoke_test.py"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK:", result.stdout)
        self.assertFalse(os.path.exists(missing))

    def test_main_warns_about_torn_tail_on_startup(self):
        good = encode_record("set", "a", 1)
        with open(self.kv_path, "wb") as fh:
            fh.write(good + b'{"op":"se')
        proc = subprocess.Popen(
            [sys.executable, "serve.py", "0"], cwd=ROOT, env=dict(os.environ, KV_PATH=self.kv_path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            first = proc.stdout.readline()
            self.assertIn("serving Hello World", first)
        finally:
            proc.terminate()
            _, err = proc.communicate(timeout=10)
        self.assertIn("TornTailWarning", err)
        self.assertIn(f"byte offset {len(good)}", err)
        self.assertEqual(self.read_log(), good)

    def test_main_starts_on_corrupt_log(self):
        data = encode_record("set", "a", 1) + b"bad\n" + encode_record("set", "b", 1)
        with open(self.kv_path, "wb") as fh:
            fh.write(data)
        proc = subprocess.Popen(
            [sys.executable, "serve.py", "0"], cwd=ROOT, env=dict(os.environ, KV_PATH=self.kv_path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            first = proc.stdout.readline()
            self.assertIn("serving Hello World", first)
            self.port = int(first.split(":")[2].split("/")[0])
            self.assertEqual(self.request("GET", "/")[0], 200)
            self.assertEqual(self.request("GET", "/kv/a")[0], 503)
        finally:
            proc.terminate()
            _, err = proc.communicate(timeout=10)
        self.assertIn("line 2", err)
        self.assertEqual(self.read_log(), data)

    def test_docstring_documents_kv(self):
        doc = serve.__doc__
        for needle in ("/kv/", "KV_PATH", "./kv.log", "python3 serve.py", "PORT=", "HOST="):
            self.assertIn(needle, doc)


class DocsTest(unittest.TestCase):
    def test_readme_documents_store(self):  # AC13, AC18
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in (
            "## Hello World script", "KV_PATH", "./kv.log", "curl", "/kv/", "?ttl=", "-X PUT", "-X DELETE",
            "/kv/app/config", "%20", "400", "404", "413", "503", "HOST=0.0.0.0",
        ):
            self.assertIn(needle, readme)

    def test_gitignore_lists_store_file(self):  # AC18
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("kv.log", fh.read().split())


if __name__ == "__main__":
    unittest.main()
