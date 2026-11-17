# --- InvestTimer: Kuendigen/Widerrufen ohne Login, Abo-Mails -----------------
# In volafly_chat.py vor /health eingefuegt. Aktiv nur mit IT_PAYWALL=1 (Vertraege moeglich),
# Abo-Mails zusaetzlich mit IT_ABO_MAILS=1.
import investtimer_vertrag as _vertrag

_it_erkl_ip = {}


def _it_resend():
    try:
        with open(os.path.join(os.environ.get("IT_GEHEIM_DIR", "/root/.investtimer"), "resend-key")) as f:
            return f.read().strip()
    except OSError:
        return ""


def _it_email_von_uid(uid):
    try:
        key = _it_service_role()
        r = _rq.get(_it_env("IT_SUPABASE_URL").rstrip("/") + "/auth/v1/admin/users/" + uid,
                    headers={"apikey": key, "Authorization": "Bearer " + key}, timeout=10)
        return r.json().get("email") if r.status_code == 200 else None
    except Exception:
        return None


async def _it_erklaerung(art, request):
    if not _it_schalter("IT_PAYWALL"):
        return _JSONResp({"error": "inaktiv"}, status_code=503)
    heute, ip = time.strftime("%Y-%m-%d"), _it_client_ip(request)
    z = _it_erkl_ip.get(ip)
    if not z or z[0] != heute:
        z = [heute, 0]
    if z[1] >= 5:
        return _JSONResp({"error": "limit"}, status_code=429)
    try:
        name, email, angaben = _vertrag.pruefen(art, await _it_json(request))
    except _vertrag.Fehler as f:
        return _JSONResp({"error": f.code}, status_code=f.status)
    z[1] += 1
    _it_erkl_ip[ip] = z
    eid, eingang = _vertrag.speichern(art, name, email, angaben)
    ergebnis, ende, gefunden = {}, None, None
    s = _it_stripe()
    if art == "kuendigung" and angaben["kuendigungsart"] == "ordentlich" and angaben["zeitpunkt"] == "naechstmoeglich" and s:
        try:
            abos = _vertrag.stripe_abos(s, email)
            gefunden = bool(abos)
            erstattung = False
            for abo in abos:
                ende = _vertrag.stripe_kuendigen(s, abo)
                erstattung = erstattung or bool(ende and (_vertrag._periodenende(abo) or 0) > ende + 86400)
            ergebnis = {"stripe_abos": len(abos), "ende": ende, "erstattung_von_hand": erstattung}
        except Exception as e:
            print(f"[investtimer] kuendigung stripe: {type(e).__name__}", flush=True)
            ergebnis = {"stripe_fehler": type(e).__name__}
    else:
        ergebnis = {"manuell": True}
    text = (_vertrag.text_kuendigung(name, eingang, angaben, ende, gefunden, ergebnis.get("erstattung_von_hand")) if art == "kuendigung"
            else _vertrag.text_widerruf(name, eingang, angaben))
    betreff = "Eingangsbestätigung: Kündigung" if art == "kuendigung" else "Eingangsbestätigung: Widerruf"
    ergebnis["mail"] = _vertrag.senden(_it_resend(), email, betreff, text)
    _vertrag.ergebnis_setzen(eid, ergebnis)
    print(f"[investtimer] {art} eingegangen #{eid} mail={ergebnis['mail']}", flush=True)
    return {"ok": True, "nummer": eid, "eingang": _vertrag.zeit_text(eingang), "art": art, "angaben": angaben,
            "name": name, "email": email, "ende": _vertrag.datum_text(ende) if ende else None}


@app.post("/v1/investtimer/vertrag/kuendigen")
async def it_vertrag_kuendigen(request: Request):
    return await _it_erklaerung("kuendigung", request)


@app.post("/v1/investtimer/vertrag/widerrufen")
async def it_vertrag_widerrufen(request: Request):
    return await _it_erklaerung("widerruf", request)


def _it_abo_mail(uid, anlass, stand=None):
    if not anlass or not _it_schalter("IT_ABO_MAILS"):
        return False
    s = stand or _konto.status(uid)
    schluessel = "%s:%s:%s" % (uid, anlass, s.get("premiumBis"))
    inhalt = _vertrag.abo_mail_text(anlass, s)
    if not inhalt or not _vertrag.abo_mail_einmal(schluessel):
        return False
    email = _it_email_von_uid(uid)
    if not email:
        return False
    return _vertrag.senden(_it_resend(), email, inhalt[0], inhalt[1] + _vertrag.FUSS, kopie=False)


@app.post("/v1/investtimer/abo/erinnerungen")
def it_abo_erinnerungen(request: Request):
    """Stuendlich vom Server (nur 127.0.0.1): Erinnerung 2 Tage vor Ende der Testphase."""
    if (request.client.host if request.client else "") != "127.0.0.1" or request.headers.get("x-real-ip"):
        return _JSONResp({"error": "intern"}, status_code=403)
    jetzt = _konto.jetzt_ms()
    with _konto.verbinden() as db:
        uids = [r[0] for r in db.execute("SELECT uid FROM berechtigung WHERE status='test' AND verlaengerung=1 "
                                          "AND premium_bis BETWEEN ? AND ?", (jetzt, jetzt + 2 * 86400000))]
    n = sum(1 for uid in uids if _it_abo_mail(uid, "testende"))
    return {"geprueft": len(uids), "gesendet": n}
