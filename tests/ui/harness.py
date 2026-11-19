"""Testumgebung fuer die ausgelieferte Seite: liefert public/ aus und spielt die API nach.

- /data/stress.json: oeffentlicher (zeitversetzter) Stand wie live
- /api/aktuell: aktueller Stand (letzter Tag aus /var/lib/investtimer/data/history.json), Wert per WERT ueberschreibbar
- /api/historie: echte Verlaufsdaten (gleiche Verdichtung wie die API), ausgeloggt bis zum oeffentlichen Datum
- /api/konto, /api/alarme, /api/chat: nachgespielt
Anmeldung: Rueckkehr aus dem E-Mail-Link mit Test-Token (JWT-Form mit E-Mail), Supabase-Aufrufe per Route abgefangen.
Nur fuer Tests auf diesem Server (liest Daten aus /var/lib/investtimer, nichts davon gelangt ins Repo).
"""
import base64, functools, http.server, json, os, re, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'public'
EMAIL = 'test@investtimer.net'
_p = base64.urlsafe_b64encode(json.dumps({'email': EMAIL, 'exp': int(time.time()) + 86400}).encode()).decode().rstrip('=')
TOKEN = 'eyJhbGciOiJIUzI1NiJ9.' + _p + '.sig'
LOGIN_HASH = '#access_token=%s&refresh_token=r1&expires_in=3600&type=magiclink' % TOKEN
ZUSTAND = {'wert': None, 'chat_status': 200, 'chat_ok': True, 'rest': 2, 'chat_verzoegerung': 0.4, 'alarme': None,
           'antwort': None, 'aufrufe': []}


def _historie_funktion():
    """_it_historie_daten aus dem API-Modul (gleicher Code wie live)."""
    src = (ROOT / 'volafly-api' / 'investtimer_api_konto.py').read_text(encoding='utf-8')
    m = re.search(r'\n_it_hist_cache = .*?\n(?=\n\n@app\.get\("/v1/investtimer/historie"\))', src, re.S)
    ns = {'os': os, 'json': json}
    exec(m.group(0), ns)
    ns['IT_HIST_PFADE'] = ("/var/lib/investtimer/data/history.json", "/var/lib/investtimer/historie/rueckrechnung.json",
                           str(ROOT / 'historie' / 'ereignisse.json'))
    return ns['_it_historie_daten'], ns['_it_historie_bis']


HIST, HIST_BIS = _historie_funktion()


def stress_json():
    return json.load(open('/var/lib/investtimer/data/stress.json'))


def aktuell():
    h = json.load(open('/var/lib/investtimer/data/history.json'))
    d = dict(h[sorted(h)[-1]])
    if ZUSTAND['wert'] is not None:
        d['rounded'] = ZUSTAND['wert']
    return d


def antwort_standard(frage):
    return {'antwort': '51 heißt: angespannt, aber weit weg von Panik. Am stärksten ziehen gerade die Kursschwankungen, ihr Teilwert liegt bei 68 und damit so hoch wie zuletzt im Sommer. Die Breite des Marktes hält dagegen noch ganz gut.\n\nMan kann es sich wie Wellengang vorstellen, nicht wie Sturm. Im April 2025 stand derselbe Wert bei 95, da kam alles zusammen. Davon ist der Markt heute ein gutes Stück entfernt.',
            'rest': ZUSTAND['rest'],
            'belege': {'reihe': [[p[0], p[1]] for p in HIST()['taeglich'][-30:]], 'markiert': HIST()['taeglich'][-1][0],
                       'bis': HIST()['taeglich'][-1][0], 'teilwerte': {'volatility': 52, 'price': 38, 'positioning': 44}}}


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        return self.headers.get('Authorization') == 'Bearer ' + TOKEN

    def do_GET(self):
        pfad = self.path.split('?')[0]
        ZUSTAND['aufrufe'].append(('GET', pfad))
        if pfad == '/data/stress.json':
            return self._json(stress_json())
        if pfad == '/api/chat':
            return self._json({'ok': ZUSTAND['chat_ok']})
        if pfad == '/api/aktuell':
            return self._json(aktuell()) if self._auth() else self._json({'error': 'login'}, 401)
        if pfad == '/api/historie':
            d = HIST()
            aus = {k: d[k] for k in ('taeglich', 'woechentlich', 'monatlich', 'ersterAufgezeichnet', 'ereignisse')}
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            return self._json(aus)
        if pfad == '/api/historie-oeffentlich':
            return self._json(HIST_BIS(HIST(), stress_json()['publicSnapshot']['asOf']))
        if pfad == '/api/konto':
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            return self._json({'premium': False, 'pflicht': False, 'paywall': False, 'status': 'frei',
                               'ki': {'tag': 2, 'heute': 2 - ZUSTAND['rest'], 'monat': 200}, 'tarife': {}})
        if pfad == '/api/konto/export':
            return self._json({'email': EMAIL, 'alarme': []}) if self._auth() else self._json({'error': 'login'}, 401)
        if pfad == '/api/alarme':
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            return self._json(ZUSTAND['alarme'] or {'alarme': [
                {'id': 1, 'richtung': 'ueber', 'schwelle': 60, 'aktiv': True, 'scharf': True, 'kanal': 'push'},
                {'id': 2, 'richtung': 'unter', 'schwelle': 50, 'aktiv': True, 'scharf': False, 'kanal': 'email'},
                {'id': 3, 'richtung': 'unter', 'schwelle': 30, 'aktiv': False, 'scharf': True, 'kanal': 'beide'}],
                'geraete': 0, 'max': 5, 'vapid': 'BNrcZE0FOPtHxiqv0ALj', 'email': EMAIL})
        return super().do_GET()

    def do_POST(self):
        pfad = self.path.split('?')[0]
        roh = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        ZUSTAND['aufrufe'].append(('POST', pfad, roh[:300]))
        if pfad == '/api/chat':
            time.sleep(ZUSTAND['chat_verzoegerung'])
            if ZUSTAND['chat_status'] != 200:
                return self._json({'error': 'x'}, ZUSTAND['chat_status'])
            frage = json.loads(roh or b'{}').get('frage', '')
            return self._json(ZUSTAND['antwort'] or antwort_standard(frage))
        return self._json({'ok': True})

    do_PATCH = do_POST
    do_DELETE = do_POST


def starten(verzeichnis=PUBLIC, port=0):
    h = functools.partial(Handler, directory=str(verzeichnis))
    s = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, 'http://127.0.0.1:%d/' % s.server_address[1]


async def supabase_route(ctx):
    """Supabase-Aufrufe (Konto-Daten, Abmelden) abfangen."""
    async def antwort(route):
        u = route.request.url
        if '/auth/v1/user' in u:
            return await route.fulfill(json={'id': 'u1', 'email': EMAIL, 'created_at': '2026-11-16T09:12:00Z'})
        return await route.fulfill(json={})
    await ctx.route(re.compile(r'https://[a-z0-9]+\.supabase\.co/.*'), antwort)
