"""Testes da lógica de agendamento. Rodar com: python -m unittest discover -s tests -v"""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecoa import schedule  # noqa: E402
from ecoa.models import Reminder  # noqa: E402

# 2026-11-09 é segunda-feira
SEG = datetime(2026, 11, 9)
D = lambda day, h=0, m=0, s=0: datetime(2026, 11, day, h, m, s)  # noqa: E731
ALL = [0, 1, 2, 3, 4, 5, 6]
WEEK = [0, 1, 2, 3, 4]


def rem(**kw):
    base = dict(mode="interval", interval_value=30, interval_unit="min", start="09:00", end="18:00", days=ALL)
    base.update(kw)
    return Reminder(**base)


class NormalizeTests(unittest.TestCase):
    def test_formats(self):
        cases = {"9": "09:00", "09": "09:00", "900": "09:00", "0930": "09:30", "9:30": "09:30",
                 "9h30": "09:30", "18:00": "18:00", " 7h ": "07:00", "23:59": "23:59"}
        for raw, expected in cases.items():
            self.assertEqual(schedule.normalize_hhmm(raw), expected, raw)

    def test_invalid(self):
        for raw in ["", "24:00", "12:60", "abc", "12345", ":30", "-1"]:
            self.assertIsNone(schedule.normalize_hhmm(raw), raw)


class WindowTests(unittest.TestCase):
    def test_same_day_window_half_open(self):
        r = rem()
        self.assertIsNone(schedule.active_window(r, D(9, 8, 59, 59)))
        self.assertIsNotNone(schedule.active_window(r, D(9, 9, 0)))
        self.assertIsNotNone(schedule.active_window(r, D(9, 17, 59, 59)))
        self.assertIsNone(schedule.active_window(r, D(9, 18, 0)))

    def test_overnight_window(self):
        r = rem(start="22:00", end="06:00")
        self.assertIsNotNone(schedule.active_window(r, D(9, 23, 0)))
        self.assertIsNotNone(schedule.active_window(r, D(10, 5, 59)))
        self.assertIsNone(schedule.active_window(r, D(10, 6, 0)))
        self.assertIsNone(schedule.active_window(r, D(10, 12, 0)))

    def test_overnight_uses_start_day(self):
        r = rem(start="22:00", end="06:00", days=[0])
        self.assertIsNotNone(schedule.active_window(r, D(10, 3, 0)))
        self.assertIsNone(schedule.active_window(r, D(11, 3, 0)))
        self.assertIsNone(schedule.active_window(r, D(10, 23, 0)))

    def test_full_day(self):
        r = rem(start="00:00", end="00:00")
        self.assertTrue(schedule.is_full_day(r))
        for h in (0, 6, 12, 23):
            self.assertIsNotNone(schedule.active_window(r, D(9, h, 30)))

    def test_days_filter(self):
        r = rem(days=WEEK)
        self.assertIsNotNone(schedule.active_window(r, D(13, 10)))
        self.assertIsNone(schedule.active_window(r, D(14, 10)))


class NextTriggerTests(unittest.TestCase):
    def test_grid_inside_window(self):
        r = rem()
        self.assertEqual(schedule.next_trigger(r, D(9, 9, 10)), D(9, 9, 30))
        self.assertEqual(schedule.next_trigger(r, D(9, 9, 30)), D(9, 10, 0))
        self.assertEqual(schedule.next_trigger(r, D(9, 8, 0)), D(9, 9, 0))

    def test_end_is_exclusive_and_rolls_to_next_day(self):
        self.assertEqual(schedule.next_trigger(rem(), D(9, 17, 45)), D(10, 9, 0))

    def test_weekend_skipped(self):
        self.assertEqual(schedule.next_trigger(rem(days=WEEK), D(13, 17, 45)), D(16, 9, 0))

    def test_hourly_interval_anchored_to_start(self):
        r = rem(interval_value=1, interval_unit="h", start="09:15", end="12:00")
        self.assertEqual(schedule.next_trigger(r, D(9, 9, 16)), D(9, 10, 15))
        self.assertEqual(schedule.next_trigger(r, D(9, 11, 16)), D(10, 9, 15))

    def test_overnight_grid(self):
        r = rem(start="22:00", end="06:00", interval_value=2, interval_unit="h")
        self.assertEqual(schedule.next_trigger(r, D(10, 1, 10)), D(10, 2, 0))
        self.assertEqual(schedule.next_trigger(r, D(10, 5, 10)), D(10, 22, 0))

    def test_no_days(self):
        self.assertIsNone(schedule.next_trigger(rem(days=[]), D(9, 10)))

    def test_next_window_start(self):
        self.assertEqual(schedule.next_window_start(rem(days=WEEK), D(13, 19)), D(16, 9, 0))


class TextTests(unittest.TestCase):
    def test_describe(self):
        self.assertEqual(schedule.describe_days(ALL), "Todos os dias")
        self.assertEqual(schedule.describe_days(WEEK), "Seg a Sex")
        self.assertEqual(schedule.describe_days([5, 6]), "Fins de semana")
        self.assertEqual(schedule.describe_days([0, 2, 4]), "Seg, Qua, Sex")
        self.assertEqual(schedule.describe_rule(rem(interval_value=2, interval_unit="h")), "A cada 2 h")
        self.assertEqual(schedule.describe_rule(rem(mode="loop")), "Em loop contínuo")
        self.assertEqual(schedule.describe_window(rem(start="00:00", end="00:00")), "Dia todo")

    def test_fmt_when(self):
        now = D(9, 10)
        self.assertEqual(schedule.fmt_when(D(9, 14, 30), now), "hoje às 14:30")
        self.assertEqual(schedule.fmt_when(D(10, 9, 0), now), "amanhã às 09:00")
        self.assertEqual(schedule.fmt_when(D(13, 9, 0), now), "sex às 09:00")


if __name__ == "__main__":
    unittest.main()
