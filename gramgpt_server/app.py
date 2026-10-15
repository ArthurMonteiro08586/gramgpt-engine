# -*- coding: utf-8 -*-
"""app.py — stdlib HTTP server exposing the full GramGPT-clone API.

* Routes are matched against routes_spec.json (generated verbatim from their
  OpenAPI 3.0.3, 92 paths / 101 routes) — unknown paths -> 404, known path +
  wrong method -> 405, like the real API.
* Auth: `Authorization: Bearer ggk_live_*`. Clone-only key issuance:
  POST /api/v1/auth/token {"username": ...} -> {"token": "ggk_live_..."}.
* /panel serves the Task-Monitor UI built on their real component CSS.
* /api/v1/openapi.json serves the original spec.
"""
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import auth as A
from . import handlers as H
from .store import Store
from .worker import TaskWorker

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
ROUTES_SPEC = json.load(open(os.path.join(_HERE, "routes_spec.json"), encoding="utf-8"))
PANEL_HTML = os.path.join(_ROOT, "examples", "panel_live.html")
OPENAPI_SRC = os.path.join(_HERE, "openapi_served.json")


def _compile(pattern):
    rx = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern.rstrip("/") + "/?$")
    return re.compile("^/" + rx.lstrip("/"))


COMPILED = [(r["method"], _compile(r["path"]), r["path"], r["tag"]) for r in ROUTES_SPEC]
# static paths must win over parameterized ones (/webhooks/events/ vs /webhooks/{id}/)
COMPILED.sort(key=lambda r: (r[2].count("{"), r[2]))
REGISTRY = H.build_registry()

# clone-only extras (clearly outside their spec)
EXTRA = {("POST", "/api/v1/auth/token/"), ("POST", "/api/v1/auth/token")}


class Server:
    def __init__(self, db=":memory:", speed=4.0, autostart_worker=True):
        self.store = Store(db)
        self.worker = TaskWorker(self.store, speed=speed)
        if autostart_worker:
            self.worker.start()
        self.httpd = None

    # ------------------------------------------------------------
    def dispatch(self, method, path, query, body, headers):
        """Returns (status, json_body, content_type_or_None, bytes_or_None)."""
        if path == "/healthz":
            return 200, {"ok": True}, None, None
        if path in ("/", "/panel", "/panel/"):
            if os.path.exists(PANEL_HTML):
                return 200, None, "text/html; charset=utf-8", \
                    open(PANEL_HTML, "rb").read()
            return 404, {"detail": "panel_live.html not built"}, None, None
        if path == "/api/v1/openapi.json":
            if os.path.exists(OPENAPI_SRC):
                return 200, None, "application/json", open(OPENAPI_SRC, "rb").read()
            return 200, {"openapi": "3.0.3", "info": {"title": "GramGPT Clone API"},
                         "paths": {r["path"]: {} for r in ROUTES_SPEC}}, None, None
        if (method, path) in EXTRA or (method, path.rstrip("/") + "/") in EXTRA:
            if method == "POST":
                b = body or {}
                tok = A.issue_token(self.store, username=b.get("username", "demo"),
                                    plan=b.get("plan", "basic"),
                                    quota_total=int(b.get("quota_total", 1000)),
                                    balance=float(b.get("balance", 0)))
                return 200, {"token": tok}, None, None
        # spec routing
        params = None
        matched = None
        path_exists = False
        for m, rx, pat, tag in COMPILED:
            mo = rx.match(path)
            if mo:
                path_exists = True
                if m == method:
                    params = mo.groupdict()
                    matched = pat
                    break
        if params is None:
            if path_exists:
                return 405, {"detail": "Method Not Allowed"}, None, None
            return 404, {"detail": "Not Found"}, None, None
        # auth
        hdr = headers.get("authorization", "")
        token = hdr[7:] if hdr.lower().startswith("bearer ") else None
        user = A.user_by_token(self.store, token)
        if not user:
            return 401, {"detail": "Invalid or missing token"}, None, None
        handler = REGISTRY.get((method, matched)) or H.h_generic_tool
        ctx = {"store": self.store, "user": user, "params": params,
               "query": query, "body": body, "headers": headers}
        try:
            status, payload = handler(ctx)
        except Exception as e:
            return 500, {"detail": f"internal error: {e.__class__.__name__}: {e}"}, None, None
        return status, payload, None, None

    # ------------------------------------------------------------
    def handler_cls(server):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _run(self, method):
                u = urlparse(self.path)
                ln = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(ln) if ln else b""
                body = None
                if raw:
                    try:
                        body = json.loads(raw.decode("utf-8"))
                    except Exception:
                        self._send(400, {"detail": "invalid JSON body"})
                        return
                headers = {k.lower(): v for k, v in self.headers.items()}
                status, payload, ctype, blob = server.dispatch(
                    method, u.path, parse_qs(u.query), body, headers)
                if blob is not None:
                    self.send_response(status)
                    self.send_header("Content-Type", ctype or "application/octet-stream")
                    self.send_header("Content-Length", str(len(blob)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(blob)
                else:
                    self._send(status, payload)

            def _send(self, status, payload):
                blob = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(blob)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.end_headers()
                self.wfile.write(blob)

            def do_GET(self):    self._run("GET")
            def do_POST(self):   self._run("POST")
            def do_PUT(self):    self._run("PUT")
            def do_PATCH(self):  self._run("PATCH")
            def do_DELETE(self): self._run("DELETE")
            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Content-Length", "0")
                self.end_headers()
        return Handler

    def serve(self, host="127.0.0.1", port=8770, block=True):
        self.httpd = ThreadingHTTPServer((host, port), self.handler_cls())
        print(f"[gramgpt-clone] API on http://{host}:{port}  (/panel, /healthz, /api/v1/openapi.json)")
        if block:
            self.httpd.serve_forever()
        else:
            t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            t.start()
            return t

    def shutdown(self):
        self.worker.stop()
        if self.httpd:
            self.httpd.shutdown()
