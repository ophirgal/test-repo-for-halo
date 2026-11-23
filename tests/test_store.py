"""SCRUM-119 t2 — store API with TTL, validation, durability and threads (AC3-AC7, AC16, AC17)."""

import json
import os
import tempfile
import threading
import unittest
import warnings
from unittest import mock

from kvstore import CorruptLogError, KVStore, TornTailWarning, encode_record


class FakeClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "kv.log")
        self.clock = FakeClock()

    def open(self):
        store = KVStore(self.path, clock=self.clock)
        self.addCleanup(store.close)
        return store

    def read(self):
        with open(self.path, "rb") as fh:
            return fh.read()


class DictBehaviourTest(StoreTestCase):
    def test_set_get_delete_like_a_dict(self):  # AC4
        store = self.open()
        store.set("a", {"x": 1})
        store.set("b", [1, "two", None, True])
        store.set("a", 2)
        self.assertEqual(store.get("a"), 2)
        self.assertEqual(store.get("b"), [1, "two", None, True])
        store.delete("b")
        with self.assertRaises(KeyError):
            store.get("b")
        with self.assertRaises(KeyError):
            store.delete("b")
        with self.assertRaises(KeyError):
            store.get("never")
        self.assertEqual(store.keys(), ["a"])

    def test_every_mutation_is_fsynced_and_survives_reopen(self):  # AC4
        store = self.open()
        with mock.patch("os.fsync", wraps=os.fsync) as fsync:
            store.set("a", 1)
            self.assertEqual(fsync.call_count, 1)
            store.set("b", 2)
            self.assertEqual(fsync.call_count, 2)
            store.set("c", 3, ttl=50)
            self.assertEqual(fsync.call_count, 3)
            store.delete("a")
            self.assertEqual(fsync.call_count, 4)
        store.close()
        reopened = self.open()
        self.assertEqual(reopened.keys(), ["b", "c"])
        self.assertEqual((reopened.get("b"), reopened.get("c")), (2, 3))

    def test_keys_sorted_ascending(self):
        store = self.open()
        for k in ("zeta", "Alpha", "beta", "a/b", "ä"):
            store.set(k, 1)
        self.assertEqual(store.keys(), sorted(["zeta", "Alpha", "beta", "a/b", "ä"]))

    def test_context_manager_closes(self):
        with KVStore(self.path, clock=self.clock) as store:
            store.set("a", 1)
        with self.assertRaises(ValueError):
            store.set("b", 2)
        with KVStore(self.path) as store:  # default wall clock
            self.assertEqual(store.get("a"), 1)

    def test_records_written_in_log_format(self):
        store = self.open()
        store.set("a", 1, ttl=5)
        store.delete("a")
        lines = self.read().splitlines(keepends=True)
        self.assertEqual(lines, [encode_record("set", "a", 1, 105.0), encode_record("del", "a")])


class ExpiryTest(StoreTestCase):
    def test_ac5_expiry(self):
        store = self.open()
        store.set("a", 1, ttl=10)
        store.set("b", 2)
        self.clock.now = 109.9
        self.assertEqual(store.get("a"), 1)
        self.assertEqual(store.keys(), ["a", "b"])
        self.clock.now = 110
        with self.assertRaises(KeyError):
            store.get("a")
        self.assertEqual(store.keys(), ["b"])
        self.clock.now = 500
        with self.assertRaises(KeyError):
            store.get("a")

    def test_expiry_survives_reopen(self):
        store = self.open()
        store.set("a", 1, ttl=10)
        store.close()
        self.clock.now = 109.9
        self.assertEqual(self.open().get("a"), 1)
        self.clock.now = 110
        self.assertEqual(self.open().keys(), [])

    def test_deleting_expired_key_appends_nothing(self):
        store = self.open()
        store.set("a", 1, ttl=1)
        before = self.read()
        self.clock.now = 101
        with self.assertRaises(KeyError):
            store.delete("a")
        self.assertEqual(self.read(), before)

    def test_set_without_ttl_clears_expiry(self):  # AC17
        store = self.open()
        store.set("a", 1, ttl=10)
        store.set("a", 2)
        self.clock.now = 1000
        self.assertEqual(store.get("a"), 2)
        store.close()
        self.assertEqual(self.open().get("a"), 2)

    def test_fractional_ttl(self):
        store = self.open()
        store.set("a", 1, ttl=0.5)
        self.clock.now = 100.25
        self.assertEqual(store.get("a"), 1)
        self.clock.now = 100.5
        with self.assertRaises(KeyError):
            store.get("a")


class ValidationTest(StoreTestCase):
    def assert_rejected(self, rule, call):
        store = self.open()
        store.set("existing", 1)
        before = self.read()
        with self.assertRaises(ValueError) as ctx:
            call(store)
        self.assertIn(rule, str(ctx.exception))
        self.assertEqual(self.read(), before)
        store.close()

    def test_bad_keys(self):  # AC6
        cases = {
            "x" * 129: "key length",
            "": "key length",
            "a\x00b": "key printable",
            "tab\there": "key printable",
            "line\n": "key printable",
            "zero​width": "key printable",
            "lone\ud800": "key printable",
            5: "key length",
            None: "key length",
            b"bytes": "key length",
        }
        for key, rule in cases.items():
            with self.subTest(key=key):
                self.assert_rejected(rule, lambda s: s.set(key, 1))

    def test_good_keys(self):  # AC16
        store = self.open()
        for key in ("x" * 128, "a", "with space", "app/config", "שלום", "\U0001f600", "~!@#$%^&*()"):
            with self.subTest(key=key):
                store.set(key, key)
                self.assertEqual(store.get(key), key)
        store.close()
        self.assertIn("app/config", self.open().keys())

    def test_value_size_limit(self):  # AC6, AC17
        store = self.open()
        exact = "x" * (65536 - 2)  # quotes make it 65,536 bytes
        self.assertEqual(len(json.dumps(exact)), 65536)
        store.set("big", exact)
        self.assertEqual(store.get("big"), exact)
        multibyte = "é" * 32767  # 65,534 bytes + quotes = 65,536
        store.set("mb", multibyte)
        store.close()
        self.assert_rejected("value size", lambda s: s.set("big", exact + "x"))
        self.assert_rejected("value size", lambda s: s.set("mb", multibyte + "x"))

    def test_bad_values(self):  # AC6, AC17
        for value in (float("nan"), float("inf"), [float("-inf")], {1, 2}, b"bytes", object(), "lone\ud800"):
            with self.subTest(value=value):
                self.assert_rejected("value JSON", lambda s: s.set("k", value))

    def test_bad_ttls(self):  # AC17
        for ttl in (0, -1, -0.5, float("nan"), float("inf"), True, False, "5", 10**400, [1]):
            with self.subTest(ttl=ttl):
                self.assert_rejected("ttl", lambda s: s.set("k", 1, ttl=ttl))

    def test_invalid_key_on_get_and_delete(self):
        store = self.open()
        with self.assertRaises(ValueError):
            store.get("")
        with self.assertRaises(ValueError):
            store.delete("x" * 129)


class ConcurrencyTest(StoreTestCase):
    def test_two_threads_500_keys_each(self):  # AC7
        store = self.open()
        errors = []

        def writer(prefix):
            try:
                for i in range(500):
                    store.set(f"{prefix}{i}", i)
            except Exception as err:  # surfaced below
                errors.append(err)

        threads = [threading.Thread(target=writer, args=(p,)) for p in ("t1-", "t2-")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        store.close()
        reopened = self.open()
        keys = reopened.keys()
        self.assertEqual(len(keys), 1000)
        self.assertEqual(set(keys), {f"{p}{i}" for p in ("t1-", "t2-") for i in range(500)})
        self.assertEqual(reopened.get("t2-499"), 499)


class RecoveryTest(StoreTestCase):
    def test_corrupt_log_refuses_every_operation(self):  # AC3, AC17
        data = encode_record("set", "a", 1) + b"garbage\n" + encode_record("set", "b", 2)
        with open(self.path, "wb") as fh:
            fh.write(data)
        with self.assertRaises(CorruptLogError) as ctx:
            KVStore(self.path, clock=self.clock)
        err = ctx.exception
        self.assertEqual(err.lineno, 2)
        self.assertIn("line 2", str(err))
        refused = err.store
        self.assertIsInstance(refused, KVStore)
        for call in (
            lambda: refused.set("c", 3),
            lambda: refused.delete("a"),
            lambda: refused.get("a"),
            lambda: refused.keys(),
        ):
            with self.assertRaises(CorruptLogError) as op_ctx:
                call()
            self.assertEqual(op_ctx.exception.lineno, 2)
        refused.close()
        self.assertEqual(self.read(), data)

    def test_torn_tail_then_store_keeps_working(self):
        good = encode_record("set", "a", 1)
        with open(self.path, "wb") as fh:
            fh.write(good + b'{"op":"set","k":"b"')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store = self.open()
        self.assertTrue(any(issubclass(w.category, TornTailWarning) for w in caught))
        self.assertIn(str(len(good)), str(caught[0].message))
        store.set("b", 2)
        store.close()
        self.assertEqual(self.read(), good + encode_record("set", "b", 2))
        self.assertEqual(self.open().keys(), ["a", "b"])

    def test_unterminated_last_record_gets_newline_before_next(self):
        with open(self.path, "wb") as fh:
            fh.write(encode_record("set", "a", 1)[:-1])
        store = self.open()
        store.set("b", 2)
        store.close()
        self.assertEqual(self.read(), encode_record("set", "a", 1) + encode_record("set", "b", 2))


if __name__ == "__main__":
    unittest.main()
