"""SCRUM-119 t3 — atomic compaction, manual and automatic, crash safety (AC8, AC9, AC15)."""

import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from kvstore import CorruptLogError, KVStore, encode_record
from kvstore.log import decode_record


class FakeClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


class CompactionTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "kv.log")
        self.temp = self.path + ".compact.tmp"
        self.clock = FakeClock()

    def open(self):
        store = KVStore(self.path, clock=self.clock)
        self.addCleanup(store.close)
        return store

    def read(self):
        with open(self.path, "rb") as fh:
            return fh.read()

    def write(self, data):
        with open(self.path, "wb") as fh:
            fh.write(data)

    def records(self):
        lines = self.read().split(b"\n")
        self.assertEqual(lines[-1], b"")
        parsed = [decode_record(line) for line in lines[:-1]]
        self.assertNotIn(None, parsed)  # every line passes the CRC check
        return parsed

    def snapshot(self, store):
        return store.keys(), {k: store.get(k) for k in store.keys()}


class ManualCompactTest(CompactionTestCase):
    def build_mostly_dead_log(self):
        # Written directly so automatic compaction does not interfere.
        self.write(
            encode_record("set", "a", 1) + encode_record("set", "a", 2)
            + encode_record("set", "b", "x", 200.0) + encode_record("set", "gone", 1)
            + encode_record("del", "gone") + encode_record("set", "old", 1, 150.0)
            + encode_record("set", "c", {"n": [1]}) + encode_record("set", "c", {"n": [2]})
        )

    def test_compact_keeps_only_live_unexpired_sets(self):  # AC8
        self.build_mostly_dead_log()
        self.clock.now = 160  # "old" has expired, "b" has not
        store = self.open()
        before = self.snapshot(store)
        store.compact()
        self.assertEqual(self.snapshot(store), before)
        self.assertEqual(
            self.records(),
            [
                {"op": "set", "k": "a", "v": 2, "exp": None, "crc": mock.ANY},
                {"op": "set", "k": "b", "v": "x", "exp": 200.0, "crc": mock.ANY},
                {"op": "set", "k": "c", "v": {"n": [2]}, "exp": None, "crc": mock.ANY},
            ],
        )
        self.assertFalse(os.path.exists(self.temp))
        store.close()
        self.assertEqual(self.snapshot(self.open()), before)
        self.clock.now = 200
        self.assertEqual(self.open().keys(), ["a", "c"])  # kept exp still applies

    def test_atomic_order_temp_fsync_replace_dir_fsync(self):  # AC8
        self.build_mostly_dead_log()
        store = self.open()
        events = []
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(fd):
            target = os.readlink(f"/proc/self/fd/{fd}") if os.path.exists("/proc/self/fd") else str(fd)
            events.append(("fsync", target))
            return real_fsync(fd)

        def replace(src, dst):
            events.append(("replace", os.fspath(src), os.fspath(dst)))
            return real_replace(src, dst)

        with mock.patch("os.fsync", side_effect=fsync), mock.patch("os.replace", side_effect=replace):
            store.compact()
        kinds = [e[0] for e in events]
        self.assertEqual(kinds, ["fsync", "replace", "fsync"])
        self.assertEqual(events[1], ("replace", self.temp, self.path))
        if os.path.exists("/proc/self/fd"):
            self.assertEqual(os.path.realpath(events[0][1]), os.path.realpath(self.temp))
            self.assertEqual(os.path.realpath(events[2][1]), os.path.realpath(self.tmp.name))

    def test_manual_compact_always_rewrites(self):
        store = self.open()
        store.set("a", 1)
        store.set("b", 2)
        with mock.patch("os.replace", wraps=os.replace) as replace:
            store.compact()
        replace.assert_called_once()
        self.assertEqual([r["k"] for r in self.records()], ["a", "b"])

    def test_compact_of_empty_store(self):
        store = self.open()
        store.compact()
        self.assertEqual(self.read(), b"")

    def test_writes_after_compaction_survive_reopen(self):
        self.build_mostly_dead_log()
        store = self.open()
        store.compact()
        store.set("new", "value")
        store.delete("a")
        store.close()
        reopened = self.open()
        self.assertEqual(reopened.get("new"), "value")
        self.assertNotIn("a", reopened.keys())

    def test_compact_after_unterminated_tail(self):
        self.write(encode_record("set", "a", 1)[:-1])
        store = self.open()
        store.compact()
        store.set("b", 2)
        store.close()
        self.assertEqual(self.read(), encode_record("set", "a", 1) + encode_record("set", "b", 2))


class AutoCompactTest(CompactionTestCase):
    def test_compacts_when_live_ratio_below_half(self):  # AC15
        store = self.open()
        store.set("a", 1)
        store.set("a", 2)  # 1 live / 2 records = 0.5: not compacted
        self.assertEqual(len(self.records()), 2)
        with mock.patch("os.replace", wraps=os.replace) as replace:
            store.set("a", 3)  # 1 live / 3 records < 0.5: compacted
        replace.assert_called_once()
        self.assertEqual(self.records(), [{"op": "set", "k": "a", "v": 3, "exp": None, "crc": mock.ANY}])
        self.assertEqual(store.get("a"), 3)
        store.close()
        self.assertEqual(self.open().get("a"), 3)

    def test_no_rewrite_at_or_above_half(self):
        store = self.open()
        with mock.patch("os.replace", wraps=os.replace) as replace:
            store.set("a", 1)
            store.set("b", 1)
            store.set("c", 1)
            store.delete("c")  # 2 live / 4 records = 0.5
        replace.assert_not_called()
        self.assertEqual(len(self.records()), 4)

    def test_delete_triggers_compaction(self):
        store = self.open()
        store.set("a", 1)
        store.set("b", 2)
        store.delete("a")  # 1 live / 3 records
        self.assertEqual([r["k"] for r in self.records()], ["b"])
        store.delete("b")  # 0 live / 2 records -> empty log
        self.assertEqual(self.read(), b"")
        store.set("c", 3)
        store.close()
        self.assertEqual(self.open().keys(), ["c"])

    def test_expired_keys_count_as_dead(self):
        store = self.open()
        store.set("a", 1, ttl=5)
        store.set("b", 1, ttl=5)
        self.clock.now = 106
        store.set("c", 1)  # 1 live / 3 records
        self.assertEqual([r["k"] for r in self.records()], ["c"])
        self.assertEqual(store.keys(), ["c"])


class CrashSafetyTest(CompactionTestCase):
    def test_crash_before_rename_keeps_old_log_and_reopen_removes_temp(self):  # AC9
        store = self.open()
        for i in range(4):
            store.set(f"k{i}", i)
        store.set("k0", "latest")
        before = self.read()
        snapshot = self.snapshot(store)
        with mock.patch("os.replace", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                store.compact()
        self.assertTrue(os.path.exists(self.temp))  # temp written, never renamed
        self.assertEqual(self.read(), before)
        self.assertEqual(self.snapshot(store), snapshot)
        # The live store still appends to the original log.
        store.set("after", 1)
        store.close()
        reopened = self.open()
        self.assertFalse(os.path.exists(self.temp))
        self.assertEqual(reopened.get("k0"), "latest")
        self.assertEqual(reopened.get("after"), 1)

    def test_failed_auto_compaction_does_not_fail_the_mutation(self):
        store = self.open()
        store.set("a", 1)
        store.set("a", 2)
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertWarns(RuntimeWarning):
                store.set("a", 3)
        store.close()
        self.assertEqual(self.open().get("a"), 3)

    def test_stale_temp_removed_on_open(self):
        with open(self.temp, "wb") as fh:
            fh.write(encode_record("set", "stale", 1))
        self.write(encode_record("set", "a", 1))
        store = self.open()
        self.assertFalse(os.path.exists(self.temp))
        self.assertEqual(store.keys(), ["a"])

    def test_refused_store_compact_touches_nothing(self):
        data = encode_record("set", "a", 1) + b"bad\n" + encode_record("set", "b", 1)
        self.write(data)
        with self.assertRaises(CorruptLogError) as ctx:
            KVStore(self.path, clock=self.clock)
        refused = ctx.exception.store
        with self.assertRaises(CorruptLogError):
            refused.compact()
        self.assertFalse(os.path.exists(self.temp))
        self.assertEqual(self.read(), data)
        self.assertEqual(os.listdir(self.tmp.name), ["kv.log"])


class ConcurrencyTest(CompactionTestCase):
    def test_threaded_sets_with_compactions_lose_nothing(self):
        store = self.open()
        errors = []

        def writer(prefix):
            try:
                for i in range(200):
                    store.set(f"{prefix}{i}", i)
                    store.set(f"{prefix}{i}", i * 10)  # overwrites drive auto compaction
            except Exception as err:
                errors.append(err)

        def compactor():
            try:
                for _ in range(30):
                    store.compact()
            except Exception as err:
                errors.append(err)

        threads = [threading.Thread(target=writer, args=(p,)) for p in ("a", "b")]
        threads.append(threading.Thread(target=compactor))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        store.close()
        reopened = self.open()
        self.assertEqual(len(reopened.keys()), 400)
        self.assertEqual(reopened.get("b199"), 1990)
        self.assertTrue(all(json.loads(line) for line in self.read().splitlines()))


if __name__ == "__main__":
    unittest.main()
