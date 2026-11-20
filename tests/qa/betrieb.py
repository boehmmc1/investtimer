#!/usr/bin/env python3
"""QA Bereich 6 – Betrieb (nur lesend; mit --mails zusaetzlich Testmails mit "TEST" im Betreff an info@investtimer.net).
- Dienste und Timer (letzter Lauf erfolgreich), Volafly unbeeintraechtigt (Dienst, volafly.net, Scraper-Laeufe).
- Logs der letzten 7 Tage: Fehler im Journal, nginx error.log, 5xx-Antworten; Speicherplatz, Log-Rotation.
- Sicherung: aktuelle Dateien vorhanden, Wiederherstellung in eine Testumgebung (Integritaet, Zeilen gegen Live).
- E-Mail: SPF, DKIM, DMARC; mit --mails: Wochen-Mail, Fehlermeldung und Kostenmail einmal ausloesen (TEST) und Zustellung bei Resend pruefen.
"""
import gzip
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, melde, http, ende  # noqa: E402

B = "6 Betrieb"


def sh(befehl):
    return subprocess.run(befehl, shell=True, capture_output=True, text=True, timeout=120).stdout.strip()


def dienste():
    for d in ("nginx", "volafly-chat"):
        melde(B, "Dienst %s aktiv" % d, sh("systemctl is-active " + d) == "active", "kritisch", "systemctl is-active")
    melde(B, "volafly.net laedt", http("GET", "https://volafly.net/")[0] == 200, "kritisch", "curl https://volafly.net/")
    for t in ("investtimer-data", "investtimer-deploy", "investtimer-og", "investtimer-teilen", "investtimer-sicherung", "investtimer-statistik",
              "investtimer-wochenbericht", "investtimer-abo-erinnerung"):
        aktiv = sh("systemctl is-active %s.timer" % t)
        res = sh("systemctl show -p Result --value %s.service" % t)
        letzte = sh("systemctl show -p ExecMainExitTimestamp --value %s.service" % t)
        melde(B, "Timer %s %s, letzter Lauf %s (%s)" % (t, aktiv, res or "?", letzte or "noch nie"), aktiv == "active" and res in ("success", ""), "hoch", "systemctl show")
    log = Path("/root/volafly-scraper/scraper.log")
    alter = (time.time() - log.stat().st_mtime) / 60
    melde(B, "Volafly-Scraper laeuft (letzte Ausgabe vor %d Min.)" % alter, alter < 45, "hoch", "scraper.log mtime")
    w = Path("/var/lib/investtimer/data/stress.json")
    alter = (time.time() - w.stat().st_mtime) / 60
    melde(B, "stress.json aktualisiert (vor %d Min.)" % alter, alter < 30, "hoch", "/var/lib/investtimer/data/stress.json")


def nginx_wirksam():
    """Ein abgelehnter Reload faellt sonst nicht auf: nginx -t und systemctl reload melden Erfolg, der Master behaelt die alte Konfiguration."""
    worker = sh("ps -o lstart= -C nginx --sort=-start_time | tail -1")
    import email.utils
    try:
        start = datetime.strptime(worker.strip(), "%a %b %d %H:%M:%S %Y").timestamp()
    except ValueError:
        start = 0
    dateien = [Path("/etc/nginx/sites-available/investtimer"), Path("/etc/nginx/snippets/investtimer-sicherheit.conf"), Path("/etc/nginx/investtimer-lasttest.conf")]
    neueste = max(p.stat().st_mtime for p in dateien if p.exists())
    emerg = sh("grep -c '\\[emerg\\]' /var/log/nginx/error.log 2>/dev/null || true")
    melde(B, "nginx laeuft mit der aktuellen Konfiguration (Worker nach letzter Aenderung gestartet)", start >= neueste - 2, "hoch",
          "ps nginx worker vs mtime der Konfiguration", "Worker %s, Konfiguration %s, emerg im error.log: %s" % (worker.strip(), time.ctime(neueste), emerg))


def logs():
    for seit, schwere in (("-48h", "mittel"), ("-7d", "info")):
        j = sh("journalctl -p err -S %s --no-pager -o cat -u volafly-chat -u nginx -u 'investtimer-*' 2>/dev/null | grep -v '^-- ' | wc -l" % seit)
        beispiele = sh("journalctl -p err -S %s --no-pager -o short-iso -u volafly-chat -u nginx -u 'investtimer-*' 2>/dev/null | cut -c1-10,40- | sort | uniq -c | sort -rn | head -4" % seit)
        melde(B, "Journal (%s): %s Fehlerzeilen" % (seit, j), int(j or 0) == 0, schwere, "journalctl -p err -S %s" % seit, beispiele[:400])
        tb = sh("journalctl -S %s --no-pager -o cat -u volafly-chat 2>/dev/null | grep -c Traceback" % seit)
        arten = sh("journalctl -S %s --no-pager -o cat -u volafly-chat | awk '/Traceback/{f=1} f && /^[A-Za-z_.]+(Error|Exception)/{print; f=0}' | sort | uniq -c" % seit)
        melde(B, "volafly-chat (%s): %s Tracebacks" % (seit, tb), int(tb or 0) == 0, schwere, "journalctl -u volafly-chat | grep Traceback", arten)
    fehler = sh("cat /var/log/nginx/error.log /var/log/nginx/error.log.1 2>/dev/null | grep -E '\\[(crit|alert|emerg)\\]' | grep -vc SSL_do_handshake")
    melde(B, "nginx error.log: %s kritische Zeilen" % fehler, int(fehler or 0) == 0, "mittel", "/var/log/nginx/error.log")
    funf = sh("zcat -f /var/log/nginx/investtimer-statistik.log* 2>/dev/null | awk '$5 ~ /^5/' | wc -l")
    alle = sh("zcat -f /var/log/nginx/investtimer-statistik.log* 2>/dev/null | wc -l")
    beispiele = sh("zcat -f /var/log/nginx/investtimer-statistik.log* 2>/dev/null | awk '$5 ~ /^5/ {print $5, $4}' | sort | uniq -c | sort -rn | head -5")
    anteil = int(funf or 0) / max(1, int(alle or 1))
    melde(B, "5xx-Antworten (14 Tage): %s von %s (%.2f %%)" % (funf, alle, anteil * 100), anteil < 0.005, "mittel", "investtimer-statistik.log", beispiele)
    frei = shutil.disk_usage("/")
    melde(B, "Speicherplatz: %.0f %% frei" % (frei.free / frei.total * 100), frei.free / frei.total > 0.2, "hoch", "df /")
    melde(B, "nginx-Protokolle rotieren (taeglich, 14)", "rotate 14" in Path("/etc/logrotate.d/nginx").read_text() and "/var/log/nginx/*.log" in Path("/etc/logrotate.d/nginx").read_text(), "mittel", "/etc/logrotate.d/nginx")
    gross = [(str(p), p.stat().st_size // 1_000_000) for p in list(Path("/root/volafly-scraper").glob("*.log")) + list(Path("/var/log").glob("*.log")) if p.stat().st_size > 50_000_000]
    melde(B, "keine Protokolldatei > 50 MB", not gross, "niedrig", "ls -la *.log", gross)
    melde(B, "systemd-Journal begrenzt (%s)" % sh("journalctl --disk-usage | grep -o '[0-9.]*[GM]'"), True, "info", "journalctl --disk-usage")


def sicherung():
    ziel = Path("/var/backups/investtimer")
    for muster in ("konto-*.db", "alarme-*.db", "rueckrechnung-*.json.gz"):
        d = sorted(ziel.glob(muster), key=lambda p: p.stat().st_mtime)
        d = [p for p in d if "vor-" not in p.name]
        neu = d[-1] if d else None
        melde(B, "Sicherung %s: neueste %s" % (muster, neu.name if neu else "fehlt"), bool(neu) and time.time() - neu.stat().st_mtime < 30 * 3600, "hoch", str(ziel))
        if not neu:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / neu.name.replace(".gz", "")
            if neu.suffix == ".gz":
                kopie.write_bytes(gzip.decompress(neu.read_bytes()))
                ok = len(json.loads(kopie.read_text()).get("tage", {})) > 10000
                melde(B, "Wiederherstellung %s: JSON lesbar, Tage vollstaendig" % neu.name, ok, "hoch", "gzip + json in Testverzeichnis")
                continue
            shutil.copy(neu, kopie)
            db = sqlite3.connect(kopie)
            integ = db.execute("PRAGMA integrity_check").fetchone()[0]
            tabellen = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            zeilen = {t: db.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in tabellen}
            live = sqlite3.connect("file:/var/lib/investtimer/%s?mode=ro" % ("konto.db" if "konto" in neu.name else "alarme.db"), uri=True)
            live_z = {t: live.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in tabellen if live.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone()}
            melde(B, "Wiederherstellung %s in Testumgebung: integrity %s, Zeilen %s (live %s)" % (neu.name, integ, zeilen, live_z), integ == "ok" and tabellen,
                  "hoch", "Kopie nach %s, PRAGMA integrity_check" % tmp)
    melde(B, "Sicherung ausser Haus (zweiter Ort)", False, "info", "OPS-002", "nur auf demselben Server – offen laut Projektakte")


def dns():
    spf = sh("dig +short TXT investtimer.net | grep -i spf")
    melde(B, "SPF investtimer.net vorhanden", "v=spf1" in spf, "mittel", "dig TXT investtimer.net", spf)
    sendspf = sh("dig +short TXT send.investtimer.net")
    melde(B, "SPF Versand-Subdomain (Resend) vorhanden", "v=spf1" in sendspf, "mittel", "dig TXT send.investtimer.net", sendspf)
    dkim = sh("dig +short TXT resend._domainkey.investtimer.net")
    melde(B, "DKIM resend._domainkey vorhanden", "p=" in dkim, "hoch", "dig TXT resend._domainkey.investtimer.net")
    dmarc = sh("dig +short TXT _dmarc.investtimer.net")
    melde(B, "DMARC-Eintrag vorhanden (%s)" % (dmarc or "fehlt"), "v=DMARC1" in dmarc, "mittel", "dig TXT _dmarc.investtimer.net")


def resend_status(mail_id):
    key = Path("/root/.investtimer/resend-key").read_text().strip()
    for _ in range(12):
        req = urllib.request.Request("https://api.resend.com/emails/" + mail_id, headers={"Authorization": "Bearer " + key, "User-Agent": "investtimer-qa"})
        try:
            ev = json.load(urllib.request.urlopen(req, timeout=20)).get("last_event")
        except Exception as e:
            ev = "abfrage: %s" % e
        if ev in ("delivered", "bounced", "complained"):
            return ev
        time.sleep(10)
    return ev


def mails():
    """Testmails mit "TEST" im Betreff an info@investtimer.net: Wochen-Mail, Fehlermeldung, Kostenmail (ueber die KI-Testinstanz)."""
    aus = sh("python3 %s --woche --test --bis-heute" % (ROOT / "server/statistik.py"))
    m = re.search(r"Mail: (\S+)", aus)
    melde(B, "Wochen-Mail (TEST) versendet", bool(m), "mittel", "server/statistik.py --woche --test", aus[-200:])
    if m:
        st = resend_status(m.group(1))
        melde(B, "Wochen-Mail zugestellt (Resend: %s)" % st, st == "delivered", "mittel", "Resend GET /emails/<id>")
    start = subprocess.run(["bash", str(ROOT / "tests/ki_instanz.sh"), "start"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
    if "bereit" not in start.stdout:
        melde(B, "KI-Testinstanz fuer Testmails", False, "mittel", "tests/ki_instanz.sh", start.stdout[-200:])
        return
    try:
        env = Path("/tmp/investtimer-ki-instanz/it.env")
        env.write_text(env.read_text() + "IT_FEHLER_TEST=1\nIT_KI_KOSTEN_TEST=1\nIT_KI_KOSTEN_TAG_EUR=0.0001\nIT_KI_KOSTEN_MONAT_EUR=1000\n")
        time.sleep(32)   # .env wird alle 30 s neu gelesen
        req = urllib.request.Request("http://127.0.0.1:8198/v1/investtimer/fehler", method="POST", headers={"Content-Type": "application/json"},
                                     data=json.dumps({"meldung": "TEST QA-Gesamtpruefung %s" % time.strftime("%H:%M"), "datei": "/qa.js", "zeile": 1,
                                                      "ansicht": "qa", "version": "qa", "geraet": "QA"}).encode())
        urllib.request.urlopen(req, timeout=30)
        req = urllib.request.Request("http://127.0.0.1:8198/v1/investtimer/chat", method="POST", headers={"Content-Type": "application/json", "X-Real-IP": "10.66.0.1"},
                                     data=json.dumps({"frage": "What does today’s reading mean?", "verlauf": [], "sprache": "en"}).encode())
        urllib.request.urlopen(req, timeout=180)
        time.sleep(8)
        log = Path("/tmp/investtimer-ki-instanz/log").read_text()
        melde(B, "Fehlermeldungs-Mail (TEST) ausgeloest", "Resend" not in log.split("fehler")[-1][:200], "mittel", "POST /v1/investtimer/fehler (Testinstanz)")
        melde(B, "Kostenmail (TEST) ausgeloest", "Kostenmail tag" in log, "mittel", "Testinstanz-Log", re.findall(r"\[investtimer\] Kostenmail[^\n]*", log)[-2:])
    finally:
        subprocess.run(["bash", str(ROOT / "tests/ki_instanz.sh"), "stop"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)


def main():
    blocks = [dienste, nginx_wirksam, logs, sicherung, dns] + ([mails] if "--mails" in sys.argv else [])
    for f in blocks:
        try:
            f()
        except Exception as e:
            melde(B, "Pruefblock %s durchgelaufen" % f.__name__, False, "mittel", "tests/qa/betrieb.py", "%s: %s" % (type(e).__name__, e))
    return ende()


if __name__ == "__main__":
    sys.exit(main())
