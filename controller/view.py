"""Supervisor view + loop health, served read-only over HTTP (stdlib). One place instead of fifty alerts."""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .explain import explain, supervisor_view


def serve(ctl, port):
    path = ctl.s.path

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                if u.path == "/view":
                    out = supervisor_view(db, q.get("wf", [None])[0])
                elif u.path == "/explain":
                    out = explain(db, q["wf"][0], q.get("at", [None])[0])
                elif u.path == "/alerts":
                    cur = db.execute("SELECT key,wf,severity,message,opened_ts,cleared_ts FROM alerts ORDER BY opened_ts DESC LIMIT 100")
                    out = [dict(zip(["key", "wf", "severity", "message", "opened", "cleared"], r)) for r in cur.fetchall()]
                elif u.path == "/metrics":
                    out = {"ingest_events_per_s": ctl.stats["ingest_eps"], "decision_lag_s": ctl.stats["decision_lag_s"],
                           "events_total": ctl.ing.total_events, "credits_remaining": ctl.credits, "sim_ts": ctl.now,
                           "tick_seconds": ctl.stats["tick_s"]}
                else:
                    out = {"endpoints": ["/view?wf=", "/explain?wf=&at=ISO", "/metrics", "/alerts"]}
                body = json.dumps(out, indent=1, default=str).encode()
                self.send_response(200)
            except Exception as e:
                body = json.dumps({"error": repr(e)}).encode()
                self.send_response(500)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            db.close()

    try:
        HTTPServer(("127.0.0.1", port), H).serve_forever()
    except OSError as e:
        ctl.log(f"[view] cannot bind {port}: {e}")
