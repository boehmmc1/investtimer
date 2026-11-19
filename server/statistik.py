#!/usr/bin/env python3
"""Nutzungsauswertung ohne Cookies (Nachtrag 3): aus den nginx-Protokollen von investtimer.net.

Quellen (nur auf dem Server):
  /var/log/nginx/investtimer-statistik.log*   Seitenaufrufe mit gekuerzter IP (nginx-Format it_anon, keine Query-Strings)
  /var/log/nginx/investtimer-ansichten.log*   Ansichtswechsel (Zaehlaufruf /api/v ohne IP und ohne Kennung)
  /var/lib/investtimer/fehler.db              Fehlermeldungen aus dem Browser (Zaehlung)
  Supabase (Admin-API, nur Zaehlung)          Registrierungen und Anmeldungen im Zeitraum
Ausgaben:
  --bericht   HTML-Bericht nach /var/lib/investtimer/statistik/index.html (Basic-Auth, nicht verlinkt)
  --woche     Kurzzusammenfassung der letzten 7 Tage mit Vorwochenvergleich per Mail an info@investtimer.net
  --test      Mail mit "TEST" im Betreff
Keine IP-Adressen in Bericht oder Mail; Besucher werden nur als Anzahl unterschiedlicher gekuerzter IP+Browser je Tag geschaetzt.
"""
import collections, glob, gzip, html, json, os, re, sqlite3, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

LOG = "/var/log/nginx/investtimer-statistik.log*"
ANSICHTEN = "/var/log/nginx/investtimer-ansichten.log*"
FEHLER_DB = os.environ.get("IT_FEHLER_DB", "/var/lib/investtimer/fehler.db")
ZIEL = os.environ.get("IT_STATISTIK_DIR", "/var/lib/investtimer/statistik")
ZEILE = re.compile(r'^(\S+) \[([^\]]+)\] "(\S+) ([^"]*)" (\d{3}) "([^"]*)" "([^"]*)" "([^"]*)"')
BOT = re.compile(r"(?i)bot|crawl|spider|slurp|preview|facebookexternalhit|curl|python|wget|headless|monitor|uptime")


def lesen(muster):
    for pfad in sorted(glob.glob(muster)):
        oeffnen = gzip.open if pfad.endswith(".gz") else open
        try:
            with oeffnen(pfad, "rt", encoding="utf-8", errors="replace") as f:
                yield from f
        except OSError:
            continue


def geraet(ua):
    return "Handy" if re.search(r"(?i)iphone|android.+mobile|mobile", ua) else "Tablet" if re.search(r"(?i)ipad|android|tablet", ua) else "Computer"


def auswerten(von, bis):
    """Kennzahlen fuer [von, bis] (date, einschliesslich)."""
    tage = collections.Counter(); besucher = collections.defaultdict(set); geraete = collections.Counter()
    sprachen = collections.Counter(); quellen = collections.Counter()
    for z in lesen(LOG):
        m = ZEILE.match(z)
        if not m:
            continue
        ip, zeit, methode, pfad, status, ref, ua, al = m.groups()
        tag = zeit[:10]
        if not (von.isoformat() <= tag <= bis.isoformat()) or methode != "GET" or pfad not in ("/", "/index.html") or status != "200" or BOT.search(ua):
            continue
        tage[tag] += 1; besucher[tag].add(ip + ua); geraete[geraet(ua)] += 1
        sprachen[(al[:2] or "?").lower()] += 1
        host = re.sub(r"^https?://([^/]+).*", r"\1", ref) if ref and ref != "-" else ""
        if host and "investtimer.net" not in host:
            quellen[host.replace("www.", "")] += 1
    ansichten = collections.Counter(); ansicht_sprache = collections.Counter(); ansicht_geraet = collections.Counter()
    for z in lesen(ANSICHTEN):
        teile = z.split()
        if len(teile) < 4 or not (von.isoformat() <= teile[0][:10] <= bis.isoformat()):
            continue
        ansichten[teile[1]] += 1; ansicht_sprache[teile[2]] += 1; ansicht_geraet[teile[3]] += 1
    fehler = {"meldungen": 0, "arten": 0, "neu": 0}
    try:
        db = sqlite3.connect(FEHLER_DB)
        r = db.execute("SELECT COALESCE(SUM(anzahl),0), COUNT(DISTINCT fp) FROM tage WHERE tag BETWEEN ? AND ?", (von.isoformat(), bis.isoformat())).fetchone()
        fehler = {"meldungen": r[0], "arten": r[1],
                  "neu": db.execute("SELECT COUNT(*) FROM fehler WHERE substr(erst,1,10) BETWEEN ? AND ?", (von.isoformat(), bis.isoformat())).fetchone()[0],
                  "haeufigste": db.execute("SELECT f.meldung, SUM(t.anzahl) n FROM tage t JOIN fehler f ON f.fp=t.fp WHERE t.tag BETWEEN ? AND ? GROUP BY t.fp ORDER BY n DESC LIMIT 3",
                                           (von.isoformat(), bis.isoformat())).fetchall()}
    except sqlite3.Error:
        pass
    return {"von": von.isoformat(), "bis": bis.isoformat(), "aufrufe": sum(tage.values()), "besucher": sum(len(v) for v in besucher.values()),
            "tage": {t: [tage[t], len(besucher[t])] for t in sorted(tage)}, "geraete": geraete.most_common(), "sprachen": sprachen.most_common(5),
            "quellen": quellen.most_common(8), "ansichten": ansichten.most_common(), "ansicht_sprache": ansicht_sprache.most_common(),
            "ansicht_geraet": ansicht_geraet.most_common(), "konten": konten(von, bis), "fehler": fehler}


def konten(von, bis):
    """Registrierungen und Anmeldungen im Zeitraum (nur Zahlen) ueber die Supabase-Admin-API; service_role nur zur Laufzeit."""
    try:
        token = open("/root/.investtimer/supabase-token").read().strip()
        url = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deploy", "supabase.json")))["url"].rstrip("/")
        ref = url.split("//", 1)[1].split(".", 1)[0]
        req = urllib.request.Request("https://api.supabase.com/v1/projects/%s/api-keys" % ref, headers={"Authorization": "Bearer " + token, "User-Agent": "investtimer-statistik"})
        key = next(k["api_key"] for k in json.load(urllib.request.urlopen(req, timeout=15)) if k.get("name") == "service_role")
        reg = anm = gesamt = 0
        for seite in range(1, 50):
            req = urllib.request.Request(url + "/auth/v1/admin/users?page=%d&per_page=200" % seite, headers={"apikey": key, "Authorization": "Bearer " + key})
            nutzer = json.load(urllib.request.urlopen(req, timeout=15)).get("users", [])
            for n in nutzer:
                gesamt += 1
                if von.isoformat() <= (n.get("created_at") or "")[:10] <= bis.isoformat():
                    reg += 1
                if von.isoformat() <= (n.get("last_sign_in_at") or "")[:10] <= bis.isoformat():
                    anm += 1
            if len(nutzer) < 200:
                break
        return {"registrierungen": reg, "angemeldet": anm, "konten_gesamt": gesamt}
    except Exception as e:
        return {"fehler": type(e).__name__}


NAMEN = {"stress": "Marktstress", "ki": "KI", "verlauf": "Verlauf", "konto": "Konto", "feedback": "Feedback", "faq": "Häufige Fragen"}


def mail_text(w, v):
    d = lambda a, b: ("+%d" % (a - b) if a >= b else "%d" % (a - b))
    k, kv = w["konten"], v["konten"]
    zeilen = ["InvestTimer – Woche %s bis %s" % (w["von"], w["bis"]), "",
              "Seitenaufrufe: %d (Vorwoche %d, %s)" % (w["aufrufe"], v["aufrufe"], d(w["aufrufe"], v["aufrufe"])),
              "Besucher (geschätzt, je Tag eindeutig): %d (Vorwoche %d)" % (w["besucher"], v["besucher"]),
              "Registrierungen: %s (Vorwoche %s) · Anmeldungen: %s · Konten gesamt: %s" % (k.get("registrierungen", "?"), kv.get("registrierungen", "?"), k.get("angemeldet", "?"), k.get("konten_gesamt", "?")),
              "", "Top-Ansichten:"] + ["  %s: %d" % (NAMEN.get(a, a), n) for a, n in w["ansichten"][:6]] + [
              "", "Geräte: " + ", ".join("%s %d" % g for g in w["geraete"]), "Sprache (Ansichten): " + ", ".join("%s %d" % s for s in w["ansicht_sprache"]),
              "Verweisquellen: " + (", ".join("%s %d" % q for q in w["quellen"][:5]) or "keine"), "",
              "Fehler aus dem Browser: %d Meldungen, %d Arten, davon %d neu (Vorwoche %d Meldungen)" % (w["fehler"].get("meldungen", 0), w["fehler"].get("arten", 0), w["fehler"].get("neu", 0), v["fehler"].get("meldungen", 0))]
    for m, n in w["fehler"].get("haeufigste", []) or []:
        zeilen.append("  %dx %s" % (n, m[:100]))
    zeilen += ["", "Ausführlicher Bericht: nur auf dem Server bzw. hinter Basic-Auth (Adresse in /root/.investtimer/statistik-zugang).",
               "Ohne Cookies, ohne Kennungen; IP-Adressen gekürzt."]
    return "\n".join(zeilen)


def bericht_html(e):
    def tab(titel, zeilen):
        return "<h2>%s</h2><table>%s</table>" % (titel, "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(str(a)), html.escape(str(b))) for a, b in zeilen) or "<tr><td>—</td></tr>")
    return ("<!doctype html><html lang=de><meta charset=utf-8><meta name=robots content=noindex><title>InvestTimer Statistik</title>"
            "<style>body{font:15px/1.5 system-ui;margin:24px;max-width:760px;color:#1b3330;background:#f8f8f3}table{border-collapse:collapse;margin:0 0 18px}"
            "td{padding:4px 14px 4px 0;border-bottom:1px solid #dfe5db}h2{font-size:16px;margin:22px 0 6px}</style>"
            "<h1>InvestTimer · %s bis %s</h1><p>Erstellt %s UTC. Ohne Cookies, IP-Adressen gekürzt, Bots ausgefiltert.</p>" % (e["von"], e["bis"], datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M"))
            + tab("Aufrufe je Tag (Seitenaufrufe / Besucher geschätzt)", [(t, "%d / %d" % tuple(v)) for t, v in e["tage"].items()])
            + tab("Ansichten", [(NAMEN.get(a, a), n) for a, n in e["ansichten"]]) + tab("Geräte", e["geraete"]) + tab("Ansichten nach Gerät", e["ansicht_geraet"])
            + tab("Sprache (Browser)", e["sprachen"]) + tab("Sprache (Seite)", e["ansicht_sprache"]) + tab("Verweisquellen", e["quellen"])
            + tab("Konten (Zählung)", list(e["konten"].items())) + tab("Fehler aus dem Browser", [(k, v) for k, v in e["fehler"].items() if k != "haeufigste"]))


def senden(betreff, text):
    key = open(os.environ.get("IT_RESEND_KEY", "/root/.investtimer/resend-key")).read().strip()
    req = urllib.request.Request("https://api.resend.com/emails", method="POST", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "investtimer-statistik"},
                                 data=json.dumps({"from": "InvestTimer Statistik <statistik@investtimer.net>", "to": [os.environ.get("IT_STATISTIK_AN", "info@investtimer.net")],
                                                  "subject": betreff, "text": text}).encode())
    return json.load(urllib.request.urlopen(req, timeout=20)).get("id")


def main():
    heute = datetime.now(timezone.utc).date()
    if "--bericht" in sys.argv:
        e = auswerten(heute - timedelta(days=29), heute)
        os.makedirs(ZIEL, exist_ok=True)
        open(os.path.join(ZIEL, "index.html"), "w", encoding="utf-8").write(bericht_html(e))
        os.chmod(os.path.join(ZIEL, "index.html"), 0o644)
        print("Bericht:", e["aufrufe"], "Aufrufe,", sum(n for _, n in e["ansichten"]), "Ansichtswechsel")
    if "--woche" in sys.argv:
        bis = heute if "--bis-heute" in sys.argv else heute - timedelta(days=1)  # --bis-heute nur fuer Tests
        w, v = auswerten(bis - timedelta(days=6), bis), auswerten(bis - timedelta(days=13), bis - timedelta(days=7))
        text = mail_text(w, v)
        print(text)
        if "--nur-anzeigen" not in sys.argv:
            print("Mail:", senden(("TEST " if "--test" in sys.argv else "") + "InvestTimer Wochenzahlen %s–%s" % (w["von"], w["bis"]), text))


if __name__ == "__main__":
    main()
