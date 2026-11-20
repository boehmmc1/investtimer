#!/usr/bin/env python3
"""KI-Limit ueber die echte API (eigene Instanz, Port 8197) mit nachgebauten Diensten, ohne Kosten:
Anthropic (zaehlt Aufrufe, liefert feste Antwort und einstellbare usage), Supabase (/auth/v1/user: Token = Nutzer-ID),
Resend (faengt Mails ab). Prueft: Limit je Konto, je IP, Gesamtbremse, Beispielfragen ohne Limit und mit Tages-Cache,
Kostenmail (Testmodus, niedrige Schwellen) und Pause ab doppelter Tagesschwelle. Aufruf: python3 tests/test_ki_limit_api.py"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8197
fehler = []
ZUSTAND = {"aufrufe": 0, "eingabe": 50, "mails": []}


def pruefe(bed, text):
    print(("ok   " if bed else "FEHL ") + text)
    if not bed:
        fehler.append(text)


class Dienste(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, d, status=200):
        b = json.dumps(d).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/auth/v1/user"):
            tok = self.headers.get("Authorization", "")[7:]
            return self._json({"id": tok, "email": tok + "@test.invalid"})
        self._json({}, 404)

    def do_POST(self):
        laenge = int(self.headers.get("Content-Length") or 0)
        d = json.loads(self.rfile.read(laenge) or b"{}")
        if self.path.startswith("/v1/messages"):
            ZUSTAND["aufrufe"] += 1
            ZUSTAND.setdefault("anfragen", []).append({k: d.get(k) for k in ("thinking", "output_config", "model")})
            return self._json({"id": "msg_test", "type": "message", "role": "assistant", "model": d.get("model"),
                               "content": [{"type": "text", "text": "Der Marktstress liegt heute im mittleren Bereich. "
                                            "Die Kursschwankungen sind etwas erhöht, die Stimmung ist gedämpft."}],
                               "stop_reason": "end_turn", "stop_sequence": None,
                               "usage": {"input_tokens": ZUSTAND["eingabe"], "output_tokens": 40,
                                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}})
        if self.path.startswith("/emails"):
            ZUSTAND["mails"].append(d)
            return self._json({"id": "mail"})
        self._json({}, 404)


def frage(text, nutzer, ip, sprache="de"):
    req = urllib.request.Request("http://127.0.0.1:%d/v1/investtimer/chat" % PORT, method="POST",
                                 data=json.dumps({"frage": text, "verlauf": [], "sprache": sprache}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + nutzer, "X-Real-IP": ip})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Dienste)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dienst = "http://127.0.0.1:%d" % srv.server_address[1]
    tmp = Path(tempfile.mkdtemp(prefix="it-kilimit-"))
    os.chmod(tmp, 0o700)
    try:
        for f in list(Path("/root/volafly-chat").glob("*.py")) + list(Path("/root/volafly-chat").glob("*.json")):
            if f.name not in ("volafly_chat.py",) and not f.name.startswith("investtimer_"):
                (tmp / f.name).symlink_to(f)
        shutil.copy2("/root/volafly-chat/volafly_chat.py", tmp / "volafly_chat.py")
        subprocess.run([sys.executable, str(ROOT / "deploy" / "api_einbauen.py"), str(tmp)], check=True, capture_output=True)
        for b in tmp.glob("volafly_chat.py.bak-*"):
            b.unlink()
        src = (tmp / "volafly_chat.py").read_text().replace("/var/www/investtimer/", str(ROOT) + "/")
        (tmp / "volafly_chat.py").write_text(src)
        geheim = tmp / "geheim"
        geheim.mkdir()
        (geheim / "resend-key").write_text("re_test")
        (tmp / "it.env").write_text("\n".join([
            "INVESTTIMER_CHAT=on", "IT_SUPABASE_URL=" + dienst, "IT_SUPABASE_ANON_KEY=test",
            "IT_KI_TAG=1", "IT_KI_IP_TAG=3", "INVESTTIMER_CHAT_TAGESLIMIT=5",
            "IT_KI_KOSTEN_TAG_EUR=0.5", "IT_KI_KOSTEN_MONAT_EUR=0.8", "IT_KI_KOSTEN_TEST=1", "IT_KI_KOSTEN_AN=test@investtimer.net"]) + "\n")
        umgebung = dict(os.environ, IT_ENV_DATEI=str(tmp / "it.env"), IT_KI_DB=str(tmp / "ki.db"),
                        INVESTTIMER_KONTO_DB=str(tmp / "konto.db"), IT_GEHEIM_DIR=str(geheim),
                        ANTHROPIC_BASE_URL=dienst, ANTHROPIC_API_KEY="test", IT_RESEND_API=dienst,
                        IT_TEILEN_AKTUELL_DIR=str(tmp / "teilen-aktuell"))
        log = open(tmp / "log", "w")
        api = subprocess.Popen(["/usr/local/bin/uvicorn", "volafly_chat:app", "--host", "127.0.0.1", "--port", str(PORT)],
                               cwd=tmp, env=umgebung, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                try:
                    urllib.request.urlopen("http://127.0.0.1:%d/v1/investtimer/chat" % PORT, timeout=2)
                    break
                except Exception:
                    time.sleep(1)
            pruefe_alles(tmp)
        finally:
            api.terminate()
            api.wait(10)
            if fehler:
                print((tmp / "log").read_text()[-3000:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        srv.shutdown()
    print("FEHLER:", len(fehler))
    return 1 if fehler else 0


def teilen_pruefen(tmp):
    """Teilen: Bild-Weiterleitung auf den zeitversetzten Stand, Schalter IT_TEILEN_AKTUELL (aus: auch eingeloggt zeitversetzt;
    an: aktueller Wert nur mit Login, einmal je Tag gerendert)."""
    def hole(pfad, tok=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, pfad), headers={"Authorization": "Bearer " + tok} if tok else {})
        class Kein(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        try:
            r = urllib.request.build_opener(Kein).open(req, timeout=120)
            return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()
    s, h, _ = hole("/v1/investtimer/teilen/bild?art=wert&format=hoch&l=de&aktuell=1", "nutzerT")
    pruefe(s == 302 and "/teilen/20" in (h.get("Location") or ""), f"Teilen: Schalter aus -> zeitversetztes Bild ({s} {h.get('Location')})")
    s, _, _ = hole("/v1/investtimer/teilen/bild?art=phase&phase=../../etc&format=quer")
    pruefe(s == 400, f"Teilen: ungueltige Phase abgelehnt ({s})")
    s, _, b = hole("/v1/investtimer/teilen/s/wert?utm_medium=%3Cscript%3E")
    pruefe(s == 200 and b"<script>location" in b and b"%3Cscript" not in b and b"<script%3E" not in b and b"utm_medium=script" in b, "Teilen-Seite: utm_medium bereinigt")
    env = (tmp / "it.env").read_text()
    (tmp / "it.env").write_text(env + "IT_TEILEN_AKTUELL=1\n")
    time.sleep(31)   # .env wird alle 30 s neu gelesen
    s, _, _ = hole("/v1/investtimer/teilen/bild?art=wert&format=quer&l=de&aktuell=1")
    pruefe(s == 401, f"Teilen aktuell: ohne Login 401 ({s})")
    t0 = time.time()
    s, h, b = hole("/v1/investtimer/teilen/bild?art=wert&format=quer&l=de&aktuell=1", "nutzerT")
    t1 = time.time()
    s2, _, b2 = hole("/v1/investtimer/teilen/bild?art=wert&format=quer&l=de&aktuell=1", "nutzerT")
    t2 = time.time()
    pruefe(s == 200 and b[:4] == b"\x89PNG" and "private" in (h.get("Cache-Control") or "") and s2 == 200 and b2 == b and t2 - t1 < (t1 - t0) / 2,
           f"Teilen aktuell: mit Login PNG, privat, zweiter Abruf aus dem Tages-Cache ({t1 - t0:.1f} s / {t2 - t1:.2f} s)")
    (tmp / "it.env").write_text(env)


def pruefe_alles(tmp):
    teilen_pruefen(tmp)
    # 1. Beispielfragen: statisch ohne Modell, beliebig oft, zaehlen nicht
    n0 = ZUSTAND["aufrufe"]
    for _ in range(4):
        s, d = frage("Was misst InvestTimer eigentlich?", "nutzerA", "10.0.0.1")
    pruefe(s == 200 and d.get("katalog") is True and ZUSTAND["aufrufe"] == n0 and not d["frei"]["verbraucht"],
           f"statische Beispielfrage 4x ohne Modellaufruf, zaehlt nicht ({s}, {d.get('frei')})")
    # 2. Beispielfrage mit Live-Werten (Vorlage) und englische Beispielfrage: einmal Modell, dann Tages-Cache, ohne Denken
    for text, sp in (("Was bewegt den Wert gerade?", "de"), ("What does today’s reading mean?", "en"),
                     ("Ist 59 viel oder wenig?", "de"), ("Wie verlief „Corona-Crash 2020“?", "de")):
        n0 = ZUSTAND["aufrufe"]
        s1, d1 = frage(text, "nutzerA", "10.0.0.1", sp)
        n1 = ZUSTAND["aufrufe"]
        s2, d2 = frage(text, "nutzerB", "10.0.0.2", sp)
        anfrage = (ZUSTAND.get("anfragen") or [{}])[-1]
        pruefe(s1 == 200 and s2 == 200 and d1.get("katalog") and n1 - n0 >= 1 and ZUSTAND["aufrufe"] == n1 and d1["antwort"] == d2["antwort"],
               f"Beispielfrage '{text}': {n1 - n0} Aufruf(e), danach Cache ({s1}/{s2})")
        pruefe((anfrage.get("thinking") or {}).get("type") == "disabled" and (anfrage.get("output_config") or {}).get("effort") == "low",
               f"Beispielfrage '{text}': ohne Denken, Aufwand niedrig {anfrage}")
    s, d = frage("Wie verlief „Erfundene Phase 1999“?", "nutzerZ", "10.9.9.9")
    pruefe(s == 200 and d.get("katalog") is False, "unbekannte Ereignisfrage ist eine freie Frage")
    # 3. Konto: eine freie Frage je Tag
    s, d = frage("Was ist heute anders als gestern?", "nutzerA", "10.0.0.1")
    pruefe(s == 200 and d.get("katalog") is False and d["frei"]["verbraucht"], f"Konto A: erste freie Frage ok, danach verbraucht {d.get('frei')}")
    s, d = frage("Und was heisst das fuer morgen?", "nutzerA", "10.0.0.1")
    pruefe(s == 429 and d.get("error") == "limit" and d.get("grund") == "konto", f"Konto A: zweite freie Frage abgelehnt {s} {d}")
    s, d = frage("Was misst InvestTimer eigentlich?", "nutzerA", "10.0.0.1")
    pruefe(s == 200 and d["frei"]["verbraucht"], "Konto A: Beispielfrage nach Verbrauch weiter moeglich")
    # 4. IP: hoechstens 3 freie Fragen je IP (Z hat schon eine auf 10.9.9.9)
    for u in ("nutzerC", "nutzerD"):
        s, d = frage("Wie schaetzt du die Lage ein?", u, "10.9.9.9")
        pruefe(s == 200, f"IP 10.9.9.9: {u} ok")
    s, d = frage("Wie schaetzt du die Lage ein?", "nutzerE", "10.9.9.9")
    pruefe(s == 429 and d.get("grund") == "ip", f"IP 10.9.9.9: vierte freie Frage abgelehnt {s} {d}")
    # 5. Gesamtbremse 5: bisher Z, A, C, D = 4
    s, d = frage("Wie schaetzt du die Lage ein?", "nutzerF", "10.0.0.6")
    pruefe(s == 200, "Gesamt: fuenfte freie Frage ok")
    s, d = frage("Wie schaetzt du die Lage ein?", "nutzerG", "10.0.0.7")
    pruefe(s == 429 and d.get("error") == "ausgelastet" and d.get("grund") == "gesamt", f"Gesamtbremse greift {s} {d}")
    s, d = frage("Wie lange dauern Stressphasen meistens?", "nutzerG", "10.0.0.7")
    pruefe(s == 200 and d["frei"]["ausgelastet"], "Gesamtbremse: Beispielfragen laufen weiter")
    # 6. Kosten: Zaehler zuruecksetzen, teure Aufrufe (300 000 Eingabe-Token = 0,55 EUR)
    db = sqlite3.connect(tmp / "ki.db")
    db.execute("DELETE FROM frei")
    db.execute("DELETE FROM kosten")
    db.commit()
    db.close()
    ZUSTAND["eingabe"] = 300_000
    ZUSTAND["mails"].clear()
    s, d = frage("Wie schaetzt du die Lage ein?", "nutzerH", "10.0.1.1")
    time.sleep(1.5)
    pruefe(s == 200 and [m["subject"] for m in ZUSTAND["mails"]] == ["TEST Tageskosten der InvestTimer-KI über 0,50 €"],
           f"Kostenmail Tag {[m['subject'] for m in ZUSTAND['mails']]}")
    pruefe(all(m["to"] == ["test@investtimer.net"] for m in ZUSTAND["mails"]), "Kostenmail an die eingestellte Adresse")
    s, d = frage("How did “Stress phase, spring 2008” unfold?", "nutzerH", "10.0.1.1", "en")
    time.sleep(1.5)
    betreffe = sorted(m["subject"] for m in ZUSTAND["mails"])
    pruefe(any("pausiert" in b for b in betreffe) and "TEST Monatskosten der InvestTimer-KI über 0,80 €" in betreffe,
           f"Kostenmails Pause und Monat {betreffe}")
    s, d = frage("Wie schaetzt du die Lage ein?", "nutzerI", "10.0.1.2")
    pruefe(s == 429 and d.get("grund") == "pause", f"ab doppelter Tagesschwelle: freie Fragen pausiert {s} {d}")
    s, d = frage("Was misst InvestTimer eigentlich?", "nutzerI", "10.0.1.2")
    pruefe(s == 200 and d["frei"]["ausgelastet"], "Pause: Beispielfragen laufen weiter")
    n = len(ZUSTAND["mails"])
    frage("Wie verlief „Corona-Crash 2020“?", "nutzerI", "10.0.1.2")
    time.sleep(1)
    pruefe(len(ZUSTAND["mails"]) == n, "jede Kostenmail nur einmal je Tag/Monat")
    log = (tmp / "log").read_text()
    pruefe("[usage] investtimer frei" in log and "eur=" in log and "cache_write=" in log, "usage-Zeilen mit Kosten im Log")


if __name__ == "__main__":
    sys.exit(main())
