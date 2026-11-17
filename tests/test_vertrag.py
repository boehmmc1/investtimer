"""Kuendigung nach § 309 Nr. 9 BGB und Abo-Mail-Regeln (ohne Netz)."""
import os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "volafly-api"))
os.environ["INVESTTIMER_KONTO_DB"] = os.path.join(tempfile.mkdtemp(), "konto.db")
import investtimer_vertrag as v  # noqa: E402

J = 86400


class Antwort:
    def __init__(self, d): self.d = d
    def raise_for_status(self): pass
    def json(self): return self.d


class Kuendigung(unittest.TestCase):
    def kuendige(self, abo, monatlich=True, jetzt=1_900_000_000):
        gesendet = {}
        def post(url, data=None, **kw):
            gesendet.update(data)
            return Antwort(dict(abo, cancel_at=int(data["cancel_at"])) if "cancel_at" in data else dict(abo, cancel_at_period_end=True))
        with mock.patch.object(v.requests, "post", post):
            ende = v.stripe_kuendigen({"secret": "x", "verlaengerung_monatlich": monatlich}, abo, jetzt)
        return gesendet, ende

    def test_erste_laufzeit_zum_periodenende(self):
        t = 1_900_000_000
        abo = {"id": "s", "status": "active", "start_date": t - 100 * J, "current_period_start": t - 100 * J, "current_period_end": t + 265 * J}
        g, ende = self.kuendige(abo, jetzt=t)
        self.assertEqual(g, {"cancel_at_period_end": "true"}); self.assertEqual(ende, t + 265 * J)

    def test_nach_verlaengerung_hoechstens_ein_monat(self):
        t = 1_900_000_000
        abo = {"id": "s", "status": "active", "start_date": t - 400 * J, "current_period_start": t - 35 * J, "current_period_end": t + 330 * J}
        g, ende = self.kuendige(abo, jetzt=t)
        self.assertEqual(g["cancel_at"], str(t + 30 * J)); self.assertEqual(ende, t + 30 * J)

    def test_verlaengert_aber_ende_naeher_als_monat(self):
        t = 1_900_000_000
        abo = {"id": "s", "status": "active", "start_date": t - 700 * J, "current_period_start": t - 350 * J, "current_period_end": t + 15 * J}
        g, ende = self.kuendige(abo, jetzt=t)
        self.assertEqual(g, {"cancel_at_period_end": "true"}); self.assertEqual(ende, t + 15 * J)

    def test_testphase_endet_mit_test(self):
        t = 1_900_000_000
        abo = {"id": "s", "status": "trialing", "start_date": t - 2 * J, "trial_end": t + 5 * J, "current_period_start": t - 2 * J, "current_period_end": t + 5 * J}
        g, ende = self.kuendige(abo, jetzt=t)
        self.assertEqual(g, {"cancel_at_period_end": "true"}); self.assertEqual(ende, t + 5 * J)

    def test_ohne_schalter_periodenende(self):
        t = 1_900_000_000
        abo = {"id": "s", "status": "active", "start_date": t - 400 * J, "current_period_start": t - 35 * J, "current_period_end": t + 330 * J}
        g, _ = self.kuendige(abo, monatlich=False, jetzt=t)
        self.assertEqual(g, {"cancel_at_period_end": "true"})


class Mails(unittest.TestCase):
    def test_anlaesse(self):
        self.assertEqual(v.abo_anlass("INITIAL_PURCHASE", "TRIAL", None, "stripe"), "teststart")
        self.assertIsNone(v.abo_anlass("INITIAL_PURCHASE", "TRIAL", None, "apple"))     # Apple bestaetigt selbst
        self.assertEqual(v.abo_anlass("RENEWAL", "NORMAL", "test", "stripe"), "bezahlt")
        self.assertIsNone(v.abo_anlass("RENEWAL", "NORMAL", "aktiv", "stripe"))        # nur nach der Testphase
        self.assertEqual(v.abo_anlass("EXPIRATION", "NORMAL", "gekuendigt", "apple"), "abgelaufen")

    def test_einmal(self):
        self.assertTrue(v.abo_mail_einmal("u:testende:1")); self.assertFalse(v.abo_mail_einmal("u:testende:1"))

    def test_eingabe(self):
        with self.assertRaises(v.Fehler): v.pruefen("kuendigung", {"name": "A", "email": "a@b.de", "kuendigungsart": "ordentlich"})
        with self.assertRaises(v.Fehler): v.pruefen("kuendigung", {"name": "Anna", "email": "kein-mail", "kuendigungsart": "ordentlich"})
        n, e, a = v.pruefen("kuendigung", {"name": " Anna B ", "email": "Anna@B.de", "kuendigungsart": "ordentlich"})
        self.assertEqual((n, e, a["zeitpunkt"]), ("Anna B", "anna@b.de", "naechstmoeglich"))


if __name__ == "__main__":
    unittest.main()
