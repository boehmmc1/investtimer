# ── Testumgebung (DEC-020, 26.11.2026): nur aktiv mit IT_TESTUMGEBUNG=1 (Dienst investtimer-test-api, Port 8101).
# Mail-Filter statt Resend: alle InvestTimer-Mails der Testinstanz gehen ueber IT_RESEND_API=http://127.0.0.1:8101/v1/test/resend.
# Betreff bekommt "[TEST] ", Absender test@investtimer.net, Empfaenger nur info@investtimer.net und IT_TEST_EMPFAENGER (Komma-Liste);
# alles andere wird nur protokolliert (/var/lib/investtimer-test/mails.log). Live (ohne Schalter) antwortet der Endpunkt mit 404.
@app.post("/v1/test/resend/emails")
async def it_test_resend(request: Request):
    if os.environ.get("IT_TESTUMGEBUNG") != "1" or (request.client.host if request.client else "") != "127.0.0.1" or request.headers.get("x-real-ip"):
        return _JSONResp({"error": "nicht gefunden"}, status_code=404)
    d = await _it_json(request)
    erlaubt = {"info@investtimer.net"} | {e.strip().lower() for e in (os.environ.get("IT_TEST_EMPFAENGER") or _it_env("IT_TEST_EMPFAENGER") or "").split(",") if e.strip()}
    an = d.get("to") or []
    an = [an] if isinstance(an, str) else list(an)
    ziel = [e for e in an if str(e).strip().lower() in erlaubt]
    betreff = "[TEST] " + str(d.get("subject") or "").replace("[TEST] ", "")
    log = "/var/lib/investtimer-test/mails.log"
    try:
        with open(log, "a") as f:
            f.write("%s an=%s gesendet=%s betreff=%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), ",".join(map(str, an)), ",".join(ziel) or "-", betreff[:120]))
    except OSError:
        pass
    if not ziel:
        return {"id": "nur-log", "test": True}
    key = _it_resend()
    if not key:
        return _JSONResp({"error": "kein Schluessel"}, status_code=500)
    d.update(to=ziel, subject=betreff, **{"from": "InvestTimer TEST <test@investtimer.net>"})
    d.pop("cc", None); d.pop("bcc", None)
    r = _rq.post("https://api.resend.com/emails", json=d, timeout=20, headers={"Authorization": "Bearer " + key})
    return _JSONResp(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"status": r.status_code}, status_code=r.status_code)
