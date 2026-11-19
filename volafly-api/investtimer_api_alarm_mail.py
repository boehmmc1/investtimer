# --- InvestTimer: E-Mail-Alarm abbestellen ohne Login (signierter Link, One-Click) ---
_IT_ABMELDE_SEITE = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>__TITEL__ · InvestTimer</title>
<style>body{margin:0;background:#f8f8f3;color:#1c2f2b;font:16px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
main{max-width:560px;margin:0 auto;padding:40px 20px}h1{font-size:26px;line-height:1.3}
button{min-height:52px;width:100%;border:0;border-radius:10px;background:#2f6b5c;color:#fff;font:600 17px inherit;font-family:inherit;cursor:pointer}
a{color:#2f6b5c}p.klein{font-size:14px;color:#5b6b66}</style></head><body><main>__INHALT__</main></body></html>"""


_IT_ABMELDE_TEXTE = {
    "de": {"titel": "E-Mail-Alarm abbestellen",
           "ungueltig": "<h1>Link nicht mehr gültig</h1><p>Diesen Alarm gibt es nicht mehr oder der Link ist unvollständig. "
                        "Deine Alarme verwaltest du auf <a href=\"https://investtimer.net/\">investtimer.net</a> unter „Marktstress abonnieren“.</p>",
           "frage": "<h1>E-Mails zu diesem Alarm abbestellen?</h1><p>Du bekommst dann zu diesem einen Alarm keine E-Mails mehr. "
                    "Push-Mitteilungen und andere Alarme bleiben, wie sie sind.</p>",
           "knopf": "E-Mails abbestellen",
           "klein": "Ohne Anmeldung. Alle Alarme verwaltest du auf <a href=\"https://investtimer.net/\">investtimer.net</a>.",
           "fertig": "<h1>Erledigt.</h1><p>Zu diesem Alarm bekommst du keine E-Mails mehr. "
                     "Deine Alarme verwaltest du auf <a href=\"https://investtimer.net/\">investtimer.net</a> unter „Marktstress abonnieren“.</p>"},
    "en": {"titel": "Unsubscribe from alert emails",
           "ungueltig": "<h1>This link is no longer valid</h1><p>The alert no longer exists or the link is incomplete. "
                        "Manage your alerts at <a href=\"https://investtimer.net/\">investtimer.net</a> under “Set up alerts”.</p>",
           "frage": "<h1>Stop emails for this alert?</h1><p>You won’t get any more emails for this alert. "
                    "Push notifications and your other alerts stay as they are.</p>",
           "knopf": "Unsubscribe",
           "klein": "No sign-in needed. Manage all alerts at <a href=\"https://investtimer.net/\">investtimer.net</a>.",
           "fertig": "<h1>Done.</h1><p>You won’t get any more emails for this alert. "
                     "Manage your alerts at <a href=\"https://investtimer.net/\">investtimer.net</a> under “Set up alerts”.</p>"},
}


def _it_abmelde_antwort(inhalt, status=200, l="de"):
    sp = "en" if l == "en" else "de"
    seite = _IT_ABMELDE_SEITE.replace("__LANG__", sp).replace("__TITEL__", _IT_ABMELDE_TEXTE[sp]["titel"])
    return _Resp(seite.replace("__INHALT__", inhalt), status_code=status, media_type="text/html; charset=utf-8",
                 headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex",
                          "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})


@app.get("/v1/investtimer/alarm-abmelden")
def it_alarm_abmelden_seite(a: str = "", t: str = "", l: str = ""):
    tx = _IT_ABMELDE_TEXTE["en" if l == "en" else "de"]
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
        return _it_abmelde_antwort(tx["ungueltig"], 404, l)
    return _it_abmelde_antwort(tx["frage"] + '<form method="post" action="/api/alarm-abmelden?a=%d&amp;t=%s%s"><button type="submit">%s</button></form>'
                               '<p class="klein">%s</p>' % (a_int, _h.escape(t), "&amp;l=en" if l == "en" else "", tx["knopf"], tx["klein"]), 200, l)


@app.post("/v1/investtimer/alarm-abmelden")
def it_alarm_abmelden(a: str = "", t: str = "", l: str = ""):
    tx = _IT_ABMELDE_TEXTE["en" if l == "en" else "de"]
    """Abbestellen per Formular oder One-Click (RFC 8058, List-Unsubscribe-Post)."""
    try:
        ergebnis = _alarme.per_link_abmelden(a, t)
    except _alarme.Fehler:
        return _it_abmelde_antwort(tx["ungueltig"], 404, l)
    print(f"[investtimer] E-Mail-Alarm abbestellt ({ergebnis})", flush=True)
    return _it_abmelde_antwort(tx["fertig"], 200, l)
