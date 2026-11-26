"""SCRUM-103 — newsletter signup rules and the durable signup store."""

import contextlib
import datetime
import io
import json
import os
import tempfile
import threading
import unittest

import newsletter
from newsletter import store as nl_store

UTC = datetime.timezone.utc


def at(minute):
    return datetime.datetime(2026, 11, 26, 9, minute, 7, 123456, tzinfo=UTC)


class SignupRulesTest(unittest.TestCase):
    def errors(self, name, email):
        return newsletter.check(name, email)[2]

    def test_name_line_breaks_become_spaces_and_trimmed(self):
        for sep in ("\n", "\r\n", "\r", " ", "\x85"):
            with self.subTest(sep=sep):
                self.assertEqual(newsletter.check(" Maya" + sep + "Levi ", "a@b.co")[0], "Maya Levi")

    def test_name_empty(self):
        for raw in ("", "   ", "\n\r\n"):
            with self.subTest(raw=raw):
                self.assertEqual(self.errors(raw, "a@b.co"), {"name": newsletter.NAME_EMPTY})

    def test_name_length_in_code_points(self):
        self.assertEqual(self.errors("ש" * 80, "a@b.co"), {})
        self.assertEqual(self.errors(" " + "a" * 80 + " ", "a@b.co"), {})
        self.assertEqual(self.errors("ש" * 81, "a@b.co"), {"name": newsletter.NAME_TOO_LONG})
        self.assertEqual(self.errors("a", "a@b.co"), {})

    def test_email_empty(self):
        for raw in ("", "   "):
            with self.subTest(raw=raw):
                self.assertEqual(self.errors("Maya", raw), {"email": newsletter.EMAIL_EMPTY})

    def test_email_malformed(self):
        for raw in ("maya.levi@example", "a@@b.co", "a b@c.de", "a@b..co", "a@.b.co", "@b.co",
                    "a@b.co.", "ab.co", "a@b@c.co", "a\t@b.co", "a@b.co x",
                    "a@" + "b" * 250 + ".co"):
            with self.subTest(raw=raw):
                self.assertEqual(self.errors("Maya", raw), {"email": newsletter.EMAIL_MALFORMED})

    def test_email_valid_trimmed_case_kept(self):
        for raw, kept in (("a@b.co", "a@b.co"), (" A@B.CO ", "A@B.CO"), ("x@y.zé", "x@y.zé"),
                          ("maya.levi@example.com", "maya.levi@example.com")):
            with self.subTest(raw=raw):
                _, email, errors = newsletter.check("Maya", raw)
                self.assertEqual((email, errors), (kept, {}))

    def test_email_254_limit(self):
        local = "a" * 64
        domain = ".".join(["b" * 60] * 3) + "." + "c" * (254 - 64 - 1 - 183 - 1 + 1)
        email = local + "@" + domain
        self.assertEqual(len(email), 254)
        self.assertEqual(self.errors("Maya", email), {})
        self.assertEqual(self.errors("Maya", email + "c"), {"email": newsletter.EMAIL_MALFORMED})

    def test_both_fields_fail_together(self):
        self.assertEqual(self.errors("", ""), {"name": newsletter.NAME_EMPTY, "email": newsletter.EMAIL_EMPTY})
        self.assertEqual(self.errors("a" * 81, "x@y"),
                         {"name": newsletter.NAME_TOO_LONG, "email": newsletter.EMAIL_MALFORMED})

    def test_address_key(self):
        self.assertEqual(newsletter.address_key(" Maya@Example.com "), "maya@example.com")
        self.assertNotEqual(newsletter.address_key("ß@x.co"), newsletter.address_key("ss@x.co"))


class SignupStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "newsletter.jsonl")

    def raw(self):
        with open(self.path, "rb") as fh:
            return fh.read()

    def lines(self):
        return self.raw().decode("utf-8").splitlines()

    def test_record_format_utc_seconds(self):
        store = newsletter.SignupStore(self.path)
        local = at(3).astimezone(datetime.timezone(datetime.timedelta(hours=2)))
        self.assertTrue(store.add(" מאיה, \"Levi\" ", " Maya@Example.com ", now=local))
        self.assertEqual(self.raw().decode("utf-8"),
                         '{"t":"2026-11-26T09:03:07Z","n":"מאיה, \\"Levi\\"","e":"Maya@Example.com"}\n')
        [record] = store.records()
        self.assertEqual(record, newsletter.Record(at(3).replace(microsecond=0), 'מאיה, "Levi"', "Maya@Example.com"))

    def test_default_time_is_now_utc(self):
        store = newsletter.SignupStore(self.path)
        before = datetime.datetime.now(UTC).replace(microsecond=0)
        store.add("Maya", "maya@example.com")
        after = datetime.datetime.now(UTC)
        when = store.records()[0].time
        self.assertTrue(before <= when <= after)
        self.assertEqual(when.tzinfo, UTC)

    def test_repeated_address_stores_nothing_and_keeps_first(self):
        store = newsletter.SignupStore(self.path)
        self.assertTrue(store.add("Maya", "maya@example.com", now=at(1)))
        before = self.raw()
        for name, email in (("Other", "Maya@Example.com"), ("Maya", "  maya@example.com  "),
                            ("X", "MAYA@EXAMPLE.COM")):
            with self.subTest(email=email):
                self.assertFalse(store.add(name, email, now=at(5)))
        self.assertEqual(self.raw(), before)
        self.assertEqual([(r.name, r.time.minute) for r in store.records()], [("Maya", 1)])

    def test_sharp_s_is_not_ss(self):
        store = newsletter.SignupStore(self.path)
        self.assertTrue(store.add("A", "ss@x.co"))
        self.assertTrue(store.add("B", "ß@x.co"))
        self.assertEqual([r.email for r in store.records()], ["ss@x.co", "ß@x.co"])

    def test_twenty_threads_same_address_one_record(self):
        store = newsletter.SignupStore(self.path)
        barrier = threading.Barrier(20)
        results = []

        def go(i):
            barrier.wait()
            results.append(store.add(f"N{i}", "Race@Example.com" if i % 2 else "race@example.com"))

        threads = [threading.Thread(target=go, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(len(self.lines()), 1)
        self.assertEqual(sorted(results), [False] * 19 + [True])

    def test_survives_restart(self):
        newsletter.SignupStore(self.path).add("Maya", "maya@example.com", now=at(1))
        fresh = newsletter.SignupStore(self.path)
        self.assertFalse(fresh.add("Maya", "MAYA@example.com"))
        self.assertTrue(fresh.add("Dan", "dan@example.com", now=at(2)))
        self.assertEqual([r.email for r in fresh.records()], ["maya@example.com", "dan@example.com"])

    def test_missing_file_and_directory_never_created_by_read(self):
        missing = os.path.join(self.tmp.name, "absent", "newsletter.jsonl")
        store = newsletter.SignupStore(missing)
        self.assertEqual(store.records(), [])
        self.assertEqual(list(nl_store.read_records(missing)), [])
        self.assertFalse(os.path.exists(os.path.dirname(missing)))

    def test_bad_lines_skipped_with_warning(self):
        good = '{"t":"2026-11-26T09:00:00Z","n":"Maya","e":"maya@example.com"}'
        bad = ["", "not json", "[1]", '{"t":"2026-11-26T09:00:00Z","n":"x"}',
               '{"t":"yesterday","n":"x","e":"y@z.co"}', '{"t":"2026-11-26T09:00:00Z","n":1,"e":"y@z.co"}']
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join([good] + bad) + '\n{"t":"2026-11-26T09:0')  # torn last line
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            records = newsletter.SignupStore(self.path).records()
        self.assertEqual([r.email for r in records], ["maya@example.com"])
        warnings = err.getvalue().splitlines()
        self.assertEqual(len(warnings), 7)
        for lineno, warning in zip(range(2, 9), warnings):
            self.assertIn(f"skipped invalid line {lineno}", warning)

    def test_newline_repaired_before_append(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"t":"2026-11-26T09:00:00Z","n":"Maya","e":"maya@example.com"}')
        store = newsletter.SignupStore(self.path)
        self.assertTrue(store.add("Dan", "dan@example.com", now=at(2)))
        self.assertEqual(len(self.lines()), 2)
        self.assertEqual([r.name for r in store.records()], ["Maya", "Dan"])

    def test_torn_line_repaired_and_address_still_new(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"t":"2026-11-26T09:00:00Z","n":"Maya","e":"maya@exa')
        with contextlib.redirect_stderr(io.StringIO()):
            store = newsletter.SignupStore(self.path)
            self.assertTrue(store.add("Maya", "maya@example.com", now=at(2)))
            self.assertEqual([r.email for r in store.records()], ["maya@example.com"])

    def test_write_failure_raises_and_remembers_nothing(self):
        missing = os.path.join(self.tmp.name, "absent", "newsletter.jsonl")
        store = newsletter.SignupStore(missing)
        with self.assertRaises(OSError):
            store.add("Maya", "maya@example.com")
        self.assertFalse(os.path.exists(os.path.dirname(missing)))
        store.path = self.path  # the address was not remembered: it is still new
        self.assertTrue(store.add("Maya", "maya@example.com"))

    def test_invalid_input_never_written(self):
        store = newsletter.SignupStore(self.path)
        for name, email in (("", "a@b.co"), ("Maya", ""), ("Maya", "maya.levi@example"), ("a" * 81, "a@b.co")):
            with self.subTest(name=name, email=email):
                with self.assertRaises(ValueError):
                    store.add(name, email)
        self.assertFalse(os.path.exists(self.path))

    def test_line_is_compact_json(self):
        store = newsletter.SignupStore(self.path)
        store.add("Maya", "maya@example.com", now=at(0))
        self.assertEqual(json.loads(self.lines()[0]), {"t": "2026-11-26T09:00:07Z", "n": "Maya", "e": "maya@example.com"})


if __name__ == "__main__":
    unittest.main()
