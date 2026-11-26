# --- InvestTimer: Fehlermeldungen aus dem Browser (Nachtrag 3, 19.11.2026) --------
# POST /v1/investtimer/fehler: Meldung, gekuerzter Stack (ohne Query-Strings), Ansicht, App-Version, Geraet grob.
# Keine E-Mail, keine Nutzer-ID, keine Eingabetexte. Zusammengefasst je Fingerabdruck (Meldung + Datei + Zeile), gezaehlt,
# 30 Tage aufbewahrt (SQLite /var/lib/investtimer/fehler.db). Neuer Fehler: sofort Mail an info@investtimer.net,
# hoechstens eine Mail je Fehlerart und Tag. Limit 30 Meldungen je IP und Stunde. Schalter .env: IT_FEHLER_TEST=1 (Betreff "TEST").
import sqlite3 as _sql3
IT_FEHLER_DB = os.environ.get("IT_FEHLER_DB", "/var/lib/investtimer/fehler.db")
_it_fehler_ip = {}


def _it_fehler_db():
    db = _sql3.connect(IT_FEHLER_DB, timeout=5)
    db.execute("CREATE TABLE IF NOT EXISTS fehler (fp TEXT PRIMARY KEY, meldung TEXT, datei TEXT, zeile INTEGER, stack TEXT, ansicht TEXT,"
               " version TEXT, geraet TEXT, anzahl INTEGER, erst TEXT, zuletzt TEXT, gemeldet TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS tage (tag TEXT, fp TEXT, anzahl INTEGER, PRIMARY KEY (tag, fp))")
    if "umfeld" not in {r[1] for r in db.execute("PRAGMA table_info(fehler)")}:
        db.execute("ALTER TABLE fehler ADD COLUMN umfeld TEXT")
    return db


def _it_umfeld(u):
    """Umfeld ohne Personenbezug (Block E, 25.11.2026): nur feste Felder, Werte streng gefiltert."""
    if not isinstance(u, dict):
        return ""
    teile = []
    for k in ("score", "stage"):
        try:
            teile.append("%s=%d" % (k, max(0, min(99, int(u.get(k))))))
        except (TypeError, ValueError):
            pass
    for k in ("uebersetzt", "erweiterung", "webdriver"):
        if u.get(k) in ("ja", "nein"):
            teile.append("%s=%s" % (k, u[k]))
    if u.get("sichtbar") in ("visible", "hidden", "prerender"):
        teile.append("sichtbar=" + u["sichtbar"])
    ref = _re.sub(r"[^a-z0-9.\-]", "", str(u.get("ref") or "").lower())[:80]
    if ref:
        teile.append("ref=" + ref)
    return " ".join(teile)


def _it_kurz(text, n):
    return _re.sub(r"\?[^\s:)]*", "", str(text or ""))[:n]


@app.post("/v1/investtimer/fehler")
async def it_fehler(request: Request):
    stunde = time.strftime("%Y-%m-%d %H")
    ip = _it_client_ip(request)
    stand = _it_fehler_ip.get(ip)
    if not stand or stand[0] != stunde:
        stand = [stunde, 0]
    if stand[1] >= 30:
        return _JSONResp({"error": "limit"}, status_code=429)
    stand[1] += 1
    if len(_it_fehler_ip) > 20000:
        _it_fehler_ip.clear()
    _it_fehler_ip[ip] = stand
    d = await _it_json(request)
    meldung = _it_kurz(d.get("meldung"), 300).strip()
    if not meldung:
        return _JSONResp({"error": "leer"}, status_code=400)
    datei = _re.sub(r"^https?://[^/]+", "", _it_kurz(d.get("datei"), 200))
    try:
        zeile = int(d.get("zeile") or 0)
    except (TypeError, ValueError):
        zeile = 0
    stack = _re.sub(r"https?://[^/\s)]+", "", _it_kurz(d.get("stack"), 1500))
    ansicht = _re.sub(r"[^a-z]", "", str(d.get("ansicht") or ""))[:20]
    version = _re.sub(r"[^0-9A-Za-z.\-]", "", str(d.get("version") or ""))[:40]
    geraet = _re.sub(r"[^A-Za-z ,]", "", str(d.get("geraet") or ""))[:60]
    umfeld = _it_umfeld(d.get("umfeld"))
    fp = _hl.sha1(("%s|%s|%s" % (_re.sub(r"\d+", "#", meldung), datei, zeile)).encode()).hexdigest()[:16]
    jetzt, heute = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), time.strftime("%Y-%m-%d", time.gmtime())
    mail = False
    try:
        with _it_fehler_db() as db:
            db.execute("DELETE FROM fehler WHERE zuletzt < ?", (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30 * 86400)),))
            db.execute("DELETE FROM tage WHERE tag < ?", (time.strftime("%Y-%m-%d", time.gmtime(time.time() - 30 * 86400)),))
            alt = db.execute("SELECT gemeldet FROM fehler WHERE fp=?", (fp,)).fetchone()
            if alt is None:
                db.execute("INSERT INTO fehler (fp, meldung, datei, zeile, stack, ansicht, version, geraet, anzahl, erst, zuletzt, gemeldet, umfeld)"
                           " VALUES (?,?,?,?,?,?,?,?,1,?,?,NULL,?)", (fp, meldung, datei, zeile, stack, ansicht, version, geraet, jetzt, jetzt, umfeld))
                mail = True
            else:
                db.execute("UPDATE fehler SET anzahl=anzahl+1, zuletzt=?, version=?, geraet=?, ansicht=?, umfeld=? WHERE fp=?", (jetzt, version, geraet, ansicht, umfeld, fp))
            db.execute("INSERT INTO tage VALUES (?,?,1) ON CONFLICT(tag, fp) DO UPDATE SET anzahl=anzahl+1", (heute, fp))
            if mail:
                db.execute("UPDATE fehler SET gemeldet=? WHERE fp=?", (heute, fp))
    except Exception as e:
        print(f"[investtimer] fehler: DB {type(e).__name__}", flush=True)
        return _JSONResp({"error": "intern"}, status_code=500)
    if mail:
        key = _it_resend()
        text = ("Neuer Fehler auf investtimer.net (erstmals gemeldet %s UTC)\n\nMeldung: %s\nDatei/Zeile: %s:%s\nAnsicht: %s\nVersion: %s\nGeraet: %s\nUmfeld: %s\n\nStack:\n%s\n\n"
                "Fingerabdruck %s. Weitere Meldungen derselben Art werden nur gezaehlt (Wochenbericht)." % (jetzt, meldung, datei or "-", zeile, ansicht or "-", version or "-", geraet or "-", umfeld or "-", stack or "-", fp))
        try:
            if key:
                _rq.post(os.environ.get("IT_RESEND_API", "https://api.resend.com") + "/emails", timeout=15, headers={"Authorization": "Bearer " + key},
                         json={"from": "InvestTimer Fehler <fehler@investtimer.net>", "to": [_it_env("IT_FEHLER_AN") or "info@investtimer.net"],
                               "subject": ("TEST " if _it_env("IT_FEHLER_TEST") == "1" else "") + "InvestTimer: neuer Fehler · " + meldung[:80], "text": text})
        except Exception as e:
            print(f"[investtimer] fehler: Mail {type(e).__name__}", flush=True)
    return {"ok": True, "neu": mail}
