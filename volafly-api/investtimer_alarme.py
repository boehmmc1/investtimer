"""Alarme (eigene Schwelle) und Push-Geraete der InvestTimer-Nutzer.

SQLite auf dem Server (Frankfurt), nur Standardbibliothek. Wird von der
Volafly-API (Endpunkte /v1/investtimer/alarme, /v1/investtimer/push/...) und
vom Versand server/push_senden.py genutzt. Gespeichert werden nur die
Supabase-Nutzer-ID, Richtung und Schwelle sowie die Push-Adresse des Geraets
(vom Browser erzeugt, enthaelt keinen Namen und keine E-Mail).
"""
import hashlib
import hmac
import os
import sqlite3
import time

DB = os.environ.get("INVESTTIMER_ALARME_DB", "/var/lib/investtimer/alarme.db")
MAX_ALARME = 5
MAX_GERAETE = 5
KANAELE = ("push", "email", "beide")
ABMELDE_SCHLUESSEL = os.environ.get("INVESTTIMER_ABMELDE_KEY", "/root/.investtimer/alarm-abmelde-key")

SCHEMA = """
CREATE TABLE IF NOT EXISTS alarme (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  uid TEXT NOT NULL,
  richtung TEXT NOT NULL CHECK (richtung IN ('ueber','unter')),
  schwelle INTEGER NOT NULL CHECK (schwelle BETWEEN 1 AND 99),
  aktiv INTEGER NOT NULL DEFAULT 1,
  erstellt INTEGER NOT NULL,
  ausgeloest_am TEXT
);
CREATE INDEX IF NOT EXISTS alarme_uid ON alarme(uid);
CREATE TABLE IF NOT EXISTS geraete (
  endpoint TEXT PRIMARY KEY,
  uid TEXT NOT NULL,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  erstellt INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS geraete_uid ON geraete(uid);
CREATE TABLE IF NOT EXISTS stand (schluessel TEXT PRIMARY KEY, wert TEXT);
"""


def verbinden():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    spalten = {r[1] for r in db.execute("PRAGMA table_info(alarme)")}
    if "kanal" not in spalten:  # E-Mail-Alarme (DAT-002): Kanal je Alarm, Ziel ist die Konto-Adresse
        db.execute("ALTER TABLE alarme ADD COLUMN kanal TEXT NOT NULL DEFAULT 'push'")
        db.execute("ALTER TABLE alarme ADD COLUMN email TEXT")
    if "sprache" not in spalten:  # Sprache der Nachrichten (Push/E-Mail), beim Anlegen/Aendern aus der Seite
        db.execute("ALTER TABLE alarme ADD COLUMN sprache TEXT NOT NULL DEFAULT 'de'")
    if "scharf" not in spalten:  # Ueberqueren mit Ruecklauf: Alarm meldet sich erst nach erneutem Ueberqueren
        db.execute("ALTER TABLE alarme ADD COLUMN scharf INTEGER NOT NULL DEFAULT 1")
        wert = db.execute("SELECT wert FROM stand WHERE schluessel='letzter_wert'").fetchone()
        if wert:
            w = int(wert[0])
            db.execute("UPDATE alarme SET scharf=CASE WHEN richtung='ueber' THEN (? <= schwelle) ELSE (? >= schwelle) END", (w, w))
    return db


def scharf_bei(richtung, schwelle, wert):
    """Scharf, solange der Wert auf der Ausgangsseite der Schwelle liegt (Schwelle selbst zaehlt dazu).
    'ueber X': scharf bei Wert <= X, loest aus beim Wechsel auf > X. 'unter X': scharf bei Wert >= X, loest aus bei < X."""
    if wert is None:
        return True
    return int(wert) <= schwelle if richtung == "ueber" else int(wert) >= schwelle


def ausgeloest_bei(richtung, schwelle, wert):
    return int(wert) > schwelle if richtung == "ueber" else int(wert) < schwelle


def _letzter_wert(db):
    r = db.execute("SELECT wert FROM stand WHERE schluessel='letzter_wert'").fetchone()
    return int(r[0]) if r else None


class Fehler(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


def _alarm(r):
    return {"id": r["id"], "richtung": r["richtung"], "schwelle": r["schwelle"], "aktiv": bool(r["aktiv"]), "kanal": r["kanal"],
            "scharf": bool(r["scharf"])}


def _kanal(kanal, email):
    kanal = kanal or "push"
    if kanal not in KANAELE:
        raise Fehler("kanal")
    if kanal != "push" and not email:
        raise Fehler("email")
    return kanal


def liste(uid):
    with verbinden() as db:
        alarme = [_alarm(r) for r in db.execute("SELECT * FROM alarme WHERE uid=? ORDER BY id", (uid,))]
        geraete = db.execute("SELECT COUNT(*) FROM geraete WHERE uid=?", (uid,)).fetchone()[0]
        wert = _letzter_wert(db)
    return {"alarme": alarme, "geraete": geraete, "max": MAX_ALARME, "wert": wert}


def _sprache(s):
    return "en" if s == "en" else "de"


def neu(uid, richtung, schwelle, kanal="push", email=None, sprache="de"):
    kanal = _kanal(kanal, email)
    if richtung not in ("ueber", "unter"):
        raise Fehler("richtung")
    try:
        schwelle = int(schwelle)
    except (TypeError, ValueError):
        raise Fehler("schwelle")
    if not 1 <= schwelle <= 99:
        raise Fehler("schwelle")
    with verbinden() as db:
        if db.execute("SELECT COUNT(*) FROM alarme WHERE uid=?", (uid,)).fetchone()[0] >= MAX_ALARME:
            raise Fehler("max", 409)
        if db.execute("SELECT 1 FROM alarme WHERE uid=? AND richtung=? AND schwelle=?", (uid, richtung, schwelle)).fetchone():
            raise Fehler("doppelt", 409)
        # Liegt der Wert schon jenseits der Schwelle: keine sofortige Nachricht, Alarm wartet auf Ruecklauf
        db.execute("INSERT INTO alarme (uid, richtung, schwelle, erstellt, kanal, email, scharf, sprache) VALUES (?,?,?,?,?,?,?,?)",
                   (uid, richtung, schwelle, int(time.time()), kanal, email if kanal != "push" else None,
                    1 if scharf_bei(richtung, schwelle, _letzter_wert(db)) else 0, _sprache(sprache)))
    return liste(uid)


def aendern(uid, alarm_id, aktiv=None, kanal=None, email=None, sprache=None):
    with verbinden() as db:
        n = 0
        if sprache is not None:
            db.execute("UPDATE alarme SET sprache=? WHERE id=? AND uid=?", (_sprache(sprache), int(alarm_id), uid))
        if aktiv is not None:
            n = db.execute("UPDATE alarme SET aktiv=? WHERE id=? AND uid=?", (1 if aktiv else 0, int(alarm_id), uid)).rowcount
            if aktiv and n:  # Wieder eingeschaltet: wie neu angelegt behandeln
                r = db.execute("SELECT richtung, schwelle FROM alarme WHERE id=?", (int(alarm_id),)).fetchone()
                db.execute("UPDATE alarme SET scharf=? WHERE id=?", (1 if scharf_bei(r[0], r[1], _letzter_wert(db)) else 0, int(alarm_id)))
        if kanal is not None:
            kanal = _kanal(kanal, email)
            n = db.execute("UPDATE alarme SET kanal=?, email=? WHERE id=? AND uid=?",
                           (kanal, email if kanal != "push" else None, int(alarm_id), uid)).rowcount
    if not n:
        raise Fehler("unbekannt", 404)
    return liste(uid)


def loeschen(uid, alarm_id):
    with verbinden() as db:
        n = db.execute("DELETE FROM alarme WHERE id=? AND uid=?", (int(alarm_id), uid)).rowcount
    if not n:
        raise Fehler("unbekannt", 404)
    return liste(uid)


def geraet_speichern(uid, abo):
    if isinstance(abo, dict) and "apns" in abo:   # iOS-App: Geraete-Token von Apple (hex)
        tok = str(abo["apns"]).strip().lower()
        if not (32 <= len(tok) <= 200) or any(c not in "0123456789abcdef" for c in tok):
            raise Fehler("abo")
        abo = {"endpoint": "apns:" + tok, "keys": {"p256dh": "", "auth": ""}}
    try:
        endpoint, keys = str(abo["endpoint"]), abo["keys"]
        p256dh, auth = str(keys["p256dh"]), str(keys["auth"])
    except (KeyError, TypeError):
        raise Fehler("abo")
    if not (endpoint.startswith("https://") or endpoint.startswith("apns:")) or len(endpoint) > 1000 or len(p256dh) > 200 or len(auth) > 100:
        raise Fehler("abo")
    with verbinden() as db:
        db.execute("INSERT INTO geraete (endpoint, uid, p256dh, auth, erstellt) VALUES (?,?,?,?,?) "
                   "ON CONFLICT(endpoint) DO UPDATE SET uid=excluded.uid, p256dh=excluded.p256dh, auth=excluded.auth",
                   (endpoint, uid, p256dh, auth, int(time.time())))
        # Nur die juengsten Geraete je Nutzer behalten
        db.execute("DELETE FROM geraete WHERE uid=? AND endpoint NOT IN "
                   "(SELECT endpoint FROM geraete WHERE uid=? ORDER BY erstellt DESC LIMIT ?)", (uid, uid, MAX_GERAETE))
    return liste(uid)


def geraet_loeschen(uid, endpoint):
    with verbinden() as db:
        db.execute("DELETE FROM geraete WHERE uid=? AND endpoint=?", (uid, str(endpoint)))
    return liste(uid)


def konto_loeschen(uid):
    """Alle Alarme und Geraete eines Nutzers entfernen (Kontoloeschung)."""
    with verbinden() as db:
        db.execute("DELETE FROM alarme WHERE uid=?", (uid,))
        db.execute("DELETE FROM geraete WHERE uid=?", (uid,))


# --- fuer den Versand -------------------------------------------------------

def geraete(uid=None):
    with verbinden() as db:
        sql, args = ("SELECT * FROM geraete WHERE uid=?", (uid,)) if uid else ("SELECT * FROM geraete", ())
        return [dict(r) for r in db.execute(sql, args)]


def aktive_alarme():
    """Alle eingeschalteten Alarme (auch ohne Geraet, damit Scharf/Ruecklauf immer mitlaeuft)."""
    with verbinden() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM alarme WHERE aktiv=1")]


# --- Abmeldung per E-Mail-Link (ohne Login) -----------------------------------

def _abmelde_key():
    try:
        with open(ABMELDE_SCHLUESSEL, "rb") as f:
            return f.read().strip()
    except OSError:
        key = os.urandom(32).hex().encode()
        with open(os.open(ABMELDE_SCHLUESSEL, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
            f.write(key)
        return key


def abmelde_token(alarm_id, uid):
    """Signiert genau einen Alarm eines Nutzers. Gilt bis der Alarm geloescht ist."""
    return hmac.new(_abmelde_key(), ("alarm-mail:%d:%s" % (int(alarm_id), uid)).encode(), hashlib.sha256).hexdigest()[:32]


def per_link_abmelden(alarm_id, token):
    """E-Mail fuer diesen einen Alarm abschalten. Rueckgabe: 'ok', 'schon' oder Fehler."""
    try:
        alarm_id = int(alarm_id)
    except (TypeError, ValueError):
        raise Fehler("token", 400)
    with verbinden() as db:
        r = db.execute("SELECT * FROM alarme WHERE id=?", (alarm_id,)).fetchone()
        if not r or not hmac.compare_digest(abmelde_token(alarm_id, r["uid"]), str(token or "")):
            raise Fehler("token", 404)
        if r["kanal"] == "push":
            return "schon"
        if r["kanal"] == "beide":
            db.execute("UPDATE alarme SET kanal='push', email=NULL WHERE id=?", (alarm_id,))
        else:  # nur E-Mail: Alarm pausieren, damit nichts mehr kommt
            db.execute("UPDATE alarme SET kanal='push', email=NULL, aktiv=0 WHERE id=?", (alarm_id,))
    return "ok"


def ausgeloest(alarm_id, tag):
    with verbinden() as db:
        db.execute("UPDATE alarme SET ausgeloest_am=? WHERE id=?", (tag, alarm_id))


def scharf_setzen(alarm_id, scharf):
    with verbinden() as db:
        db.execute("UPDATE alarme SET scharf=? WHERE id=?", (1 if scharf else 0, alarm_id))


def geraet_entfernen(endpoint):
    with verbinden() as db:
        db.execute("DELETE FROM geraete WHERE endpoint=?", (endpoint,))


def stand(schluessel, wert=None):
    with verbinden() as db:
        if wert is None:
            r = db.execute("SELECT wert FROM stand WHERE schluessel=?", (schluessel,)).fetchone()
            return r[0] if r else None
        db.execute("INSERT INTO stand VALUES (?,?) ON CONFLICT(schluessel) DO UPDATE SET wert=excluded.wert",
                   (schluessel, str(wert)))
