#!/usr/bin/env python3
"""Erzeugt /etc/nginx/sites-available/investtimer-test aus der Live-Konfiguration (DEC-020, 26.11.2026):
gleiche Header und Limits, eigene Wurzel /var/www/investtimer-test/public, API auf 127.0.0.1:8101, Zertifikat test.investtimer.net,
Basic-Auth (/etc/nginx/investtimer-test.htpasswd, legt Michel an), X-Robots-Tag noindex, robots.txt Disallow.
Ohne Basic-Auth (Stand Zweitsitzung 27.11.2026, "auth_basic off; allow all;", weil "satisfy any" + "deny all" sonst 403 liefert):
- alle /api/-Locations: der Bearer-Token des Frontends ersetzt den Basic-Header (Bearer gegen Basic -> 401); Schutz per Supabase-Token in der API
- Stripe-Webhook, ACME-Challenge, manifest.json, App-Icons, favicon.ico, sw.js (Browser holen sie ohne Zugangsdaten)
- robots.txt nur "auth_basic off" (wie auf dem Server)
limit_req_status 429 als Sicherheitsnetz. Eigene Logs, keine Statistik.
Pruefung: python3 nginx_test.py /tmp/x.conf && diff /tmp/x.conf /etc/nginx/sites-available/investtimer-test (muss leer sein)."""
import re, sys
from pathlib import Path

LIVE = Path("/etc/nginx/sites-available/investtimer").read_text()
start = LIVE.index("server {")
s = LIVE[start:]
s = s.replace("server_name investtimer.net www.investtimer.net;", "server_name test.investtimer.net;")
s = s.replace("/var/www/investtimer/public", "/var/www/investtimer-test/public")
s = s.replace("127.0.0.1:8100", "127.0.0.1:8101")
s = s.replace("/etc/letsencrypt/live/investtimer.net/", "/etc/letsencrypt/live/test.investtimer.net/")
s = s.replace("include snippets/investtimer-sicherheit.conf;", "include snippets/investtimer-test-sicherheit.conf;")
s = s.replace("listen [::]:443 ssl ipv6only=on;", "listen [::]:443 ssl;")
s = re.sub(r"\n\s*access_log [^\n]*;", "", s)
s = re.sub(r"\n\s*include /etc/nginx/investtimer-statistik.conf;", "", s)
s = s.replace("# managed by Certbot", "")
# Vorschau- und Teilen-Bilder des zeitversetzten Stands: nur lesend wie live (gleiche oeffentliche Daten); Bilder der Testinstanz
# mit Login rendert die Test-API bei Bedarf selbst (IT_TEILEN_DIR=/var/lib/investtimer-test/teilen)
# Basic-Auth fuer den ganzen HTTPS-Block, Ausnahmen: Stripe-Webhook und ACME
erster = s.index("server {") + len("server {")
s = s[:erster] + """
    access_log /var/log/nginx/investtimer-test.log;
    auth_basic "InvestTimer Testumgebung";
    auth_basic_user_file /etc/nginx/investtimer-test.htpasswd;
    # Tests vom Server selbst (Playwright, curl) ohne Passwort; von aussen immer Basic-Auth
    satisfy any;
    allow 127.0.0.1;
    allow ::1;
    allow 187.124.169.24;
    allow 2a02:4780:79:9191::1;
    deny all;
    location = /robots.txt { auth_basic off; include snippets/investtimer-test-sicherheit.conf; default_type text/plain; return 200 "User-agent: *\\nDisallow: /\\n"; }
    # 27.11.2026 (Zweitsitzung Testumgebung): bei "satisfy any" + "deny all" reicht "auth_basic off" nicht (sonst 403 von aussen),
    # daher zusaetzlich "allow all" in jeder Ausnahme
    location ^~ /.well-known/acme-challenge/ { auth_basic off; allow all; root /var/www/html; }
    # Ohne Basic-Auth: Manifest, App-Icons, Favicon (Browser holen sie ohne Zugangsdaten -> sonst Extra-Passwortfenster)
    location = /manifest.json { auth_basic off; allow all; include snippets/investtimer-test-sicherheit.conf; add_header Cache-Control "no-cache" always; }
    location ~ ^/(icon-192|icon-512|icon-maskable-512|apple-touch-icon)\\.png$ { auth_basic off; allow all; include snippets/investtimer-test-sicherheit.conf; add_header Cache-Control "no-cache" always; }
    location = /favicon.ico { auth_basic off; allow all; include snippets/investtimer-test-sicherheit.conf; return 204; }
    location = /api/abo/stripe-webhook {
        auth_basic off;
        allow all;
        include snippets/investtimer-test-sicherheit.conf;
        client_max_body_size 256k;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_pass http://127.0.0.1:8101/v1/investtimer/abo/stripe-webhook;
    }
""" + s[erster:]
# Ratenlimit nie als 503
s = s.replace("    limit_conn_status 429;\n", "    limit_conn_status 429;\n    # Sicherheitsnetz: Ratenlimit nie als 503 (gilt fuer locations ohne eigenes limit_req_status)\n    limit_req_status 429;\n", 1)
# Bearer gegen Basic: jede /api/-Location (ausser dem Webhook oben, der es schon hat) ohne Basic-Auth
API = ("        # API: ohne Basic-Auth (Bearer-Token des Frontends ersetzt sonst den Basic-Header -> 401); Schutz per Supabase-Token in der API\n"
       "        auth_basic off;\n        allow all;\n")
s = re.sub(r"(\n    location (?:= |~ \^)/api/(?!abo/stripe-webhook \{)[^\n]*\{\n)", lambda m: m.group(1) + API, s)
# Service Worker: Browser prueft Updates ohne Zugangsdaten
s = s.replace("    location = /sw.js {\n", "    location = /sw.js {\n        # ohne Basic-Auth (statisch, Browser prueft Updates ohne Zugangsdaten)\n        auth_basic off;\n        allow all;\n", 1)
Path(sys.argv[1] if len(sys.argv) > 1 else "/etc/nginx/sites-available/investtimer-test").write_text(
    "# Erzeugt von deploy/testumgebung/nginx_test.py aus der Live-Konfiguration – nicht von Hand aendern\n" + s)
snip = Path("/etc/nginx/snippets/investtimer-sicherheit.conf").read_text()
Path("/etc/nginx/snippets/investtimer-test-sicherheit.conf").write_text(snip.rstrip() + '\nadd_header X-Robots-Tag "noindex, nofollow" always;\n')
print("ok")
