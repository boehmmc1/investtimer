# --- InvestTimer: Teilen (Auftrag C, 20.11.2026) ---------------------------------
# GET /v1/investtimer/teilen/bild?art=wert|verlauf|phase&zeitraum=1M|3M|1J|5J|A&phase=<id>&format=quer|hoch&l=de|en
#     -> 302 auf das vorab gerenderte Bild des zeitversetzten Stands (/teilen/<asOf>/<name>.png, server/teilen_bilder.py).
#     Mit IT_TEILEN_AKTUELL=1 und gueltigem Login (&aktuell=1): Bild mit aktuellem Wert/Verlauf bis heute, einmal je Tag
#     (Europe/Berlin) und Variante gerendert, nur mit Token abrufbar (nicht oeffentlich abgelegt).
# GET /v1/investtimer/teilen/s/<pfad> (nginx: /s/...) -> kleine HTML-Seite mit og:/twitter:-Tags, leitet in die App weiter:
#     /s/wert/<datum> -> /, /s/verlauf/<zeitraum>/<datum> -> #verlauf mit Zeitraum, /s/phase/<id> -> #verlauf mit Phase.
#     utm_source/utm_medium werden weitergereicht; die App zaehlt den Besuch cookiefrei ueber /api/v (ohne Kennung).
import html as _thtml
from fastapi.responses import HTMLResponse as _THTML, RedirectResponse as _TRedirect, FileResponse as _TFile

IT_TEILEN_DIR = os.environ.get("IT_TEILEN_DIR", "/var/lib/investtimer/teilen")
IT_TEILEN_SERVER = "/var/www/investtimer/server"
IT_TEILEN_BASIS = "https://investtimer.net"
_IT_SPANNEN = ("1M", "3M", "1J", "5J", "A")
_IT_TEXTE = {
    "de": {"stufen": ["Ruhig", "Moderat", "Erhöht", "Hoch", "Panik"], "monate": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sept.", "Okt.", "Nov.", "Dez."],
           "wert": "Marktstress am US-Aktienmarkt: {w} von 100 ({s})", "stand": "Stand {d}.",
           "verlauf": "Marktstress {z}", "phase_t": "{n}", "phase_d": "Höchster Marktstress {w} am {d}. {u}",
           "unter": "Wieder unter 40 nach {n} Tagen.", "noch": "Noch nicht wieder unter 40.",
           "zusatz": "InvestTimer zeigt, wie angespannt der US-Aktienmarkt ist. Keine Anlageberatung.", "weiter": "Weiter zu InvestTimer",
           "spannen": {"1M": "im letzten Monat", "3M": "in den letzten 3 Monaten", "1J": "in den letzten 12 Monaten", "5J": "in den letzten 5 Jahren", "A": "seit 2006"}},
    "en": {"stufen": ["Calm", "Moderate", "Elevated", "High", "Panic"], "monate": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
           "wert": "Market stress in the US stock market: {w} out of 100 ({s})", "stand": "As of {d}.",
           "verlauf": "Market stress {z}", "phase_t": "{n}", "phase_d": "Highest market stress {w} on {d}. {u}",
           "unter": "Back below 40 after {n} days.", "noch": "Not back below 40 yet.",
           "zusatz": "InvestTimer shows how tense the US stock market is. Not investment advice.", "weiter": "Continue to InvestTimer",
           "spannen": {"1M": "over the past month", "3M": "over the past 3 months", "1J": "over the past 12 months", "5J": "over the past 5 years", "A": "since 2006"}},
}


def _it_t_datum(d, sp):
    from datetime import date as _d
    d = _d.fromisoformat(d)
    m = _IT_TEXTE[sp]["monate"][d.month - 1]
    return "%d. %s %d" % (d.day, m, d.year) if sp == "de" else "%s %d, %d" % (m, d.day, d.year)


def _it_t_stand(m, sp, datum=None):
    """Stand mit Uhrzeit (Live-Stand) oder nur Datum (zeitversetzter Tagesstand)."""
    if m.get("zeit") and not datum:
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        z = _dt.fromisoformat(m["zeit"].replace("Z", "+00:00")).astimezone(_Z("Europe/Berlin"))
        return "%s, %02d:%02d" % (_it_t_datum(z.date().isoformat(), sp), z.hour, z.minute)
    return _it_t_datum(datum or m["asOf"], sp)


def _it_t_stufe(w):
    return sum(w >= g for g in (20, 40, 60, 80))


def _it_t_manifest(datum=None):
    """Manifest des gewuenschten Stands (Datum) oder des neuesten; None, wenn noch nichts gerendert wurde."""
    for ordner in ([datum] if datum and _re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum) else []) + ["aktuell"]:
        try:
            with open(os.path.join(IT_TEILEN_DIR, ordner, "manifest.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return None


def _it_t_name(art, zeitraum, phase, fmt, sp):
    fmt = fmt if fmt in ("quer", "hoch") else "quer"
    sp = "en" if sp == "en" else "de"
    if art == "verlauf":
        return "verlauf-%s-%s-%s" % (zeitraum if zeitraum in _IT_SPANNEN else "1J", fmt, sp)
    if art == "phase":
        return "phase-%s-%s-%s" % (phase, fmt, sp) if _re.fullmatch(r"[a-z0-9]{2,40}", phase or "") else None
    return "wert-%s-%s" % (fmt, sp)


@app.get("/v1/investtimer/teilen/bild")
def it_teilen_bild(request: Request, art: str = "wert", zeitraum: str = "1J", phase: str = "", format: str = "quer", l: str = "de", aktuell: str = ""):
    name = _it_t_name(art, zeitraum, phase, format, l)
    if not name:
        return _JSONResp({"error": "phase"}, status_code=400)
    if aktuell == "1" and _it_env("IT_TEILEN_AKTUELL") == "1":
        uid = _it_check_user(request.headers.get("authorization"))
        if not uid:
            return _JSONResp({"error": "login"}, status_code=401)
        return _it_teilen_live_bild(name)
    m = _it_t_manifest()
    if not m:
        return _JSONResp({"error": "noch_nicht"}, status_code=503)
    if art == "phase" and phase not in (m.get("phasen") or {}):
        return _JSONResp({"error": "phase"}, status_code=404)
    return _TRedirect("/teilen/%s/%s.png" % (m["asOf"], name), status_code=302, headers={"Cache-Control": "public, max-age=600"})


_it_teilen_sperre = __import__("threading").Lock()


def _it_hist_sync(hist, wert, as_of):
    """Verlauf mit dem aktuellen Wert als letztem Punkt (gleiche Quelle wie /api/aktuell): heutiger Tag, laufende Woche und Monat."""
    from datetime import date as _d
    aus = dict(hist)
    for art, schl in (("taeglich", lambda x: x), ("woechentlich", lambda x: _d.fromisoformat(x).isocalendar()[:2]), ("monatlich", lambda x: x[:7])):
        r = list(hist.get(art) or [])
        if r and r[-1][0] <= as_of:
            letzt = r[-1]
            if schl(letzt[0]) == schl(as_of):
                lo, hi = (letzt[4], letzt[5]) if len(letzt) > 5 else (wert, wert)
                r[-1] = [as_of, wert, letzt[2], "a"] + ([min(lo, wert), max(hi, wert)] if len(letzt) > 5 else [])
            else:
                r.append([as_of, wert, 14, "a"] + ([wert, wert] if art != "taeglich" else []))
        aus[art] = r
    return aus


def _it_teilen_live():
    """Aktueller Stand fuer das Teilen (IT_TEILEN_AKTUELL=1, nur mit Login): Ordner /teilen/live/<stamp>/ mit Manifest.
    stamp = Zeitpunkt der Berechnung in Europe/Berlin (JJJJ-MM-TTTHHMM); gleicher Wert wie /api/aktuell."""
    import sys as _sys
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _Z
    roh = _it_aktuell_roh()
    if roh is None:
        return None
    live = json.loads(roh)
    zeit = live.get("berechnetUm") or _dt.utcnow().strftime("%Y-%m-%dT%H:%M:00Z")
    stamp = _dt.fromisoformat(zeit.replace("Z", "+00:00")).astimezone(_Z("Europe/Berlin")).strftime("%Y-%m-%dT%H%M")
    ordner = os.path.join(IT_TEILEN_DIR, "live", stamp)
    if IT_TEILEN_SERVER not in _sys.path:
        _sys.path.insert(0, IT_TEILEN_SERVER)
    import teilen_bilder as _tb
    hist = _it_hist_sync(_it_historie_daten(), int(live["rounded"]), live["asOf"])
    d = {"wert": int(live["rounded"]), "asOf": live["asOf"], "zeit": zeit, "historie": hist}
    mf = os.path.join(ordner, "manifest.json")
    if not os.path.exists(mf):
        with _it_teilen_sperre:
            if not os.path.exists(mf):
                os.makedirs(ordner, exist_ok=True)
                os.chmod(os.path.join(IT_TEILEN_DIR, "live"), 0o755)
                os.chmod(ordner, 0o755)
                m = _tb.manifest(d)
                m["stamp"] = stamp
                with open(mf + ".tmp", "w", encoding="utf-8") as f:
                    json.dump(m, f, ensure_ascii=False)
                os.chmod(mf + ".tmp", 0o644)
                os.replace(mf + ".tmp", mf)
    return {"d": d, "ordner": ordner, "stamp": stamp, "tb": _tb}


def _it_teilen_rendern(stand, name):
    """Ein Bild eines Stands einmal rendern (Sperre); Rueckgabe: Dateipfad oder None."""
    datei = os.path.join(stand["ordner"], name + ".png")
    if not os.path.exists(datei):
        with _it_teilen_sperre:
            if not os.path.exists(datei):
                _tb = stand["tb"]
                eintrag = next((v for v in _tb.varianten(stand["d"]) if v[0] == name), None)
                h = eintrag and eintrag[1](*eintrag[2])
                if not h:
                    return None
                _tb.rendern(h, *_tb.FORMATE["quer" if "-quer-" in name else "hoch"], datei)
                print(f"[investtimer] Teilen live gerendert: {stand['stamp']}/{name}", flush=True)
    return datei


def _it_teilen_live_bild(name):
    stand = _it_teilen_live()
    if not stand:
        return _it_aus()
    if not _it_teilen_rendern(stand, name):
        return _JSONResp({"error": "variante"}, status_code=404)
    return _TRedirect("/teilen/live/%s/%s.png" % (stand["stamp"], name), status_code=302, headers={"Cache-Control": "private, no-store"})


@app.get("/v1/investtimer/teilen/stand")
def it_teilen_stand(request: Request):
    """Fuer das Teilen mit Login: aktueller Stand (Wert, Stufe, Zeitpunkt, Stamp fuer Links). Ohne Schalter: zeitversetzter Stand."""
    uid = _it_check_user(request.headers.get("authorization"))
    if not uid:
        return _JSONResp({"error": "login"}, status_code=401)
    if _it_env("IT_TEILEN_AKTUELL") != "1":
        return _JSONResp({"aktuell": False}, headers={"Cache-Control": "no-store"})
    stand = _it_teilen_live()
    if not stand:
        return _it_aus()
    with open(os.path.join(stand["ordner"], "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)
    m["aktuell"] = True
    return _JSONResp(m, headers={"Cache-Control": "no-store"})


_IT_STAMP = __import__("re").compile(r"\d{4}-\d{2}-\d{2}T\d{4}")


def _it_t_live_manifest(stamp):
    try:
        with open(os.path.join(IT_TEILEN_DIR, "live", stamp, "manifest.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


@app.get("/v1/investtimer/teilen/s/{pfad:path}")
def it_teilen_seite(request: Request, pfad: str, l: str = "de", utm_source: str = "", utm_medium: str = ""):
    sp = "en" if l == "en" else "de"
    t = _IT_TEXTE[sp]
    teile = [p for p in pfad.split("/") if p]
    medium = _re.sub(r"[^a-z0-9-]", "", (utm_medium or "link").lower())[:20] or "link"
    utm = "utm_source=teilen&utm_medium=" + medium + ("&lang=en" if sp == "en" else "")
    datum = None
    live = None
    if teile[:1] in (["wert"], ["verlauf"]) and teile[-1:] and _IT_STAMP.fullmatch(teile[-1]):
        live = _it_t_live_manifest(teile[-1])
    if teile[:1] == ["wert"] and len(teile) <= 2:
        datum = teile[1] if len(teile) == 2 else None
        m = live or _it_t_manifest(datum)
        if not m:
            return _TRedirect("/", status_code=302)
        s = _it_t_stufe(m["wert"])
        titel = t["wert"].format(w=m["wert"], s=t["stufen"][s])
        text = t["stand"].format(d=_it_t_stand(m, sp)) + " " + t["zusatz"]
        bild = "wert-quer-" + sp
        ziel = "/?geteilt=wert&st=%s&%s" % (m.get("stamp") or m["asOf"], utm)
    elif teile[:1] == ["verlauf"] and len(teile) in (2, 3) and teile[1] in _IT_SPANNEN:
        z = teile[1]
        datum = teile[2] if len(teile) == 3 else None
        m = live or _it_t_manifest(datum)
        if not m:
            return _TRedirect("/#verlauf", status_code=302)
        titel = t["verlauf"].format(z=t["spannen"][z])
        text = t["stand"].format(d=_it_t_stand(m, sp, None if live else (m.get("spannen") or {}).get(z))) + " " + t["zusatz"]
        bild = "verlauf-%s-quer-%s" % (z, sp)
        ziel = "/?z=%s&geteilt=verlauf&st=%s&%s#verlauf" % (z, m.get("stamp") or m["asOf"], utm)
    elif teile[:1] == ["phase"] and len(teile) == 2 and _re.fullmatch(r"[a-z0-9]{2,40}", teile[1]):
        m = _it_t_manifest()
        ph = (m or {}).get("phasen", {}).get(teile[1])
        if not ph:
            return _TRedirect("/#verlauf", status_code=302)
        titel = ph["name_en"] if sp == "en" else ph["name"]
        u = t["unter"].format(n=ph["unter40"]["tage"]) if ph.get("unter40") else t["noch"]
        text = t["phase_d"].format(w=ph["spitze"]["w"], d=_it_t_datum(ph["spitze"]["d"], sp), u=u) + " " + t["zusatz"]
        bild = "phase-%s-quer-%s" % (teile[1], sp)
        ziel = "/?phase=%s&%s#verlauf" % (teile[1], utm)
    else:
        return _TRedirect("/", status_code=302)
    ordner = ("live/" + m["stamp"]) if live else m["asOf"]
    if live and not os.path.exists(os.path.join(IT_TEILEN_DIR, ordner, bild + ".png")):
        # Vorschaubild des geteilten Stands fehlt (z. B. nur im Hochformat geteilt): einmal nachrendern
        try:
            import sys as _sys
            if IT_TEILEN_SERVER not in _sys.path:
                _sys.path.insert(0, IT_TEILEN_SERVER)
            import teilen_bilder as _tb
            hist = _it_hist_sync(_it_historie_daten(), int(live["wert"]), live["asOf"])
            _it_teilen_rendern({"d": {"wert": live["wert"], "asOf": live["asOf"], "zeit": live.get("zeit"), "historie": hist},
                                "ordner": os.path.join(IT_TEILEN_DIR, ordner), "stamp": live["stamp"], "tb": _tb}, bild)
        except Exception as e:
            print(f"[investtimer] Teilen Vorschau: {type(e).__name__}", flush=True)
    bild_url = "%s/teilen/%s/%s.png" % (IT_TEILEN_BASIS, ordner, bild)
    adresse = "%s/s/%s%s" % (IT_TEILEN_BASIS, "/".join(teile), "?l=en" if sp == "en" else "")
    e = lambda x: _thtml.escape(str(x), quote=True)
    seite = ("<!doctype html><html lang=\"%(l)s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
             "<title>%(t)s · InvestTimer</title><meta name=\"description\" content=\"%(d)s\"><meta name=\"robots\" content=\"noindex\">"
             "<link rel=\"canonical\" href=\"%(a)s\">"
             "<meta property=\"og:type\" content=\"website\"><meta property=\"og:site_name\" content=\"InvestTimer\">"
             "<meta property=\"og:title\" content=\"%(t)s\"><meta property=\"og:description\" content=\"%(d)s\">"
             "<meta property=\"og:url\" content=\"%(a)s\"><meta property=\"og:image\" content=\"%(b)s\">"
             "<meta property=\"og:image:width\" content=\"1200\"><meta property=\"og:image:height\" content=\"630\"><meta property=\"og:image:alt\" content=\"%(t)s\">"
             "<meta property=\"og:locale\" content=\"%(loc)s\"><meta name=\"twitter:card\" content=\"summary_large_image\">"
             "<meta name=\"twitter:title\" content=\"%(t)s\"><meta name=\"twitter:description\" content=\"%(d)s\"><meta name=\"twitter:image\" content=\"%(b)s\">"
             "<meta http-equiv=\"refresh\" content=\"0;url=%(z)s\"><style>body{font:16px system-ui,sans-serif;background:#f8f8f3;color:#1b3330;padding:40px 24px}"
             "a{color:#2e6d5c}</style></head><body><p><a href=\"%(z)s\">%(w)s</a></p>"
             "<script>location.replace(%(zj)s)</script></body></html>") % dict(
        l=sp, t=e(titel), d=e(text), a=e(adresse), b=e(bild_url), loc="en_US" if sp == "en" else "de_DE", z=e(ziel), zj=json.dumps(ziel), w=e(t["weiter"]))
    return _THTML(seite, headers={"Cache-Control": "public, max-age=300", "X-Robots-Tag": "noindex"})
