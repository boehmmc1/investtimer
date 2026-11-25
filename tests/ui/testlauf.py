"""Regeln fuer Browser-Tests auf dem Live-Server (Auftrag 25.11.2026, Speicher):
- nie zwei Testlaeufe gleichzeitig (Sperre /tmp/investtimer-browsertest.lock),
- nie gleichzeitig mit dem Volafly-Scraper (Sperre /tmp/volafly_scraper.lock, Start alle :00/:30 per Cron),
- nach jedem Test Test-Chrome sicher beenden (nur Playwright-Profile, nie der Chrome des Scrapers)."""
import fcntl, os, signal, subprocess, time

SCRAPER_LOCK = '/tmp/volafly_scraper.lock'
TEST_LOCK = '/tmp/investtimer-browsertest.lock'
_halter = None


def exklusiv():
    """Sperre fuer den ganzen Lauf; wartet, falls schon ein Testlauf laeuft."""
    global _halter
    if _halter:
        return
    _halter = open(TEST_LOCK, 'w')
    fcntl.flock(_halter, fcntl.LOCK_EX)


def scraper_aktiv():
    try:
        with open(SCRAPER_LOCK, 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    except OSError:
        return False


def warten_auf_ruhe(dauer_min=4):
    """Wartet, bis der Scraper nicht laeuft und in den naechsten dauer_min Minuten keiner startet (Cron :00 und :30)."""
    while True:
        m = time.localtime().tm_min % 30
        if not scraper_aktiv() and m <= 30 - dauer_min - 1 and m >= 6:
            return
        time.sleep(15)


def chrome_aufraeumen():
    """Beendet uebrig gebliebene Test-Chromes (Playwright-Profile unter /tmp/playwright*); der Scraper nutzt ~/.config/google-chrome."""
    r = subprocess.run(['pgrep', '-f', '--', '--user-data-dir=/tmp/playwright'], capture_output=True, text=True)
    for pid in r.stdout.split():
        try:
            os.kill(int(pid), signal.SIGKILL)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
