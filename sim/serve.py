#!/usr/bin/env python3
"""No-cache dev server for the simulator — the reliable way to iterate.
Run from the repo root:  python3 sim/serve.py [port]
Serves docs/ with Cache-Control: no-store on EVERYTHING, so the browser can
never hold a stale index.html / charge_sim.js / charge_sim.wasm (each layer
of that chain has bitten us once)."""
import http.server, os, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs"))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

print("simulator: http://localhost:%d/sign-preview/simulator/  (no-cache)" % PORT)
http.server.ThreadingHTTPServer(("", PORT), NoCacheHandler).serve_forever()
