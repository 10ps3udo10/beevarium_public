"""Test de scripts/uptime_report.py sur une base SQLite synthetique.

Lancer : python3 -m unittest scripts/tests/test_uptime_report.py
"""

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uptime_report  # noqa: E402


class UptimeReportTest(unittest.TestCase):
    def test_synthetic_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "kuma.db")
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE monitor (id INTEGER PRIMARY KEY, name TEXT)")
            con.execute("CREATE TABLE heartbeat (id INTEGER PRIMARY KEY AUTOINCREMENT, monitor_id INTEGER, status INTEGER, time DATETIME, ping INTEGER)")
            con.execute("INSERT INTO monitor VALUES (1, 'API'), (2, 'Vide')")
            t0 = datetime(2026, 9, 10, 0, 0, 0)
            # 1000 mesures a 60 s : hors service aux index 900-909 et 940-949 (2 x 10 min),
            # ping 100 ms sauf une mesure a 500 ms.
            for i in range(1000):
                down = 900 <= i < 910 or 940 <= i < 950
                ping = None if down else (500 if i == 5 else 100)
                con.execute("INSERT INTO heartbeat (monitor_id, status, time, ping) VALUES (1, ?, ?, ?)",
                            (0 if down else 1, (t0 + timedelta(seconds=60 * i)).strftime("%Y-%m-%d %H:%M:%S.000"), ping))
            # hors du mois : ignore
            con.execute("INSERT INTO heartbeat (monitor_id, status, time, ping) VALUES (1, 0, '2026-10-01 00:00:00.000', NULL)")
            con.commit()
            con.close()

            report = uptime_report.build_report(db, "2026-09")["moniteurs"]
            api = report["API"]
            self.assertEqual(api["mesures"], 1000)
            self.assertEqual(api["secondes_mesurees"], 60000)
            self.assertEqual(api["indisponibilites"], 2)
            self.assertEqual(api["indisponibilite_totale_s"], 1200)
            self.assertEqual(api["plus_longue_coupure_s"], 600)
            self.assertEqual(api["disponibilite_pct"], 98.0)
            self.assertEqual(api["ping_moyen_ms"], round((980 * 100 + 500) / 981, 1))
            self.assertEqual(api["ping_p95_ms"], 100)
            self.assertIsNone(report["Vide"]["disponibilite_pct"])
            markdown = uptime_report.to_markdown({"mois": "2026-09", "moniteurs": report})
            self.assertIn("| API | 98.000 % | 2 | 20 min 00 s | 10 min 00 s |", markdown)

    def test_gap_excluded(self):
        start, end = uptime_report.month_bounds("2026-09")
        beats = [(start, 1, 10), (start + timedelta(hours=2), 0, None)]
        result = uptime_report.analyse(beats, end)
        self.assertEqual(result["secondes_mesurees"], uptime_report.GAP_MAX + uptime_report.LAST_SEGMENT)
        self.assertEqual(result["indisponibilite_totale_s"], uptime_report.LAST_SEGMENT)


if __name__ == "__main__":
    unittest.main()
