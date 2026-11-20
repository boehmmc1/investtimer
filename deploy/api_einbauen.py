#!/usr/bin/env python3
"""Baut die InvestTimer-Bloecke (Konto/Abo, Vertrag) in die Volafly-API ein.

Ersetzt alles ab der Markierung '# ── InvestTimer-Chat' bis vor '@app.get("/health")'
durch volafly-api/investtimer_api_chat.py, investtimer_api_konto.py, investtimer_api_vertrag.py
und investtimer_api_alarm_mail.py, kopiert die Module neben die API und legt vorher eine
Sicherung an. Danach: systemctl restart volafly-chat
"""
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = Path(sys.argv[1] if len(sys.argv) > 1 else "/root/volafly-chat")
ziel = API / "volafly_chat.py"
s = ziel.read_text(encoding="utf-8")
start, ende = s.index("# ── InvestTimer-Chat (oeffentlich"), s.index('@app.get("/health")')
block = "".join((ROOT / "volafly-api" / n).read_text(encoding="utf-8").rstrip() + "\n\n\n"
                for n in ("investtimer_api_chat.py", "investtimer_api_konto.py", "investtimer_api_vertrag.py", "investtimer_api_alarm_mail.py", "investtimer_api_feedback.py", "investtimer_api_fehler.py"))
neu = s[:start] + block + s[ende:]
compile(neu, str(ziel), "exec")
shutil.copy2(ziel, ziel.with_name(ziel.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S")))
ziel.write_text(neu, encoding="utf-8")
for m in ("investtimer_konto.py", "investtimer_alarme.py", "investtimer_vertrag.py", "investtimer_ki_limit.py", "investtimer_ki_preise.json"):
    shutil.copy2(ROOT / "volafly-api" / m, API / m)
print("eingebaut:", len(block), "Zeichen")
