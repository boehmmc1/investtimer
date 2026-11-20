"""KI-Limit (volafly-api/investtimer_ki_limit.py): Konto, IP, Gesamtbremse, Tageswechsel Europe/Berlin, Kostenpause,
Kostenwarnungen je Tag/Monat nur einmal, Antwort-Cache je Tag. Aufruf: python3 -m unittest tests/test_ki_limit.py"""
import datetime
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "volafly-api"))
import investtimer_ki_limit as k  # noqa: E402

GRENZEN = (1, 3, 5, 5.0)   # Konto, IP, gesamt, Tagesschwelle Euro


class KiLimit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["IT_KI_DB"] = os.path.join(self.tmp.name, "ki.db")

    def tearDown(self):
        self.tmp.cleanup()
        k._IP.clear()

    def test_konto_einmal_je_tag(self):
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"))
        self.assertEqual(k.buchen("u1", "1.1.1.2", *GRENZEN, t="2026-11-20"), "konto")
        s = k.stand("u1", None, *GRENZEN, t="2026-11-20")
        self.assertTrue(s["verbraucht"])
        self.assertFalse(s["ausgelastet"])
        self.assertFalse(k.stand("u2", None, *GRENZEN, t="2026-11-20")["verbraucht"])

    def test_ip_drei_je_tag(self):
        for u in ("a", "b", "c"):
            self.assertIsNone(k.buchen(u, "9.9.9.9", *GRENZEN, t="2026-11-20"))
        self.assertEqual(k.buchen("d", "9.9.9.9", *GRENZEN, t="2026-11-20"), "ip")
        self.assertIsNone(k.buchen("d", "8.8.8.8", *GRENZEN, t="2026-11-20"))
        self.assertTrue(k.stand("e", "9.9.9.9", *GRENZEN, t="2026-11-20")["verbraucht"])

    def test_gesamtbremse(self):
        for i in range(5):
            self.assertIsNone(k.buchen("u%d" % i, "10.0.0.%d" % i, *GRENZEN, t="2026-11-20"))
        self.assertEqual(k.buchen("u9", "10.0.0.9", *GRENZEN, t="2026-11-20"), "gesamt")
        self.assertTrue(k.stand("u9", None, *GRENZEN, t="2026-11-20")["ausgelastet"])

    def test_tageswechsel_berlin(self):
        # 22:59 UTC am 20.11. = 23:59 in Berlin (MEZ), 23:00 UTC = 00:00 am 21.11.
        self.assertEqual(k.tag(datetime.datetime(2026, 11, 20, 22, 59, tzinfo=datetime.timezone.utc)), "2026-11-20")
        self.assertEqual(k.tag(datetime.datetime(2026, 11, 20, 23, 0, tzinfo=datetime.timezone.utc)), "2026-11-21")
        self.assertEqual(k.tag(datetime.datetime(2026, 7, 1, 22, 0, tzinfo=datetime.timezone.utc)), "2026-07-02")  # MESZ
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"))
        self.assertEqual(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"), "konto")
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-21"))

    def test_zurueckbuchen(self):
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"))
        k.zurueckbuchen("u1", "1.1.1.1", "2026-11-20")
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"))

    def test_kosten_pause_und_warnungen(self):
        t = "2026-11-20"
        eur, tag_eur, _ = k.kosten_buchen("frei", "claude-sonnet-5", 1_000_000, 0, t=t)   # 2 $ = 1,84 EUR
        self.assertAlmostEqual(eur, 1.84, places=2)
        self.assertEqual(k.faellige_warnungen(1.0, 50.0, t=t)[0][0], "tag")
        self.assertEqual(k.faellige_warnungen(1.0, 50.0, t=t), [])           # nur einmal je Tag
        self.assertIsNone(k.buchen("u1", "1.1.1.1", 1, 3, 5, 1.0, t=t))      # 1,84 < 2 x 1,0
        k.kosten_buchen("katalog", "claude-sonnet-5", 200_000, 0, t=t)       # + 0,37 -> 2,21 >= 2,0
        self.assertEqual(k.buchen("u2", "2.2.2.2", 1, 3, 5, 1.0, t=t), "pause")
        self.assertTrue(k.stand("u2", None, 1, 3, 5, 1.0, t=t)["ausgelastet"])
        arten = [w[0] for w in k.faellige_warnungen(1.0, 2.0, t=t)]
        self.assertEqual(sorted(arten), ["monat", "pause"])
        self.assertIsNone(k.buchen("u2", "2.2.2.2", 1, 3, 5, 1.0, t="2026-11-21"))  # neuer Tag: Pause vorbei
        self.assertEqual(k.faellige_warnungen(1.0, 2.0, t="2026-11-21"), [])       # Monat schon gemeldet
        k.warnung_zuruecknehmen("monat", "2026-11")
        self.assertEqual([w[0] for w in k.faellige_warnungen(1.0, 2.0, t="2026-11-21")], ["monat"])

    def test_konto_loeschen(self):
        self.assertIsNone(k.buchen("u1", "1.1.1.1", *GRENZEN, t="2026-11-20"))
        k.konto_loeschen("u1")
        self.assertEqual(k.stand("u1", None, *GRENZEN, t="2026-11-20")["heute"], 0)

    def test_cache_je_tag(self):
        k.cache_schreiben("beispiel|de|x", "Antwort", t="2026-11-20")
        self.assertEqual(k.cache_lesen("beispiel|de|x", t="2026-11-20"), "Antwort")
        self.assertIsNone(k.cache_lesen("beispiel|de|x", t="2026-11-21"))

    def test_ip_nie_auf_der_platte(self):
        k.buchen("u1", "203.0.113.7", *GRENZEN, t="2026-11-20")
        roh = Path(os.environ["IT_KI_DB"]).read_bytes()
        self.assertNotIn(b"203.0.113.7", roh)
        self.assertEqual(k._ip_anzahl("2026-11-20", "203.0.113.7"), 1)

if __name__ == "__main__":
    unittest.main()
