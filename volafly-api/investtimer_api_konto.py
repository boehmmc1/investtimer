# --- InvestTimer: Konto, Premium, Abo (Stripe/RevenueCat), KI-Kontingent ------
# Wird in volafly_chat.py vor /health eingefuegt (siehe deploy/api_einbauen.py).
# Schalter in /root/volafly-chat/.env:
#   IT_PREMIUM_PFLICHT=1  aktueller Wert, KI und Alarme nur mit Premium (Standard: aus)
#   IT_PAYWALL=1          Tarifauswahl und Checkout anbieten (Standard: aus)
#   IT_ZAHLUNG_LIVE=1     Stripe-Live-Schluessel zulassen (Standard: nur sk_test_)
#   IT_KI_TAG / IT_KI_MONAT  KI-Fragen je Konto (Standard 10 / 200)
# Geheimnisse (0600): /root/.investtimer/stripe.json, /root/.investtimer/revenuecat.json
import hmac as _hmac
import investtimer_konto as _konto

_it_geheim_cache = {}
_it_sr_cache = {"t": 0.0, "key": None}


def _it_geheim(name):
    pfad = "/root/.investtimer/%s.json" % name
    try:
        st = os.stat(pfad)
        c = _it_geheim_cache.get(name)
        if c and c[0] == st.st_mtime:
            return c[1]
        with open(pfad) as f:
            werte = json.load(f)
        _it_geheim_cache[name] = (st.st_mtime, werte)
        return werte
    except (OSError, ValueError):
        return {}


def _it_schalter(name):
    return _it_env(name).strip() == "1"


def _it_zahl(name, standard):
    try:
        return int(_it_env(name).strip())
    except ValueError:
        return standard


def _it_stripe():
    s = _it_geheim("stripe")
    key = s.get("secret", "")
    if not key or not (key.startswith("sk_test_") or key.startswith("rk_test_") or _it_schalter("IT_ZAHLUNG_LIVE")):
        return None
    return s


def _it_premium_noetig(uid):
    """None = erlaubt, sonst Fehlerantwort. Ohne Pflicht-Schalter gilt der bisherige Zugang (Anmeldung reicht)."""
    if not _it_schalter("IT_PREMIUM_PFLICHT") or _konto.ist_premium(uid):
        return None
    return _JSONResp({"error": "premium"}, status_code=403)


def _it_rc_abgleich(uid):
    """Abonnenten bei RevenueCat abrufen und speichern. Bei Ausfall bleibt der letzte Stand."""
    rc = _it_geheim("revenuecat")
    if not rc.get("secret"):
        return None
    try:
        r = _rq.get("https://api.revenuecat.com/v1/subscribers/" + _rq.utils.quote(uid, safe=""),
                    headers={"Authorization": "Bearer " + rc["secret"]}, timeout=8)
        if r.status_code != 200:
            print(f"[investtimer] revenuecat: HTTP {r.status_code}", flush=True)
            return None
        return _konto.aus_subscriber(uid, r.json())
    except Exception as e:
        print(f"[investtimer] revenuecat: {type(e).__name__}", flush=True)
        return None


def _it_konto_antwort(uid):
    s = _konto.status(uid)
    pflicht = _it_schalter("IT_PREMIUM_PFLICHT")
    s.update(pflicht=pflicht, paywall=_it_schalter("IT_PAYWALL") and _it_stripe() is not None,
             appKauf=bool(_it_geheim("revenuecat").get("apple_public")),
             ki=dict(_konto.ki_stand(uid), tag=_it_ki_limits(uid)[0], monat=_it_ki_limits(uid)[1]),
             tarife=_konto.TARIFE)
    return _JSONResp(s, headers={"Cache-Control": "no-store"})


def _it_ki_limits(uid):
    if _it_schalter("IT_PREMIUM_PFLICHT") and not _konto.ist_premium(uid):
        return 0, 0
    return _it_zahl("IT_KI_TAG", IT_LIMIT_NUTZER), _it_zahl("IT_KI_MONAT", 200)


@app.get("/v1/investtimer/konto")
def it_konto(request: Request):
    uid, fehler = _it_nutzer_oder_fehler(request)
    return fehler or _it_konto_antwort(uid)


@app.post("/v1/investtimer/konto/abgleich")
def it_konto_abgleich(request: Request):
    """Nach Kauf, Wiederherstellung oder Rueckkehr aus dem Checkout: Stand bei RevenueCat holen."""
    uid, fehler = _it_nutzer_oder_fehler(request)
    if fehler:
        return fehler
    _it_rc_abgleich(uid)
    return _it_konto_antwort(uid)


def _it_service_role():
    """service_role-Schluessel nur zur Laufzeit ueber die Management-API (nie gespeichert)."""
    if _it_sr_cache["key"] and time.time() - _it_sr_cache["t"] < 3600:
        return _it_sr_cache["key"]
    with open("/root/.investtimer/supabase-token") as f:
        token = f.read().strip()
    ref = _it_env("IT_SUPABASE_URL").split("//", 1)[1].split(".", 1)[0]
    r = _rq.get("https://api.supabase.com/v1/projects/%s/api-keys" % ref,
                headers={"Authorization": "Bearer " + token}, timeout=10)
    r.raise_for_status()
    key = next(k["api_key"] for k in r.json() if k.get("name") == "service_role")
    _it_sr_cache.update(t=time.time(), key=key)
    return key


@app.post("/v1/investtimer/konto/loeschen")
async def it_konto_loeschen(request: Request):
    uid, fehler = _it_nutzer_oder_fehler(request)
    if fehler:
        return fehler
    daten = await _it_json(request)
    if str(daten.get("bestaetigung", "")).strip().lower() != "löschen":
        return _JSONResp({"error": "bestaetigung"}, status_code=400)
    _it_rc_abgleich(uid)
    try:
        _konto.loeschen_pruefen(uid)
    except _konto.Fehler as f:
        return _JSONResp({"error": f.code, "konto": _konto.status(uid)}, status_code=f.status)
    try:
        key = _it_service_role()
        r = _rq.delete(_it_env("IT_SUPABASE_URL").rstrip("/") + "/auth/v1/admin/users/" + uid,
                       headers={"apikey": key, "Authorization": "Bearer " + key}, timeout=10)
        if r.status_code not in (200, 204, 404):
            print(f"[investtimer] konto loeschen: HTTP {r.status_code}", flush=True)
            return _it_aus()
    except Exception as e:
        print(f"[investtimer] konto loeschen: {type(e).__name__}", flush=True)
        return _it_aus()
    _alarme.konto_loeschen(uid)
    _konto.konto_loeschen(uid)
    for tok in [t for t, c in _it_auth_cache.items() if c[0] == uid]:
        del _it_auth_cache[tok]
    rc = _it_geheim("revenuecat")
    if rc.get("secret"):
        try:  # Kundendaten bei RevenueCat entfernen (Kaufbelege bleiben bei Apple/Stripe)
            _rq.delete("https://api.revenuecat.com/v1/subscribers/" + _rq.utils.quote(uid, safe=""),
                       headers={"Authorization": "Bearer " + rc["secret"]}, timeout=8)
        except Exception as e:
            print(f"[investtimer] revenuecat loeschen: {type(e).__name__}", flush=True)
    print("[investtimer] Konto geloescht", flush=True)
    return {"ok": True}


def _it_stripe_post(s, pfad, felder):
    r = _rq.post("https://api.stripe.com/v1/" + pfad, data=felder, auth=(s["secret"], ""), timeout=15)
    if r.status_code >= 300:
        print(f"[investtimer] stripe {pfad}: HTTP {r.status_code} {r.json().get('error', {}).get('code')}", flush=True)
        return None
    return r.json()


def _it_email(request):
    tok = (request.headers.get("authorization") or "")[7:].strip()
    try:
        r = _rq.get(_it_env("IT_SUPABASE_URL").rstrip("/") + "/auth/v1/user",
                    headers={"apikey": _it_env("IT_SUPABASE_ANON_KEY"), "Authorization": "Bearer " + tok}, timeout=6)
        return r.json().get("email") if r.status_code == 200 else None
    except Exception:
        return None


@app.post("/v1/investtimer/abo/checkout")
async def it_abo_checkout(request: Request):
    uid, fehler = _it_nutzer_oder_fehler(request)
    if fehler:
        return fehler
    s = _it_stripe()
    if not _it_schalter("IT_PAYWALL") or not s:
        return _JSONResp({"error": "zahlung_inaktiv"}, status_code=503)
    tarif = (await _it_json(request)).get("tarif")
    preis = (s.get("preise") or {}).get(tarif)
    if not preis:
        return _JSONResp({"error": "tarif"}, status_code=400)
    _it_rc_abgleich(uid)
    try:
        test = _konto.kaufen_erlaubt(uid)["testErlaubt"]
    except _konto.Fehler as f:
        return _JSONResp({"error": f.code}, status_code=f.status)
    email = _it_email(request)
    if test and email and _konto.test_schon_genutzt(uid, email):
        test = False
    basis = s.get("basis", "https://investtimer.net")
    felder = {"mode": "subscription", "line_items[0][price]": preis, "line_items[0][quantity]": "1",
              "client_reference_id": uid, "locale": "de",
              "subscription_data[metadata][app_user_id]": uid, "metadata[app_user_id]": uid,
              "payment_method_collection": "always",
              "success_url": basis + "/?abo=ok", "cancel_url": basis + "/?abo=abbruch"}
    kunde = (_konto.roh(uid) or {}).get("stripe_kunde")
    if kunde:
        felder["customer"] = kunde
    elif email:
        felder["customer_email"] = email
    if test:
        felder["subscription_data[trial_period_days]"] = "7"
        felder["subscription_data[trial_settings][end_behavior][missing_payment_method]"] = "cancel"
    if s.get("steuer_automatisch"):
        felder["automatic_tax[enabled]"] = "true"
    if s.get("agb_zustimmung"):
        felder["consent_collection[terms_of_service]"] = "required"
    sitzung = _it_stripe_post(s, "checkout/sessions", felder)
    if not sitzung:
        return _it_aus()
    if test and email:
        _konto.test_merken(email)
    return {"url": sitzung["url"], "test": test}


@app.post("/v1/investtimer/abo/verwalten")
def it_abo_verwalten(request: Request):
    """Stripe-Kundenportal (Kuendigen, Zahlungsmethode, Rechnungen, Tarifwechsel)."""
    uid, fehler = _it_nutzer_oder_fehler(request)
    if fehler:
        return fehler
    s, kunde = _it_stripe(), (_konto.roh(uid) or {}).get("stripe_kunde")
    if not s or not kunde:
        return _JSONResp({"error": "kein_web_abo"}, status_code=404)
    sitzung = _it_stripe_post(s, "billing_portal/sessions",
                              {"customer": kunde, "return_url": s.get("basis", "https://investtimer.net") + "/?konto=1",
                               "locale": "de"})
    return {"url": sitzung["url"]} if sitzung else _it_aus()


def _it_stripe_signatur_ok(roh, kopf, geheim, toleranz=300):
    try:
        teile = dict(p.split("=", 1) for p in kopf.split(",") if "=" in p)
        ts = int(teile["t"])
    except Exception:
        return False
    if abs(time.time() - ts) > toleranz:
        return False
    soll = _hmac.new(geheim.encode(), str(ts).encode() + b"." + roh, "sha256").hexdigest()
    return any(_hmac.compare_digest(soll, v) for p, v in
               (x.split("=", 1) for x in kopf.split(",") if "=" in x) if p == "v1")


@app.post("/v1/investtimer/abo/stripe-webhook")
async def it_stripe_webhook(request: Request):
    """Stripe meldet einen abgeschlossenen Checkout: Kunde merken und den Kauf an RevenueCat geben."""
    s = _it_stripe()
    if not s or not s.get("webhook"):
        return _it_aus()
    roh = await request.body()
    if not _it_stripe_signatur_ok(roh, request.headers.get("stripe-signature", ""), s["webhook"]):
        return _JSONResp({"error": "signatur"}, status_code=400)
    e = json.loads(roh)
    if e.get("type") == "checkout.session.completed":
        o = e["data"]["object"]
        uid = o.get("client_reference_id") or (o.get("metadata") or {}).get("app_user_id")
        if uid and o.get("customer"):
            _konto.stripe_kunde_setzen(uid, o["customer"])
        rc = _it_geheim("revenuecat")
        if uid and o.get("subscription") and rc.get("stripe_public"):
            try:
                _rq.post("https://api.revenuecat.com/v1/receipts", timeout=10,
                         headers={"Authorization": "Bearer " + rc["stripe_public"], "X-Platform": "stripe"},
                         json={"app_user_id": uid, "fetch_token": o["subscription"]})
            except Exception as ex:
                print(f"[investtimer] revenuecat receipts: {type(ex).__name__}", flush=True)
            _it_rc_abgleich(uid)
    return {"ok": True}


@app.post("/v1/investtimer/abo/revenuecat-webhook")
async def it_rc_webhook(request: Request):
    rc = _it_geheim("revenuecat")
    erwartet = rc.get("webhook", "")
    if not erwartet or not _hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + erwartet):
        return _JSONResp({"error": "auth"}, status_code=401)
    try:
        uid = _konto.rc_ereignis(json.loads(await request.body()))
    except Exception as e:
        print(f"[investtimer] revenuecat webhook: {type(e).__name__}", flush=True)
        return _JSONResp({"error": "ereignis"}, status_code=400)
    if uid:
        _it_rc_abgleich(uid)  # verlaesslicher Stand; scheitert er, gilt das Ereignis
    return {"ok": True}

