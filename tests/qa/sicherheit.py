#!/usr/bin/env python3
"""QA Bereich 3 – Sicherheit (gegen die Live-Seite, nur Testkonten, nichts wird dauerhaft veraendert).
Header/TLS/Zertifikat, gesperrte Pfade, alle API-Endpunkte ohne Token, Zugriff auf fremde Daten mit zwei Testkonten,
manipuliertes Token, Ratenlimits, Eingaben (Alarmwerte, Teilen-Parameter), Geheimnisse in Repo und ausgelieferter Seite,
Supabase-RLS, offene Ports, Stand Volafly OPS-005/OPS-006 (nur lesen)."""
import base64
import json
import os
import re
import sqlite3
import ssl
import socket
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, SEITE, melde, http, testkonto, aufraeumen, bearer, auth_url, _admin_kopf, ende  # noqa: E402

B = "3 Sicherheit"
HOST = urllib.parse.urlparse(SEITE).hostname


def header_tls():
    _, _, h = http("GET", "/")
    h = {k.lower(): v for k, v in h.items()}
    for name, muss in (("strict-transport-security", "max-age="), ("content-security-policy", "frame-ancestors 'none'"),
                       ("x-content-type-options", "nosniff"), ("referrer-policy", "strict-origin"), ("permissions-policy", "camera=()"),
                       ("x-frame-options", "DENY")):
        melde(B, "Header %s" % name, muss in h.get(name, ""), "mittel", "curl -sI %s/" % SEITE, h.get(name, "fehlt"))
    melde(B, "Server verraet keine Version", re.fullmatch(r"nginx", h.get("server", "nginx")) is not None, "niedrig", "Server-Header", h.get("server"))
    for pfad in ("/teilen/aktuell/manifest.json", "/data/stress.json", "/sw.js"):
        _, _, hh = http("GET", pfad)
        melde(B, "Sicherheits-Header auch auf %s" % pfad, "content-security-policy" in {k.lower() for k in hh}, "niedrig", "curl -sI " + pfad)
    for v, erlaubt in ((ssl.TLSVersion.TLSv1, False), (ssl.TLSVersion.TLSv1_1, False), (ssl.TLSVersion.TLSv1_2, True), (ssl.TLSVersion.TLSv1_3, True)):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_default_certs()
        try:
            ctx.minimum_version = ctx.maximum_version = v
            ctx.set_ciphers("ALL:@SECLEVEL=0")
        except (ValueError, ssl.SSLError):
            pass
        try:
            with socket.create_connection((HOST, 443), timeout=8) as s, ctx.wrap_socket(s, server_hostname=HOST):
                geht = True
        except Exception:
            geht = False
        melde(B, "TLS %s %s" % (v.name, "angeboten" if erlaubt else "abgelehnt"), geht == erlaubt, "hoch" if not erlaubt else "mittel", "ssl-Verbindung")
    ctx = ssl.create_default_context()
    with socket.create_connection((HOST, 443), timeout=8) as s, ctx.wrap_socket(s, server_hostname=HOST) as t:
        ende_ = datetime.strptime(t.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    tage = (ende_ - datetime.now(timezone.utc)).days
    melde(B, "Zertifikat gueltig noch %d Tage" % tage, tage > 20, "hoch", "TLS-Zertifikat", ende_.date())
    code, _, h = http("GET", "http://%s/" % HOST, folgen=False)
    melde(B, "HTTP leitet auf HTTPS um", code == 301 and h.get("Location", "").startswith("https://"), "hoch", "curl http://")


def pfade():
    for pfad in ("/.env", "/.git/config", "/.git/HEAD", "/deploy/supabase.json", "/server/og_bild.py", "/volafly-api/investtimer_api_chat.py",
                 "/CLAUDE.md", "/tests/", "/data/history.json", "/teilen/", "/backup/", "/../../etc/passwd", "/vorschau/.git/config"):
        code, _, _ = http("GET", pfad, folgen=False)
        melde(B, "nicht erreichbar: %s" % pfad, code in (301, 302, 403, 404, 400), "hoch", "curl " + pfad, code)
    code, _, _ = http("GET", "https://api.volafly.net/v1/marktstress")
    melde(B, "api.volafly.net/v1/marktstress oeffentlich gesperrt", code in (401, 403, 404), "hoch", "curl", code)
    code, b, _ = http("GET", "/data/stress.json")
    from datetime import date, timedelta
    grenze = (date.today() - timedelta(days=7)).isoformat()
    ps = (b.get("publicSnapshot") or {}) if isinstance(b, dict) else {}
    melde(B, "stress.json nur zeitversetzt (oben und publicSnapshot <= heute-7)", isinstance(b, dict) and b.get("asOf", "9") <= grenze and ps.get("asOf", "9") <= grenze
          and b.get("rounded") == ps.get("rounded"), "kritisch", "/data/stress.json", (b.get("asOf"), ps.get("asOf")) if isinstance(b, dict) else b)


ENDPUNKTE_TOKEN = [("GET", "/api/aktuell"), ("GET", "/api/historie"), ("GET", "/api/konto"), ("GET", "/api/konto/export"), ("GET", "/api/alarme"),
                   ("POST", "/api/alarme"), ("PATCH", "/api/alarme/1"), ("DELETE", "/api/alarme/1"), ("POST", "/api/konto/abgleich"),
                   ("POST", "/api/konto/loeschen"), ("POST", "/api/push/geraet"), ("POST", "/api/push/geraet-entfernen"), ("POST", "/api/push/test"),
                   ("POST", "/api/chat"), ("POST", "/api/abo/checkout"), ("POST", "/api/abo/verwalten")]


def endpunkte():
    for m, p in ENDPUNKTE_TOKEN:
        code, _, _ = http(m, p, daten=({"frage": "x"} if p == "/api/chat" else {}) if m != "GET" else None)
        melde(B, "%s %s ohne Token gesperrt" % (m, p), code in (401, 403), "kritisch", "curl -X %s" % m, code)
    for m, p, erwart in (("POST", "/api/abo/stripe-webhook", (400, 401, 403, 503)), ("POST", "/api/abo/revenuecat-webhook", (400, 401, 403, 503)),
                         ("POST", "/api/vertrag/kuendigen", (400, 404, 422, 429, 503)), ("POST", "/api/vertrag/widerrufen", (400, 404, 422, 429, 503))):
        code, _, _ = http(m, p, daten={"x": 1})
        melde(B, "%s %s ohne Signatur/Daten abgelehnt" % (m, p), code in erwart, "kritisch", "curl", code)
    # manipuliertes Token (gueltige Form, falsche Signatur)
    kopf = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    nutz = base64.urlsafe_b64encode(json.dumps({"sub": "00000000-0000-0000-0000-000000000000", "email": "x@y.z", "exp": 4102444800, "role": "authenticated"}).encode()).rstrip(b"=").decode()
    falsch = kopf + "." + nutz + ".AAAA"
    for p in ("/api/aktuell", "/api/konto", "/api/alarme", "/api/konto/export"):
        code, _, _ = http("GET", p, kopf=bearer(falsch))
        melde(B, "gefaelschtes Token abgelehnt: %s" % p, code == 401, "kritisch", "JWT ohne gueltige Signatur", code)


def fremde_daten():
    a = b = None
    try:
        a, b = testkonto(), testkonto()
        code, al, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": 77, "kanal": "push", "sprache": "de"}, bearer(a["token"]))
        aid = (al.get("alarm") or al).get("id") if isinstance(al, dict) else None
        if not aid and isinstance(al, dict):
            aid = next((x["id"] for x in al.get("alarme", []) if x.get("schwelle") == 77), None)
        melde(B, "Testkonto A legt Alarm an", code == 200 and aid, "info", "POST /api/alarme", (code, str(al)[:160]))
        code, lb, _ = http("GET", "/api/alarme", kopf=bearer(b["token"]))
        melde(B, "Konto B sieht Alarme von A nicht", code == 200 and "77" not in json.dumps(lb) or (code == 200 and all(x.get("schwelle") != 77 for x in (lb.get("alarme", lb) if isinstance(lb, dict) else lb))),
              "kritisch", "GET /api/alarme mit Token B", str(lb)[:160])
        if aid:
            code, _, _ = http("PATCH", "/api/alarme/%s" % aid, {"aktiv": False}, bearer(b["token"]))
            melde(B, "Konto B kann Alarm von A nicht aendern", code in (403, 404), "kritisch", "PATCH mit Token B", code)
            code, _, _ = http("DELETE", "/api/alarme/%s" % aid, kopf=bearer(b["token"]))
            melde(B, "Konto B kann Alarm von A nicht loeschen", code in (403, 404), "kritisch", "DELETE mit Token B", code)
            code, la, _ = http("GET", "/api/alarme", kopf=bearer(a["token"]))
            melde(B, "Alarm von A danach unveraendert vorhanden", code == 200 and "77" in json.dumps(la), "kritisch", "GET mit Token A")
        code, ex, _ = http("GET", "/api/konto/export", kopf=bearer(b["token"]))
        t = json.dumps(ex)
        melde(B, "Export von B enthaelt keine Daten von A", code == 200 and a["email"] not in t and a["id"] not in t and b["email"] in t, "kritisch", "GET /api/konto/export Token B", code)
        # Eingaben: Alarmwerte
        for wert in ("<script>alert(1)</script>", 0, 100, -5, "50; DROP TABLE alarme", 50.5, True):
            code, _, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": wert, "kanal": "push"}, bearer(b["token"]))
            melde(B, "ungueltiger Alarmwert abgelehnt: %r" % (wert,), code in (400, 422), "hoch", "POST /api/alarme", code)
        code, _, _ = http("POST", "/api/alarme", {"richtung": "<b>x</b>", "schwelle": 50, "kanal": "push"}, bearer(b["token"]))
        melde(B, "ungueltige Richtung abgelehnt", code in (400, 422), "hoch", "POST /api/alarme", code)
        code, _, _ = http("POST", "/api/alarme", {"richtung": "ueber", "schwelle": 50, "kanal": "sms"}, bearer(b["token"]))
        melde(B, "ungueltiger Kanal abgelehnt", code in (400, 422), "hoch", "POST /api/alarme", code)
        # Kontoloeschung A ueber die API: danach alles weg
        code, d, _ = http("POST", "/api/konto/loeschen", {"bestaetigung": "löschen"}, bearer(a["token"]))
        melde(B, "Konto A loeschen ueber /api/konto/loeschen", code == 200, "hoch", "POST /api/konto/loeschen", (code, str(d)[:160]))
        if code == 200:
            u, anon = auth_url()
            c2, _, _ = http("GET", u + "/auth/v1/admin/users/" + a["id"], kopf=_admin_kopf())
            melde(B, "Supabase-Nutzer A nach Loeschung weg", c2 == 404, "kritisch", "Admin-API", c2)
            reste = {}
            for db, tabellen in (("/var/lib/investtimer/alarme.db", ("alarme", "geraete")), ("/var/lib/investtimer/konto.db", ("berechtigung", "ki_nutzung", "ereignis"))):
                try:
                    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
                    for tb in tabellen:
                        try:
                            reste[tb] = c.execute("SELECT COUNT(*) FROM %s WHERE uid=?" % tb, (a["id"],)).fetchone()[0]
                        except sqlite3.Error:
                            pass
                except sqlite3.Error:
                    pass
            try:
                c = sqlite3.connect("file:/var/lib/investtimer/ki.db?mode=ro", uri=True)
                reste["ki_frei"] = c.execute("SELECT COUNT(*) FROM frei WHERE art='konto' AND schluessel=?", (a["id"],)).fetchone()[0]
            except sqlite3.Error:
                pass
            melde(B, "nach Loeschung keine Daten von A in Alarm-/Konto-/KI-Datenbank", not any(reste.values()), "kritisch", "SQLite (nur lesend)", reste)
            code, _, _ = http("GET", "/api/konto", kopf=bearer(a["token"]))
            melde(B, "altes Token von A nach Loeschung wirkungslos", code in (401, 403), "hoch", "GET /api/konto Token A", code)
    except Exception as e:
        melde(B, "Pruefung fremde Daten durchgelaufen", False, "hoch", "tests/qa/sicherheit.py", "%s: %s" % (type(e).__name__, e))
    finally:
        aufraeumen()


def ratenlimits():
    codes = [http("POST", "/api/chat", {"frage": "x"}, takt=0)[0] for _ in range(24)]
    melde(B, "Ratenlimit /api/chat greift (24 schnelle Anfragen)", 429 in codes, "mittel", "nginx limit_req investtimer_chat", codes.count(429))
    codes = [http("GET", "/api/konto", takt=0)[0] for _ in range(80)]
    melde(B, "Ratenlimit /api/* greift (80 schnelle Anfragen)", 429 in codes, "mittel", "nginx limit_req investtimer_api", codes.count(429))
    time.sleep(65)   # Limits wieder frei fuer die folgenden Pruefungen


def teilen_eingaben():
    for p in ("/api/teilen/bild?art=phase&phase=..%2F..%2Fetc", "/api/teilen/bild?art=phase&phase=%3Cscript%3E", "/s/phase/%3Cscript%3E", "/s/verlauf/ZZ/2026-01-01"):
        code, b, h = http("GET", p, folgen=False)
        melde(B, "Teilen-Parameter sicher: %s" % p, code in (302, 400, 404) and "<script>" not in str(b), "hoch", "curl", code)
    code, b, _ = http("GET", "/s/wert?utm_medium=%22%3E%3Cscript%3Ealert(1)%3C/script%3E")
    melde(B, "Teilen-Seite gibt utm_medium nicht ungefiltert aus", code == 200 and "alert(1)" not in str(b), "hoch", "curl /s/wert?utm_medium=...", code)


MUSTER = [("Anthropic-Schluessel", r"sk-ant-[A-Za-z0-9_-]{20,}"), ("Stripe-Schluessel", r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"),
          ("Resend-Schluessel", r"\bre_[A-Za-z0-9]{20,}"), ("Google-API-Schluessel", r"(?<![A-Za-z0-9+/])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9+/])"),
          ("privater Schluessel", r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), ("GitHub-Token", r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
          ("Supabase service_role", r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]*cm9sZSI6InNlcnZpY2Vfcm9sZS[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+")]


def geheimnisse():
    dateien = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True).stdout.split()
    treffer = []
    for f in dateien:
        p = ROOT / f
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, m in MUSTER:
            if re.search(m, t):
                treffer.append("%s: %s" % (f, name))
    melde(B, "keine Schluessel im Repo (%d Dateien)" % len(dateien), not treffer, "kritisch", "git ls-files + Muster", treffer[:5])
    verlauf = subprocess.run(["git", "-C", str(ROOT), "log", "-p", "--all", "-S", "sk-ant-", "--oneline"], capture_output=True, text=True).stdout
    melde(B, "keine Anthropic-Schluessel in der Git-Historie", not re.search(MUSTER[0][1], verlauf), "kritisch", "git log -S sk-ant-")
    _, seite, _ = http("GET", "/")
    t = str(seite)
    gefunden = [n for n, m in MUSTER if re.search(m, t)]
    melde(B, "ausgelieferte Seite ohne Schluessel und ohne service_role", not gefunden and "service_role" not in t, "kritisch", "GET /", gefunden)
    melde(B, ".env nur root-lesbar", oct(os.stat("/root/volafly-chat/.env").st_mode & 0o777) in ("0o600", "0o400"), "hoch", "stat .env", oct(os.stat("/root/volafly-chat/.env").st_mode & 0o777))
    offen = [str(p) for p in Path("/root/.investtimer").glob("*") if p.is_file() and p.stat().st_mode & 0o077 and "public" not in p.name]
    melde(B, "Geheimnisse in /root/.investtimer nur fuer root", not offen, "hoch", "stat /root/.investtimer/*", offen)


def rls():
    u, anon = auth_url()
    ref = urllib.parse.urlparse(u).hostname.split(".")[0]
    sys.path.insert(0, str(ROOT / "deploy"))
    from supabase_einrichten import API, token
    code, rows, _ = http("POST", "%s/projects/%s/database/query" % (API, ref),
                         {"query": "select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'"},
                         {"Authorization": "Bearer " + token()})
    if code not in (200, 201):
        melde(B, "Supabase-Tabellen abfragbar", False, "mittel", "Management-API database/query", code)
        return
    ohne = [r["relname"] for r in rows if not r.get("relrowsecurity")]
    melde(B, "Supabase public-Schema: %d Tabellen, alle mit RLS" % len(rows), not ohne, "kritisch", "pg_class.relrowsecurity", ohne)
    for r in rows:
        code, b, _ = http("GET", "%s/rest/v1/%s?select=*&limit=1" % (u, r["relname"]), kopf={"apikey": anon, "Authorization": "Bearer " + anon})
        melde(B, "anon liest public.%s nicht" % r["relname"], code in (401, 403, 404) or b == [], "kritisch", "REST mit anon-Key", (code, str(b)[:80]))
    code, b, _ = http("GET", u + "/auth/v1/admin/users", kopf={"apikey": anon, "Authorization": "Bearer " + anon})
    melde(B, "Admin-API mit anon-Key gesperrt", code in (401, 403), "kritisch", "GET /auth/v1/admin/users anon", code)


def ports():
    aus = subprocess.run(["ss", "-tlnH"], capture_output=True, text=True).stdout
    offen = sorted({z.split()[3] for z in aus.splitlines() if not re.match(r"(127\.0\.0\.\d+|\[::1\]|::1):", z.split()[3])})
    erlaubt = {"0.0.0.0:22", "[::]:22", "0.0.0.0:80", "[::]:80", "0.0.0.0:443", "[::]:443", "*:22", "*:80", "*:443"}
    fremd = [p for p in offen if p not in erlaubt and not p.startswith("127.0.0.53")]
    melde(B, "nur 22/80/443 nach aussen offen", not fremd, "hoch", "ss -tlnH", fremd or offen)


def volafly_stand():
    """OPS-005/OPS-006: nur Stand feststellen, nichts aendern."""
    cfg = subprocess.run(["sshd", "-T"], capture_output=True, text=True).stdout
    pw = re.search(r"^passwordauthentication (\w+)", cfg, re.M)
    root = re.search(r"^permitrootlogin ([\w-]+)", cfg, re.M)
    melde(B, "OPS-006 SSH: Passwort-Anmeldung %s, root-Login %s" % (pw and pw.group(1), root and root.group(1)),
          bool(pw and pw.group(1) == "no"), "info", "sshd -T (nur gelesen)")
    upd = subprocess.run(["bash", "-c", "apt list --upgradable 2>/dev/null | grep -c upgradable; apt list --upgradable 2>/dev/null | grep -ci security"], capture_output=True, text=True).stdout.split()
    ua = subprocess.run(["systemctl", "is-enabled", "unattended-upgrades"], capture_output=True, text=True).stdout.strip()
    melde(B, "OPS-006 Updates: %s ausstehend (davon %s Sicherheit), unattended-upgrades %s" % (upd[0] if upd else "?", upd[1] if len(upd) > 1 else "?", ua),
          upd[:2] == ["0", "0"], "info", "apt list --upgradable (nur gelesen)")
    n = 0
    for d in ("/root/volafly-chat", "/root/volafly-scraper"):
        for p in Path(d).glob("*.py"):
            t = p.read_text(errors="ignore")
            n += sum(1 for _, m in MUSTER if re.search(m, t)) + len(re.findall(r"(?i)(api_key|token|secret|passwort|password)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", t))
    melde(B, "OPS-005 Volafly: %d Fundstellen fest eingetragener Schluessel in .py-Dateien" % n, n == 0, "info", "grep in /root/volafly-chat, /root/volafly-scraper (nur gezaehlt, nichts ausgegeben)")


def main():
    for f in (header_tls, pfade, endpunkte, fremde_daten, teilen_eingaben, geheimnisse, rls, ports, volafly_stand, ratenlimits):
        time.sleep(int(os.environ.get("QA_PAUSE", "20")))   # Ratenlimits der Seite nicht durch die Pruefung selbst ausloesen
        try:
            f()
        except Exception as e:
            melde(B, "Pruefblock %s durchgelaufen" % f.__name__, False, "mittel", "tests/qa/sicherheit.py", "%s: %s" % (type(e).__name__, e))
    return ende()


if __name__ == "__main__":
    sys.exit(main())
