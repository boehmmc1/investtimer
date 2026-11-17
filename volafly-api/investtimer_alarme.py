"""Alarme (eigene Schwelle) und Push-Geraete der InvestTimer-Nutzer.

SQLite auf dem Server (Frankfurt), nur Standardbibliothek. Wird von der
Volafly-API (Endpunkte /v1/investtimer/alarme, /v1/investtimer/push/...) und
vom Versand server/push_senden.py genutzt. Gespeichert werden nur die
Supabase-Nutzer-ID, Richtung und Schwelle sowie die Push-Adresse des Geraets
(vom Browser erzeugt, enthaelt keinen Namen und keine E-Mail).
"""
import os
import sqlite3
import time

DB = os.environ.get("INVESTTIMER_ALARME_DB", "/var/lib/investtimer/alarme.db")
MAX_ALARME = 5
MAX_GERAETE = 5

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
    return db


class Fehler(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


def _alarm(r):
    return {"id": r["id"], "richtung": r["richtung"], "schwelle": r["schwelle"], "aktiv": bool(r["aktiv"])}


def liste(uid):
    with verbinden() as db:
        alarme = [_alarm(r) for r in db.execute("SELECT * FROM alarme WHERE uid=? ORDER BY id", (uid,))]
        geraete = db.execute("SELECT COUNT(*) FROM geraete WHERE uid=?", (uid,)).fetchone()[0]
    return {"alarme": alarme, "geraete": geraete, "max": MAX_ALARME}


def neu(uid, richtung, schwelle):
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
        db.execute("INSERT INTO alarme (uid, richtung, schwelle, erstellt) VALUES (?,?,?,?)",
                   (uid, richtung, schwelle, int(time.time())))
    return liste(uid)


def aendern(uid, alarm_id, aktiv):
    with verbinden() as db:
        n = db.execute("UPDATE alarme SET aktiv=? WHERE id=? AND uid=?", (1 if aktiv else 0, int(alarm_id), uid)).rowcount
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
    with verbinden() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM alarme WHERE aktiv=1 AND uid IN (SELECT uid FROM geraete)")]


def ausgeloest(alarm_id, tag):
    with verbinden() as db:
        db.execute("UPDATE alarme SET ausgeloest_am=? WHERE id=?", (tag, alarm_id))


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
