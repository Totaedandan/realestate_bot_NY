import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run():
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    run()
