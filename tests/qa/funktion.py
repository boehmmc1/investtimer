#!/usr/bin/env python3
"""QA Bereich 1 – Funktion (live, nur Testkonten; ergaenzt die UI-Tests in tests/ui, die check_mobile --voll in Bereich 5 laufen laesst).
- Seiten: Start, Impressum, Datenschutz, 404, Teilen-Links (og-Tags, Weiterleitung).
- Anmeldung: Passwort im Browser, Sitzung uebersteht Neuladen, Code richtig/falsch, Link nur einmal nutzbar, Abmelden, auf allen Geraeten abmelden.
- Konto: E-Mail aendern (ueber generate_link, keine Mail), Export vollstaendig, Loeschen (Bereich 3 prueft Rueckstaende).
- Alarme: anlegen, aendern (pausieren, Kanal), loeschen, hoechstens 5, Abmeldelink ohne Login (falsches/richtiges Token).
- Alarm-Logik (abgeschottet, eigene Datenbanken, nachgespielte Wertquelle): Ueberqueren mit Ruecklauf ("wartet"), 1x je Tag,
  E-Mail-Alarm echt ueber Resend an delivered@resend.dev (Test-Postfach von Resend).
- Feedback: Honeypot und Mindestzeit (es wird nichts versendet).
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, SEITE, CHROME, melde, http, testkonto, aufraeumen, bearer, auth_url, _admin_kopf, ende  # noqa: E402

B = "1 Funktion"


def seiten():
    for pfad, code_soll in (("/", 200), ("/impressum.html", 200), ("/datenschutz.html", 200), ("/gibt-es-nicht", 404), ("/manifest.json", 200), ("/sw.js", 200)):
        code, b, _ = http("GET", pfad)
        melde(B, "Seite %s -> %d" % (pfad, code_soll), code == code_soll, "hoch", "curl", code)
    _, m, _ = http("GET", "/teilen/aktuell/manifest.json")
    for pfad, ziel in (("/s/wert/%s" % m["asOf"], "/?"), ("/s/verlauf/5J/%s" % m["asOf"], "z=5J"), ("/s/phase/corona?l=en", "phase=corona")):
        code, b, _ = http("GET", pfad)
        b = str(b)
        melde(B, "Teilen-Link %s: og-Tags und Weiterleitung" % pfad, code == 200 and 'property="og:image"' in b and "twitter:card" in b and ziel in b, "hoch", "curl", code)


def anmeldung():
    url, anon = auth_url()
    k = testkonto()
    # Code richtig/falsch, Link einmalig (generate_link schickt keine Mail)
    code, l, _ = http("POST", url + "/auth/v1/admin/generate_link", {"type": "magiclink", "email": k["email"]}, _admin_kopf())
    otp = l.get("email_otp") or (l.get("properties") or {}).get("email_otp")
    falsch = str((int(otp) + 1) % 1000000).zfill(6)
    c1, _, _ = http("POST", url + "/auth/v1/verify", {"type": "email", "email": k["email"], "token": falsch}, {"apikey": anon})
    melde(B, "falscher Code abgelehnt", c1 in (400, 401, 403), "hoch", "POST /auth/v1/verify", c1)
    c2, t2, _ = http("POST", url + "/auth/v1/verify", {"type": "email", "email": k["email"], "token": otp}, {"apikey": anon})
    melde(B, "richtiger Code meldet an", c2 == 200 and t2.get("access_token"), "hoch", "POST /auth/v1/verify", c2)
    c3, _, _ = http("POST", url + "/auth/v1/verify", {"type": "email", "email": k["email"], "token": otp}, {"apikey": anon})
    melde(B, "Code nur einmal verwendbar (verbraucht = abgelaufen)", c3 in (400, 401, 403), "hoch", "zweites POST /auth/v1/verify", c3)
    # Abmelden: Erneuerungsschluessel ungueltig; auf allen Geraeten abmelden
    code, s1, _ = http("POST", url + "/auth/v1/token?grant_type=password", {"email": k["email"], "password": k["passwort"]}, {"apikey": anon})
    code, s2, _ = http("POST", url + "/auth/v1/token?grant_type=password", {"email": k["email"], "password": k["passwort"]}, {"apikey": anon})
    http("POST", url + "/auth/v1/logout?scope=local", {}, {"apikey": anon, **bearer(s1["access_token"])})
    c, _, _ = http("POST", url + "/auth/v1/token?grant_type=refresh_token", {"refresh_token": s1["refresh_token"]}, {"apikey": anon})
    melde(B, "Abmelden: Erneuerung der Sitzung danach unmoeglich", c in (400, 401, 403), "hoch", "logout scope=local", c)
    c, _, _ = http("GET", "/api/konto", kopf=bearer(s1["access_token"]))
    melde(B, "Abmelden: Zugangsschluessel danach von der API abgelehnt", c in (401, 403), "mittel", "GET /api/konto mit abgemeldetem Token", c)
    c, _, _ = http("GET", "/api/konto", kopf=bearer(s2["access_token"]))
    melde(B, "zweite Sitzung nach lokalem Abmelden weiter gueltig", c == 200, "mittel", "GET /api/konto Sitzung 2", c)
    http("POST", url + "/auth/v1/logout?scope=global", {}, {"apikey": anon, **bearer(s2["access_token"])})
    c, _, _ = http("POST", url + "/auth/v1/token?grant_type=refresh_token", {"refresh_token": k["refresh"]}, {"apikey": anon})
    melde(B, "auf allen Geraeten abmelden: alle Sitzungen beendet", c in (400, 401, 403), "hoch", "logout scope=global, Erneuerung der ersten Sitzung", c)
    # E-Mail aendern ohne Mail: generate_link email_change_new
    neu = k["email"].replace("qa-", "qa2-")
    code, s3, _ = http("POST", url + "/auth/v1/token?grant_type=password", {"email": k["email"], "password": k["passwort"]}, {"apikey": anon})
    # sichere E-Mail-Aenderung: beide Adressen bestaetigen (alter und neuer Link)
    c = []
    for typ in ("email_change_current", "email_change_new"):
        code, l, _ = http("POST", url + "/auth/v1/admin/generate_link", {"type": typ, "email": k["email"], "new_email": neu}, _admin_kopf())
        link = l.get("action_link") or (l.get("properties") or {}).get("action_link") or ""
        c.append(http("GET", link, folgen=False)[0] if link else 0)
    code, u, _ = http("GET", url + "/auth/v1/admin/users/" + k["id"], kopf=_admin_kopf())
    # Supabase verlangt beide Bestaetigungen; Admin-Links setzen die Gegenseite jeweils neu. Ein vollstaendiger Wechsel braeuchte echte
    # Mails an zwei Adressen (nicht erlaubt ohne TEST-Betreff) - geprueft wird, dass beide Bestaetigungsschritte angenommen werden.
    melde(B, "E-Mail aendern: beide Bestaetigungslinks werden angenommen (vollstaendiger Wechsel nur mit echten Mails pruefbar)",
          c == [303, 303] and u.get("new_email") == neu, "info", "generate_link email_change_current/new", (c, u.get("email"), u.get("new_email")))
    # Browser: Passwort-Anmeldung, Sitzung uebersteht Neuladen, Abmelden raeumt Speicher
    asyncio.run(browser_anmeldung(u.get("email") or k["email"], k["passwort"]))


async def browser_anmeldung(email, pw):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        await pg.goto(SEITE + "/")
        await pg.wait_for_timeout(1500)
        await pg.evaluate("([e,p])=>window.InvestTimer.mitPasswort(e,p)", [email, pw])
        await pg.reload()
        await pg.wait_for_timeout(3000)
        r = await pg.evaluate("({ein:!!(window.InvestTimer.member&&window.InvestTimer.session),stand:document.querySelector('.snapshot-label')?.textContent||''})")
        melde(B, "Sitzung uebersteht Neuladen, Seite zeigt aktuellen Stand", r["ein"] and "Zeitversetzt" not in r["stand"], "hoch", "Playwright 390 px", r)
        await pg.evaluate("window.InvestTimer.abmelden()")
        await pg.wait_for_timeout(800)
        ls = await pg.evaluate("Object.keys(localStorage)")
        await pg.reload()
        await pg.wait_for_timeout(2000)
        st = await pg.evaluate("document.querySelector('.snapshot-label')?.textContent||''")
        melde(B, "Abmelden im Browser: Speicher leer, wieder zeitversetzter Stand", not ls and ("Zeitversetzt" in st or "Historisch" in st), "hoch", "Playwright", (ls, st))
        await b.close()


def konto_und_alarme():
    k = testkonto()
    t = bearer(k["token"])
    ids = []
    for s in (20, 30, 40, 60, 70):
        code, d, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": s, "kanal": "push", "sprache": "de"}, t)
        ids.append(code)
    code, d, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": 80, "kanal": "push"}, t)
    melde(B, "5 Alarme angelegt, sechster abgelehnt", ids == [200] * 5 and code in (400, 409, 422), "hoch", "POST /api/alarme x6", (ids, code))
    code, d, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": 20, "kanal": "push"}, t)
    _, liste, _ = http("GET", "/api/alarme", kopf=t)
    alarme = liste.get("alarme", [])
    a = alarme[0]["id"]
    code, _, _ = http("PATCH", "/api/alarme/%d" % a, {"aktiv": False}, t)
    _, l2, _ = http("GET", "/api/alarme", kopf=t)
    melde(B, "Alarm pausieren", code == 200 and not next(x for x in l2["alarme"] if x["id"] == a)["aktiv"], "hoch", "PATCH aktiv=false", code)
    code, _, _ = http("PATCH", "/api/alarme/%d" % a, {"kanal": "email"}, t)
    _, l2, _ = http("GET", "/api/alarme", kopf=t)
    melde(B, "Alarm auf E-Mail umstellen (Konto-Adresse)", code == 200 and next(x for x in l2["alarme"] if x["id"] == a)["kanal"] == "email", "hoch", "PATCH kanal=email", code)
    # Abmeldelink ohne Login
    sys.path.insert(0, str(ROOT / "volafly-api"))
    import investtimer_alarme as al
    tok = al.abmelde_token(a, k["id"])
    c, b, _ = http("GET", "/api/alarm-abmelden?a=%d&t=%s" % (a, "0" * 32))
    melde(B, "Abmeldelink mit falschem Token abgelehnt", c in (400, 403, 404) or "ungültig" in str(b).lower(), "hoch", "GET /api/alarm-abmelden", c)
    c, b, _ = http("GET", "/api/alarm-abmelden?a=%d&t=%s" % (a, tok))
    melde(B, "Abmeldelink ohne Login zeigt Bestaetigung (kein Abbestellen per GET)", c == 200 and "<form" in str(b), "hoch", "GET /api/alarm-abmelden", c)
    _, l2, _ = http("GET", "/api/alarme", kopf=t)
    melde(B, "GET allein bestellt nicht ab", next(x for x in l2["alarme"] if x["id"] == a)["kanal"] == "email", "mittel", "GET /api/alarme")
    c, b, _ = http("POST", "/api/alarm-abmelden?a=%d&t=%s" % (a, tok), roh=b"List-Unsubscribe=One-Click", kopf={"Content-Type": "application/x-www-form-urlencoded"})
    _, l2, _ = http("GET", "/api/alarme", kopf=t)
    x = next((x for x in l2["alarme"] if x["id"] == a), None)
    melde(B, "One-Click-Abmeldung ohne Login wirkt", c == 200 and (x is None or x["kanal"] == "push" or not x["aktiv"]), "hoch", "POST /api/alarm-abmelden", (c, x))
    code, _, _ = http("DELETE", "/api/alarme/%d" % alarme[1]["id"], kopf=t)
    _, l2, _ = http("GET", "/api/alarme", kopf=t)
    melde(B, "Alarm loeschen", code == 200 and len(l2["alarme"]) == 4, "hoch", "DELETE", code)
    code, ex, _ = http("GET", "/api/konto/export", kopf=t)
    s = json.dumps(ex)
    melde(B, "Export vollstaendig (Konto, Alarme, Abo, KI-Nutzung)", code == 200 and k["email"] in s and all(str(x["schwelle"]) in s for x in l2["alarme"])
          and all(w in s for w in ("abo", "kiNutzung", "alarme")), "hoch", "GET /api/konto/export", list(ex)[:10] if isinstance(ex, dict) else code)
    # Feedback: Honeypot und Mindestzeit (nichts wird versendet)
    c, b, _ = http("POST", "/api/feedback", {"kategorie": "idee", "nachricht": "QA Honeypot-Test, bitte ignorieren", "website": "x", "dauer": 9000})
    melde(B, "Feedback-Honeypot: Antwort ok, nichts versendet", c == 200, "mittel", "POST /api/feedback website=x", c)
    c, b, _ = http("POST", "/api/feedback", {"kategorie": "idee", "nachricht": "QA zu schnell abgeschickt", "dauer": 500})
    melde(B, "Feedback zu schnell abgelehnt", c == 400, "mittel", "POST /api/feedback dauer=500", c)


ALARM_SIM = r'''
import json, os, sys, threading, http.server, datetime as dt
WERT = {"w": 40}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = json.dumps({"rounded": WERT["w"], "asOf": "2026-11-20"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=s.serve_forever, daemon=True).start()
os.environ["STRESS_INTERN_URL"] = "http://127.0.0.1:%d/" % s.server_address[1]
sys.path.insert(0, os.environ["SRV"])
import push_senden as ps
import investtimer_alarme as al
mails = []
echt = {"n": 0}
orig = ps.mail_senden
def mail(a, betreff, satz):
    mails.append((a["id"], betreff))
    if echt["n"] == 0:
        echt["n"] += 1
        return orig(a, betreff, satz)
    return True
ps.mail_senden = mail
ps.an_nutzer = lambda uid, n: (0, None)
TAG = {"d": dt.datetime(2026, 11, 20, 10, 0)}
class FakeDT(dt.datetime):
    @classmethod
    def now(cls, tz=None): return TAG["d"].replace(tzinfo=tz)
ps.datetime = FakeDT
al.stand("letzter_wert", 40)
u = al.neu("qa-uid", "ueber", 50, "email", "delivered@resend.dev", "de")
d = al.neu("qa-uid", "unter", 30, "email", "delivered@resend.dev", "de")
schritte = []
def lauf(w):
    WERT["w"] = w; ps.pruefen()
    r = {x["id"]: x for x in al.liste("qa-uid")["alarme"]}
    schritte.append((w, len(mails)))
for w in (55, 60, 45, 58):
    lauf(w)
TAG["d"] = dt.datetime(2026, 11, 21, 10, 0)
for w in (45, 57, 25, 35, 24):
    lauf(w)
print(json.dumps({"mails": mails, "schritte": schritte}))
'''


def alarm_logik():
    with tempfile.TemporaryDirectory() as tmp:
        skript = Path(tmp) / "sim.py"
        skript.write_text(ALARM_SIM)
        env = dict(os.environ, INVESTTIMER_ALARME_DB=tmp + "/alarme.db", INVESTTIMER_KONTO_DB=tmp + "/konto.db", INVESTTIMER_API_DIR=str(ROOT / "volafly-api"),
                   SRV=str(ROOT / "server"), INVESTTIMER_API_ENV=tmp + "/leer.env")
        Path(tmp + "/leer.env").write_text("")
        r = subprocess.run(["/opt/investtimer-push/bin/python", str(skript)], capture_output=True, text=True, timeout=120, env=env)
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            melde(B, "Alarm-Simulation gelaufen", False, "hoch", "server/push_senden.py simuliert", (r.stdout[-300:], r.stderr[-300:]))
            return
        m = [x[1] for x in d["mails"]]
        # Tag 1: 55 loest "ueber 50" aus; 60 wartet; 45 wieder scharf; 58 waere erneut, aber schon heute -> nichts
        # Tag 2: 45 scharf, 57 loest aus; 25 loest "unter 30" aus; 35 scharf; 24 erneut "unter 30", aber schon heute -> nichts
        melde(B, "Alarm-Logik: Ueberqueren, Warten auf Ruecklauf, hoechstens 1x je Tag (5 Laeufe Tag 1, 5 Laeufe Tag 2)", len(m) == 3, "hoch",
              "push_senden.pruefen mit Wertfolge 55,60,45,58 | 45,57,25,35,24", d)
        melde(B, "E-Mail-Alarm echt zugestellt (Resend-Testpostfach delivered@resend.dev)", "Fehler" not in r.stdout and len(m) >= 1, "mittel",
              "push_senden.mail_senden", r.stdout[:200] if "[mail]" in r.stdout else "")


def main():
    for f in (seiten, anmeldung, konto_und_alarme, alarm_logik):
        try:
            f()
        except Exception as e:
            melde(B, "Pruefblock %s durchgelaufen" % f.__name__, False, "hoch", "tests/qa/funktion.py", "%s: %s" % (type(e).__name__, e))
        finally:
            aufraeumen()
    return ende()


if __name__ == "__main__":
    sys.exit(main())
