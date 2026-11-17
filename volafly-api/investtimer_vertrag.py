"""Kuendigung (§ 312k BGB) und Widerruf (§ 356a BGB) ohne Anmeldung, dazu Abo-Mails.

- Erklaerungen werden mit Eingangszeit in konto.db gespeichert (Nachweis).
- Eingangsbestaetigung per E-Mail (Resend) an die angegebene Adresse, Kopie an info@.
- Ordentliche Kuendigung eines Web-Abos: bei Stripe zum Ende des bezahlten Zeitraums
  (cancel_at_period_end). Ausserordentliche Kuendigung und Widerruf: Bearbeitung von Hand,
  Hinweis an info@ (Erstattung/Wertersatz sind Einzelfaelle).
Die Texte der Mails sind Entwuerfe und vor dem Start rechtlich zu pruefen (LAW-002/LAW-003).
"""
import html
import os
import json
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import investtimer_konto as konto

STRIPE_API = "https://api.stripe.com"   # in Tests ersetzbar

ABSENDER = "InvestTimer <abo@investtimer.net>"
KOPIE = "info@investtimer.net"
BERLIN = ZoneInfo("Europe/Berlin")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,24}$", re.I)

SCHEMA = """
CREATE TABLE IF NOT EXISTS erklaerung (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  art TEXT NOT NULL,            -- kuendigung | widerruf
  eingang INTEGER NOT NULL,     -- Unix-Zeit
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  angaben TEXT NOT NULL,        -- JSON: Kuendigungsart, Grund, Zeitpunkt, Vertrag
  ergebnis TEXT                 -- JSON: was automatisch passiert ist
);
CREATE TABLE IF NOT EXISTS abo_mail (
  schluessel TEXT PRIMARY KEY,  -- uid + Anlass + Zeitraum, gegen doppelte Mails
  gesendet INTEGER NOT NULL
);
"""


class Fehler(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


def _db():
    db = konto.verbinden()
    db.executescript(SCHEMA)
    return db


def zeit_text(ts):
    d = datetime.fromtimestamp(ts, BERLIN)
    return d.strftime("%d.%m.%Y um %H:%M:%S Uhr")


def datum_text(ts):
    return datetime.fromtimestamp(ts, BERLIN).strftime("%d.%m.%Y")


def pruefen(art, d):
    name = str(d.get("name", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    if not (2 <= len(name) <= 120):
        raise Fehler("name")
    if not EMAIL_RE.match(email):
        raise Fehler("email")
    angaben = {"vertrag": "InvestTimer Premium"}
    if art == "kuendigung":
        k = d.get("kuendigungsart")
        if k not in ("ordentlich", "ausserordentlich"):
            raise Fehler("kuendigungsart")
        grund = str(d.get("grund", "")).strip()[:2000]
        if k == "ausserordentlich" and len(grund) < 3:
            raise Fehler("grund")
        zp = d.get("zeitpunkt", "naechstmoeglich")
        if zp not in ("naechstmoeglich", "datum"):
            raise Fehler("zeitpunkt")
        datum = str(d.get("datum", "")).strip()
        if zp == "datum" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum):
            raise Fehler("datum")
        angaben.update(kuendigungsart=k, grund=grund, zeitpunkt=zp, datum=datum if zp == "datum" else "")
    else:
        angaben["bestelldatum"] = str(d.get("bestelldatum", "")).strip()[:20]
    return name, email, angaben


def speichern(art, name, email, angaben, ergebnis=None):
    eingang = int(time.time())
    with _db() as db:
        cur = db.execute("INSERT INTO erklaerung (art, eingang, name, email, angaben, ergebnis) VALUES (?,?,?,?,?,?)",
                         (art, eingang, name, email, json.dumps(angaben, ensure_ascii=False), json.dumps(ergebnis or {})))
        return cur.lastrowid, eingang


def ergebnis_setzen(eid, ergebnis):
    with _db() as db:
        db.execute("UPDATE erklaerung SET ergebnis=? WHERE id=?", (json.dumps(ergebnis, ensure_ascii=False), eid))


# --- Stripe ------------------------------------------------------------------

def stripe_abos(stripe, email):
    """Laufende Web-Abos zu einer E-Mail-Adresse (Kunde bei Stripe)."""
    auth = (stripe["secret"], "")
    r = requests.get(stripe.get("api", STRIPE_API) + "/v1/customers", params={"email": email, "limit": 10}, auth=auth, timeout=15)
    r.raise_for_status()
    abos = []
    for kunde in r.json().get("data", []):
        s = requests.get(stripe.get("api", STRIPE_API) + "/v1/subscriptions", params={"customer": kunde["id"], "status": "all", "limit": 20},
                         auth=auth, timeout=15)
        s.raise_for_status()
        abos += [a for a in s.json().get("data", []) if a.get("status") in ("active", "trialing", "past_due")]
    return abos


def _periodenende(abo):
    ende = abo.get("current_period_end")
    if ende is None:  # neuere API-Versionen: Zeitraum je Position
        ende = max((i.get("current_period_end") or 0) for i in (abo.get("items") or {}).get("data", [])) or None
    return abo.get("trial_end") if abo.get("status") == "trialing" and abo.get("trial_end") else ende


MONAT = 30 * 86400


def verlaengert(abo):
    """Laeuft das Abo schon in einem verlaengerten Zeitraum (nicht mehr in der ersten Laufzeit)?"""
    beginn = abo.get("current_period_start")
    if beginn is None:
        beginn = min((i.get("current_period_start") or 0) for i in (abo.get("items") or {}).get("data", [{}])) or None
    start = abo.get("trial_end") or abo.get("start_date")
    return bool(beginn and start and beginn > start + 86400)


def stripe_kuendigen(stripe, abo, jetzt=None):
    """Kuendigung zum Ende des bezahlten Zeitraums. § 309 Nr. 9 BGB: nach einer stillschweigenden
    Verlaengerung hoechstens ein Monat Frist - mit "verlaengerung_monatlich": true endet ein schon
    verlaengertes Abo spaetestens nach einem Monat (Erstattung des Rests von Hand, Ergebnis 'erstattung')."""
    ende = _periodenende(abo)
    jetzt = int(jetzt or time.time())
    daten = {"cancel_at_period_end": "true"}
    if stripe.get("verlaengerung_monatlich") and verlaengert(abo) and ende and ende > jetzt + MONAT:
        daten = {"cancel_at": str(jetzt + MONAT), "proration_behavior": "none"}
    r = requests.post(stripe.get("api", STRIPE_API) + "/v1/subscriptions/" + abo["id"], data=daten,
                      auth=(stripe["secret"], ""), timeout=15)
    r.raise_for_status()
    neu = r.json()
    return neu.get("cancel_at") or _periodenende(neu) or ende


# --- Mail ----------------------------------------------------------------------

def senden(resend_key, an, betreff, text, kopie=True):
    if not resend_key:
        return False
    daten = {"from": ABSENDER, "to": [an], "reply_to": KOPIE, "subject": betreff, "text": text,
             "html": "<div style=\"font:15px/1.6 -apple-system,Segoe UI,Arial,sans-serif;color:#1c2f2b\">"
                     + "".join("<p>%s</p>" % html.escape(a).replace("\n", "<br>") for a in text.split("\n\n")) + "</div>"}
    if kopie and an.lower() != KOPIE:
        daten["bcc"] = [KOPIE]
    r = requests.post(os.environ.get("IT_RESEND_API", "https://api.resend.com") + "/emails", json=daten, headers={"Authorization": "Bearer " + resend_key}, timeout=15)
    return r.status_code < 300


FUSS = ("\n\nInvestTimer · investtimer.net\nFragen? Antworte einfach auf diese E-Mail.\n"
        "Abos, die du in der iOS-App über Apple abgeschlossen hast, verwaltest und kündigst du in den Einstellungen deiner Apple-ID "
        "(Einstellungen → dein Name → Abonnements).")


def text_kuendigung(name, eingang, angaben, ende, gefunden, erstattung=False):
    art = "ordentliche Kündigung" if angaben["kuendigungsart"] == "ordentlich" else "außerordentliche Kündigung"
    zp = "zum nächstmöglichen Zeitpunkt" if angaben["zeitpunkt"] == "naechstmoeglich" else "zum " + angaben["datum"]
    zeilen = ["Hallo %s," % name,
              "wir haben deine Kündigung am %s erhalten." % zeit_text(eingang),
              "Deine Angaben:\nVertrag: %s\nArt: %s\nZeitpunkt: %s%s" % (
                  angaben["vertrag"], art, zp, ("\nGrund: " + angaben["grund"]) if angaben.get("grund") else "")]
    if ende:
        zeilen.append("Dein Abo endet am %s. Bis dahin kannst du Premium weiter nutzen, danach wird nichts mehr abgebucht." % datum_text(ende))
        if erstattung:
            zeilen.append("Für die bereits bezahlte Zeit nach diesem Datum erstatten wir dir den Betrag anteilig auf dein Zahlungsmittel.")
    elif gefunden is False:
        zeilen.append("Zu dieser E-Mail-Adresse haben wir kein laufendes Abo über die Website gefunden. Wir prüfen deine Angaben "
                      "von Hand und melden uns, wann dein Vertrag endet.")
    else:
        zeilen.append("Wir bearbeiten deine Kündigung und bestätigen dir das Vertragsende in einer weiteren E-Mail.")
    return "\n\n".join(zeilen) + FUSS


def text_widerruf(name, eingang, angaben):
    return "\n\n".join([
        "Hallo %s," % name,
        "wir haben deinen Widerruf am %s erhalten." % zeit_text(eingang),
        "Vertrag: %s%s" % (angaben["vertrag"], ("\nBestellt am: " + angaben["bestelldatum"]) if angaben.get("bestelldatum") else ""),
        "Wir bearbeiten den Widerruf und melden uns mit den Einzelheiten zur Rückzahlung."]) + FUSS


# --- Abo-Mails (FR-020) ----------------------------------------------------

def abo_mail_einmal(schluessel):
    """True, wenn diese Mail noch nicht gesendet wurde (und merkt sie sich)."""
    with _db() as db:
        try:
            db.execute("INSERT INTO abo_mail VALUES (?,?)", (schluessel, int(time.time())))
            return True
        except Exception:
            return False


def abo_mail_text(anlass, s):
    """Text je Anlass aus dem einheitlichen Abo-Stand (konto.status). None = keine Mail."""
    preis = "%s pro %s" % (s.get("preis") or "", s.get("intervall") or "")
    bis = datum_text(s["premiumBis"] / 1000) if s.get("premiumBis") else ""
    if anlass == "teststart":
        return ("Deine 7 Tage InvestTimer Premium laufen",
                "Willkommen bei InvestTimer Premium. Deine kostenlose Testphase läuft bis %s.\n\n"
                "Danach beginnt dein Abo (%s) automatisch, die erste Abbuchung erfolgt am %s. "
                "Wenn du das nicht möchtest, kündige vorher unter „Mein Konto“ → „Abo verwalten oder kündigen“ – dann wird nichts abgebucht." % (bis, preis, bis))
    if anlass == "testende":
        return ("Deine Testphase endet am %s" % bis,
                "In zwei Tagen endet deine kostenlose Testphase. Am %s beginnt dein Abo (%s) und wird zum ersten Mal abgebucht.\n\n"
                "Möchtest du das nicht, kündige bis dahin unter „Mein Konto“ → „Abo verwalten oder kündigen“." % (bis, preis))
    if anlass == "bezahlt":
        return ("Dein InvestTimer Premium ist jetzt aktiv",
                "Deine Testphase ist vorbei, dein Abo (%s) läuft jetzt. Die nächste Verlängerung ist am %s. "
                "Den Beleg findest du unter „Mein Konto“ → „Abo verwalten“." % (preis, bis))
    if anlass == "gekuendigt":
        return ("Dein Abo ist gekündigt",
                "Dein Abo verlängert sich nicht mehr. Premium bleibt bis %s aktiv, danach wird nichts mehr abgebucht." % bis)
    if anlass == "abgelaufen":
        return ("Dein Premium-Zugang ist beendet",
                "Dein Premium-Zugang ist abgelaufen. Den zeitversetzten Marktstress siehst du weiter kostenlos. "
                "Unter „Mein Konto“ kannst du Premium jederzeit wieder abonnieren.")
    return None


def abo_anlass(typ, period_type, status_vorher, kanal):
    """RevenueCat-Ereignis -> Anlass der Mail. Doppelte Nachrichten vermeiden: Apple bestaetigt
    Kauf, Verlaengerung und Kuendigung selbst, Stripe verschickt Zahlungsbelege selbst."""
    if kanal == "apple" and typ != "EXPIRATION":
        return None
    if typ == "INITIAL_PURCHASE":
        return "teststart" if period_type == "TRIAL" else None
    if typ == "RENEWAL" and period_type == "NORMAL" and status_vorher == "test":
        return "bezahlt"
    if typ == "CANCELLATION":
        return "gekuendigt"
    if typ == "EXPIRATION":
        return "abgelaufen"
    return None
