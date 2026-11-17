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


RESEND_KEY = os.environ.get("INVESTTIMER_RESEND_KEY", "/root/.investtimer/resend-key")
RESEND_API = os.environ.get("IT_RESEND_API", "https://api.resend.com")
SEITE = "https://investtimer.net"
ABSENDER = "InvestTimer Alarm <alarm@investtimer.net>"


def mail_senden(alarm, betreff, satz):
    """E-Mail-Alarm (DAT-002) an die Konto-Adresse, mit Abmeldelink ohne Login und One-Click-Abmeldung."""
    import html
    import requests
    try:
        key = open(RESEND_KEY).read().strip()
    except OSError:
        print("[mail] Resend-Schluessel fehlt", flush=True)
        return False
    abmelden = "%s/api/alarm-abmelden?a=%d&t=%s" % (SEITE, alarm["id"], alarme.abmelde_token(alarm["id"], alarm["uid"]))
    richtung = "über" if alarm["richtung"] == "ueber" else "unter"
    text = ("%s\n\nDu hast für den Marktstress einen Alarm %s %d eingerichtet. Den aktuellen Stand und die Einordnung siehst du auf %s\n\n"
            "Der Hinweis beschreibt nur den Stand des Marktstress-Werts. Er ist keine Anlageberatung und keine Empfehlung zum Kauf oder Verkauf.\n\n"
            "Keine E-Mails mehr zu diesem Alarm: %s\nAlle Alarme verwalten: %s (Marktstress abonnieren)\n\nInvestTimer · investtimer.net"
            % (satz, richtung, alarm["schwelle"], SEITE, abmelden, SEITE))
    e = html.escape
    inhalt = ('<div style="font:15px/1.6 -apple-system,Segoe UI,Arial,sans-serif;color:#1c2f2b;max-width:560px">'
              '<p style="font-size:20px;font-weight:600;margin:0 0 12px">%s</p>'
              '<p>Du hast für den Marktstress einen Alarm %s %d eingerichtet. Den aktuellen Stand und die Einordnung siehst du auf '
              '<a href="%s" style="color:#2f6b5c">investtimer.net</a>.</p>'
              '<p style="font-size:13px;color:#5b6b66">Der Hinweis beschreibt nur den Stand des Marktstress-Werts. Er ist keine Anlageberatung '
              'und keine Empfehlung zum Kauf oder Verkauf.</p>'
              '<p style="font-size:13px;color:#5b6b66;border-top:1px solid #dfe5dc;padding-top:12px">'
              '<a href="%s" style="color:#5b6b66">Keine E-Mails mehr zu diesem Alarm</a> · Alle Alarme verwaltest du auf investtimer.net unter „Marktstress abonnieren“.</p>'
              '</div>') % (e(satz), richtung, alarm["schwelle"], SEITE, e(abmelden))
    try:
        r = requests.post(RESEND_API + "/emails", timeout=15, headers={"Authorization": "Bearer " + key}, json={
            "from": ABSENDER, "to": [alarm["email"]], "reply_to": "info@investtimer.net", "subject": betreff,
            "text": text, "html": inhalt,
            "headers": {"List-Unsubscribe": "<%s>" % abmelden, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}})
    except Exception as fehler:
        print("[mail] Fehler: %s" % type(fehler).__name__, flush=True)
        return False
    if r.status_code >= 300:
        print("[mail] Resend %s %s" % (r.status_code, (r.json() if r.content else {}).get("name")), flush=True)
        return False
    return True


APNS = os.environ.get("INVESTTIMER_APNS", "/root/.investtimer/apns.json")
_apns_jwt = {"t": 0, "jwt": None}


def _b64(b):
    import base64
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _apns_token(k):
    """JWT (ES256) fuer APNs, hoechstens 50 Minuten wiederverwenden."""
    import time
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    if _apns_jwt["jwt"] and time.time() - _apns_jwt["t"] < 3000:
        return _apns_jwt["jwt"]
    with open(k["p8"], "rb") as f:
        schluessel = serialization.load_pem_private_key(f.read(), password=None)
    jetzt = int(time.time())
    kopf = _b64(json.dumps({"alg": "ES256", "kid": k["key_id"]}).encode()) + "." + _b64(json.dumps({"iss": k["team_id"], "iat": jetzt}).encode())
    r, s = decode_dss_signature(schluessel.sign(kopf.encode(), ec.ECDSA(hashes.SHA256())))
    _apns_jwt.update(t=jetzt, jwt=kopf + "." + _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big")))
    return _apns_jwt["jwt"]


def senden_apns(geraet, nachricht):
    """iOS-App: Mitteilung ueber Apple Push (HTTP/2). Ohne Schluessel: nicht zustellbar (None)."""
    try:
        with open(APNS) as f:
            k = json.load(f)
    except (OSError, ValueError):
        print("[push] APNs nicht eingerichtet", flush=True)
        return None
    import httpx
    host = "api.sandbox.push.apple.com" if k.get("sandbox") else "api.push.apple.com"
    token = geraet["endpoint"].split(":", 1)[1]
    daten = {"aps": {"alert": {"title": nachricht.get("title", "InvestTimer"), "body": nachricht.get("body", "")},
                     "sound": "default", "thread-id": nachricht.get("tag", "investtimer")}, "url": nachricht.get("url", "/")}
    try:
        with httpx.Client(http2=True, timeout=15) as c:
            r = c.post("https://%s/3/device/%s" % (host, token), json=daten,
                       headers={"authorization": "bearer " + _apns_token(k), "apns-topic": k.get("bundle", "net.investtimer.app"),
                                "apns-push-type": "alert", "apns-priority": "10", "apns-expiration": str(int(__import__("time").time()) + 12 * 3600),
                                "apns-collapse-id": nachricht.get("tag", "investtimer")[:64]})
    except Exception as fehler:
        print("[push] APNs Fehler: %s" % type(fehler).__name__, flush=True)
        return None
    if r.status_code == 200:
        return True
    grund = (r.json() if r.content else {}).get("reason")
    if r.status_code == 410 or grund in ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"):
        alarme.geraet_entfernen(geraet["endpoint"])
        return False
    print("[push] APNs %s %s" % (r.status_code, grund), flush=True)
    return None


def senden(geraet, nachricht):
    """True = zugestellt, False = Geraet abgemeldet (entfernt), None = voruebergehender Fehler."""
    if geraet["endpoint"].startswith("apns:"):
        return senden_apns(geraet, nachricht)
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


def test(uid, kennung=None):
    """Testnachricht. Ausgabe als JSON (eine Zeile), damit die API das Ergebnis an die Seite melden kann."""
    geraete = alarme.geraete(uid)
    ergebnis = [senden(g, {"title": "InvestTimer", "body": "Push ist eingerichtet. So sieht ein Hinweis zu deiner Schwelle aus.",
                           "tag": "investtimer-test", "url": "/", "id": kennung}) for g in geraete]
    aus = {"geraete": len(geraete), "angenommen": ergebnis.count(True), "abgemeldet": ergebnis.count(False),
           "fehler": ergebnis.count(None)}
    print(json.dumps(aus), flush=True)
    return aus["angenommen"]


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
    tag = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    ausgeloest = zugestellt = mails = 0
    pflicht = premium_pflicht()
    for a in alarme.aktive_alarme():
        if pflicht and not konto.ist_premium(a["uid"]):
            continue
        s = a["schwelle"]
        # Ueberqueren mit Ruecklauf: scharf solange der Wert auf der Ausgangsseite liegt (<= X bzw. >= X).
        # Ein scharfer Alarm loest aus, sobald der Wert > X (bzw. < X) ist, und wartet dann auf den Ruecklauf.
        if not a["scharf"]:
            if alarme.scharf_bei(a["richtung"], s, jetzt):
                alarme.scharf_setzen(a["id"], True)
            continue
        if not alarme.ausgeloest_bei(a["richtung"], s, jetzt):
            continue
        alarme.scharf_setzen(a["id"], False)
        if a["ausgeloest_am"] == tag:  # hoechstens eine Nachricht je Alarm und Tag (Pendeln um die Schwelle)
            continue
        text = ("Marktstress bei %d: über deiner Schwelle von %d." if a["richtung"] == "ueber"
                else "Marktstress bei %d: unter deiner Schwelle von %d.") % (jetzt, s)
        kanal = a.get("kanal") or "push"
        ok = 0
        if kanal in ("push", "beide"):
            ok, _ = an_nutzer(a["uid"], {"title": "InvestTimer", "body": text, "tag": "investtimer-alarm-%d" % a["id"], "url": "/"})
        if kanal in ("email", "beide") and a.get("email"):
            if mail_senden(a, text.rstrip("."), text):
                ok += 1
                mails += 1
        if ok:
            alarme.ausgeloest(a["id"], tag)
            ausgeloest += 1
            zugestellt += ok
    if ausgeloest or vorher != jetzt:
        print("[push] Wert %d -> %d: %d Alarme ausgeloest, %d Nachrichten (davon %d E-Mails)" % (vorher, jetzt, ausgeloest, zugestellt, mails), flush=True)


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--test":
        sys.exit(0 if test(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None) else 1)
    pruefen()
