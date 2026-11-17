# --- InvestTimer: E-Mail-Alarm abbestellen ohne Login (signierter Link, One-Click) ---
_IT_ABMELDE_SEITE = """<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>E-Mail-Alarm abbestellen · InvestTimer</title>
<style>body{margin:0;background:#f8f8f3;color:#1c2f2b;font:16px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
main{max-width:560px;margin:0 auto;padding:40px 20px}h1{font-size:26px;line-height:1.3}
button{min-height:52px;width:100%;border:0;border-radius:10px;background:#2f6b5c;color:#fff;font:600 17px inherit;font-family:inherit;cursor:pointer}
a{color:#2f6b5c}p.klein{font-size:14px;color:#5b6b66}</style></head><body><main>__INHALT__</main></body></html>"""


def _it_abmelde_antwort(inhalt, status=200):
    return _Resp(_IT_ABMELDE_SEITE.replace("__INHALT__", inhalt), status_code=status, media_type="text/html; charset=utf-8",
                 headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex",
                          "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})


@app.get("/v1/investtimer/alarm-abmelden")
def it_alarm_abmelden_seite(a: str = "", t: str = ""):
    """Link aus der Mail: Bestaetigungsseite (ein Klick). GET aendert nichts, damit Link-Scanner nichts abbestellen."""
    import html as _h
    try:
        a_int = int(a)
    except ValueError:
        a_int = -1
    gueltig = False
    try:
        with _alarme.verbinden() as db:
            r = db.execute("SELECT uid FROM alarme WHERE id=?", (a_int,)).fetchone()
        gueltig = bool(r) and _hmac.compare_digest(_alarme.abmelde_token(a_int, r["uid"]), t)
    except Exception:
        pass
    if not gueltig:
        return _it_abmelde_antwort("<h1>Link nicht mehr gültig</h1><p>Diesen Alarm gibt es nicht mehr oder der Link ist unvollständig. "
                                   "Deine Alarme verwaltest du auf <a href=\"https://investtimer.net/\">investtimer.net</a> unter „Marktstress abonnieren“.</p>", 404)
    return _it_abmelde_antwort('<h1>E-Mails zu diesem Alarm abbestellen?</h1><p>Du bekommst dann zu diesem einen Alarm keine E-Mails mehr. '
                               'Push-Mitteilungen und andere Alarme bleiben, wie sie sind.</p>'
                               '<form method="post" action="/api/alarm-abmelden?a=%d&amp;t=%s"><button type="submit">E-Mails abbestellen</button></form>'
                               '<p class="klein">Ohne Anmeldung. Alle Alarme verwaltest du auf <a href="https://investtimer.net/">investtimer.net</a>.</p>'
                               % (a_int, _h.escape(t)))


@app.post("/v1/investtimer/alarm-abmelden")
def it_alarm_abmelden(a: str = "", t: str = ""):
    """Abbestellen per Formular oder One-Click (RFC 8058, List-Unsubscribe-Post)."""
    try:
        ergebnis = _alarme.per_link_abmelden(a, t)
    except _alarme.Fehler:
        return _it_abmelde_antwort("<h1>Link nicht mehr gültig</h1><p>Diesen Alarm gibt es nicht mehr oder der Link ist unvollständig.</p>", 404)
    print(f"[investtimer] E-Mail-Alarm abbestellt ({ergebnis})", flush=True)
    return _it_abmelde_antwort("<h1>Erledigt.</h1><p>Zu diesem Alarm bekommst du keine E-Mails mehr. "
                               "Deine Alarme verwaltest du auf <a href=\"https://investtimer.net/\">investtimer.net</a> unter „Marktstress abonnieren“.</p>")
