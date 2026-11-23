"""SCRUM-119 t1 — log format, replay and crash recovery (AC1-AC3)."""

import json
import os
import tempfile
import unittest
import warnings
import zlib

from kvstore import CorruptLogError, TornTailWarning, encode_record, replay


def raw_record(op, k, v=None, exp=None, crc=None):
    """Build a record line by hand, independently of encode_record."""
    body = {"op": op, "k": k, "v": v, "exp": exp}
    canonical = json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    record = dict(body, crc=zlib.crc32(canonical.encode("utf-8")) if crc is None else crc)
    return (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")


class LogTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "kv.log")

    def write(self, data):
        with open(self.path, "wb") as fh:
            fh.write(data)

    def read(self):
        with open(self.path, "rb") as fh:
            return fh.read()

    def replay_quietly(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = replay(self.path)
        return result, caught


class EncodeTest(LogTestCase):
    def test_record_shape_and_crc_match_independent_computation(self):
        line = encode_record("set", "a", {"x": [1, 2]}, 12.5)
        self.assertTrue(line.endswith(b"\n"))
        self.assertEqual(line.count(b"\n"), 1)
        record = json.loads(line)
        self.assertEqual(set(record), {"op", "k", "v", "exp", "crc"})
        expected = zlib.crc32(
            json.dumps(
                {"op": "set", "k": "a", "v": {"x": [1, 2]}, "exp": 12.5},
                separators=(",", ":"), sort_keys=True, ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        )
        self.assertEqual(record["crc"], expected)

    def test_del_and_untimed_set_carry_nulls(self):
        self.assertEqual(json.loads(encode_record("del", "a"))["v"], None)
        self.assertEqual(json.loads(encode_record("del", "a"))["exp"], None)
        self.assertIsNone(json.loads(encode_record("set", "a", 1))["exp"])

    def test_nan_refused(self):
        with self.assertRaises(ValueError):
            encode_record("set", "a", float("nan"))


class ReplayTest(LogTestCase):
    def test_three_sets_and_a_del_leave_two_live_keys(self):  # AC1
        self.write(
            raw_record("set", "a", 1) + raw_record("set", "b", 2)
            + raw_record("set", "a", 3) + raw_record("del", "b")
            + raw_record("set", "c", "x")
        )
        result, caught = self.replay_quietly()
        self.assertEqual(result.index, {"a": (3, None), "c": ("x", None)})
        self.assertEqual(result.records, 5)
        self.assertEqual(caught, [])

    def test_ac1_exact(self):
        self.write(raw_record("set", "a", 1) + raw_record("set", "b", 2)
                   + raw_record("set", "c", 3) + raw_record("del", "b"))
        result, _ = self.replay_quietly()
        self.assertEqual(result.index, {"a": (1, None), "c": (3, None)})

    def test_latest_record_wins_and_keeps_exp(self):
        self.write(raw_record("set", "a", 1, 50) + raw_record("set", "a", 2, 99.5))
        result, _ = self.replay_quietly()
        self.assertEqual(result.index, {"a": (2, 99.5)})

    def test_missing_file_is_created_empty(self):
        result, _ = self.replay_quietly()
        self.assertEqual(result.index, {})
        self.assertEqual(self.read(), b"")

    def test_empty_file(self):
        self.write(b"")
        result, caught = self.replay_quietly()
        self.assertEqual((result.index, result.records, result.missing_newline), ({}, 0, False))
        self.assertEqual(caught, [])

    def test_unicode_and_embedded_newlines_round_trip(self):
        value = {"text": "line1\nline2\r\nשלום", "emoji": "\U0001f600"}
        self.write(encode_record("set", "מפתח / key", value))
        result, _ = self.replay_quietly()
        self.assertEqual(result.index, {"מפתח / key": (value, None)})

    def test_valid_last_record_without_newline_is_kept(self):
        data = raw_record("set", "a", 1) + raw_record("set", "b", 2)[:-1]
        self.write(data)
        result, caught = self.replay_quietly()
        self.assertEqual(result.index, {"a": (1, None), "b": (2, None)})
        self.assertTrue(result.missing_newline)
        self.assertEqual(caught, [])
        self.assertEqual(self.read(), data)


class TornTailTest(LogTestCase):
    GOOD = raw_record("set", "a", 1) + raw_record("set", "b", 2)

    TORN = {
        "truncated mid-record": raw_record("set", "c", 3)[:15],
        "bad crc": raw_record("set", "c", 3, crc=1)[:-1],
        "not json": b"hello world",
        "missing key": b'{"op":"set","k":"c","v":3,"crc":1}',
        "extra key": raw_record("set", "c", 3)[:-2] + b',"x":1}',
        "unknown op": raw_record("put", "c", 3)[:-1],
        "invalid key": raw_record("set", "", 3)[:-1],
        "control char key": raw_record("set", "a\x01", 3)[:-1],
        "del with value": raw_record("del", "c", 3)[:-1],
        "invalid utf-8": b'{"op":"set","k":"\xff"}',
        "empty line": b"",
    }

    def test_invalid_last_record_is_dropped_and_truncated(self):  # AC2
        for name, tail in self.TORN.items():
            for newline in (b"", b"\n"):
                if name == "empty line" and newline == b"":
                    continue  # no record at all
                with self.subTest(name=name, newline=newline):
                    body = tail + newline
                    self.write(self.GOOD + body)
                    result, caught = self.replay_quietly()
                    self.assertEqual(result.index, {"a": (1, None), "b": (2, None)})
                    self.assertEqual(result.records, 2)
                    self.assertEqual(self.read(), self.GOOD)
                    self.assertEqual(len(caught), 1)
                    self.assertTrue(issubclass(caught[0].category, TornTailWarning))
                    self.assertTrue(issubclass(caught[0].category, UserWarning))
                    self.assertIn(str(len(self.GOOD)), str(caught[0].message))

    def test_bad_crc_last_record_with_and_without_newline(self):
        bad = raw_record("set", "c", 3, crc=7)
        for tail in (bad, bad[:-1]):
            with self.subTest(tail=tail):
                self.write(self.GOOD + tail)
                self.replay_quietly()
                self.assertEqual(self.read(), self.GOOD)

    def test_torn_only_record(self):
        self.write(b'{"op":"set","k":"a"')
        result, caught = self.replay_quietly()
        self.assertEqual(result.index, {})
        self.assertEqual(self.read(), b"")
        self.assertIn("offset 0", str(caught[0].message))

    def test_append_after_kept_unterminated_record_lands_on_own_line(self):
        # The store appends "\n" first when missing_newline is set; the log
        # still replays both records on their own lines.
        self.write(raw_record("set", "a", 1)[:-1])
        result, _ = self.replay_quietly()
        self.assertTrue(result.missing_newline)
        with open(self.path, "ab") as fh:
            fh.write(b"\n" + encode_record("set", "b", 2))
        result, caught = self.replay_quietly()
        self.assertEqual(result.index, {"a": (1, None), "b": (2, None)})
        self.assertEqual(caught, [])


class CorruptionTest(LogTestCase):
    def assert_corrupt(self, data, lineno):
        self.write(data)
        with self.assertRaises(CorruptLogError) as ctx:
            self.replay_quietly()
        self.assertEqual(ctx.exception.lineno, lineno)
        self.assertIn(f"line {lineno}", str(ctx.exception))
        self.assertIn(self.path, str(ctx.exception))
        self.assertEqual(self.read(), data)

    def test_bad_crc_in_the_middle(self):  # AC3
        self.assert_corrupt(
            raw_record("set", "a", 1) + raw_record("set", "b", 2, crc=5) + raw_record("set", "c", 3), 2
        )

    def test_empty_line_in_the_middle(self):
        self.assert_corrupt(raw_record("set", "a", 1) + b"\n" + raw_record("set", "c", 3), 2)

    def test_corrupt_first_line(self):
        self.assert_corrupt(b"garbage\n" + raw_record("set", "c", 3), 1)

    def test_corrupt_middle_with_torn_tail_leaves_bytes_unchanged(self):
        self.assert_corrupt(
            raw_record("set", "a", 1) + b"xx\n" + raw_record("set", "c", 3) + b'{"op":"s', 2
        )


if __name__ == "__main__":
    unittest.main()
