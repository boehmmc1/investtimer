#!/usr/bin/env python3
"""Echter Anmeldetest gegen Supabase und die Live-Seite, ohne Postfach.

Aufruf:  python3 deploy/supabase_test.py [https://investtimer.net] [--browser]

Legt einen Testnutzer ueber die Admin-API an, erzeugt Magic Link und Code mit
generate_link, prueft beide Wege (Link -> Weiterleitung mit Sitzung, Code ->
/auth/v1/verify), danach /api/aktuell und /api/chat mit dem Token und ohne.
Am Ende wird der Testnutzer geloescht. Der service_role-Schluessel wird nur zur
Laufzeit ueber die Management-API geholt und nirgends gespeichert oder ausgegeben.
"""
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_einrichten import API, token  # noqa: E402

SEITE = next((a for a in sys.argv[1:] if a.startswith("http")), "https://investtimer.net").rstrip("/")
AUTH = json.loads((Path(__file__).resolve().parent / "supabase.json").read_text())
REF = urllib.parse.urlparse(AUTH["url"]).hostname.split(".")[0]


def http(methode, url, daten=None, kopf=None, folgen=True):
    anfrage = urllib.request.Request(url, method=methode, data=None if daten is None else json.dumps(daten).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "investtimer-test", **(kopf or {})})
    oeffner = urllib.request.build_opener() if folgen else urllib.request.build_opener(KeinFolgen)
    try:
        with oeffner.open(anfrage, timeout=90) as a:
            text = a.read().decode()
            return a.status, (json.loads(text) if text[:1] in "{[" else text), dict(a.headers)
    except urllib.error.HTTPError as f:
        text = f.read().decode()
        return f.code, (json.loads(text) if text[:1] in "{[" else text), dict(f.headers)


class KeinFolgen(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def pruefe(name, bedingung, info=""):
    print(("ok    " if bedingung else "FEHLER") + "  " + name + (("  (" + info + ")") if info and not bedingung else ""))
    return bool(bedingung)


def main():
    _, schluessel, _ = http("GET", "%s/projects/%s/api-keys" % (API, REF), kopf={"Authorization": "Bearer " + token()})
    service = next(k["api_key"] for k in schluessel if k.get("name") == "service_role")
    admin = {"apikey": service, "Authorization": "Bearer " + service}
    anon = {"apikey": AUTH["anonKey"]}
    email = "it-test-%d@investtimer.net" % int(time.time())
    alles = True
    code, nutzer, _ = http("POST", AUTH["url"] + "/auth/v1/admin/users", {"email": email, "email_confirm": True}, admin)
    alles &= pruefe("Testnutzer angelegt", code == 200, str(nutzer)[:200])
    try:
        # Weg 1: Link
        code, link, _ = http("POST", AUTH["url"] + "/auth/v1/admin/generate_link",
                             {"type": "magiclink", "email": email, "redirect_to": SEITE + "/"}, admin)
        alles &= pruefe("Magic Link erzeugt", code == 200 and link.get("action_link"), str(link)[:200])
        code, _, kopf = http("GET", link["action_link"], kopf=anon, folgen=False)
        ziel = kopf.get("Location", "")
        alles &= pruefe("Link leitet auf die Seite", code in (302, 303) and ziel.startswith(SEITE + "/#"), ziel[:120])
        hash_ = dict(urllib.parse.parse_qsl(ziel.split("#", 1)[-1]))
        alles &= pruefe("Weiterleitung enthaelt Sitzung", bool(hash_.get("access_token")))
        if "--browser" in sys.argv:
            print("LINK " + link["action_link"])
        # Weg 2: Code
        code, link2, _ = http("POST", AUTH["url"] + "/auth/v1/admin/generate_link", {"type": "magiclink", "email": email}, admin)
        code, sitzung, _ = http("POST", AUTH["url"] + "/auth/v1/verify",
                                {"type": "email", "email": email, "token": link2.get("email_otp")}, anon)
        alles &= pruefe("Code-Anmeldung", code == 200 and sitzung.get("access_token"), str(sitzung)[:200])
        # Passwort: setzen (wie nach Registrierung/Zuruecksetzen), anmelden, falsches Passwort, Mindestlaenge
        pw = "Test-Passwort-" + secrets.token_hex(4)
        code, _, _ = http("PUT", AUTH["url"] + "/auth/v1/user", {"password": pw}, {"apikey": AUTH["anonKey"], "Authorization": "Bearer " + sitzung.get("access_token", "")})
        alles &= pruefe("Passwort setzen", code == 200, str(code))
        code, d, _ = http("POST", AUTH["url"] + "/auth/v1/token?grant_type=password", {"email": email, "password": pw}, {"apikey": AUTH["anonKey"]})
        alles &= pruefe("Anmeldung mit Passwort", code == 200 and d.get("access_token"), str(code))
        code, d, _ = http("POST", AUTH["url"] + "/auth/v1/token?grant_type=password", {"email": email, "password": pw + "x"}, {"apikey": AUTH["anonKey"]})
        alles &= pruefe("Falsches Passwort abgelehnt", code == 400, str(code))
        code, d, _ = http("POST", AUTH["url"] + "/auth/v1/signup", {"email": "kurz-" + email, "password": "kurz"}, {"apikey": AUTH["anonKey"]})
        alles &= pruefe("Zu kurzes Passwort abgelehnt (min. 10)", code == 422 and "weak_password" in str(d), "%s %s" % (code, str(d)[:120]))
        tok = sitzung.get("access_token") or hash_.get("access_token")
        # Seite mit Token und ohne
        code, d, _ = http("GET", SEITE + "/api/aktuell", kopf={"Authorization": "Bearer " + tok})
        alles &= pruefe("/api/aktuell mit Token", code == 200 and isinstance(d, dict) and "rounded" in d, "%s %s" % (code, str(d)[:120]))
        code, _, _ = http("GET", SEITE + "/api/aktuell")
        alles &= pruefe("/api/aktuell ohne Token gesperrt", code == 401, str(code))
        code, d, _ = http("POST", SEITE + "/api/chat", {"frage": "Wie setzt sich der Wert zusammen?", "verlauf": []}, {"Authorization": "Bearer " + tok})
        alles &= pruefe("/api/chat mit Token", code == 200 and isinstance(d, dict) and d.get("antwort"), "%s %s" % (code, str(d)[:160]))
        code, _, _ = http("POST", SEITE + "/api/chat", {"frage": "Wie setzt sich der Wert zusammen?", "verlauf": []})
        alles &= pruefe("/api/chat ohne Token gesperrt", code == 401, str(code))
        code, d, _ = http("GET", SEITE + "/data/stress.json")
        alles &= pruefe("stress.json nur zeitversetzt", code == 200 and d.get("publicOnly") is True, str({k: d.get(k) for k in ("asOf", "rounded", "publicOnly")}))
    finally:
        if nutzer and nutzer.get("id"):
            code, _, _ = http("DELETE", AUTH["url"] + "/auth/v1/admin/users/" + nutzer["id"], kopf=admin)
            pruefe("Testnutzer geloescht", code == 200, str(code))
    print("ALLES OK" if alles else "ES GIBT FEHLER")
    sys.exit(0 if alles else 1)


if __name__ == "__main__":
    main()
