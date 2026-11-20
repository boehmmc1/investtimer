"""KI-Limit und Kostenschutz fuer InvestTimer (Auftrag 20.11.2026).

- Freie Fragen (Antwort neu vom Modell): je Konto und Tag (IT_KI_TAG, Standard 1), je IP und Tag (IT_KI_IP_TAG, Standard 3),
  insgesamt je Tag (INVESTTIMER_CHAT_TAGESLIMIT, Standard 150). Tageswechsel 00:00 Europe/Berlin.
- Katalog-, Folge- und Ereignisfragen zaehlen nicht; muessen sie das Modell fragen, wird die Antwort je Tag, Sprache und
  Frage gespeichert (gleiche Frage am gleichen Tag = gleiche Antwort, kein neuer Aufruf).
- Kosten: jeder Modellaufruf wird mit seinen usage-Zahlen gebucht (Preise je Modell in investtimer_ki_preise.json).
  Ab dem Doppelten der Tagesschwelle sind freie Fragen bis Mitternacht pausiert.
- IP-Adressen werden nur im Arbeitsspeicher bis zum Ende des Tages gezaehlt (wie in der Datenschutzerklaerung), nie auf der Platte.
  Die API laeuft mit einem uvicorn-Prozess; nach einem Neustart beginnt die IP-Zaehlung neu.
SQLite: /var/lib/investtimer/ki.db (IT_KI_DB ueberschreibt, z. B. fuer Tests).
"""
import datetime
import json
import os
import sqlite3
import threading
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
PREISE_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investtimer_ki_preise.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS frei (
  tag TEXT NOT NULL, art TEXT NOT NULL, schluessel TEXT NOT NULL, anzahl INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (tag, art, schluessel)
);
CREATE TABLE IF NOT EXISTS kosten (
  tag TEXT NOT NULL, art TEXT NOT NULL, modell TEXT NOT NULL,
  eingabe INTEGER NOT NULL DEFAULT 0, ausgabe INTEGER NOT NULL DEFAULT 0,
  cache_lesen INTEGER NOT NULL DEFAULT 0, cache_schreiben INTEGER NOT NULL DEFAULT 0,
  aufrufe INTEGER NOT NULL DEFAULT 0, eur REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (tag, art, modell)
);
CREATE TABLE IF NOT EXISTS antwort_cache (
  tag TEXT NOT NULL, schluessel TEXT NOT NULL, antwort TEXT NOT NULL, PRIMARY KEY (tag, schluessel)
);
CREATE TABLE IF NOT EXISTS warnung (
  art TEXT NOT NULL, periode TEXT NOT NULL, gesendet TEXT NOT NULL, PRIMARY KEY (art, periode)
);
"""


def db_pfad():
    return os.environ.get("IT_KI_DB", "/var/lib/investtimer/ki.db")


def verbinden():
    pfad = db_pfad()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    neu = not os.path.exists(pfad)
    db = sqlite3.connect(pfad, timeout=10, isolation_level=None)
    db.executescript(SCHEMA)
    if neu:
        os.chmod(pfad, 0o600)
    return db


def jetzt():
    return datetime.datetime.now(BERLIN)


def tag(zeit=None):
    """Kalendertag in Europe/Berlin (YYYY-MM-DD)."""
    return (zeit or jetzt()).astimezone(BERLIN).strftime("%Y-%m-%d")


_IP = {}                     # (tag, ip) -> Anzahl freier Fragen, nur im Arbeitsspeicher
_IP_SPERRE = threading.Lock()


def _ip_anzahl(t, ip):
    return _IP.get((t, str(ip or "")), 0) if ip else 0


def _ip_plus(t, ip, n):
    if not ip:
        return
    with _IP_SPERRE:
        for k in [k for k in _IP if k[0] != t]:
            del _IP[k]
        _IP[(t, str(ip))] = max(0, _IP.get((t, str(ip)), 0) + n)


def _anzahl(db, t, art, schluessel):
    z = db.execute("SELECT anzahl FROM frei WHERE tag=? AND art=? AND schluessel=?", (t, art, schluessel)).fetchone()
    return z[0] if z else 0


def kosten_eur(db, t=None, monat=None):
    if monat:
        z = db.execute("SELECT COALESCE(SUM(eur),0) FROM kosten WHERE tag LIKE ?", (monat + "%",)).fetchone()
    else:
        z = db.execute("SELECT COALESCE(SUM(eur),0) FROM kosten WHERE tag=?", (t or tag(),)).fetchone()
    return float(z[0])


def pausiert(tagesschwelle_eur, t=None, db=None):
    """Freie Fragen pausiert, wenn die Tageskosten das Doppelte der Tagesschwelle erreichen (bis Mitternacht Berlin)."""
    if not tagesschwelle_eur or tagesschwelle_eur <= 0:
        return False
    eigene = db is None
    db = db or verbinden()
    try:
        return kosten_eur(db, t) >= 2 * tagesschwelle_eur
    finally:
        if eigene:
            db.close()


def stand(uid, ip, limit_konto, limit_ip, limit_gesamt, tagesschwelle_eur, t=None):
    """Zustand fuer die Anzeige, ohne zu buchen: verbraucht (Konto oder IP am Limit) bzw. ausgelastet (Gesamtbremse/Pause)."""
    t = t or tag()
    db = verbinden()
    try:
        konto = _anzahl(db, t, "konto", uid) if uid else 0
        ipz = _ip_anzahl(t, ip)
        gesamt = _anzahl(db, t, "gesamt", "-")
        return {"heute": konto, "frei": limit_konto,
                "verbraucht": konto >= limit_konto or ipz >= limit_ip,
                "ausgelastet": gesamt >= limit_gesamt or pausiert(tagesschwelle_eur, t, db)}
    finally:
        db.close()


def buchen(uid, ip, limit_konto, limit_ip, limit_gesamt, tagesschwelle_eur, t=None):
    """Bucht eine freie Frage, wenn alle Grenzen es erlauben. Rueckgabe: None (gebucht) oder Grund
    'konto' | 'ip' | 'gesamt' | 'pause'. Alles in einer Transaktion (parallele Anfragen)."""
    t = t or tag()
    db = verbinden()
    _IP_SPERRE.acquire()
    try:
        db.execute("BEGIN IMMEDIATE")
        if pausiert(tagesschwelle_eur, t, db):
            grund = "pause"
        elif uid and _anzahl(db, t, "konto", uid) >= limit_konto:
            grund = "konto"
        elif ip and _IP.get((t, str(ip)), 0) >= limit_ip:
            grund = "ip"
        elif _anzahl(db, t, "gesamt", "-") >= limit_gesamt:
            grund = "gesamt"
        else:
            grund = None
            if ip:
                _IP[(t, str(ip))] = _IP.get((t, str(ip)), 0) + 1
            for art, schluessel in (("konto", uid), ("gesamt", "-")):
                if schluessel:
                    db.execute("INSERT INTO frei VALUES (?,?,?,1) ON CONFLICT(tag, art, schluessel) DO UPDATE SET anzahl=anzahl+1",
                               (t, art, schluessel))
            alt = (datetime.date.fromisoformat(t) - datetime.timedelta(days=3)).isoformat()
            db.execute("DELETE FROM frei WHERE tag < ?", (alt,))
            db.execute("DELETE FROM antwort_cache WHERE tag < ?", (alt,))
        db.execute("COMMIT")
        return grund
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        _IP_SPERRE.release()
        db.close()


def konto_loeschen(uid):
    """Kontoloeschung: Zaehler der KI-Fragen des Kontos entfernen (Kosten und Antwort-Cache enthalten keine Kontodaten)."""
    if not uid:
        return
    db = verbinden()
    try:
        db.execute("DELETE FROM frei WHERE art='konto' AND schluessel=?", (uid,))
    finally:
        db.close()


def zurueckbuchen(uid, ip, t):
    """Frage ohne Antwort (Fehler beim Modell): Buchung zuruecknehmen."""
    _ip_plus(t, ip, -1)
    db = verbinden()
    try:
        for art, schluessel in (("konto", uid), ("gesamt", "-")):
            if schluessel:
                db.execute("UPDATE frei SET anzahl=MAX(0, anzahl-1) WHERE tag=? AND art=? AND schluessel=?", (t, art, schluessel))
    finally:
        db.close()


# ── Antwort-Cache fuer Katalog-/Folge-/Ereignisfragen ─────────────────────────
def cache_lesen(schluessel, t=None):
    db = verbinden()
    try:
        z = db.execute("SELECT antwort FROM antwort_cache WHERE tag=? AND schluessel=?", (t or tag(), schluessel)).fetchone()
        return z[0] if z else None
    finally:
        db.close()


def cache_schreiben(schluessel, antwort, t=None):
    db = verbinden()
    try:
        db.execute("INSERT OR REPLACE INTO antwort_cache VALUES (?,?,?)", (t or tag(), schluessel, antwort))
    finally:
        db.close()


# ── Kosten ───────────────────────────────────────────────────────────────────
def preise():
    try:
        return json.load(open(PREISE_DATEI, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def preis_eur(modell, eingabe=0, ausgabe=0, cache_lesen=0, cache_schreiben=0, p=None):
    p = p or preise()
    m = (p.get("modelle") or {}).get(modell) or (p.get("modelle") or {}).get("standard") or {}
    usd = (eingabe * m.get("in", 0) + ausgabe * m.get("out", 0) + cache_lesen * m.get("cache_read", 0)
           + cache_schreiben * m.get("cache_write", 0)) / 1e6
    return usd * float(p.get("usd_eur", 1.0))


def kosten_buchen(art, modell, eingabe=0, ausgabe=0, cache_lesen=0, cache_schreiben=0, t=None):
    """Bucht einen Modellaufruf. Rueckgabe: (Kosten dieses Aufrufs, Tag gesamt, Monat gesamt) in Euro."""
    t = t or tag()
    eur = preis_eur(modell, eingabe, ausgabe, cache_lesen, cache_schreiben)
    db = verbinden()
    try:
        db.execute("INSERT INTO kosten VALUES (?,?,?,?,?,?,?,1,?) ON CONFLICT(tag, art, modell) DO UPDATE SET "
                   "eingabe=eingabe+excluded.eingabe, ausgabe=ausgabe+excluded.ausgabe, cache_lesen=cache_lesen+excluded.cache_lesen, "
                   "cache_schreiben=cache_schreiben+excluded.cache_schreiben, aufrufe=aufrufe+1, eur=eur+excluded.eur",
                   (t, art, modell, int(eingabe), int(ausgabe), int(cache_lesen), int(cache_schreiben), eur))
        return eur, kosten_eur(db, t), kosten_eur(db, monat=t[:7])
    finally:
        db.close()


def faellige_warnungen(tagesschwelle_eur, monatsschwelle_eur, t=None):
    """Welche Kostenmails jetzt faellig sind (je Tag bzw. Monat nur einmal). Markiert sie als gesendet.
    Rueckgabe: Liste von (art, periode, betrag, schwelle)."""
    t = t or tag()
    db = verbinden()
    aus = []
    try:
        db.execute("BEGIN IMMEDIATE")
        pruefen = [("tag", t, kosten_eur(db, t), tagesschwelle_eur),
                   ("pause", t, kosten_eur(db, t), 2 * tagesschwelle_eur if tagesschwelle_eur else 0),
                   ("monat", t[:7], kosten_eur(db, monat=t[:7]), monatsschwelle_eur)]
        for art, periode, betrag, schwelle in pruefen:
            if schwelle and schwelle > 0 and betrag > schwelle and not db.execute(
                    "SELECT 1 FROM warnung WHERE art=? AND periode=?", (art, periode)).fetchone():
                db.execute("INSERT INTO warnung VALUES (?,?,?)", (art, periode, jetzt().isoformat(timespec="seconds")))
                aus.append((art, periode, betrag, schwelle))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return aus


def warnung_zuruecknehmen(art, periode):
    """Versand fehlgeschlagen: beim naechsten Aufruf erneut versuchen."""
    db = verbinden()
    try:
        db.execute("DELETE FROM warnung WHERE art=? AND periode=?", (art, periode))
    finally:
        db.close()


def uebersicht(t=None):
    t = t or tag()
    db = verbinden()
    try:
        return {"tag": t, "tagEur": round(kosten_eur(db, t), 4), "monatEur": round(kosten_eur(db, monat=t[:7]), 4),
                "freiGesamt": _anzahl(db, t, "gesamt", "-"),
                "arten": [dict(zip(("art", "modell", "aufrufe", "eur"), r)) for r in
                          db.execute("SELECT art, modell, aufrufe, round(eur,4) FROM kosten WHERE tag=? ORDER BY art", (t,))]}
    finally:
        db.close()
