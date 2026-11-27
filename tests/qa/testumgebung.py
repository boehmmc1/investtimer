#!/usr/bin/env python3
"""QA – Testumgebung test.investtimer.net (Nachtrag N5, 27.11.2026).
- Ein kurzlebiges Testkonto (Supabase-Admin-API, wird am Ende immer geloescht) ruft die API der Testumgebung mit seinem Bearer-Token
  auf: Konto-Status muss 200 liefern. Hintergrund: Bearer-Token und Basic-Auth kollidierten (Anmeldefehler auf test), deshalb
  laufen alle /api/-Locations ohne Basic-Auth ("auth_basic off; allow all;").
- Kontoloeschung (Nachtrag N4): nach POST /api/konto/loeschen wird der alte Token sofort abgewiesen (401).
- Grenze: Dieser Server steht selbst in der IP-Freigabe der Testumgebung (satisfy any). Ein Aufruf von hier beweist daher nicht,
  dass Basic-Auth fuer /api/ abgeschaltet ist. Das prueft der zweite Teil an der ausgerollten nginx-Konfiguration: jede /api/-Location
  hat "auth_basic off" und "allow all", die Seite selbst bleibt hinter Basic-Auth. Ein echter Aufruf von aussen ist von diesem
  Server aus nicht moeglich (test.investtimer.net hat nur die IPv4-Adresse dieses Servers).
Aufruf: python3 tests/qa/testumgebung.py (laeuft in tools/qa_gesamt.sh und naechtlich ueber investtimer-qa-test.timer).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import melde, http, testkonto, aufraeumen, bearer, ende  # noqa: E402

B = "1 Funktion"
TEST = os.environ.get("QA_TEST_SEITE", "https://test.investtimer.net").rstrip("/")
NGINX = Path("/etc/nginx/sites-available/investtimer-test")


def bearer_auf_test():
    k = testkonto()
    c, d, _ = http("GET", TEST + "/api/konto", kopf=bearer(k["token"]))
    melde(B, "Testumgebung: Konto-Status mit Bearer-Token eines Testkontos", c == 200 and isinstance(d, dict) and "status" in d,
          "hoch", "GET %s/api/konto" % TEST, (c, str(d)[:160]))
    c, _, _ = http("GET", TEST + "/api/konto")
    melde(B, "Testumgebung: Konto-Status ohne Token abgelehnt", c == 401, "hoch", "GET /api/konto ohne Token", c)
    # Kontoloeschung: alter Token sofort ungueltig
    c, d, _ = http("POST", TEST + "/api/konto/loeschen", {"bestaetigung": "löschen"}, bearer(k["token"]))
    melde(B, "Testumgebung: Konto loeschen ueber die API", c == 200, "hoch", "POST /api/konto/loeschen", (c, str(d)[:160]))
    c, _, _ = http("GET", TEST + "/api/konto", kopf=bearer(k["token"]))
    melde(B, "Testumgebung: alter Token nach der Kontoloeschung abgewiesen (401)", c == 401, "hoch", "GET /api/konto mit Token des geloeschten Kontos", c)


def nginx_konfiguration():
    if not NGINX.exists():
        melde(B, "Testumgebung: nginx-Konfiguration vorhanden", False, "mittel", str(NGINX), "fehlt")
        return
    s = NGINX.read_text()
    bloecke = re.findall(r"\n    location (?:= |~ \^|\^~ )?(/api/[^\n{]*)\{(.*?)\n    \}", s, re.S)
    ohne = [pfad.strip() for pfad, inhalt in bloecke if "auth_basic off;" not in inhalt or "allow all;" not in inhalt]
    melde(B, "Testumgebung: jede /api/-Location ohne Basic-Auth (Bearer gegen Basic)", bloecke and not ohne, "hoch", str(NGINX),
          "%d Locations, ohne Ausnahme: %s" % (len(bloecke), ohne))
    kopf = s[:s.index("location")]
    melde(B, "Testumgebung: Seite selbst hinter Basic-Auth", "auth_basic \"" in kopf and "deny all;" in kopf, "hoch", str(NGINX), "")


def main():
    for f in (bearer_auf_test, nginx_konfiguration):
        try:
            f()
        except Exception as e:
            melde(B, "Pruefblock %s durchgelaufen" % f.__name__, False, "hoch", "tests/qa/testumgebung.py", "%s: %s" % (type(e).__name__, e))
        finally:
            aufraeumen()
    return ende()


if __name__ == "__main__":
    sys.exit(main())
