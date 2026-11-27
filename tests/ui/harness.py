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
import tempfile, sys as _sys
# Alarme: echte Server-Logik (volafly-api/investtimer_alarme.py) mit Wegwerf-Datenbank je Testlauf
os.environ['INVESTTIMER_ALARME_DB'] = tempfile.mkdtemp(prefix='it-alarme-') + '/alarme.db'
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'volafly-api'))
import investtimer_alarme as ALARME

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'public'
EMAIL = 'test@investtimer.net'
_p = base64.urlsafe_b64encode(json.dumps({'sub': 'test-uid-1', 'email': EMAIL, 'exp': int(time.time()) + 86400}).encode()).decode().rstrip('=')
TOKEN = 'eyJhbGciOiJIUzI1NiJ9.' + _p + '.sig'
UID = 'test-uid-1'


def alarme_setzen(liste, wert=None):
    """Testkonto mit genau diesen Alarmen [(richtung, schwelle, scharf, ausgeloest_am)], direkt in die Datenbank (auch ueber der Grenze)."""
    with ALARME.verbinden() as db:
        db.execute('DELETE FROM alarme WHERE uid=?', (UID,))
        for e in liste:
            r, x, sch, am = e[:4]
            aktiv = e[4] if len(e) > 4 else 1
            db.execute('INSERT INTO alarme (uid, richtung, schwelle, erstellt, kanal, scharf, ausgeloest_am, aktiv) VALUES (?,?,?,?,?,?,?,?)', (UID, r, x, 0, 'push', 1 if sch else 0, am, aktiv))


# Startzustand wie der fruehere Nachbau: bereit, ausgeloest, pausiert
alarme_setzen([('ueber', 60, 1, None), ('unter', 50, 0, '2026-11-18'), ('unter', 30, 1, None, 0)])


LOGIN_HASH = '#access_token=%s&refresh_token=r1&expires_in=3600&type=magiclink' % TOKEN
ZUSTAND = {'wert': None, 'chat_status': 200, 'chat_ok': True, 'frei': {'verbraucht': False, 'ausgelastet': False}, 'chat_fehler': 'limit', 'chat_verzoegerung': 0.4, 'alarme': None,
           'antwort': None, 'aufrufe': [], 'aktuell_verzoegerung': 0, 'feedback_status': 200, 'feedback': [], 'alter_min': 3, 'fehler': [], 'ansichten': [], 'pflicht': False}


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
    # Teilwerte wie die Live-API (marktstress.calculate); aeltere aufgezeichnete Tage haben keine -> feste Testwerte, ueberschreibbar
    d.setdefault('bloecke', ZUSTAND.get('bloecke') or {'volatility': 52.4, 'price': 41.0, 'positioning': 47.6})
    return d


def antwort_standard(frage):
    return {'antwort': '51 heißt: angespannt, aber weit weg von Panik. Am stärksten ziehen gerade die Kursschwankungen, ihr Teilwert liegt bei 68 und damit so hoch wie zuletzt im Sommer. Die Breite des Marktes hält dagegen noch ganz gut.\n\nMan kann es sich wie Wellengang vorstellen, nicht wie Sturm. Im April 2025 stand derselbe Wert bei 95, da kam alles zusammen. Davon ist der Markt heute ein gutes Stück entfernt.',
            'katalog': False, 'frei': dict(ZUSTAND['frei']),
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

    def _premium_sperre(self, pfad):
        """Premium-Pflicht (IT_PREMIUM_PFLICHT=1, freies Konto): wie die API 403 {"error":"premium"} auf Premium-Pfaden"""
        if ZUSTAND['pflicht'] and self._auth() and (pfad in ('/api/aktuell', '/api/historie', '/api/chat', '/api/push/geraet') or pfad.startswith('/api/alarme')):
            if not (pfad == '/api/chat' and self.command == 'GET'):
                self._json({'error': 'premium'}, 403); return True
        return False

    def do_GET(self):
        pfad = self.path.split('?')[0]
        ZUSTAND['aufrufe'].append(('GET', pfad))
        if self._premium_sperre(pfad):
            return
        if pfad == '/api/teilen/stand':
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            if not ZUSTAND.get('teilen_aktuell'):
                return self._json({'aktuell': False})
            basis = Path(os.environ.get('IT_TEILEN_DIR', '/var/lib/investtimer/teilen'))
            m = json.loads((basis / 'aktuell' / 'manifest.json').read_text())
            d = aktuell()
            m.update(aktuell=True, stamp='2026-11-20T1534', wert=d['rounded'], zeit='2026-11-20T14:34:00Z', asOf=d['asOf'])
            return self._json(m)
        if pfad == '/api/teilen/bild':
            # Live-Bild: Weiterleitung auf eine vorhandene Datei (nachgespielt), Aufrufe werden fuer den Test gezaehlt
            ZUSTAND.setdefault('teilen_bild', []).append(self.path)
            q = dict(x.split('=', 1) for x in self.path.split('?', 1)[1].split('&') if '=' in x)
            name = {'wert': 'wert', 'verlauf': 'verlauf-' + q.get('zeitraum', '1J'), 'phase': 'phase-' + q.get('phase', '')}[q.get('art', 'wert')]
            self.send_response(302)
            self.send_header('Location', '/teilen/aktuell/%s-%s-%s.png' % (name, q.get('format', 'quer'), q.get('l', 'de')))
            self.end_headers(); return
        if pfad.startswith('/teilen/'):
            # Teilen-Bilder und Manifest aus dem gerenderten Stand (server/teilen_bilder.py)
            basis = Path(os.environ.get('IT_TEILEN_DIR', '/var/lib/investtimer/teilen')).resolve()
            datei = (basis / pfad[len('/teilen/'):]).resolve()
            if not str(datei).startswith(str(basis)) or not datei.is_file():
                self.send_response(404); self.end_headers(); return
            roh = datei.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json' if datei.suffix == '.json' else 'image/png')
            self.send_header('Content-Length', str(len(roh))); self.end_headers(); self.wfile.write(roh); return
        if pfad == '/data/stress.json':
            return self._json(stress_json())
        if pfad == '/api/chat':
            return self._json({'ok': ZUSTAND['chat_ok']})
        if pfad == '/api/aktuell':
            time.sleep(ZUSTAND['aktuell_verzoegerung'])
            d = aktuell()
            d['berechnetUm'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - ZUSTAND['alter_min'] * 60))
            return self._json(d) if self._auth() else self._json({'error': 'login'}, 401)
        if pfad == '/api/v':
            ZUSTAND['ansichten'].append(self.path)
            self.send_response(204); self.end_headers(); return
        if pfad == '/api/historie':
            d = HIST()
            aus = {k: d[k] for k in ('taeglich', 'woechentlich', 'monatlich', 'ersterAufgezeichnet', 'ereignisse')}
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            return self._json(aus)
        if pfad == '/api/historie-oeffentlich':
            bis = stress_json()['publicSnapshot']['asOf']
            from datetime import date as _d, timedelta as _t
            return self._json(HIST_BIS(HIST(), bis, (_d.fromisoformat(bis) - _t(days=365)).isoformat()))  # DEC-019
        if pfad == '/api/konto':
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            return self._json({'premium': False, 'pflicht': ZUSTAND['pflicht'], 'paywall': ZUSTAND['pflicht'], 'status': 'frei',
                               'ki': dict(ZUSTAND['frei'], heute=int(ZUSTAND['frei']['verbraucht']), frei=1), 'tarife': {}})
        if pfad == '/api/konto/export':
            return self._json({'email': EMAIL, 'alarme': []}) if self._auth() else self._json({'error': 'login'}, 401)
        if pfad == '/api/alarme':
            if not self._auth():
                return self._json({'error': 'login'}, 401)
            if ZUSTAND['alarme'] is None:
                return self._alarm(ALARME.liste, UID)
            return self._json(ZUSTAND['alarme'] or {'alarme': [
                {'id': 1, 'richtung': 'ueber', 'schwelle': 60, 'aktiv': True, 'scharf': True, 'kanal': 'push'},
                {'id': 2, 'richtung': 'unter', 'schwelle': 50, 'aktiv': True, 'scharf': False, 'kanal': 'email'},
                {'id': 3, 'richtung': 'unter', 'schwelle': 30, 'aktiv': False, 'scharf': True, 'kanal': 'beide'}],
                'geraete': 0, 'max': 5, 'vapid': 'BNrcZE0FOPtHxiqv0ALj', 'email': EMAIL})
        return super().do_GET()

    def _alarm(self, f, *a):
        ALARME.stand('letzter_wert', aktuell()['rounded'])
        try:
            return self._json(dict(f(*a), vapid='BNrcZE0FOPtHxiqv0ALj'))
        except ALARME.Fehler as e:
            return self._json({'error': e.code}, e.status)

    def _alarm_schreiben(self, methode):
        pfad = self.path.split('?')[0]
        roh = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        ZUSTAND['aufrufe'].append((methode, pfad, roh[:300]))
        if not self._auth():
            return self._json({'error': 'login'}, 401)
        d = json.loads(roh or b'{}')
        if methode == 'POST':
            return self._alarm(ALARME.neu, UID, d.get('richtung'), d.get('schwelle'), d.get('kanal', 'push'), EMAIL, d.get('sprache', 'de'))
        aid = int(pfad.rsplit('/', 1)[1])
        if methode == 'DELETE':
            return self._alarm(ALARME.loeschen, UID, aid)
        return self._alarm(ALARME.aendern, UID, aid, d['aktiv'] if 'aktiv' in d else None, d.get('kanal'), EMAIL if d.get('kanal') not in (None, 'push') else None,
                           d.get('sprache'), d.get('richtung'), d.get('schwelle'))

    def do_POST(self):
        pfad = self.path.split('?')[0]
        if self._premium_sperre(pfad):
            self.rfile.read(int(self.headers.get('Content-Length') or 0)); return
        if pfad == '/api/alarme' or pfad.startswith('/api/alarme/'):
            return self._alarm_schreiben(self.command)
        roh = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        ZUSTAND['aufrufe'].append(('POST', pfad, roh[:300]))
        if pfad == '/api/fehler':
            ZUSTAND['fehler'].append(json.loads(roh or b'{}'))
            return self._json({'ok': True})
        if pfad == '/api/feedback':
            ZUSTAND['feedback'].append(json.loads(roh or b'{}'))
            st = ZUSTAND['feedback_status']
            return self._json({'ok': True} if st == 200 else {'error': {429: 'limit', 400: 'leer'}.get(st, 'versand')}, st)
        if pfad == '/api/chat':
            time.sleep(ZUSTAND['chat_verzoegerung'])
            if ZUSTAND['chat_status'] != 200:
                return self._json({'error': ZUSTAND['chat_fehler'] if ZUSTAND['chat_status'] == 429 else 'x'}, ZUSTAND['chat_status'])
            frage = json.loads(roh or b'{}').get('frage', '')
            return self._json(ZUSTAND['antwort'] or antwort_standard(frage))
        return self._json({'ok': True})

    do_PATCH = do_POST
    do_DELETE = do_POST


def starten(verzeichnis=PUBLIC, port=0):
    # Einzelaufruf: dieselben Regeln wie check_mobile (nacheinander, nicht waehrend des Scrapers); unter check_mobile regelt das der Elternlauf
    if not os.environ.get('IT_TESTLAUF'):
        import testlauf
        testlauf.exklusiv(); testlauf.warten_auf_ruhe(); os.environ['IT_TESTLAUF'] = '1'
        import atexit; atexit.register(testlauf.chrome_aufraeumen)
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
