"""SCRUM-103 — the newsletter CSV export command (``python3 -m newsletter export``)."""

import csv
import datetime
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import newsletter
from newsletter import export as nl_export

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTC = datetime.timezone.utc
HEADER = ["name", "email", "signed_up_at"]


def at(minute):
    return datetime.datetime(2026, 11, 26, 9, minute, 0, tzinfo=UTC)


class ExportTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "newsletter.jsonl")
        self.store = newsletter.SignupStore(self.path)

    def run_export(self, *args, path=None):
        env = dict(os.environ, NEWSLETTER_PATH=path or self.path)
        return subprocess.run([sys.executable, "-m", "newsletter", *args], cwd=ROOT, env=env,
                              capture_output=True, timeout=60)

    def rows(self, data):
        return list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))


class ExportCommandTest(ExportTestCase):
    def test_three_signups_three_rows_oldest_first(self):  # scenario 3
        self.store.add("Maya Levi", "maya@example.com", now=at(1))
        self.store.add("Dan", "Dan@Example.com", now=at(2))
        self.store.add("Noa", "noa@example.org", now=at(3))
        result = self.run_export("export")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(self.rows(result.stdout), [
            HEADER,
            ["Maya Levi", "maya@example.com", "2026-11-26T09:01:00Z"],
            ["Dan", "Dan@Example.com", "2026-11-26T09:02:00Z"],
            ["Noa", "noa@example.org", "2026-11-26T09:03:00Z"],
        ])
        self.assertTrue(result.stdout.endswith(b"\r\n"))

    def test_empty_or_missing_store_header_only(self):
        missing = os.path.join(self.tmp.name, "absent", "newsletter.jsonl")
        open(self.path, "w").close()
        for path in (self.path, missing):
            with self.subTest(path=path):
                result = self.run_export("export", path=path)
                self.assertEqual((result.returncode, result.stdout), (0, b"name,email,signed_up_at\r\n"))
        self.assertFalse(os.path.exists(os.path.dirname(missing)))

    def test_commas_quotes_non_ascii_round_trip(self):
        names = ['Levi, Maya', 'Maya "the reader" Levi', "מאיה לוי", "Zoë Ñúñez 日本"]
        for i, name in enumerate(names):
            self.store.add(name, f"p{i}@example.com", now=at(i))
        result = self.run_export("export")
        self.assertEqual([r[0] for r in self.rows(result.stdout)[1:]], names)

    def test_formula_guard(self):
        for i, start in enumerate(("=", "+", "-", "@", "\t", "\r")):
            self.store.add(f"{start}cmd{i}", f"p{i}@example.com", now=at(i))
        self.store.add("Plain", "+tag@example.com", now=at(9))
        rows = self.rows(self.run_export("export").stdout)[1:]
        self.assertEqual([r[0] for r in rows[:4]], ["'=cmd0", "'+cmd1", "'-cmd2", "'@cmd3"])
        self.assertEqual(rows[-1], ["Plain", "'+tag@example.com", "2026-11-26T09:09:00Z"])
        # tab and CR are line breaks / spaces trimmed by the name rule, so test the guard directly
        self.assertEqual(nl_export.guard("\tx"), "'\tx")
        self.assertEqual(nl_export.guard("\rx"), "'\rx")
        self.assertEqual(nl_export.guard("x=1"), "x=1")

    def test_output_file_utf8_no_bom(self):
        self.store.add("מאיה", "maya@example.com", now=at(1))
        stdout = self.run_export("export").stdout
        target = os.path.join(self.tmp.name, "subscribers.csv")
        with open(target, "w") as fh:
            fh.write("old content that is longer than the export " * 10)
        result = self.run_export("export", "-o", target)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))
        with open(target, "rb") as fh:
            data = fh.read()
        self.assertEqual(data, stdout)
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["newsletter.jsonl", "subscribers.csv"])

    def test_unwritable_output_exits_1_no_file(self):
        self.store.add("Maya", "maya@example.com")
        target = os.path.join(self.tmp.name, "absent", "subscribers.csv")
        result = self.run_export("export", "-o", target)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stderr.decode().strip().splitlines()), 1)
        self.assertFalse(os.path.exists(os.path.dirname(target)))

    def test_output_to_directory_leaves_no_partial_file(self):
        self.store.add("Maya", "maya@example.com")
        target = os.path.join(self.tmp.name, "a-dir")
        os.mkdir(target)
        result = self.run_export("export", "-o", target)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["a-dir", "newsletter.jsonl"])
        self.assertEqual(os.listdir(target), [])

    def test_unreadable_store_exits_1(self):
        target = os.path.join(self.tmp.name, "out.csv")
        result = self.run_export("export", "-o", target, path=self.tmp.name)  # a directory
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stderr.decode().strip().splitlines()), 1)
        self.assertFalse(os.path.exists(target))

    def test_usage_errors_exit_2(self):
        for args in (("import",), (), ("export", "--nope")):
            with self.subTest(args=args):
                self.assertEqual(self.run_export(*args).returncode, 2)

    def test_default_path(self):
        with mock.patch.dict(os.environ, {"NEWSLETTER_PATH": ""}):
            self.assertEqual(nl_export.store_path(), "./newsletter.jsonl")


class NewsletterExportDocsTest(unittest.TestCase):
    def test_readme(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in ("## Newsletter export", "python3 -m newsletter export", "-o", "NEWSLETTER_PATH",
                       "./newsletter.jsonl", "name,email,signed_up_at", "formula", "one server process",
                       "personal data"):
            self.assertIn(needle.lower(), readme.lower())

    def test_gitignore(self):
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("newsletter.jsonl", fh.read().split())


if __name__ == "__main__":
    unittest.main()
