"""Erklaerungen der 14 Bestandteile in Alltagssprache (Auftrag 19.11.2026, Block 9): ohne Kuerzel und Indexnamen
(VIX, S&P 500, Put/Call, CNN Fear & Greed). Was gemessen wird, bleibt gleich. Laeuft im Build nach englisch.py."""
import json
import re

NEU = {
 "VIX": {"de": {"what": "Der Volatilitätsindex beschreibt, wie stark der US-Aktienmarkt in den kommenden 30 Tagen schwanken könnte. Er wird aus den Preisen von Optionen auf die großen US-Aktien abgeleitet."},
         "en": {"what": "The volatility index measures how much the US stock market is expected to move over the next 30 days. It is derived from option prices on large US stocks."}},
 "VIX_VX1": {"de": {"title": "Schwankungserwartung · heute und nächster Termin", "what": "Wir vergleichen die heutige Schwankungserwartung mit der Erwartung für den nächsten Termin am Terminmarkt. Ein Terminkontrakt bezieht sich auf einen späteren Zeitpunkt."},
             "en": {"title": "Expected volatility · now vs. next month", "kicker": "Today vs. the next contract", "what": "We compare today’s expected volatility with the next futures contract, which prices volatility at a later date.",
                    "stress": "When today’s expected volatility is high relative to the next contract, stress rises: concern is focused on the here and now."}},
 "VX1_VX2": {"de": {"title": "Schwankungserwartung · die nächsten Termine", "what": "Wir betrachten die Schwankungserwartung für die beiden nächsten Termine am Terminmarkt. Ihre Preise zeigen, wie der Markt Unsicherheit über diese Zeitpunkte verteilt."},
             "en": {"title": "Expected volatility · next two months", "what": "We compare the next two futures contracts on expected volatility to see how the market spreads uncertainty across them."}},
 "VVIX": {"en": {"what": "This tracks how much expected volatility itself is expected to move, based on option prices."}},
 "SPX_200D": {"de": {"what": "Wir ordnen den Gesamtmarkt der großen US-Aktien im Verhältnis zu seinem durchschnittlichen Stand der vergangenen 200 Handelstage ein. Diese Linie glättet kurzfristige Ausschläge."},
              "en": {"what": "We compare the broad US stock market with its 200-day average, which smooths out short-term swings."}},
 "EPC": {"de": {"what": "Wir vergleichen, wie oft auf einzelne Aktien Optionen gehandelt werden, die gegen fallende Kurse absichern, und wie oft solche, die auf steigende Kurse setzen.",
                "stress": "Mehr Absicherung gegen fallende Kurse erhöht den Stressbeitrag. Das deutet auf mehr Vorsicht hin."},
         "en": {"what": "We compare how often single-stock options that hedge against falling prices are traded versus those that bet on rising prices."}},
 "TPC": {"de": {"what": "Dieser Vergleich umfasst Optionen auf einzelne Aktien und auf ganze Aktienindizes. Indexoptionen werden häufig zur Absicherung ganzer Depots eingesetzt.",
                "stress": "Mehr Absicherung gegen fallende Kurse erhöht den Stressbeitrag. Damit fließt ein breiteres Bild der Absicherung ein."}},
 "FG": {"de": {"what": "Ein bekanntes Stimmungsbarometer zwischen Angst und Gier. Es bündelt sieben Marktbeobachtungen, darunter Kursentwicklung, Marktbreite, Optionshandel und die Nachfrage nach sicheren Anlagen."},
        "en": {"what": "A well-known sentiment gauge between fear and greed. It combines seven indicators, including momentum, breadth, options activity and demand for safe-haven assets."}},
}


def anwenden(html):
    m = re.search(r"const explanations = (\[.*?\n\]);", html, re.S)
    if not m:
        raise SystemExit("erklaerungen: Liste nicht gefunden")
    liste = json.loads(m.group(1))
    for e in liste:
        for sprache, felder in NEU.get(e["id"], {}).items():
            e[sprache].update(felder)
        for sprache, alt, neu in (("de", "Aktien des S&P 500", "der 500 großen US-Aktien"), ("en", "S&P 500 stocks", "the 500 largest US stocks")):
            e[sprache] = {k: v.replace(alt, neu) for k, v in e[sprache].items()}
    text = json.dumps(liste, ensure_ascii=False, indent=2)
    sichtbar = json.dumps([[e["de"], e["en"]] for e in liste], ensure_ascii=False)
    for rest in ("VIX", "S&P", "CNN", "Put-", "Put/", "Fear & Greed"):
        if rest in sichtbar:
            i = sichtbar.index(rest)
            raise SystemExit("erklaerungen: Rest '%s': %r" % (rest, sichtbar[max(0, i - 80):i + 40]))
    return html[:m.start(1)] + text + html[m.end(1):]
