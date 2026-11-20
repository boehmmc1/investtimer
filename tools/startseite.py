"""Startseite reduzieren (Auftrag 19.11.2026, Block 2). Laeuft im Build nach der englischen Ueberarbeitung.

- keine Gewichtungen mehr: Prozentzahlen der Blickwinkel, "Anteil an der Berechnung", Einzelgewichte, Erklaerdialog
- kein "x von 14 Bestandteilen" (Ausnahme bleibt "Eingeschraenkte Datenbasis" unter der Zahl)
- kein Abschnitt zum Datenstand, keine Alarm-Sektion und keine Sprachwahl im Detailbereich
- eingebettetes Rueckfall-Ergebnis ohne Gewichte
Die Ausblendung von Ueberschrift, Alarm-Einstieg und Anmeldehinweisen auf der Startseite steht in tools/ansichten.css.
"""
import json
import re


def _once(html, alt, neu, name):
    n = html.count(alt)
    if n != 1:
        raise SystemExit("startseite: %s erwartet 1, gefunden %d" % (name, n))
    return html.replace(alt, neu)


def _schluessel(html, key, de, en):
    """Ersetzt key:'...' im deutschen (erster Treffer) und englischen Textblock (zweiter Treffer)."""
    treffer = list(re.finditer(r"(?<=[,{])%s:'(?:[^'\\]|\\.)*'" % re.escape(key), html))
    if len(treffer) != 2:
        raise SystemExit("startseite: Schluessel %s erwartet 2, gefunden %d" % (key, len(treffer)))
    for m, wert in reversed(list(zip(treffer, (de, en)))):
        html = html[:m.start()] + ("%s:'%s'" % (key, wert) if wert is not None else "") + html[m.end():]
    return html


def _loeschen(html, key):
    """Entfernt key:'...', bzw. key:n=>`...`, in beiden Sprachen (unbenutzte Texte)."""
    vorher = html
    html = re.sub(r"(?<=[,{])%s:'(?:[^'\\]|\\.)*'," % re.escape(key), "", html)
    html = re.sub(r"(?<=[,{])%s:n=>`[^`]*`," % re.escape(key), "", html)
    if html == vorher:
        raise SystemExit("startseite: Schluessel %s nicht gefunden" % key)
    return html


NARRATIV = (
    "Die 14 Bestandteile erfassen Anspannung aus drei Blickwinkeln. Zurückgerechnet seit 2006 verlief der Wert deutlich gegenläufig "
    "zum US-Aktienmarkt: In gut 9 von 10 Wochen, in denen die Kurse um mehr als zwei Prozent fielen, stieg der Marktstress, und je weiter "
    "der Markt unter seinem Jahreshoch lag, desto höher stand er meist. Zusammen zeigen die drei Blickwinkel das deutlicher als die "
    "Kursschwankungen allein. Das beschreibt die Vergangenheit und sagt nichts über künftige Kurse.",
    "The 14 components capture market tension from three perspectives. Back-calculated since 2006, the score moved clearly against "
    "the US stock market: in more than 9 out of 10 weeks in which stocks fell by more than two percent, market stress rose, and the "
    "further the market was below its one-year high, the higher the score usually stood. Together, the three perspectives show this more "
    "clearly than price swings alone. This describes the past and says nothing about future prices.")


def anwenden(html, narrativ=False):
    # Gewichte in den Blickwinkel-Karten, Indikatorzeilen und im Erklaerdialog
    html = _once(html, '<span class="share-number">${percent(block?.effectiveWeight??0)}</span>', "", "Blickwinkel-Prozent")
    html = _once(html, "<span>${percent(row?.effectiveWeight??0)}</span>${info}", "${info}", "Indikator-Prozent")
    html = _once(html, "<div class=\"explanation-share\"><span>${t('share')}</span><strong>${percent(row?.effectiveWeight??0)}</strong></div>", "", "Erklaerdialog-Anteil")
    html = _schluessel(html, "share", "Bestandteile ansehen", "See components")
    html = _schluessel(html, "howbody",
                       "Alle Bestandteile werden auf einer gemeinsamen Skala eingeordnet und zu einem Wert zusammengeführt. 0 steht für extreme Ruhe oder Sorglosigkeit, 100 für extremen Stress. Ein einzelnes Signal entscheidet nicht allein.",
                       "Each component is placed on a common scale and combined into one score. 0 means extreme calm or complacency, 100 means extreme stress. No single signal drives the score on its own.")
    html = _schluessel(html, "missingbody",
                       "Fehlt an einem Tag ein Bestandteil, rechnet der Wert mit den übrigen weiter. Fehlen mehr als zwei, steht unter der Zahl „Eingeschränkte Datenbasis“.",
                       "If a component is missing on a given day, the score is calculated from the others. If more than two are missing, the score is marked “Limited data today”.")
    # Detailbereich: ohne Alarm-Sektion und ohne Sprachwahl (Alarme: Konto-Ansicht/Kontomenue, Sprache: Kopf bzw. Konto)
    html = re.sub(r'<section class="notifications" aria-labelledby="notifications-title">.*?</section>', "", html, count=1, flags=re.S)
    html = _once(html, "<label class=\"language-label\"><span>${t('language')}</span><select id=\"language\" aria-label=\"${t('language')}\"><option value=\"de\" ${state.lang==='de'?'selected':''}>Deutsch</option><option value=\"en\" ${state.lang==='en'?'selected':''}>English</option></select></label>",
                 "<select id=\"language\" hidden aria-hidden=\"true\" tabindex=\"-1\"><option value=\"de\" ${state.lang==='de'?'selected':''}>Deutsch</option><option value=\"en\" ${state.lang==='en'?'selected':''}>English</option></select>",
                 "Sprachwahl Details (nur noch intern, der Kopf schaltet darueber um)")
    # Unbenutzte Texte zum Datenstand und zur Vollstaendigkeit
    for k in ("complete", "incomplete", "data", "databody", "databodyPublic", "empty", "tipBestandteile", "componentCount"):
        if k == "componentCount":
            html = re.sub(r"componentCount:\(n,total\)=>`[^`]*`,", "", html)
            continue
        html = _loeschen(html, k)
    # Platz fuer den Teilen-Knopf fest im HTML (sonst Layoutsprung, wenn tools/teilen.js ihn nach dem ersten Zeichnen einfuegt)
    html = _once(html, '<p id="summary">Der Markt zeigt moderaten Stress.</p></div>',
                 '<p id="summary">Der Markt zeigt moderaten Stress.</p></div><div class="teilen-start"></div>', "Platz Teilen-Knopf")
    # Verlauf-Tooltip ohne Bestandteile (seit 20.11.2026 schon in tools/verlauf.js: nur Zeitpunkt und Wert)
    if "tipBestandteile')" in html:
        raise SystemExit("startseite: Tooltip zeigt noch Bestandteile")
    # Filmhinweis ohne Bestandteil-Zahlen
    html = html.replace("; bis Mitte 2020 standen 13 der 14 Bestandteile zur Verfügung.", ".")
    html = html.replace("; until mid-2020, 13 of the 14 components were available.", ".")
    # Eingebettetes Rueckfall-Ergebnis ohne Gewichte; die Seite braucht sie nicht mehr
    m = re.search(r'(<script type="application/json" id="investtimer-result">\n)(.*?)(\n</script>)', html, re.S)
    daten = json.loads(m.group(2))
    for k in ("rows", "blocks"):
        daten[k] = [{"name": p["name"]} for p in daten[k]]
    html = html[:m.start(2)] + json.dumps(daten, indent=1) + html[m.end(2):]
    html = _once(html, "const part=r=>r&&typeof r.name==='string'&&Number.isFinite(r.effectiveWeight);",
                 "const part=r=>r&&typeof r.name==='string';", "normaliseResult ohne Gewichte")
    # "Keine Anlageberatung" in der Fusszeile jeder Ansicht (Nachtrag 2)
    html = _schluessel(html, "tagline", "Marktstress verstehen · Keine Anlageberatung", "Understand market stress · Not investment advice")
    # Einheitlicher Begriff fuer den oeffentlichen Wert: "zeitversetzter Stand"
    html = _once(html, "source:'US-Aktienmarkt · gespeicherter Stand '", "source:'US-Aktienmarkt · zeitversetzter Stand '", "Fusszeile zeitversetzt")
    html = _once(html, "noCurrent:'Historischer Wert – nicht der aktuelle", "noCurrent:'Zeitversetzter Stand – nicht der aktuelle", "Hinweis zeitversetzt")
    # Narrativ "So entsteht der Wert" nur mit Schalter IT_NARRATIV=1 (Freigabe Michel), sonst steht nichts davon in der Seite
    if narrativ:
        html = _once(html, "<h3 class=\"composition-eyebrow\">${t('groups')}</h3>",
                     "<h3 class=\"composition-eyebrow\">${t('groups')}</h3><p class=\"narrativ\">${state.lang==='en'?" + repr(NARRATIV[1]) + ":" + repr(NARRATIV[0]) + "}</p>",
                     "Narrativ")
    for rest in ("effectiveWeight", "von 14", "of 14", "Anteil an der Berechnung", "Share of the calculation", "Datenstand:", "notifications-title"):
        if rest in html:
            i = html.index(rest)
            raise SystemExit("startseite: Rest '%s' gefunden: %r" % (rest, html[max(0, i - 80):i + 80]))
    return html
