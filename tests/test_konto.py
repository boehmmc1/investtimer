"""Abo- und Berechtigungsablauf (FR-026) gegen investtimer_konto, ohne Netz.

Aufruf: python3 -m unittest tests/test_konto.py
RevenueCat-Ereignisse und Abonnentenobjekte sind nach der RevenueCat-Doku
nachgebildet (Webhook-Felder event.type, period_type, expiration_at_ms ...).
"""
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "volafly-api"))
os.environ["INVESTTIMER_KONTO_DB"] = os.path.join(tempfile.mkdtemp(), "konto.db")
import investtimer_konto as k  # noqa: E402

TAG = 86400000
T0 = 1_800_000_000_000  # fester Startzeitpunkt (ms)
UID = "11111111-2222-3333-4444-555555555555"


def ev(eid, typ, ts, period="NORMAL", bis=None, pid="investtimer_premium_yearly", store="STRIPE", **mehr):
    e = {"id": eid, "type": typ, "app_user_id": UID, "event_timestamp_ms": ts, "period_type": period,
         "product_id": pid, "store": store, "entitlement_ids": ["premium"], "purchased_at_ms": ts,
         "expiration_at_ms": bis}
    e.update(mehr)
    return {"api_version": "1.0", "event": e}


def abonnent(pid, store, kauf, bis, period="normal", **mehr):
    a = {"store": store, "purchase_date": kauf, "expires_date": bis, "period_type": period}
    a.update(mehr)
    return {"subscriber": {"subscriptions": {pid: a},
                           "entitlements": {"premium": {"product_identifier": pid, "expires_date": bis}}}}


class Abo(unittest.TestCase):
    def setUp(self):
        with k.verbinden() as db:
            for t in ("berechtigung", "ereignis", "ki_nutzung", "test_marker"):
                db.execute("DELETE FROM " + t)
        k.jetzt_ms = lambda: self.jetzt
        self.jetzt = T0

    def st(self):
        return k.status(UID, self.jetzt)

    def test_01_neu_ohne_abo_ist_frei(self):
        s = self.st()
        self.assertFalse(s["premium"])
        self.assertEqual(s["status"], "frei")
        self.assertEqual(k.kaufen_erlaubt(UID), {"testErlaubt": True})

    def test_02_03_testphase_monat_und_jahr(self):
        for pid, tarif in (("investtimer_premium_monthly", "monatlich"), ("net.investtimer.premium.yearly", "jaehrlich")):
            self.setUp()
            k.rc_ereignis(ev("a-" + pid, "INITIAL_PURCHASE", T0, "TRIAL", T0 + 7 * TAG, pid=pid))
            s = self.st()
            self.assertTrue(s["premium"])
            self.assertEqual((s["status"], s["tarif"], s["testTageRest"]), ("test", tarif, 7))
            self.assertTrue(s["verlaengerung"])

    def test_04_testphase_endet_erste_zahlung(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "TRIAL", T0 + 7 * TAG))
        self.jetzt = T0 + 7 * TAG + 1000
        k.rc_ereignis(ev("2", "RENEWAL", self.jetzt, "NORMAL", self.jetzt + 365 * TAG))
        s = self.st()
        self.assertEqual((s["premium"], s["status"], s["testTageRest"]), (True, "aktiv", None))
        self.assertTrue(s["testGenutzt"])

    def test_05_kuendigung_in_testphase(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "TRIAL", T0 + 7 * TAG))
        self.jetzt = T0 + 2 * TAG
        k.rc_ereignis(ev("2", "CANCELLATION", self.jetzt, "TRIAL", T0 + 7 * TAG, cancel_reason="UNSUBSCRIBE"))
        s = self.st()
        self.assertEqual((s["premium"], s["status"], s["verlaengerung"]), (True, "gekuendigt", False))
        self.jetzt = T0 + 7 * TAG + 1
        self.assertFalse(self.st()["premium"])
        self.assertEqual(self.st()["status"], "abgelaufen")

    def test_06_07_kuendigung_bezahlt_behaelt_zeitraum(self):
        for pid, dauer in (("investtimer_premium_monthly", 30), ("investtimer_premium_yearly", 365)):
            self.setUp()
            k.rc_ereignis(ev("1" + pid, "INITIAL_PURCHASE", T0, "NORMAL", T0 + dauer * TAG, pid=pid))
            self.jetzt = T0 + 10 * TAG
            k.rc_ereignis(ev("2" + pid, "CANCELLATION", self.jetzt, "NORMAL", T0 + dauer * TAG, pid=pid,
                             cancel_reason="UNSUBSCRIBE"))
            self.assertTrue(self.st()["premium"])
            self.assertEqual(self.st()["premiumBis"], T0 + dauer * TAG)
            self.jetzt = T0 + dauer * TAG + 1
            self.assertFalse(self.st()["premium"])

    def test_08_regulaerer_ablauf(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG))
        self.jetzt = T0 + 30 * TAG + 5
        k.rc_ereignis(ev("2", "EXPIRATION", self.jetzt, "NORMAL", T0 + 30 * TAG))
        self.assertEqual((self.st()["premium"], self.st()["status"]), (False, "abgelaufen"))

    def test_09_zahlung_fehlgeschlagen(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG))
        self.jetzt = T0 + 30 * TAG - 10
        # Kulanzfrist des Anbieters verlaengert expiration; ohne Kulanz bleibt das alte Ende
        k.rc_ereignis(ev("2", "BILLING_ISSUE", self.jetzt, "NORMAL", T0 + 33 * TAG))
        self.assertEqual((self.st()["premium"], self.st()["status"]), (True, "zahlungsproblem"))
        self.jetzt = T0 + 33 * TAG + 1
        self.assertFalse(self.st()["premium"])

    def test_10_erstattung_sperrt_sofort(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 365 * TAG))
        self.jetzt = T0 + 3 * TAG
        k.rc_ereignis(ev("2", "CANCELLATION", self.jetzt, "NORMAL", T0 + 365 * TAG, cancel_reason="CUSTOMER_SUPPORT"))
        self.assertEqual((self.st()["premium"], self.st()["status"]), (False, "erstattet"))

    def test_11_tarifwechsel(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG, pid="investtimer_premium_monthly"))
        self.jetzt = T0 + 30 * TAG
        k.rc_ereignis(ev("2", "PRODUCT_CHANGE", self.jetzt, "NORMAL", self.jetzt + 365 * TAG))
        self.assertEqual(self.st()["tarif"], "jaehrlich")

    def test_12_plattformwechsel_gleiche_berechtigung(self):
        # Kauf im Web (Stripe), Abruf aus der App: dieselbe uid, derselbe Stand
        k.aus_subscriber(UID, abonnent("investtimer_premium_yearly", "stripe", "2027-01-15T00:00:00Z",
                                       "2028-01-15T00:00:00Z"), jetzt=T0)
        s = self.st()
        self.assertEqual((s["premium"], s["kanal"], s["tarif"]), (True, "stripe", "jaehrlich"))
        # Apple-Kauf eines anderen Nutzers beruehrt ihn nicht
        self.assertFalse(k.ist_premium("andere-uid", T0))

    def test_13_zweite_testphase_verweigert(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "TRIAL", T0 + 7 * TAG))
        k.rc_ereignis(ev("2", "CANCELLATION", T0 + TAG, "TRIAL", T0 + 7 * TAG, cancel_reason="UNSUBSCRIBE"))
        self.jetzt = T0 + 8 * TAG
        k.rc_ereignis(ev("3", "EXPIRATION", self.jetzt, "TRIAL", T0 + 7 * TAG))
        self.assertEqual(k.kaufen_erlaubt(UID), {"testErlaubt": False})
        # auch nach Kontoloeschung und Neuanmeldung mit derselben E-Mail
        k.test_merken("Kunde@Example.org")
        self.assertTrue(k.test_schon_genutzt("neue-uid", "kunde@example.org"))

    def test_14_zweites_abo_verweigert(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG, store="APP_STORE",
                         pid="net.investtimer.premium.monthly"))
        with self.assertRaises(k.Fehler) as f:
            k.kaufen_erlaubt(UID)
        self.assertEqual((f.exception.code, f.exception.status), ("schon_premium", 409))
        self.assertEqual(self.st()["verwaltung"], "apple")

    def test_15_webhook_doppelt_und_verspaetet(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG))
        self.jetzt = T0 + 5 * TAG
        k.rc_ereignis(ev("2", "CANCELLATION", self.jetzt, "NORMAL", T0 + 30 * TAG, cancel_reason="UNSUBSCRIBE"))
        # dasselbe Ereignis noch einmal: keine Wirkung
        self.assertIsNone(k.rc_ereignis(ev("2", "CANCELLATION", self.jetzt, "NORMAL", T0 + 30 * TAG)))
        # ein aelteres Ereignis kommt verspaetet: Stand bleibt "gekuendigt"
        k.rc_ereignis(ev("0", "UNCANCELLATION", T0 + TAG, "NORMAL", T0 + 30 * TAG))
        self.assertEqual(self.st()["status"], "gekuendigt")

    def test_16_kontoloeschung(self):
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG))
        with self.assertRaises(k.Fehler) as f:
            k.loeschen_pruefen(UID)
        self.assertEqual(f.exception.code, "abo_aktiv")
        k.rc_ereignis(ev("2", "CANCELLATION", T0 + TAG, "NORMAL", T0 + 30 * TAG, cancel_reason="UNSUBSCRIBE"))
        k.loeschen_pruefen(UID)
        k.ki_buchen(UID, 10, 100)
        k.konto_loeschen(UID)
        self.assertIsNone(k.roh(UID))
        self.assertEqual(k.ki_stand(UID)["heute"], 0)

    def test_17_wiederherstellung_apple(self):
        # Neuinstallation: App ruft "Kaeufe wiederherstellen", Server holt den Abonnenten neu
        k.aus_subscriber(UID, abonnent("net.investtimer.premium.monthly", "app_store", "2027-01-01T00:00:00Z",
                                       "2027-02-01T00:00:00Z"), jetzt=_ms("2027-01-10T00:00:00Z"))
        self.jetzt = _ms("2027-01-10T00:00:00Z")
        s = self.st()
        self.assertEqual((s["premium"], s["kanal"], s["verwaltung"]), (True, "apple", "apple"))

    def test_18_revenuecat_nicht_erreichbar(self):
        # Ohne neuen Abruf gilt der zuletzt gespeicherte Stand weiter (kein Sperren, kein Freischalten)
        k.rc_ereignis(ev("1", "INITIAL_PURCHASE", T0, "NORMAL", T0 + 30 * TAG))
        self.jetzt = T0 + 10 * TAG
        self.assertTrue(self.st()["premium"])
        self.jetzt = T0 + 31 * TAG
        self.assertFalse(self.st()["premium"])

    def test_subscriber_status_varianten(self):
        jetzt = _ms("2027-01-03T00:00:00Z")
        k.aus_subscriber(UID, abonnent("investtimer_premium_monthly", "stripe", "2027-01-01T00:00:00Z",
                                       "2027-01-08T00:00:00Z", period="trial"), jetzt=jetzt)
        self.assertEqual(k.status(UID, jetzt)["status"], "test")
        k.aus_subscriber(UID, abonnent("investtimer_premium_monthly", "stripe", "2027-01-01T00:00:00Z",
                                       "2027-01-08T00:00:00Z", period="trial",
                                       unsubscribe_detected_at="2027-01-02T00:00:00Z"), jetzt=jetzt + 1)
        self.assertEqual(k.status(UID, jetzt + 1)["status"], "gekuendigt")
        k.aus_subscriber(UID, {"subscriber": {"subscriptions": {}, "entitlements": {}}}, jetzt=jetzt + 2)
        self.assertFalse(k.ist_premium(UID, jetzt + 2))

    def test_ki_kontingent(self):
        for _ in range(3):
            self.assertTrue(k.ki_buchen(UID, 3, 100, tag="2027-01-05")[0])
        self.assertFalse(k.ki_buchen(UID, 3, 100, tag="2027-01-05")[0])
        self.assertTrue(k.ki_buchen(UID, 3, 100, tag="2027-01-06")[0])
        self.assertFalse(k.ki_buchen(UID, 99, 4, tag="2027-01-07")[0])  # Monatsgrenze
        self.assertTrue(k.ki_buchen(UID, 99, 4, tag="2027-02-01")[0])


_ms = k._ms

if __name__ == "__main__":
    unittest.main()
