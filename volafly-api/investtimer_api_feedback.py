# --- InvestTimer: Feedback-/Kontaktformular (Nachtrag 2, 19.11.2026) ---------
# POST /v1/investtimer/feedback -> Mail ueber Resend an info@investtimer.net, Reply-To = angegebene Adresse.
# Nichts wird dauerhaft gespeichert (nur Zaehler je IP/Konto und Tag im Speicher). Spamschutz ohne Fremdanbieter:
# Honeypot-Feld, Mindestzeit 3 s zwischen Oeffnen und Absenden, 5 Nachrichten je IP und Tag, 10 je Konto und Tag.
# Schalter in .env: IT_FEEDBACK_AN (Ziel, Standard info@investtimer.net), IT_FEEDBACK_TEST=1 (Betreff beginnt mit "TEST").
IT_FB_KATEGORIEN = {"idee": "Idee", "kritik": "Kritik", "fehler": "Fehler gefunden", "sonstiges": "Sonstiges"}
IT_FB_LIMIT_IP, IT_FB_LIMIT_KONTO, IT_FB_MIN_MS = 5, 10, 3000
_it_fb_ip, _it_fb_konto = {}, {}


def _it_fb_zaehlen(tabelle, schluessel, limit):
    heute = time.strftime("%Y-%m-%d")
    stand = tabelle.get(schluessel)
    if not stand or stand[0] != heute:
        stand = [heute, 0]
    if stand[1] >= limit:
        return False
    if len(tabelle) > 20000:
        for k in [k for k, v in tabelle.items() if v[0] != heute]:
            del tabelle[k]
    stand[1] += 1
    tabelle[schluessel] = stand
    return True


@app.post("/v1/investtimer/feedback")
async def it_feedback(request: Request):
    d = await _it_json(request)
    # Honeypot: Bots fuellen das versteckte Feld; Antwort sieht aus wie Erfolg, es wird nichts versendet
    if str(d.get("website") or "").strip():
        print("[investtimer] feedback: honeypot", flush=True)
        return {"ok": True}
    try:
        dauer = int(d.get("dauer") or 0)
    except (TypeError, ValueError):
        dauer = 0
    if dauer < IT_FB_MIN_MS:
        return _JSONResp({"error": "zu_schnell"}, status_code=400)
    kategorie = IT_FB_KATEGORIEN.get(str(d.get("kategorie") or ""), "")
    nachricht = str(d.get("nachricht") or "").strip()
    email = str(d.get("email") or "").strip()[:200]
    if not kategorie or not (10 <= len(nachricht) <= 2000):
        return _JSONResp({"error": "leer"}, status_code=400)
    if email and not _re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return _JSONResp({"error": "email"}, status_code=400)
    uid = _it_check_user(request.headers.get("authorization")) if request.headers.get("authorization") else None
    if not _it_fb_zaehlen(_it_fb_ip, _it_client_ip(request), IT_FB_LIMIT_IP):
        return _JSONResp({"error": "limit"}, status_code=429)
    if uid and not _it_fb_zaehlen(_it_fb_konto, uid, IT_FB_LIMIT_KONTO):
        return _JSONResp({"error": "limit"}, status_code=429)
    sprache = "en" if str(d.get("sprache") or "").lower().startswith("en") else "de"
    ansicht = _re.sub(r"[^a-z#-]", "", str(d.get("ansicht") or ""))[:20] or "-"
    version = _re.sub(r"[^0-9A-Za-z.\-]", "", str(d.get("version") or ""))[:40] or "-"
    text = ("Kategorie: %s\nSprache: %s\nAnsicht: %s\nApp-Version: %s\nEingeloggt: %s\nAntwort an: %s\n\n%s\n"
            % (kategorie, sprache, ansicht, version, "ja" if uid else "nein", email or "(keine Adresse angegeben)", nachricht))
    betreff = ("TEST " if _it_env("IT_FEEDBACK_TEST") == "1" else "") + "InvestTimer Feedback · " + kategorie
    daten = {"from": "InvestTimer Feedback <feedback@investtimer.net>", "to": [_it_env("IT_FEEDBACK_AN") or "info@investtimer.net"],
             "subject": betreff, "text": text}
    if email:
        daten["reply_to"] = email
    key = _it_resend()
    if not key:
        return _JSONResp({"error": "versand"}, status_code=503)
    try:
        r = _rq.post(os.environ.get("IT_RESEND_API", "https://api.resend.com") + "/emails", json=daten,
                     headers={"Authorization": "Bearer " + key}, timeout=15)
        if r.status_code >= 300:
            print(f"[investtimer] feedback: Resend {r.status_code}", flush=True)
            return _JSONResp({"error": "versand"}, status_code=502)
    except Exception as e:
        print(f"[investtimer] feedback: {type(e).__name__}", flush=True)
        return _JSONResp({"error": "versand"}, status_code=502)
    print(f"[investtimer] feedback gesendet ({kategorie}, {'konto' if uid else 'gast'})", flush=True)
    return {"ok": True}
