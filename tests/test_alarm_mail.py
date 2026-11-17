"""Ausloese-Regeln fuer E-Mail-Alarme (DAT-002) ohne echten Versand.

Aufruf: /opt/investtimer-push/bin/python -m unittest tests/test_alarm_mail.py
Nachgebaut: Resend (nimmt Mails an und zeichnet sie auf) und die Wertquelle.
"""
import http.server, json, os, sys, tempfile, threading, unittest

TMP = tempfile.mkdtemp()
os.environ.update(INVESTTIMER_ALARME_DB=os.path.join(TMP, "a.db"), INVESTTIMER_ABMELDE_KEY=os.path.join(TMP, "k"),
                  INVESTTIMER_KONTO_DB=os.path.join(TMP, "k.db"), INVESTTIMER_RESEND_KEY=os.path.join(TMP, "rk"),
                  IT_RESEND_API="http://127.0.0.1:12121", STRESS_INTERN_URL="http://127.0.0.1:12121/wert",
                  INVESTTIMER_API_ENV=os.path.join(TMP, "env"))
open(os.environ["INVESTTIMER_RESEND_KEY"], "w").write("re_test")
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "volafly-api")); sys.path.insert(0, os.path.join(HIER, "..", "server"))
os.environ["INVESTTIMER_API_DIR"] = os.path.join(HIER, "..", "volafly-api")
import investtimer_alarme as alarme  # noqa: E402
import push_senden  # noqa: E402

MAILS, WERT = [], {"rounded": 50}


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _antwort(self, d):
        b = json.dumps(d).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._antwort(WERT)
    def do_POST(self):
        MAILS.append(json.loads(self.rfile.read(int(self.headers["Content-Length"])))); self._antwort({"id": "m"})


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 12121), Fake)
threading.Thread(target=srv.serve_forever, daemon=True).start()


class AlarmMail(unittest.TestCase):
    def lauf(self, wert):
        WERT["rounded"] = wert; push_senden.pruefen()

    def test_regeln(self):
        alarme.neu("u1", "ueber", 60, "email", "a@b.de")
        alarme.neu("u2", "unter", 40, "email", "c@d.de")
        alarme.neu("u3", "ueber", 60, "push")          # ohne Geraet: nichts
        p = alarme.neu("u4", "ueber", 60, "email", "e@f.de")["alarme"][0]["id"]
        alarme.aendern("u4", p, aktiv=False)           # pausiert: nichts
        self.lauf(55)                                  # erster Lauf merkt nur den Wert
        self.assertEqual(MAILS, [])
        self.lauf(58); self.assertEqual(MAILS, [])     # keine Schwelle gekreuzt
        self.lauf(62)
        self.assertEqual([m["to"] for m in MAILS], [["a@b.de"]])
        m = MAILS[0]
        self.assertEqual(m["subject"], "Marktstress bei 62: über deiner Schwelle von 60")
        self.assertIn("InvestTimer Alarm <alarm@investtimer.net>", m["from"])
        self.assertIn("keine Anlageberatung", m["text"])
        self.assertTrue(m["headers"]["List-Unsubscribe"].startswith("<https://investtimer.net/api/alarm-abmelden?a="))
        self.assertEqual(m["headers"]["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.lauf(55); self.lauf(63)                   # am selben Tag erneut gekreuzt: keine zweite Mail
        self.assertEqual(len(MAILS), 1)
        self.lauf(38)                                  # unter 40 gekreuzt
        self.assertEqual([x["to"] for x in MAILS[1:]], [["c@d.de"]])
        self.assertIn("unter deiner Schwelle von 40", MAILS[1]["subject"])


class Ueberqueren(unittest.TestCase):
    """Ausloese-Logik (gleich fuer Push und E-Mail; hier ueber den E-Mail-Kanal beobachtet)."""

    def setUp(self):
        with alarme.verbinden() as db:
            for t in ("alarme", "geraete", "stand"):
                db.execute("DELETE FROM " + t)
        MAILS.clear()

    def lauf(self, *werte):
        for w in werte:
            WERT["rounded"] = w; push_senden.pruefen()
        return len(MAILS)

    def neu(self, richtung, x, stand=None):
        if stand is not None:
            alarme.stand("letzter_wert", stand)
        return alarme.neu("u", richtung, x, "email", "a@b.de")["alarme"][-1]

    def test_ueberqueren_ueber(self):
        a = self.neu("ueber", 60, stand=55)
        self.assertTrue(a["scharf"])
        self.assertEqual(self.lauf(60), 0)            # Schwelle erreicht, aber nicht ueberschritten
        self.assertEqual(self.lauf(61), 1)            # von <= 60 auf > 60
        self.assertIn("Marktstress bei 61: über deiner Schwelle von 60", MAILS[0]["subject"])

    def test_ueberqueren_unter(self):
        self.neu("unter", 40, stand=45)
        self.assertEqual(self.lauf(40), 0)
        self.assertEqual(self.lauf(39), 1)

    def test_speichern_jenseits_wartet(self):
        a = self.neu("ueber", 60, stand=70)
        self.assertFalse(a["scharf"])                 # wartet auf Ruecklauf, keine sofortige Nachricht
        self.assertEqual(self.lauf(72, 65), 0)
        self.assertEqual(self.lauf(60), 0)            # Ruecklauf: Schwelle erreicht -> wieder scharf
        self.assertTrue(alarme.liste("u")["alarme"][0]["scharf"])
        self.assertEqual(self.lauf(61), 1)

    def test_ruecklauf_und_erneut_naechster_tag(self):
        self.neu("ueber", 60, stand=50)
        self.assertEqual(self.lauf(62), 1)
        self.assertFalse(alarme.liste("u")["alarme"][0]["scharf"])
        self.assertEqual(self.lauf(64, 61), 1)        # bleibt drueber: nichts
        with alarme.verbinden() as db:                # ein Tag spaeter
            db.execute("UPDATE alarme SET ausgeloest_am='2000-01-01'")
        self.assertEqual(self.lauf(58, 63), 2)        # Ruecklauf, erneutes Ueberqueren -> zweite Nachricht

    def test_pendeln_am_selben_tag(self):
        self.neu("ueber", 60, stand=59)
        self.assertEqual(self.lauf(61, 59, 61, 60, 62, 58, 61), 1)   # nur eine Nachricht am Tag

    def test_wieder_einschalten_wie_neu(self):
        a = self.neu("unter", 40, stand=45)
        alarme.aendern("u", a["id"], aktiv=False)
        alarme.stand("letzter_wert", 30)
        alarme.aendern("u", a["id"], aktiv=True)
        self.assertFalse(alarme.liste("u")["alarme"][0]["scharf"])   # schon darunter: wartet


if __name__ == "__main__":
    unittest.main()
