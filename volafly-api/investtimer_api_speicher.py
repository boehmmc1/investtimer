# ── Speicher-Diagnose (25.11.2026): nur lokal, nur mit IT_SPEICHER_DIAG=1 (systemd-Drop-in). Zeigt Groessen, nie Inhalte.
import tracemalloc as _it_tm
if os.environ.get("IT_SPEICHER_DIAG") == "1" and not _it_tm.is_tracing():
    _it_tm.start(8)


def _it_rss_mb():
    try:
        with open("/proc/self/status") as f:
            return next(int(z.split()[1]) // 1024 for z in f if z.startswith("VmRSS"))
    except Exception:
        return None


@app.get("/v1/investtimer/speicher")
def it_speicher(request: Request, n: int = 25):
    if (request.client.host if request.client else "") != "127.0.0.1" or request.headers.get("x-real-ip"):
        return _JSONResp({"error": "nur lokal"}, status_code=403)
    import gc, threading
    g = globals()
    groessen = {k: len(v) for k, v in g.items() if isinstance(v, (dict, list, set)) and k.startswith("_") and len(v) > 0}
    aus = {"rss_mb": _it_rss_mb(), "threads": threading.active_count(), "gc": gc.get_count(),
           "objekte": len(gc.get_objects()), "sammlungen": dict(sorted(groessen.items(), key=lambda x: -x[1])[:20])}
    if _it_tm.is_tracing():
        cur, peak = _it_tm.get_traced_memory()
        snap = _it_tm.take_snapshot().filter_traces((_it_tm.Filter(False, _it_tm.__file__),))
        aus.update(traced_mb=round(cur / 1e6, 1), traced_peak_mb=round(peak / 1e6, 1),
                   top=[{"wo": str(s.traceback[0]), "kb": round(s.size / 1024), "anzahl": s.count} for s in snap.statistics("lineno")[:n]],
                   top_kette=[{"wo": " <- ".join(str(f) for f in list(s.traceback)[:4]), "kb": round(s.size / 1024)} for s in snap.statistics("traceback")[:8]])
    return aus
