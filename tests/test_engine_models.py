"""Testes do motor (com player falso) e da persistência."""
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecoa import paths  # noqa: E402
from ecoa.engine import Engine  # noqa: E402
from ecoa.models import Reminder, Store  # noqa: E402


class FakePlayer:
    def __init__(self):
        self.jobs = {}
        self.calls = []

    def run(self, rid, path, volume, repeats=1, gap=0, loop=False):
        if rid in self.jobs:
            return False
        self.jobs[rid] = loop
        self.calls.append((rid, repeats, loop))
        return True

    def is_playing(self, rid):
        return rid in self.jobs

    def stop(self, rid):
        self.jobs.pop(rid, None)

    def stop_all(self):
        self.jobs.clear()

    def clear_cache(self):
        pass


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        patcher = mock.patch.object(paths, "data_dir", return_value=root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        (root / "audios").mkdir()
        self.audio = root / "audios" / "aviso.wav"
        self.audio.write_bytes(b"RIFF")
        self.store = Store(root / "config.json")
        self.player = FakePlayer()
        self.engine = Engine(self.store, self.player)

    def reminder(self, **kw):
        base = dict(name="Água", audio_path="audios/aviso.wav", interval_value=30, interval_unit="min",
                    start="09:00", end="18:00", days=[0, 1, 2, 3, 4, 5, 6])
        base.update(kw)
        r = Reminder(**base)
        self.store.upsert(r)
        return r

    def test_interval_fires_on_grid_and_reschedules(self):
        r = self.reminder(repeats=3)
        self.engine.tick(datetime(2026, 11, 9, 9, 10))
        self.assertEqual(self.player.calls, [])
        self.engine.tick(datetime(2026, 11, 9, 9, 30, 1))
        self.assertEqual(self.player.calls, [(r.id, 3, False)])
        self.assertEqual(self.engine.status(r, datetime(2026, 11, 9, 9, 30, 2)), ("Tocando agora", "playing"))
        self.player.stop(r.id)
        text, _ = self.engine.status(r, datetime(2026, 11, 9, 9, 31))
        self.assertIn("10:00", text)

    def test_late_trigger_is_skipped(self):
        self.reminder()
        self.engine.tick(datetime(2026, 11, 9, 9, 10))
        self.engine.tick(datetime(2026, 11, 9, 9, 40))
        self.assertEqual(self.player.calls, [])

    def test_loop_starts_inside_window_and_stops_after(self):
        r = self.reminder(mode="loop")
        self.engine.tick(datetime(2026, 11, 9, 8, 59))
        self.assertEqual(self.player.calls, [])
        self.engine.tick(datetime(2026, 11, 9, 9, 0, 1))
        self.assertEqual(self.player.calls, [(r.id, 1, True)])
        self.engine.tick(datetime(2026, 11, 9, 12, 0))
        self.assertEqual(len(self.player.calls), 1)
        self.engine.tick(datetime(2026, 11, 9, 18, 0, 1))
        self.assertFalse(self.player.is_playing(r.id))

    def test_pause_and_disabled(self):
        r = self.reminder(mode="loop")
        self.engine.set_paused(True)
        self.engine.tick(datetime(2026, 11, 9, 10))
        self.assertEqual(self.player.calls, [])
        self.assertEqual(self.engine.status(r)[1], "off")
        self.engine.set_paused(False)
        self.store.upsert(Reminder(**{**r.to_dict(), "enabled": False}))
        self.engine.tick(datetime(2026, 11, 9, 10))
        self.assertEqual(self.player.calls, [])

    def test_missing_audio_reports_error(self):
        r = self.reminder(audio_path="audios/nao_existe.mp3")
        self.engine.tick(datetime(2026, 11, 9, 10))
        self.assertEqual(self.engine.status(r)[1], "error")
        self.assertEqual(self.player.calls, [])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        patcher = mock.patch.object(paths, "data_dir", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_roundtrip_and_sanitize(self):
        s = Store(self.root / "config.json")
        s.settings.theme = "dark"
        s.upsert(Reminder(name="  ", interval_value=99999, start="9h", end="25:00", volume=500, days=[3, 3, 9]))
        s.save()
        loaded = Store(self.root / "config.json")
        loaded.load()
        r = loaded.reminders[0]
        self.assertEqual(loaded.settings.theme, "dark")
        self.assertEqual((r.name, r.interval_value, r.start, r.end, r.volume, r.days),
                         ("Lembrete", 1440, "09:00", "18:00", 100, [3]))

    def test_corrupted_config_is_backed_up(self):
        path = self.root / "config.json"
        path.write_text("{ isto não é json", encoding="utf-8")
        s = Store(path)
        s.load()
        self.assertEqual(s.reminders, [])
        self.assertTrue(list(self.root.glob("config.corrompido-*.json")))

    def test_import_audio_copies_and_stores_relative_path(self):
        outside = self.root / "externo"
        outside.mkdir()
        src = outside / "voz.mp3"
        src.write_bytes(b"abc")
        s = Store(self.root / "config.json")
        stored = s.import_audio(str(src))
        self.assertEqual(stored, "audios/voz.mp3")
        self.assertTrue((self.root / "audios" / "voz.mp3").exists())
        self.assertEqual(s.import_audio(str(src)), "audios/voz.mp3")
        src.write_bytes(b"outro")
        self.assertEqual(s.import_audio(str(src)), "audios/voz (1).mp3")

    def test_import_audio_without_copy_keeps_absolute(self):
        src = self.root / "voz.mp3"
        src.write_bytes(b"abc")
        s = Store(self.root / "config.json")
        s.settings.copy_audio = False
        self.assertEqual(Path(s.import_audio(str(src))).name, "voz.mp3")


if __name__ == "__main__":
    unittest.main()
