#!/usr/bin/env python3
"""Ende-zu-Ende-Test der Abo-Strecke gegen eine eigene API-Instanz (Port 8199).

Echt: Supabase-Anmeldung (Testnutzer ueber die Admin-API, wird geloescht).
Nachgebaut (Port 12111): Stripe, RevenueCat und Resend - sie zeichnen auf, was die API sendet.
Eigene Datenbanken und Schalter in einem Temp-Ordner; die Live-Daten bleiben unberuehrt.

Aufruf: python3 tests/e2e_abo.py
"""
import hashlib, hmac, http.server, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "deploy")); sys.argv = sys.argv[:1]
import supabase_test as st  # noqa: E402

TMP = tempfile.mkdtemp(prefix="it-e2e-")
FAKE, API = "http://127.0.0.1:12111", "http://127.0.0.1:8199"
WHSEC, RCHOOK = "whsec_test_" + os.urandom(8).hex(), "rc_hook_" + os.urandom(8).hex()
LOG, STAND = [], {"subscriber": None, "abo": None}
TAG = 86400000
fehler = []


def check(name, bed, info=""):
    print(("OK   " if bed else "FEHL ") + name + (("  [" + str(info)[:160] + "]") if info and not bed else ""))
    if not bed:
        fehler.append(name)


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def antwort(self, code, daten):
        b = json.dumps(daten).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        roh = self.rfile.read(n).decode() if n else ""
        if "json" in (self.headers.get("Content-Type") or ""):
            return json.loads(roh or "{}")
        return dict(urllib.parse.parse_qsl(roh))

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        LOG.append(("GET", u.path, q, self.headers.get("Authorization")))
        if u.path.startswith("/rc/v1/subscribers/"):
            return self.antwort(200, STAND["subscriber"] or {"subscriber": {"subscriptions": {}, "entitlements": {}}})
        if u.path == "/v1/customers":
            return self.antwort(200, {"data": [{"id": "cus_test1"}] if STAND["abo"] else []})
        if u.path == "/v1/subscriptions":
            return self.antwort(200, {"data": [STAND["abo"]] if STAND["abo"] else []})
        self.antwort(404, {})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path); b = self.body()
        LOG.append(("POST", u.path, b, self.headers.get("Authorization")))
        if u.path == "/v1/checkout/sessions":
            return self.antwort(200, {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"})
        if u.path == "/v1/billing_portal/sessions":
            return self.antwort(200, {"url": "https://billing.stripe.com/p/session/test_1"})
        if u.path.startswith("/v1/subscriptions/"):
            a = dict(STAND["abo"], cancel_at_period_end=True); STAND["abo"] = a
            return self.antwort(200, a)
        if u.path == "/rc/v1/receipts":
            return self.antwort(200, {})
        if u.path == "/resend/emails":
            return self.antwort(200, {"id": "mail_%d" % len(LOG)})
        self.antwort(404, {})

    def do_DELETE(self):
        LOG.append(("DELETE", self.path, None, None)); self.antwort(200, {})


def rufe(methode, pfad, daten=None, tok=None, kopf=None):
    h = {"Content-Type": "application/json", **(kopf or {})}
    if tok: h["Authorization"] = "Bearer " + tok
    roh = daten if isinstance(daten, bytes) else (json.dumps(daten).encode() if daten is not None else None)
    try:
        with urllib.request.urlopen(urllib.request.Request(API + pfad, data=roh, method=methode, headers=h), timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def gesendet(pfad):
    return [x for x in LOG if x[1] == pfad]


def subscriber(period, kauf_ms, bis_ms, **mehr):
    iso = lambda ms: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))
    a = {"store": "stripe", "purchase_date": iso(kauf_ms), "expires_date": iso(bis_ms), "period_type": period}
    a.update({k: iso(v) for k, v in mehr.items()})
    return {"subscriber": {"subscriptions": {"investtimer_premium_yearly": a},
                           "entitlements": {"premium": {"product_identifier": "investtimer_premium_yearly", "expires_date": iso(bis_ms)}}}}


def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 12111), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
    geheim = os.path.join(TMP, "geheim"); os.makedirs(geheim)
    json.dump({"secret": "sk_test_e2e", "webhook": WHSEC, "api": FAKE, "preise": {"monatlich": "price_m", "jaehrlich": "price_y"}},
              open(os.path.join(geheim, "stripe.json"), "w"))
    json.dump({"secret": "sk_rc_e2e", "webhook": RCHOOK, "stripe_public": "strp_e2e", "api": FAKE + "/rc"}, open(os.path.join(geheim, "revenuecat.json"), "w"))
    open(os.path.join(geheim, "resend-key"), "w").write("re_e2e")
    envdatei = os.path.join(TMP, ".env")
    echte = [z for z in open("/root/volafly-chat/.env") if z.startswith(("IT_SUPABASE_URL=", "IT_SUPABASE_ANON_KEY="))]
    def schalter(**kw):
        open(envdatei, "w").write("".join(echte) + "".join("%s=%s\n" % kv for kv in kw.items()))
        time.sleep(31)  # API liest die Schalter alle 30 s neu
    open(envdatei, "w").write("".join(echte) + "IT_PAYWALL=1\nIT_ABO_MAILS=1\n")
    env = dict(os.environ, IT_ENV_DATEI=envdatei, IT_GEHEIM_DIR=geheim, IT_RESEND_API=FAKE + "/resend",
               INVESTTIMER_KONTO_DB=os.path.join(TMP, "konto.db"), INVESTTIMER_ALARME_DB=os.path.join(TMP, "alarme.db"), IT_KI_DB=os.path.join(TMP, "ki.db"))
    api = subprocess.Popen(["/usr/local/bin/uvicorn", "volafly_chat:app", "--host", "127.0.0.1", "--port", "8199"], cwd="/root/volafly-chat",
                           env=env, stdout=open(os.path.join(TMP, "api.log"), "w"), stderr=subprocess.STDOUT)
    _, keys, _ = st.http("GET", "%s/projects/%s/api-keys" % (st.API, st.REF), kopf={"Authorization": "Bearer " + st.token()})
    svc = next(k["api_key"] for k in keys if k.get("name") == "service_role"); admin = {"apikey": svc, "Authorization": "Bearer " + svc}
    email = "it-e2e-%d@investtimer.net" % time.time()
    _, u, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/admin/users", {"email": email, "email_confirm": True}, admin)
    try:
        _, l, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/admin/generate_link", {"type": "magiclink", "email": email}, admin)
        _, s, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/verify", {"type": "email", "email": email, "token": l["email_otp"]}, {"apikey": st.AUTH["anonKey"]})
        tok, uid = s["access_token"], u["id"]
        for _ in range(40):
            try:
                if rufe("GET", "/health")[0] == 200: break
            except Exception: time.sleep(0.5)
        jetzt = int(time.time() * 1000)

        # 1 Neuer Nutzer: frei, Paywall verfuegbar
        c, k = rufe("GET", "/v1/investtimer/konto", tok=tok)
        check("01 Konto frei, Paywall an", c == 200 and not k["premium"] and k["paywall"] and not k["testGenutzt"], k)
        # 2/3 Checkout Jahresabo mit 7 Tagen Test
        c, d = rufe("POST", "/v1/investtimer/abo/checkout", {"tarif": "jaehrlich"}, tok)
        f = gesendet("/v1/checkout/sessions")[-1][2] if gesendet("/v1/checkout/sessions") else {}
        check("02 Checkout-URL", c == 200 and d.get("url", "").startswith("https://checkout.stripe.com") and d.get("test") is True, d)
        check("03 Checkout: Jahrespreis, 7 Tage, Nutzer-ID, Abo-Modus, Kunde per E-Mail",
              f.get("line_items[0][price]") == "price_y" and f.get("subscription_data[trial_period_days]") == "7"
              and f.get("client_reference_id") == uid and f.get("subscription_data[metadata][app_user_id]") == uid
              and f.get("mode") == "subscription" and f.get("customer_email") == email
              and f.get("subscription_data[trial_settings][end_behavior][missing_payment_method]") == "cancel", f)
        c, d = rufe("POST", "/v1/investtimer/abo/checkout", {"tarif": "woechentlich"}, tok)
        check("04 Unbekannter Tarif abgelehnt", c == 400, d)
        # 5 Stripe-Webhook: falsche Signatur, dann richtig
        ereignis = json.dumps({"type": "checkout.session.completed", "data": {"object": {"client_reference_id": uid, "customer": "cus_test1", "subscription": "sub_test1"}}}).encode()
        c, _ = rufe("POST", "/v1/investtimer/abo/stripe-webhook", ereignis, kopf={"Stripe-Signature": "t=%d,v1=%s" % (time.time(), "0" * 64)})
        check("05 Stripe-Webhook mit falscher Signatur abgelehnt", c == 400)
        alt = int(time.time()) - 3600
        sig = hmac.new(WHSEC.encode(), str(alt).encode() + b"." + ereignis, hashlib.sha256).hexdigest()
        c, _ = rufe("POST", "/v1/investtimer/abo/stripe-webhook", ereignis, kopf={"Stripe-Signature": "t=%d,v1=%s" % (alt, sig)})
        check("06 Stripe-Webhook mit veraltetem Zeitstempel abgelehnt (Wiederholungsangriff)", c == 400)
        STAND["subscriber"] = subscriber("trial", jetzt, jetzt + 7 * TAG)
        ts = int(time.time()); sig = hmac.new(WHSEC.encode(), str(ts).encode() + b"." + ereignis, hashlib.sha256).hexdigest()
        c, _ = rufe("POST", "/v1/investtimer/abo/stripe-webhook", ereignis, kopf={"Stripe-Signature": "t=%d,v1=%s" % (ts, sig)})
        r = gesendet("/rc/v1/receipts")
        check("07 Stripe-Kauf an RevenueCat gemeldet (receipts, X-Platform stripe)", c == 200 and r and r[-1][2] == {"app_user_id": uid, "fetch_token": "sub_test1"}
              and r[-1][3] == "Bearer strp_e2e", r[-1:] if r else c)
        c, k = rufe("GET", "/v1/investtimer/konto", tok=tok)
        check("08 Premium in der Testphase, 7 Tage, Verwaltung Stripe", k.get("premium") and k.get("status") == "test" and k.get("testTageRest") == 7
              and k.get("verwaltung") == "stripe" and k.get("tarif") == "jaehrlich", k)
        # 9 Doppelabo verhindert
        c, d = rufe("POST", "/v1/investtimer/abo/checkout", {"tarif": "monatlich"}, tok)
        check("09 Zweites Abo verweigert", c == 409 and d.get("error") == "schon_premium", d)
        # 10 Kundenportal
        c, d = rufe("POST", "/v1/investtimer/abo/verwalten", tok=tok)
        p = gesendet("/v1/billing_portal/sessions")
        check("10 Kundenportal fuer den Stripe-Kunden", c == 200 and "billing.stripe.com" in d.get("url", "") and p and p[-1][2].get("customer") == "cus_test1", d)
        # 11 RevenueCat-Webhook: Auth, Teststart-Mail, Mehrfachzustellung
        ev = {"event": {"id": "ev1", "type": "INITIAL_PURCHASE", "app_user_id": uid, "period_type": "TRIAL", "store": "STRIPE",
                        "product_id": "investtimer_premium_yearly", "entitlement_ids": ["premium"], "event_timestamp_ms": jetzt,
                        "purchased_at_ms": jetzt, "expiration_at_ms": jetzt + 7 * TAG}}
        c, _ = rufe("POST", "/v1/investtimer/abo/revenuecat-webhook", ev, kopf={"Authorization": "Bearer falsch"})
        check("11 RevenueCat-Webhook ohne richtigen Schluessel abgelehnt", c == 401)
        n0 = len(gesendet("/resend/emails"))
        c, _ = rufe("POST", "/v1/investtimer/abo/revenuecat-webhook", ev, kopf={"Authorization": "Bearer " + RCHOOK})
        c2, _ = rufe("POST", "/v1/investtimer/abo/revenuecat-webhook", ev, kopf={"Authorization": "Bearer " + RCHOOK})
        mails = gesendet("/resend/emails")[n0:]
        check("12 Teststart-Mail genau einmal, an die Konto-Adresse", c == 200 and c2 == 200 and len(mails) == 1 and mails[0][2]["to"] == [email]
              and "Testphase" in mails[0][2]["text"], [m[2].get("subject") for m in mails])
        # 13 Erinnerung zwei Tage vor Testende
        STAND["subscriber"] = subscriber("trial", jetzt - 5 * TAG, jetzt + 2 * TAG - 60000)
        rufe("POST", "/v1/investtimer/konto/abgleich", tok=tok)
        n0 = len(gesendet("/resend/emails"))
        c, d = rufe("POST", "/v1/investtimer/abo/erinnerungen"); rufe("POST", "/v1/investtimer/abo/erinnerungen")
        mails = gesendet("/resend/emails")[n0:]
        check("13 Erinnerung vor Testende genau einmal", c == 200 and len(mails) == 1 and "endet" in mails[0][2]["subject"], (d, [m[2]["subject"] for m in mails]))
        c, d = rufe("POST", "/v1/investtimer/abo/erinnerungen", kopf={"X-Real-IP": "1.2.3.4"})
        check("14 Erinnerungen nur intern aufrufbar", c == 403)
        # 15 Testphase endet, erste Zahlung -> Mail "aktiv"
        STAND["subscriber"] = subscriber("normal", jetzt, jetzt + 365 * TAG)
        n0 = len(gesendet("/resend/emails"))
        ev2 = {"event": dict(ev["event"], id="ev2", type="RENEWAL", period_type="NORMAL", event_timestamp_ms=jetzt + 1000, expiration_at_ms=jetzt + 365 * TAG)}
        rufe("POST", "/v1/investtimer/abo/revenuecat-webhook", ev2, kopf={"Authorization": "Bearer " + RCHOOK})
        c, k = rufe("GET", "/v1/investtimer/konto", tok=tok)
        mails = gesendet("/resend/emails")[n0:]
        check("15 Nach Testende bezahlt: Status aktiv, Mail zum Abo-Beginn", k.get("status") == "aktiv" and len(mails) == 1 and "aktiv" in mails[0][2]["subject"], (k.get("status"), [m[2]["subject"] for m in mails]))
        # 16 Premium-Pflicht: Zugriff mit Abo
        schalter(IT_PAYWALL=1, IT_ABO_MAILS=1, IT_PREMIUM_PFLICHT=1)
        c1, _ = rufe("GET", "/v1/investtimer/historie", tok=tok)
        c2, _ = rufe("POST", "/v1/investtimer/alarme", {"richtung": "ueber", "schwelle": 70}, tok)
        check("16 Mit Premium: Verlauf und Alarme erlaubt", c1 == 200 and c2 == 200, (c1, c2))
        # 17 Kontoloeschung gesperrt, solange das Abo sich verlaengert
        c, d = rufe("POST", "/v1/investtimer/konto/loeschen", {"bestaetigung": "löschen"}, tok)
        check("17 Kontoloeschung bei laufendem Abo gesperrt", c == 409 and d.get("error") == "abo_aktiv", d)
        # 18 Kuendigungsbutton ohne Login: Stripe kuendigt zum Periodenende, Bestaetigung per Mail
        ende = int(time.time()) + 365 * 86400
        STAND["abo"] = {"id": "sub_test1", "status": "active", "current_period_end": ende, "cancel_at_period_end": False}
        n0 = len(gesendet("/resend/emails"))
        c, d = rufe("POST", "/v1/investtimer/vertrag/kuendigen", {"kuendigungsart": "ausserordentlich", "zeitpunkt": "naechstmoeglich", "name": "Test Person", "email": email})
        check("18 Ausserordentlich ohne Grund abgelehnt", c == 400 and d.get("error") == "grund", d)
        c, d = rufe("POST", "/v1/investtimer/vertrag/kuendigen", {"kuendigungsart": "ordentlich", "zeitpunkt": "naechstmoeglich", "name": "Test Person", "email": email.upper()})
        post = [x for x in LOG if x[0] == "POST" and x[1] == "/v1/subscriptions/sub_test1"]
        mails = gesendet("/resend/emails")[n0:]
        check("19 Kuendigung: Stripe cancel_at_period_end, Vertragsende in Antwort",
              c == 200 and post and post[-1][2] == {"cancel_at_period_end": "true"} and d.get("ende") == time.strftime("%d.%m.%Y", time.localtime(ende)) and d.get("eingang"), d)
        check("20 Eingangsbestaetigung mit Zeitpunkt und Ende, Kopie an info@", len(mails) == 1 and mails[0][2]["bcc"] == ["info@investtimer.net"]
              and "erhalten" in mails[0][2]["text"] and "endet am" in mails[0][2]["text"], [m[2].get("text", "")[:120] for m in mails])
        # 21 Widerruf
        n0 = len(gesendet("/resend/emails"))
        c, d = rufe("POST", "/v1/investtimer/vertrag/widerrufen", {"name": "Test Person", "email": email, "bestelldatum": "2026-11-17"})
        mails = gesendet("/resend/emails")[n0:]
        check("21 Widerruf: Eingangsbestaetigung", c == 200 and d.get("art") == "widerruf" and len(mails) == 1 and "Widerruf" in mails[0][2]["subject"], d)
        # 22 Kuendigung kommt per RevenueCat zurueck -> Mail, Loeschen dann erlaubt
        STAND["subscriber"] = subscriber("normal", jetzt, jetzt + 365 * TAG, unsubscribe_detected_at=jetzt + 2000)
        n0 = len(gesendet("/resend/emails"))
        ev3 = {"event": dict(ev2["event"], id="ev3", type="CANCELLATION", cancel_reason="UNSUBSCRIBE", event_timestamp_ms=jetzt + 2000)}
        rufe("POST", "/v1/investtimer/abo/revenuecat-webhook", ev3, kopf={"Authorization": "Bearer " + RCHOOK})
        c, k = rufe("GET", "/v1/investtimer/konto", tok=tok)
        mails = gesendet("/resend/emails")[n0:]
        check("22 Gekuendigt: Premium bis Periodenende, Verlaengerung aus, Mail", k.get("premium") and k.get("status") == "gekuendigt" and not k.get("verlaengerung")
              and len(mails) == 1, (k.get("status"), len(mails)))
        # 23 Ablauf -> frei, Sperre greift
        STAND["subscriber"] = {"subscriber": {"subscriptions": {}, "entitlements": {}}}
        rufe("POST", "/v1/investtimer/konto/abgleich", tok=tok)
        c1, d1 = rufe("GET", "/v1/investtimer/historie", tok=tok)
        c2, _ = rufe("GET", "/v1/investtimer/aktuell", tok=tok)
        check("23 Ohne Premium: Verlauf und aktueller Wert gesperrt (403 premium)", c1 == 403 and d1.get("error") == "premium" and c2 == 403, (c1, c2))
        c, k = rufe("GET", "/v1/investtimer/konto", tok=tok)
        check("24 KI-Kontingent ohne Premium 0", k.get("ki", {}).get("frei") == 0 and k.get("ki", {}).get("verbraucht") is True, k.get("ki"))
        # 25 Kontoloeschung: Supabase, RevenueCat, lokale Daten
        c, d = rufe("POST", "/v1/investtimer/konto/loeschen", {"bestaetigung": "löschen"}, tok)
        code, _, _ = st.http("GET", st.AUTH["url"] + "/auth/v1/admin/users/" + uid, kopf=admin)
        rcweg = [x for x in LOG if x[0] == "DELETE" and uid in x[1]]
        import sqlite3
        reste = sum(sqlite3.connect(os.path.join(TMP, "konto.db")).execute("SELECT COUNT(*) FROM %s WHERE uid=?" % t, (uid,)).fetchone()[0] for t in ("berechtigung", "ki_nutzung"))
        reste += sqlite3.connect(os.path.join(TMP, "alarme.db")).execute("SELECT COUNT(*) FROM alarme WHERE uid=?", (uid,)).fetchone()[0]
        check("25 Kontoloeschung: Supabase-Nutzer weg, RevenueCat-Kunde geloescht, keine Reste", c == 200 and code == 404 and rcweg and reste == 0, (c, code, len(rcweg), reste))
        # 26 Zweite Testphase nach Neuanmeldung mit derselben Adresse verweigert
        _, u2, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/admin/users", {"email": email, "email_confirm": True}, admin)
        _, l, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/admin/generate_link", {"type": "magiclink", "email": email}, admin)
        _, s2, _ = st.http("POST", st.AUTH["url"] + "/auth/v1/verify", {"type": "email", "email": email, "token": l["email_otp"]}, {"apikey": st.AUTH["anonKey"]})
        c, d = rufe("POST", "/v1/investtimer/abo/checkout", {"tarif": "monatlich"}, s2["access_token"])
        f = gesendet("/v1/checkout/sessions")[-1][2]
        check("26 Neues Konto mit derselben E-Mail: keine zweite Testphase", c == 200 and d.get("test") is False and "subscription_data[trial_period_days]" not in f, d)
        st.http("DELETE", st.AUTH["url"] + "/auth/v1/admin/users/" + u2["id"], kopf=admin)
        # 27 Ohne Paywall-Schalter: nichts verkaufbar
        schalter()
        c, d = rufe("POST", "/v1/investtimer/vertrag/kuendigen", {"kuendigungsart": "ordentlich", "zeitpunkt": "naechstmoeglich", "name": "Test", "email": email})
        check("27 Ohne Schalter: Kuendigungsfunktion und Checkout aus", c == 503, d)
    finally:
        st.http("DELETE", st.AUTH["url"] + "/auth/v1/admin/users/" + u["id"], kopf=admin)
        api.terminate(); api.wait(10); srv.shutdown()
        if fehler:
            print(open(os.path.join(TMP, "api.log")).read()[-3000:])
        shutil.rmtree(TMP, ignore_errors=True)
    print("\nERGEBNIS: %s" % ("alle Pruefungen bestanden" if not fehler else "%d fehlgeschlagen: %s" % (len(fehler), ", ".join(fehler))))
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
