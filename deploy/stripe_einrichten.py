#!/usr/bin/env python3
"""Richtet Stripe fuer InvestTimer ein (idempotent) und schreibt /root/.investtimer/stripe.json.

Voraussetzung: geheimer Schluessel in /root/.investtimer/stripe-key (0600), zuerst sk_test_/rk_test_.
Live-Schluessel nur mit --live (und erst nach Michels Freigabe, siehe CLAUDE.md).

Legt an bzw. prueft:
  - Produkte investtimer_premium_monthly / _yearly (IDs = Produkt-IDs bei RevenueCat)
  - Preise 4,99 EUR/Monat und 39,99 EUR/Jahr inkl. USt (tax_behavior=inclusive), Lookup-Keys gleich
  - Kundenportal: kuendigen zum Periodenende, Zahlungsmethode, Rechnungen, Tarifwechsel
  - Webhook https://investtimer.net/api/abo/stripe-webhook fuer checkout.session.completed
Preise werden nie geaendert: neuer Preis = neuer Price, bestehende Abos behalten ihren Preis.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GEHEIM = "/root/.investtimer"
BASIS = os.environ.get("STRIPE_API", "https://api.stripe.com")
SEITE = "https://investtimer.net"
TARIFE = [("investtimer_premium_monthly", "monatlich", "InvestTimer Premium Monatlich", 499, "month"),
          ("investtimer_premium_yearly", "jaehrlich", "InvestTimer Premium Jährlich", 3999, "year")]


def key():
    k = open(os.path.join(GEHEIM, "stripe-key")).read().strip()
    if not (k.startswith(("sk_test_", "rk_test_")) or "--live" in sys.argv):
        raise SystemExit("Live-Schluessel ohne --live abgelehnt")
    return k


def stripe(methode, pfad, felder=None):
    daten = urllib.parse.urlencode(felder or {}, doseq=True).encode() if methode == "POST" else None
    url = BASIS + "/v1/" + pfad + ("?" + urllib.parse.urlencode(felder, doseq=True) if methode == "GET" and felder else "")
    req = urllib.request.Request(url, data=daten, method=methode, headers={"Authorization": "Bearer " + KEY, "Stripe-Version": "2024-06-20"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        fehler = json.load(e).get("error", {})
        if e.code == 404:
            return None
        raise SystemExit("Stripe %s %s: %s %s" % (methode, pfad, e.code, fehler.get("message")))


def main():
    preise = {}
    for pid, tarif, name, cent, intervall in TARIFE:
        if not stripe("GET", "products/" + pid):
            stripe("POST", "products", {"id": pid, "name": name, "tax_code": "txcd_10103001",
                                        "description": "Aktueller Marktstress, Verlauf, Einzelindikatoren, KI-Analysen und Alarme"})
            print("Produkt angelegt:", pid)
        vorhanden = stripe("GET", "prices", {"lookup_keys[]": pid, "active": "true"})["data"]
        passend = [p for p in vorhanden if p["unit_amount"] == cent and p["currency"] == "eur" and p["recurring"]["interval"] == intervall]
        if passend:
            preis = passend[0]
        else:
            preis = stripe("POST", "prices", {"product": pid, "currency": "eur", "unit_amount": cent, "recurring[interval]": intervall,
                                             "tax_behavior": "inclusive", "lookup_key": pid, "transfer_lookup_key": "true"})
            print("Preis angelegt:", pid, cent / 100, "EUR /", intervall)
        preise[tarif] = preis["id"]

    portale = stripe("GET", "billing_portal/configurations", {"is_default": "true", "limit": 1})["data"]
    felder = {
        "business_profile[headline]": "InvestTimer Premium verwalten",
        "business_profile[privacy_policy_url]": SEITE + "/datenschutz.html",
        "business_profile[terms_of_service_url]": SEITE + "/agb.html",
        "default_return_url": SEITE + "/?konto=1",
        "features[customer_update][enabled]": "true", "features[customer_update][allowed_updates][]": ["email", "address"],
        "features[invoice_history][enabled]": "true",
        "features[payment_method_update][enabled]": "true",
        "features[subscription_cancel][enabled]": "true", "features[subscription_cancel][mode]": "at_period_end",
        "features[subscription_cancel][cancellation_reason][enabled]": "false",
        "features[subscription_update][enabled]": "true",
        "features[subscription_update][default_allowed_updates][]": ["price"],
        "features[subscription_update][proration_behavior]": "create_prorations",
    }
    for i, (pid, tarif, *_r) in enumerate(TARIFE):
        felder["features[subscription_update][products][%d][product]" % i] = pid
        felder["features[subscription_update][products][%d][prices][]" % i] = [preise[tarif]]
    if portale:
        stripe("POST", "billing_portal/configurations/" + portale[0]["id"], felder)
    else:
        stripe("POST", "billing_portal/configurations", felder)
    print("Kundenportal eingerichtet")

    ziel = SEITE + "/api/abo/stripe-webhook"
    alt = json.load(open(os.path.join(GEHEIM, "stripe.json"))) if os.path.exists(os.path.join(GEHEIM, "stripe.json")) else {}
    hooks = [h for h in stripe("GET", "webhook_endpoints", {"limit": 100})["data"] if h["url"] == ziel]
    geheim = alt.get("webhook") if hooks and alt.get("webhook") else None
    if not geheim:
        for h in hooks:
            stripe("DELETE", "webhook_endpoints/" + h["id"])
        h = stripe("POST", "webhook_endpoints", {"url": ziel, "enabled_events[]": ["checkout.session.completed"],
                                                 "description": "InvestTimer: Kauf an RevenueCat melden"})
        geheim = h["secret"]
        print("Webhook angelegt")
    neu = dict(alt, secret=KEY, webhook=geheim, preise=preise, basis=SEITE)
    pfad = os.path.join(GEHEIM, "stripe.json")
    with open(os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(neu, f)
    print("geschrieben:", pfad, "(Preise:", ", ".join("%s=%s" % kv for kv in preise.items()) + ")")


if __name__ == "__main__":
    KEY = key()
    main()
