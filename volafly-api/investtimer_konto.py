"""Konto, Premium-Berechtigung und KI-Kontingent der InvestTimer-Nutzer.

Eine Wahrheit fuer Web und App: RevenueCat sammelt Kaeufe aus Stripe (Web)
und Apple (App) unter derselben App-User-ID (= Supabase-Nutzer-ID). Diese
Datei haelt davon nur den abgeleiteten Stand (Zwischenspeicher), damit die
API Premium serverseitig pruefen kann, auch wenn RevenueCat kurz nicht
erreichbar ist. Zahlungsdaten (Karte, Adresse) liegen nie hier.

SQLite unter /var/lib/investtimer/konto.db, nur Standardbibliothek.
"""
import hashlib
import os
import sqlite3
import time
from datetime import datetime, timezone

DB = os.environ.get("INVESTTIMER_KONTO_DB", "/var/lib/investtimer/konto.db")

# Tarife: Produkt-IDs je Kanal -> gemeinsamer Tarif. Preise nur zur Anzeige,
# massgeblich ist der Preis beim Zahlungsanbieter (spaetere Preisaenderung dort).
TARIFE = {
    "monatlich": {"name": "InvestTimer Premium Monatlich", "preis": "4,99 €", "intervall": "Monat", "cent": 499},
    "jaehrlich": {"name": "InvestTimer Premium Jährlich", "preis": "39,99 €", "intervall": "Jahr", "cent": 3999},
}
PRODUKTE = {
    # Apple App Store
    "net.investtimer.premium.monthly": "monatlich",
    "net.investtimer.premium.yearly": "jaehrlich",
    # Stripe (RevenueCat nennt das Produkt beim Stripe-Kanal nach der Stripe-Produkt-ID)
    "investtimer_premium_monthly": "monatlich",
    "investtimer_premium_yearly": "jaehrlich",
}
ENTITLEMENT = "premium"
KANAELE = {"APP_STORE": "apple", "MAC_APP_STORE": "apple", "STRIPE": "stripe", "RC_BILLING": "stripe",
           "PLAY_STORE": "google", "PROMOTIONAL": "promo"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS berechtigung (
  uid TEXT PRIMARY KEY,
  status TEXT NOT NULL,              -- frei | test | aktiv | gekuendigt | zahlungsproblem | abgelaufen | erstattet
  kanal TEXT,                        -- stripe | apple | google | promo
  tarif TEXT,                        -- monatlich | jaehrlich
  produkt TEXT,
  periode_start INTEGER,             -- ms
  premium_bis INTEGER,               -- ms, Ende der Berechtigung
  verlaengerung INTEGER NOT NULL DEFAULT 0,
  test_genutzt INTEGER NOT NULL DEFAULT 0,
  stripe_kunde TEXT,
  stand_ms INTEGER NOT NULL DEFAULT 0, -- Zeitpunkt des letzten verarbeiteten Ereignisses
  aktualisiert INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ereignis (
  id TEXT PRIMARY KEY,               -- Ereignis-ID von RevenueCat/Stripe (Mehrfachzustellung)
  uid TEXT,
  typ TEXT,
  empfangen INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ki_nutzung (
  uid TEXT NOT NULL,
  tag TEXT NOT NULL,                 -- YYYY-MM-DD
  anzahl INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (uid, tag)
);
CREATE TABLE IF NOT EXISTS test_marker (
  merkmal TEXT PRIMARY KEY,          -- SHA-256 der E-Mail-Adresse, nur gegen zweite Testphase
  erstellt INTEGER NOT NULL
);
"""


class Fehler(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


def verbinden():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    neu = not os.path.exists(DB)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    if neu:
        os.chmod(DB, 0o600)
    return db


def _ms(wert):
    """ISO-Datum (RevenueCat) oder ms -> ms."""
    if wert in (None, ""):
        return None
    if isinstance(wert, (int, float)):
        return int(wert)
    return int(datetime.fromisoformat(str(wert).replace("Z", "+00:00")).timestamp() * 1000)


def jetzt_ms():
    return int(time.time() * 1000)


# --- Lesen -------------------------------------------------------------------

def roh(uid):
    with verbinden() as db:
        r = db.execute("SELECT * FROM berechtigung WHERE uid=?", (uid,)).fetchone()
    return dict(r) if r else None


def ist_premium(uid, jetzt=None):
    """Serverseitige Pruefung: Premium, solange premium_bis in der Zukunft liegt
    (gilt auch fuer gekuendigte Abos bis Periodenende und fuer die Testphase)."""
    r = roh(uid) if uid else None
    if not r or not r["premium_bis"] or r["status"] in ("erstattet", "abgelaufen"):
        return False
    return r["premium_bis"] > (jetzt or jetzt_ms())


def status(uid, jetzt=None):
    """Einheitliche Sicht fuer 'Mein Abonnement' (Web und App gleich)."""
    jetzt = jetzt or jetzt_ms()
    r = roh(uid)
    premium = ist_premium(uid, jetzt)
    aus = {"premium": premium, "status": "frei", "kanal": None, "tarif": None, "tarifName": None, "preis": None,
           "intervall": None, "periodeStart": None, "premiumBis": None, "verlaengerung": False,
           "testTageRest": None, "testGenutzt": False, "verwaltung": None}
    if not r:
        return aus
    st = r["status"]
    if not premium and st in ("test", "aktiv", "gekuendigt", "zahlungsproblem"):
        st = "abgelaufen"
    tarif = TARIFE.get(r["tarif"] or "")
    aus.update(status=st, kanal=r["kanal"], tarif=r["tarif"], tarifName=tarif and tarif["name"],
               preis=tarif and tarif["preis"], intervall=tarif and tarif["intervall"],
               periodeStart=r["periode_start"], premiumBis=r["premium_bis"],
               verlaengerung=bool(r["verlaengerung"]) and premium, testGenutzt=bool(r["test_genutzt"]))
    if premium and st == "test" and r["premium_bis"]:
        aus["testTageRest"] = max(0, -(-(r["premium_bis"] - jetzt) // 86400000))
    if r["kanal"] == "apple":
        aus["verwaltung"] = "apple"
    elif r["kanal"] == "stripe" and r["stripe_kunde"]:
        aus["verwaltung"] = "stripe"
    elif r["kanal"] == "google":
        aus["verwaltung"] = "google"
    return aus


def kaufen_erlaubt(uid):
    """Doppelte Abos verhindern: kein Neukauf, solange Premium laeuft."""
    if ist_premium(uid):
        raise Fehler("schon_premium", 409)
    r = roh(uid)
    return {"testErlaubt": not (r and r["test_genutzt"])}


# --- Schreiben aus RevenueCat ---------------------------------------------

def _speichern(db, uid, werte, stand_ms):
    alt = db.execute("SELECT * FROM berechtigung WHERE uid=?", (uid,)).fetchone()
    if alt and stand_ms and alt["stand_ms"] > stand_ms:
        return False  # aelteres Ereignis kommt verspaetet an: ignorieren
    w = dict(alt) if alt else {"uid": uid, "test_genutzt": 0, "stripe_kunde": None}
    test_vorher = bool(w.get("test_genutzt"))
    w.update({k: v for k, v in werte.items() if v is not None or k in ("premium_bis",)})
    w["test_genutzt"] = 1 if (test_vorher or werte.get("test_genutzt")) else 0
    w["stand_ms"] = max(stand_ms or 0, alt["stand_ms"] if alt else 0)
    w["aktualisiert"] = int(time.time())
    spalten = ["uid", "status", "kanal", "tarif", "produkt", "periode_start", "premium_bis", "verlaengerung",
               "test_genutzt", "stripe_kunde", "stand_ms", "aktualisiert"]
    db.execute("INSERT OR REPLACE INTO berechtigung (%s) VALUES (%s)" % (",".join(spalten), ",".join("?" * len(spalten))),
               [w.get(s) for s in spalten])
    return True


def aus_subscriber(uid, abonnent, jetzt=None):
    """Stand aus dem RevenueCat-Abonnentenobjekt (GET /v1/subscribers/{id}) ableiten.
    Das ist die verlaessliche Quelle: unabhaengig von Reihenfolge und Mehrfachzustellung."""
    jetzt = jetzt or jetzt_ms()
    sub = (abonnent or {}).get("subscriber") or {}
    abos = sub.get("subscriptions") or {}
    ent = (sub.get("entitlements") or {}).get(ENTITLEMENT)
    test_genutzt = any((a.get("period_type") == "trial") for a in abos.values())
    if not ent:
        werte = {"status": "frei", "premium_bis": None, "verlaengerung": 0, "test_genutzt": test_genutzt}
    else:
        pid = ent.get("product_identifier")
        a = abos.get(pid) or {}
        bis = _ms(ent.get("expires_date"))
        kanal = KANAELE.get(str(a.get("store", "")).upper(), a.get("store"))
        if a.get("refunded_at"):
            st = "erstattet"
        elif bis is not None and bis <= jetzt:
            st = "abgelaufen"
        elif a.get("billing_issues_detected_at"):
            st = "zahlungsproblem"
        elif a.get("unsubscribe_detected_at"):
            st = "gekuendigt"
        elif a.get("period_type") == "trial":
            st = "test"
        else:
            st = "aktiv"
        werte = {"status": st, "kanal": kanal, "produkt": pid, "tarif": PRODUKTE.get(pid),
                 "periode_start": _ms(a.get("purchase_date")), "premium_bis": bis,
                 "verlaengerung": 0 if (a.get("unsubscribe_detected_at") or st in ("erstattet", "abgelaufen")) else 1,
                 "test_genutzt": test_genutzt}
        if st == "erstattet":
            werte["premium_bis"] = min(bis or jetzt, jetzt)
    with verbinden() as db:
        _speichern(db, uid, werte, jetzt)
    return status(uid, jetzt)


def rc_ereignis(ereignis):
    """Webhook-Ereignis von RevenueCat anwenden (Notweg, wenn der Abruf des
    Abonnenten scheitert). Idempotent ueber die Ereignis-ID, verspaetete
    Ereignisse werden ueber den Zeitstempel verworfen. Rueckgabe: uid oder None."""
    e = ereignis.get("event") or ereignis
    eid, typ = str(e.get("id") or ""), str(e.get("type") or "")
    uid = e.get("app_user_id") or e.get("original_app_user_id")
    if not eid or not uid or typ == "TEST":
        return None
    with verbinden() as db:
        if db.execute("SELECT 1 FROM ereignis WHERE id=?", (eid,)).fetchone():
            return None
        db.execute("INSERT INTO ereignis VALUES (?,?,?,?)", (eid, uid, typ, int(time.time())))
        if ENTITLEMENT not in (e.get("entitlement_ids") or [ENTITLEMENT]):
            return uid
        pid = e.get("product_id")
        bis = _ms(e.get("expiration_at_ms"))
        werte = {"kanal": KANAELE.get(str(e.get("store", "")).upper()), "produkt": pid, "tarif": PRODUKTE.get(pid),
                 "periode_start": _ms(e.get("purchased_at_ms")), "premium_bis": bis,
                 "test_genutzt": e.get("period_type") == "TRIAL"}
        test = e.get("period_type") == "TRIAL"
        if typ in ("INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION", "PRODUCT_CHANGE", "SUBSCRIPTION_EXTENDED",
                   "TEMPORARY_ENTITLEMENT_GRANT"):
            werte.update(status="test" if test else "aktiv", verlaengerung=1)
        elif typ == "CANCELLATION":
            if e.get("cancel_reason") == "CUSTOMER_SUPPORT":   # Erstattung
                werte.update(status="erstattet", verlaengerung=0, premium_bis=jetzt_ms())
            else:
                werte.update(status="gekuendigt", verlaengerung=0)
        elif typ == "BILLING_ISSUE":
            werte.update(status="zahlungsproblem")
        elif typ == "EXPIRATION":
            werte.update(status="abgelaufen", verlaengerung=0)
        else:
            return uid
        if werte.get("kanal") == "stripe" and e.get("store") == "STRIPE" and isinstance(e.get("subscriber_attributes"), dict):
            kunde = (e["subscriber_attributes"].get("$stripeCustomerId") or {}).get("value")
            if kunde:
                werte["stripe_kunde"] = kunde
        _speichern(db, uid, werte, int(e.get("event_timestamp_ms") or 0))
    return uid


def stripe_kunde_setzen(uid, kunde):
    with verbinden() as db:
        if db.execute("SELECT 1 FROM berechtigung WHERE uid=?", (uid,)).fetchone():
            db.execute("UPDATE berechtigung SET stripe_kunde=? WHERE uid=?", (kunde, uid))
        else:
            db.execute("INSERT INTO berechtigung (uid, status, stripe_kunde, aktualisiert) VALUES (?,?,?,?)",
                       (uid, "frei", kunde, int(time.time())))


# --- Testphase nur einmal ---------------------------------------------------

def _merkmal(email):
    return hashlib.sha256(("investtimer-test:" + email.strip().lower()).encode()).hexdigest()


def test_schon_genutzt(uid, email=None):
    r = roh(uid)
    if r and r["test_genutzt"]:
        return True
    if email:
        with verbinden() as db:
            return bool(db.execute("SELECT 1 FROM test_marker WHERE merkmal=?", (_merkmal(email),)).fetchone())
    return False


def test_merken(email):
    with verbinden() as db:
        db.execute("INSERT OR IGNORE INTO test_marker VALUES (?,?)", (_merkmal(email), int(time.time())))


# --- KI-Kontingent --------------------------------------------------------

def ki_stand(uid, tag=None):
    tag = tag or time.strftime("%Y-%m-%d")
    with verbinden() as db:
        heute = db.execute("SELECT anzahl FROM ki_nutzung WHERE uid=? AND tag=?", (uid, tag)).fetchone()
        monat = db.execute("SELECT COALESCE(SUM(anzahl),0) FROM ki_nutzung WHERE uid=? AND tag LIKE ?",
                           (uid, tag[:7] + "%")).fetchone()[0]
    return {"heute": heute[0] if heute else 0, "monat": monat}


def ki_buchen(uid, limit_tag, limit_monat, tag=None):
    """Zaehlt eine Frage, wenn das Kontingent reicht. Rueckgabe: (erlaubt, stand)."""
    tag = tag or time.strftime("%Y-%m-%d")
    with verbinden() as db:
        db.execute("BEGIN IMMEDIATE")
        heute = (db.execute("SELECT anzahl FROM ki_nutzung WHERE uid=? AND tag=?", (uid, tag)).fetchone() or [0])[0]
        monat = db.execute("SELECT COALESCE(SUM(anzahl),0) FROM ki_nutzung WHERE uid=? AND tag LIKE ?",
                           (uid, tag[:7] + "%")).fetchone()[0]
        if heute >= limit_tag or monat >= limit_monat:
            return False, {"heute": heute, "monat": monat}
        db.execute("INSERT INTO ki_nutzung VALUES (?,?,1) ON CONFLICT(uid, tag) DO UPDATE SET anzahl=anzahl+1", (uid, tag))
        # Alte Tage (> 2 Monate) aufraeumen
        db.execute("DELETE FROM ki_nutzung WHERE tag < date(?, '-62 days')", (tag,))
    return True, {"heute": heute + 1, "monat": monat + 1}


# --- Kontoloeschung ------------------------------------------------------

def loeschen_pruefen(uid):
    """Ein laufendes Abo mit Verlaengerung muss vorher gekuendigt werden, sonst
    wuerde beim Anbieter weiter abgebucht (Apple-Abos koennen wir nicht kuendigen)."""
    s = status(uid)
    if s["premium"] and s["verlaengerung"]:
        raise Fehler("abo_aktiv", 409)
    return s


def konto_loeschen(uid):
    with verbinden() as db:
        db.execute("DELETE FROM berechtigung WHERE uid=?", (uid,))
        db.execute("DELETE FROM ki_nutzung WHERE uid=?", (uid,))
        db.execute("DELETE FROM ereignis WHERE uid=?", (uid,))
