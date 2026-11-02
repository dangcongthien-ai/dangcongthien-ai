"""Metric checks: contribution streaks and weekly aggregation."""
import datetime as dt
import unittest
from generate_profile_cards import streak_data, weekly_data
from render_contributions import render
import xml.etree.ElementTree as ET


class ContributionTests(unittest.TestCase):
    def test_empty_today_preserves_yesterday(self):
        today = dt.datetime.now(dt.timezone.utc).date()
        self.assertEqual(streak_data([(today - dt.timedelta(days=2), 3),
                                     (today - dt.timedelta(days=1), 1), (today, 0)]), (2, 2, 2))

    def test_stale_data_has_no_current_streak(self):
        today = dt.datetime.now(dt.timezone.utc).date()
        self.assertEqual(streak_data([(today - dt.timedelta(days=5), 12)]), (0, 1, 1))

    def test_missing_date_does_not_bridge_streak(self):
        today = dt.datetime.now(dt.timezone.utc).date()
        self.assertEqual(streak_data([(today - dt.timedelta(days=2), 5), (today, 8)]), (1, 1, 2))

    def test_weekly_sum_and_sunday_boundary(self):
        points = weekly_data([(dt.date(2026, 11, 1), 3), (dt.date(2026, 11, 2), 4)], 2)
        self.assertEqual(points, [(dt.date(2026, 10, 25), 0), (dt.date(2026, 11, 1), 7)])

    def test_composite_encodes_exact_language_bytes_and_daily_counts(self):
        svg = render([(dt.date(2026, 11, 2), 7)], {'Python': 300, 'HTML': 100}, 3, 0)
        root = ET.fromstring(svg)
        contents = ''.join(root.itertext())
        self.assertIn('Python: 300 bytes (75.00%)', contents)
        self.assertIn('HTML: 100 bytes (25.00%)', contents)
        self.assertIn('2026-11-02: 7 contributions', contents)
        self.assertIn('Mon: 100.00%', contents)
        self.assertIn('Stars  3', contents)
        self.assertIn('Forks  0', contents)

    def test_no_language_data_does_not_invent_a_share(self):
        svg = render([(dt.date(2026, 11, 2), 0)], {}, 0, 0)
        self.assertIn('No language data', svg)
        self.assertNotIn('stroke-dasharray="0.000000', svg)


if __name__ == '__main__':
    unittest.main()
