#!/usr/bin/env python3
"""Speicherwaechter fuer volafly-chat (Auftrag 25.11.2026): liest den Speicher des Dienstes (cgroup), schreibt ihn ins Protokoll
/var/lib/investtimer/speicher.log und schickt eine Mail an info@investtimer.net, sobald er ueber 700 MB liegt (hoechstens alle 6 h).
Timer: investtimer-speicher.timer (alle 5 Min.)."""
import json, os, time, urllib.request
from pathlib import Path

GRENZE_MB = 700
SPERRE = Path("/var/lib/investtimer/speicher-alarm.stamp")
LOG = Path("/var/lib/investtimer/speicher.log")


def mb():
    for p in ("/sys/fs/cgroup/system.slice/volafly-chat.service/memory.current",
              "/sys/fs/cgroup/memory/system.slice/volafly-chat.service/memory.usage_in_bytes"):
        if os.path.exists(p):
            return int(open(p).read()) // 2**20
    return None


def rss_mb():
    try:
        pid = open("/sys/fs/cgroup/system.slice/volafly-chat.service/cgroup.procs").read().split()[0]
        return next(int(z.split()[1]) // 1024 for z in open(f"/proc/{pid}/status") if z.startswith("VmRSS"))
    except Exception:
        return None


def mail(text, betreff=None):
    key = Path("/root/.investtimer/resend-key").read_text().strip()
    req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "investtimer-betrieb"},
                                 data=json.dumps({"from": "InvestTimer Betrieb <alarm@investtimer.net>", "to": ["info@investtimer.net"],
                                                  "subject": betreff or "InvestTimer Betrieb: volafly-chat über %d MB" % GRENZE_MB, "text": text}).encode())
    urllib.request.urlopen(req, timeout=30).read()


def main():
    m, r = mb(), rss_mb()
    with LOG.open("a") as f:
        f.write("%s cgroup=%s MB rss=%s MB\n" % (time.strftime("%Y-%m-%d %H:%M"), m, r))
    wert = r if r is not None else m
    if wert is None or wert <= GRENZE_MB:
        return
    if SPERRE.exists() and time.time() - SPERRE.stat().st_mtime < 6 * 3600:
        return
    mail("Der API-Dienst volafly-chat (InvestTimer und Volafly) belegt %s MB Arbeitsspeicher (Grenze %d MB).\n"
         "Ab 700 MB drosselt systemd, ab 900 MB startet der Dienst automatisch neu (ca. 5 s Ausfall).\n"
         "Verlauf: /var/lib/investtimer/speicher.log auf dem Server." % (wert, GRENZE_MB))
    SPERRE.touch()


if __name__ == "__main__":
    main()
