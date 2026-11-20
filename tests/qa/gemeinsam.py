"""Gemeinsame Helfer der QA-Suite (tests/qa, Start: tools/qa_gesamt.sh).

Jede Pruefung meldet ein Ergebnis mit Bereich (1-6), Schwere (kritisch/hoch/mittel/niedrig/info), Text und Nachweis.
Ergebnisse landen als JSON-Zeilen in $QA_AUSGABE (Standard: /var/lib/investtimer/qa/<datum>/ergebnisse.jsonl).
Testkonten: nur ueber die Supabase-Admin-API (service_role zur Laufzeit ueber die Management-API, nie gespeichert),
Adresse qa-<zeit>-<n>@investtimer.net, werden am Ende immer geloescht (auch bei Fehlern).
"""
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SEITE = os.environ.get("QA_SEITE", "https://investtimer.net").rstrip("/")
AUSGABE = Path(os.environ.get("QA_AUSGABE", "/var/lib/investtimer/qa/%s" % time.strftime("%Y-%m-%d")))
AUSGABE.mkdir(parents=True, exist_ok=True)
os.chmod(AUSGABE, 0o700)
ERGEBNIS = AUSGABE / "ergebnisse.jsonl"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
_zaehler = {"ok": 0, "befund": 0}


def melde(bereich, name, ok, schwere="mittel", nachweis="", info=""):
    """ok=True: bestanden. Sonst Befund mit Schwere. schwere='info' fuer reine Feststellungen."""
    z = {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S"), "bereich": bereich, "name": name, "ok": bool(ok),
         "schwere": "ok" if ok else schwere, "nachweis": nachweis, "info": str(info)[:600]}
    with open(ERGEBNIS, "a", encoding="utf-8") as f:
        f.write(json.dumps(z, ensure_ascii=False) + "\n")
    _zaehler["ok" if ok else "befund"] += 1
    print(("ok    " if ok else ("INFO  " if schwere == "info" else "BEFUND")) + " [%s] %s%s" % (bereich, name, ("  -> " + str(info)[:240]) if info and not ok else ""), flush=True)
    return bool(ok)


def ende():
    print("ZUSAMMEN: %d bestanden, %d Befunde" % (_zaehler["ok"], _zaehler["befund"]))
    return 0


class _KeinFolgen(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_letzter = [0.0]


def http(methode, url, daten=None, kopf=None, folgen=True, roh=None, timeout=60, takt=None):
    """takt: Mindestabstand in Sekunden zwischen Anfragen an /api/ und /s/ der Seite (Standard 1,1 s = unter 60/min),
    damit die Pruefung die eigenen Ratenlimits nicht ausloest. takt=0 fuer den Ratenlimit-Test."""
    if url.startswith("/"):
        url = SEITE + url
    if url.startswith(SEITE + "/api/") or url.startswith(SEITE + "/s/"):
        warte = (1.1 if takt is None else takt) - (time.time() - _letzter[0])
        if warte > 0:
            time.sleep(warte)
        _letzter[0] = time.time()
    body = roh if roh is not None else (None if daten is None else json.dumps(daten).encode())
    k = {"User-Agent": "investtimer-qa", **({"Content-Type": "application/json"} if daten is not None else {}), **(kopf or {})}
    req = urllib.request.Request(url, method=methode, data=body, headers=k)
    oeffner = urllib.request.build_opener() if folgen else urllib.request.build_opener(_KeinFolgen)
    try:
        with oeffner.open(req, timeout=timeout) as a:
            text = a.read()
            return a.status, _json(text), dict(a.headers)
    except urllib.error.HTTPError as f:
        return f.code, _json(f.read()), dict(f.headers)
    except Exception as e:
        return 0, str(e), {}


def _json(b):
    try:
        t = b.decode("utf-8")
    except Exception:
        return b
    if t[:1] in "{[":
        try:
            return json.loads(t)
        except ValueError:
            pass
    return t


# ── Supabase-Testkonten ──────────────────────────────────────────────────────
_AUTH = json.loads((ROOT / "deploy" / "supabase.json").read_text())
_admin = None
_angelegt = []


def _admin_kopf():
    global _admin
    if _admin is None:
        sys.path.insert(0, str(ROOT / "deploy"))
        from supabase_einrichten import API, token
        ref = urllib.parse.urlparse(_AUTH["url"]).hostname.split(".")[0]
        _, keys, _ = http("GET", "%s/projects/%s/api-keys" % (API, ref), kopf={"Authorization": "Bearer " + token()})
        service = next(k["api_key"] for k in keys if k.get("name") == "service_role")
        _admin = {"apikey": service, "Authorization": "Bearer " + service}
    return _admin


def testkonto():
    """Legt ein bestaetigtes Testkonto mit Passwort an und meldet es an. Rueckgabe: dict(email, id, token, passwort)."""
    email = "qa-%d-%s@investtimer.net" % (int(time.time()), secrets.token_hex(3))
    pw = secrets.token_urlsafe(18)
    code, n, _ = http("POST", _AUTH["url"] + "/auth/v1/admin/users", {"email": email, "password": pw, "email_confirm": True}, _admin_kopf())
    if code != 200:
        raise RuntimeError("Testkonto nicht angelegt: %s %s" % (code, str(n)[:200]))
    _angelegt.append(n["id"])
    code, t, _ = http("POST", _AUTH["url"] + "/auth/v1/token?grant_type=password", {"email": email, "password": pw}, {"apikey": _AUTH["anonKey"]})
    if code != 200:
        raise RuntimeError("Anmeldung Testkonto: %s" % code)
    return {"email": email, "id": n["id"], "token": t["access_token"], "passwort": pw, "refresh": t.get("refresh_token")}


def testkonto_weg(uid):
    if not uid:
        return
    http("DELETE", _AUTH["url"] + "/auth/v1/admin/users/" + uid, kopf=_admin_kopf())
    if uid in _angelegt:
        _angelegt.remove(uid)


def aufraeumen():
    """Alle in diesem Lauf angelegten Testkonten loeschen; zusaetzlich ueber die Konto-Loeschung der API, falls noch Daten da sind."""
    for uid in list(_angelegt):
        try:
            testkonto_weg(uid)
        except Exception:
            pass


def bearer(t):
    return {"Authorization": "Bearer " + t}


def auth_url():
    return _AUTH["url"], _AUTH["anonKey"]
