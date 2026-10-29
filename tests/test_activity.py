from datetime import date, timedelta
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_activity import parse_calendar, render, streaks


class ActivityTests(unittest.TestCase):
    def test_streak_today_grace_and_break(self):
        days = [(date(2026, 10, 25) + timedelta(days=i), n) for i, n in enumerate([1, 2, 3, 0])]
        self.assertEqual(streaks(days), (3, 3))
        days.append((date(2026, 10, 29), 0))
        self.assertEqual(streaks(days), (0, 3))
        ElementTree.fromstring(render(158, days, '2026-10-29 10:00 UTC'))

    def test_calendar_parses_all_days_and_heading(self):
        page = '<h2 id="js-contribution-activity-description">158 contributions in the last year</h2>'
        for i in range(365):
            d = date(2025, 10, 30) + timedelta(days=i)
            page += f'<td id="day-{i}" data-date="{d}"></td><tool-tip for="day-{i}">No contributions on day.</tool-tip>'
        total, days = parse_calendar(page)
        self.assertEqual(total, 158)
        self.assertEqual(len(days), 365)
        self.assertEqual(days[-1][0], date(2026, 10, 29))

    def test_unavailable_calendar_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_calendar('<html>Rate limit</html>')
