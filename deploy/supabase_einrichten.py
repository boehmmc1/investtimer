#!/usr/bin/env python3
"""Legt das Supabase-Projekt fuer die InvestTimer-Anmeldung an (einmalig).

Aufruf:  python3 deploy/supabase_einrichten.py [ausgabe.json]
Token aus SUPABASE_ACCESS_TOKEN oder /root/.investtimer/supabase-token (0600).

Schritte: Organisation finden -> Projekt "investtimer" in Frankfurt (eu-central-1)
anlegen oder wiederverwenden -> warten bis aktiv -> Anmelde-Adressen und deutsche
Mailtexte setzen -> URL und anon key nach ausgabe.json (Standard deploy/supabase.json).
Der Zugriffs-Token wird nirgends ausgegeben oder gespeichert. Das Datenbank-Passwort
landet nur in /root/.investtimer-supabase-db (0600).
"""
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

API = "https://api.supabase.com/v1"
NAME = "investtimer"
REGION = "eu-central-1"
SITE = "https://investtimer.net"

MAIL = """<h2>Dein Zugang zu InvestTimer</h2>
<p>Klicke auf den Link, um dich ohne Passwort anzumelden:</p>
<p><a href="{{ .ConfirmationURL }}">Bei InvestTimer anmelden</a></p>
<p>Oder gib diesen Code auf der Seite ein: <strong style="font-size:20px;letter-spacing:3px">{{ .Token }}</strong></p>
<p>Link und Code sind eine Stunde gültig und funktionieren einmal. Hast du sie nicht angefordert, kannst du diese E-Mail ignorieren.</p>"""

_STIL = '<p style="font-size:13px;color:#5b6b66">Hast du das nicht angefordert, kannst du diese E-Mail ignorieren. Fragen? info@investtimer.net</p>'
_CODE = '<p style="font-size:26px;letter-spacing:6px;font-weight:700;margin:16px 0">{{ .Token }}</p>'
MAIL_REGISTRIERUNG = ("<h2>Willkommen bei InvestTimer</h2><p>Bitte bestätige deine E-Mail-Adresse. Gib diesen Code auf der Seite ein:</p>"
                      + _CODE + '<p>Oder bestätige mit einem Klick: <a href="{{ .ConfirmationURL }}">E-Mail-Adresse bestätigen</a></p>'
                      "<p>Code und Link sind eine Stunde gültig.</p>" + _STIL)
MAIL_ZURUECKSETZEN = ("<h2>Neues Passwort für InvestTimer</h2><p>Du hast ein neues Passwort angefordert. Gib diesen Code auf der Seite ein:</p>"
                      + _CODE + '<p>Oder öffne diesen Link, um direkt ein neues Passwort festzulegen: <a href="{{ .ConfirmationURL }}">Passwort zurücksetzen</a></p>'
                      "<p>Code und Link sind eine Stunde gültig und funktionieren einmal. Dein bisheriges Passwort gilt, bis du ein neues festlegst.</p>" + _STIL)
MAIL_BESTAETIGEN = ("<h2>Bestätigungscode für InvestTimer</h2><p>Mit diesem Code bestätigst du die Änderung deines Passworts:</p>"
                    + _CODE + "<p>Der Code ist eine Stunde gültig.</p>" + _STIL)

TOKEN_DATEI = "/root/.investtimer/supabase-token"
SMTP_DATEI = "/root/.investtimer/resend-smtp-key"  # Resend-Schluessel nur zum Senden fuer investtimer.net


def smtp():
    """Eigener Versand ueber Resend (Irland). Supabase setzt SMTP zurueck, wenn ein PATCH ihn nicht mitschickt."""
    try:
        with open(SMTP_DATEI) as datei:
            schluessel = datei.read().strip()
    except OSError:
        return {}
    return {"smtp_host": "smtp.resend.com", "smtp_port": "465", "smtp_user": "resend", "smtp_pass": schluessel,
            "smtp_admin_email": "anmeldung@investtimer.net", "smtp_sender_name": "InvestTimer",
            "smtp_max_frequency": 60, "rate_limit_email_sent": 30}


def token():
    if os.environ.get("SUPABASE_ACCESS_TOKEN"):
        return os.environ["SUPABASE_ACCESS_TOKEN"].strip()
    try:
        with open(TOKEN_DATEI) as datei:
            return datei.read().strip()
    except OSError:
        return ""


def rufe(methode, pfad, daten=None):
    anfrage = urllib.request.Request(API + pfad, method=methode,
                                     data=None if daten is None else json.dumps(daten).encode(),
                                     headers={"Authorization": "Bearer " + token(),
                                              "Content-Type": "application/json", "User-Agent": "investtimer-setup"})
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            text = antwort.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as fehler:
        raise SystemExit("Supabase %s %s -> %d: %s" % (methode, pfad, fehler.code, fehler.read().decode()[:300]))


def main(ziel):
    if not token().startswith("sbp_"):
        raise SystemExit("Supabase-Token (sbp_...) fehlt: SUPABASE_ACCESS_TOKEN oder " + TOKEN_DATEI)
    projekte = rufe("GET", "/projects")
    projekt = next((p for p in projekte if p.get("name") == NAME), None)
    if projekt:
        print("Projekt %s gibt es schon (%s), wird wiederverwendet" % (NAME, projekt["id"]))
    else:
        passwort = secrets.token_urlsafe(32)
        with open(os.open("/root/.investtimer-supabase-db", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as datei:
            datei.write(passwort + "\n")
        # Organisation: aus einem vorhandenen Projekt (feingranulare Tokens duerfen /organizations oft nicht lesen)
        org = next((p.get("organization_slug") or p.get("organization_id") for p in projekte), None)
        if not org:
            org = (rufe("GET", "/organizations") or [{}])[0].get("slug")
        if not org:
            raise SystemExit("Keine Organisation im Supabase-Konto gefunden")
        projekt = rufe("POST", "/projects", {"name": NAME, "organization_id": org,
                                              "db_pass": passwort, "region": REGION})
        print("Projekt angelegt: %s (Region %s)" % (projekt["id"], REGION))
    ref = projekt["id"]
    for _ in range(60):
        status = rufe("GET", "/projects/" + ref).get("status")
        if status == "ACTIVE_HEALTHY":
            break
        print("  Status: %s" % status)
        time.sleep(10)
    else:
        raise SystemExit("Projekt wurde nicht rechtzeitig aktiv")
    rufe("PATCH", "/projects/%s/config/auth" % ref, {
        "site_url": SITE,
        "uri_allow_list": SITE + "/**",
        "external_email_enabled": True,
        "mailer_autoconfirm": False,
        "mailer_otp_exp": 3600,
        "mailer_otp_length": 6,
        "password_min_length": 10,
        "security_update_password_require_reauthentication": True,
        **smtp(),
    })
    print("Anmeldung eingestellt: Site URL %s, Weiterleitung %s/**" % (SITE, SITE))
    # Eigene Mailtexte gibt es im Free-Tarif nur mit eigenem SMTP. Ohne sie enthaelt die Mail keinen Code.
    code = True
    try:
        rufe("PATCH", "/projects/%s/config/auth" % ref, {
            "mailer_subjects_magic_link": "Dein Anmeldelink für InvestTimer",
            "mailer_templates_magic_link_content": MAIL,
            "mailer_subjects_confirmation": "Bestätige deine E-Mail-Adresse für InvestTimer",
            "mailer_templates_confirmation_content": MAIL_REGISTRIERUNG,
            "mailer_subjects_recovery": "Neues Passwort für InvestTimer",
            "mailer_templates_recovery_content": MAIL_ZURUECKSETZEN,
            "mailer_subjects_reauthentication": "Dein Bestätigungscode für InvestTimer",
            "mailer_templates_reauthentication_content": MAIL_BESTAETIGEN,
            **smtp(),
        })
        print("Deutsche Mailtexte mit Link und Code gesetzt")
    except SystemExit as fehler:
        if "entitlement_required" not in str(fehler):
            raise
        code = False
        print("Mailtexte nicht moeglich (Free-Tarif ohne eigenes SMTP): Supabase-Standardmail, nur Link, kein Code")
    schluessel = rufe("GET", "/projects/%s/api-keys" % ref)
    anon = next((k["api_key"] for k in schluessel if k.get("name") == "anon"), None)
    if not anon:
        raise SystemExit("anon key nicht gefunden")
    with open(ziel, "w") as datei:
        json.dump({"url": "https://%s.supabase.co" % ref, "anonKey": anon, "code": code}, datei, indent=1)
        datei.write("\n")
    print("geschrieben: %s (URL und anon key, beide oeffentlich)" % ziel)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "supabase.json"))
