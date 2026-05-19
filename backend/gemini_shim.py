#!/usr/bin/env python3
"""
Simple Gemini HTTP shim server for local testing.
Listens on port 5000 and responds to POST /generate with a JSON
payload containing a basic echoed response. No external web framework
required so it works inside a minimal venv.

Run: python gemini_shim.py
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 5000


class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        if self.path != "/generate":
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode())
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode()) if body else {}
        except Exception:
            payload = {}

        prompt = payload.get("prompt", "")
        # Very small deterministic response so tests are repeatable
        response_text = f"[shim] received prompt: {prompt[:200]}"

        self._set_headers(200)
        out = {"response": response_text}
        self.wfile.write(json.dumps(out).encode())


def run():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Gemini shim running at http://{HOST}:{PORT}/generate")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down shim")
        server.server_close()


if __name__ == "__main__":
    run()
