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
IT_TEILEN_AKTUELL_DIR = os.environ.get("IT_TEILEN_AKTUELL_DIR", "/var/lib/investtimer/teilen-aktuell")
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
        return _it_teilen_aktuell(name)
    m = _it_t_manifest()
    if not m:
        return _JSONResp({"error": "noch_nicht"}, status_code=503)
    if art == "phase" and phase not in (m.get("phasen") or {}):
        return _JSONResp({"error": "phase"}, status_code=404)
    return _TRedirect("/teilen/%s/%s.png" % (m["asOf"], name), status_code=302, headers={"Cache-Control": "public, max-age=600"})


_it_teilen_sperre = __import__("threading").Lock()


def _it_teilen_aktuell(name):
    """Bild mit aktuellem Stand (nur IT_TEILEN_AKTUELL=1 und Login): einmal je Tag und Variante rendern, privat ablegen."""
    import sys as _sys
    tag = _kilim.tag()
    ordner = os.path.join(IT_TEILEN_AKTUELL_DIR, tag)
    datei = os.path.join(ordner, name + ".png")
    if not os.path.exists(datei):
        with _it_teilen_sperre:
            if not os.path.exists(datei):
                if IT_TEILEN_SERVER not in _sys.path:
                    _sys.path.insert(0, IT_TEILEN_SERVER)
                import teilen_bilder as _tb
                get_current_indicators()
                live = marktstress.payload_from_rows(_cache["haupt"], _cache.get("stress_cfg"))
                hist = _it_historie_daten()
                d = {"wert": int(live["rounded"]), "asOf": hist["taeglich"][-1][0] if hist.get("taeglich") else tag, "historie": hist}
                eintrag = next((v for v in _tb.varianten(d) if v[0] == name), None)
                if not eintrag:
                    return _JSONResp({"error": "variante"}, status_code=404)
                h = eintrag[1](*eintrag[2])
                if h is None:
                    return _JSONResp({"error": "variante"}, status_code=404)
                os.makedirs(ordner, mode=0o700, exist_ok=True)
                _tb.rendern(h, *_tb.FORMATE["quer" if "-quer-" in name else "hoch"], datei)
                print(f"[investtimer] Teilen aktuell gerendert: {name}", flush=True)
    return _TFile(datei, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/v1/investtimer/teilen/s/{pfad:path}")
def it_teilen_seite(request: Request, pfad: str, l: str = "de", utm_source: str = "", utm_medium: str = ""):
    sp = "en" if l == "en" else "de"
    t = _IT_TEXTE[sp]
    teile = [p for p in pfad.split("/") if p]
    medium = _re.sub(r"[^a-z0-9-]", "", (utm_medium or "link").lower())[:20] or "link"
    utm = "utm_source=teilen&utm_medium=" + medium + ("&lang=en" if sp == "en" else "")
    datum = None
    if teile[:1] == ["wert"] and len(teile) <= 2:
        datum = teile[1] if len(teile) == 2 else None
        m = _it_t_manifest(datum)
        if not m:
            return _TRedirect("/", status_code=302)
        s = _it_t_stufe(m["wert"])
        titel = t["wert"].format(w=m["wert"], s=t["stufen"][s])
        text = t["stand"].format(d=_it_t_datum(m["asOf"], sp)) + " " + t["zusatz"]
        bild = "wert-quer-" + sp
        ziel = "/?" + utm
    elif teile[:1] == ["verlauf"] and len(teile) in (2, 3) and teile[1] in _IT_SPANNEN:
        z = teile[1]
        datum = teile[2] if len(teile) == 3 else None
        m = _it_t_manifest(datum)
        if not m:
            return _TRedirect("/#verlauf", status_code=302)
        titel = t["verlauf"].format(z=t["spannen"][z])
        text = t["stand"].format(d=_it_t_datum((m.get("spannen") or {}).get(z) or m["asOf"], sp)) + " " + t["zusatz"]
        bild = "verlauf-%s-quer-%s" % (z, sp)
        ziel = "/?z=%s&%s#verlauf" % (z, utm)
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
    ordner = m["asOf"]
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
