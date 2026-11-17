#!/usr/bin/env python3
"""Push-Benachrichtigungen fuer InvestTimer-Alarme (eigene Schwelle).

Laeuft nach jeder Datenaktualisierung (investtimer-data.service, ExecStartPost)
mit der Python-Umgebung /opt/investtimer-push (pywebpush).

  push_senden.py              Schwellen pruefen und ausloesen
  push_senden.py --test UID   Testnachricht an alle Geraete eines Nutzers

Ausgeloest wird nur beim Ueberschreiten: "ueber 50" feuert, wenn der Wert von
unter 50 auf 50 oder mehr steigt, "unter 30", wenn er von ueber 30 auf 30 oder
weniger faellt. Hoechstens einmal je Alarm und Tag (Berliner Zeit). Der Text
beschreibt nur den Stand, ohne Handlungsempfehlung.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.environ.get("INVESTTIMER_API_DIR", "/root/volafly-chat"))
import investtimer_alarme as alarme  # noqa: E402
import investtimer_konto as konto  # noqa: E402
from pywebpush import WebPushException, webpush  # noqa: E402

QUELLE = os.environ.get("STRESS_INTERN_URL", "http://127.0.0.1:8100/v1/marktstress")
VAPID_SCHLUESSEL = os.environ.get("VAPID_PRIVATE", "/root/.investtimer/vapid-private.pem")
VAPID_KONTAKT = {"sub": "mailto:info@investtimer.net"}


def premium_pflicht():
    """Gleicher Schalter wie in der API: mit IT_PREMIUM_PFLICHT=1 bekommen nur Premium-Konten Alarme."""
    try:
        for zeile in open(os.environ.get("INVESTTIMER_API_ENV", "/root/volafly-chat/.env")):
            if zeile.strip().startswith("IT_PREMIUM_PFLICHT="):
                return zeile.split("=", 1)[1].strip() == "1"
    except OSError:
        pass
    return False


def senden(geraet, nachricht):
    """True = zugestellt, False = Geraet abgemeldet (entfernt), None = voruebergehender Fehler."""
    try:
        webpush({"endpoint": geraet["endpoint"], "keys": {"p256dh": geraet["p256dh"], "auth": geraet["auth"]}},
                json.dumps(nachricht, ensure_ascii=False), vapid_private_key=VAPID_SCHLUESSEL,
                vapid_claims=dict(VAPID_KONTAKT), ttl=12 * 3600, timeout=15)
        return True
    except WebPushException as fehler:
        status = getattr(fehler.response, "status_code", None)
        if status in (403, 404, 410):
            alarme.geraet_entfernen(geraet["endpoint"])
            return False
        print("[push] Versand fehlgeschlagen: %s" % status, flush=True)
        return None


def an_nutzer(uid, nachricht):
    ergebnis = [senden(g, nachricht) for g in alarme.geraete(uid)]
    return ergebnis.count(True), ergebnis.count(False)


def test(uid):
    ok, weg = an_nutzer(uid, {"title": "InvestTimer", "body": "Push ist eingerichtet. So sieht ein Hinweis zu deiner Schwelle aus.",
                              "tag": "investtimer-test", "url": "/"})
    print("[push] Test: %d zugestellt, %d abgemeldet" % (ok, weg), flush=True)
    return ok


def pruefen():
    with urllib.request.urlopen(urllib.request.Request(QUELLE, headers={"User-Agent": "investtimer-push"}), timeout=30) as a:
        daten = json.load(a)
    jetzt = daten.get("rounded")
    if not isinstance(jetzt, int):
        print("[push] kein gueltiger Wert", flush=True)
        return
    vorher = alarme.stand("letzter_wert")
    alarme.stand("letzter_wert", jetzt)
    if vorher is None:
        print("[push] erster Lauf, Wert %d gemerkt" % jetzt, flush=True)
        return
    vorher = int(vorher)
    if vorher == jetzt:
        return
    tag = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    ausgeloest = zugestellt = 0
    pflicht = premium_pflicht()
    for a in alarme.aktive_alarme():
        if pflicht and not konto.ist_premium(a["uid"]):
            continue
        s = a["schwelle"]
        gekreuzt = (vorher < s <= jetzt) if a["richtung"] == "ueber" else (vorher > s >= jetzt)
        if not gekreuzt or a["ausgeloest_am"] == tag:
            continue
        text = ("Marktstress bei %d: über deiner Schwelle von %d." if a["richtung"] == "ueber"
                else "Marktstress bei %d: unter deiner Schwelle von %d.") % (jetzt, s)
        ok, _ = an_nutzer(a["uid"], {"title": "InvestTimer", "body": text, "tag": "investtimer-alarm-%d" % a["id"], "url": "/"})
        if ok:
            alarme.ausgeloest(a["id"], tag)
            ausgeloest += 1
            zugestellt += ok
    print("[push] Wert %d -> %d: %d Alarme ausgeloest, %d Nachrichten" % (vorher, jetzt, ausgeloest, zugestellt), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--test":
        sys.exit(0 if test(sys.argv[2]) else 1)
    pruefen()
