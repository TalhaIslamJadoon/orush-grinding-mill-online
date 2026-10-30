# -*- coding: utf-8 -*-
"""
WSGI adapter for the Phosphate Grinding Mill System (hosted edition).

WHY THIS EXISTS
---------------
The PC edition (app.py) is written against http.server's
BaseHTTPRequestHandler. PythonAnywhere (and almost every free host) runs
Python web apps through WSGI instead. This adapter runs the SAME app.py —
no business logic is copied or rewritten. For each WSGI request it builds
a handler object that quacks exactly like the pieces of
BaseHTTPRequestHandler that app.py actually uses:

    self.path       full path + query string
    self.headers    an http.client.HTTPMessage (case-insensitive .get)
    self.rfile      readable stream for the request body
    self.wfile      writable stream for the response body
    self.send_response(code) / send_header(k, v) / end_headers()

and then calls the app's own do_GET / do_POST. Everything else — routing,
sessions (the `mill_session` cookie), login lockout, RBAC, SQLite, backup
ZIPs, print pages — is 100% the app's own code.

HOSTED-EDITION DIFFERENCES (by design, see DEPLOY-STEPS.txt)
------------------------------------------------------------
* app.main() is never called, so the biometric LAN listener (DeviceH,
  /iclock/* on a second port) never starts. Fingerprint devices cannot
  push punches to a public hosted site; use the in-app CSV import or
  manual attendance instead. POSTs to /iclock/* simply 404, exactly as
  the main app answers unknown paths.
* Sessions live in the app process memory (SESSIONS dict in app.py), so
  if the host recycles the web worker everyone is logged out and must
  log in again. No data is lost — all data is in SQLite on disk.
* The first-run "folder picker" button needs a desktop (tkinter) and
  will report it is unavailable online — the data-folder path is typed
  into the setup form instead (DEPLOY-STEPS.txt gives the exact path).
"""

import io
import os
import sys
import traceback
from email.message import Message
from http.client import responses as _reasons

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import app as _mill  # noqa: E402  (the PC-edition app.py, unchanged)


class _Capture:
    """Stand-in for the socket wfile: collects everything the app writes."""

    def __init__(self):
        self.chunks = []

    def write(self, data):
        if data:
            if isinstance(data, str):
                data = data.encode("utf-8")
            self.chunks.append(data)
        return len(data) if data else 0

    def flush(self):
        pass

    def body(self):
        return b"".join(self.chunks)


def _headers_from_environ(environ):
    """Build an HTTPMessage from WSGI environ the way http.server would."""
    msg = Message()
    for key, val in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").title()
            msg[name] = val
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH") and val:
            msg[key.replace("_", "-").title()] = val
    # BaseHTTPRequestHandler also exposes Host from the request line; make
    # sure it is present even behind proxies that strip HTTP_HOST.
    if msg.get("Host") is None:
        msg["Host"] = environ.get("SERVER_NAME", "localhost")
    return msg


def _make_handler(environ, body_bytes):
    """A handler instance with the BaseHTTPRequestHandler surface app.py uses,
    minus the socket: __init__ is bypassed on purpose (it would try to read
    and parse a raw request from a connection)."""
    h = object.__new__(_mill.H)
    capture = _Capture()
    state = {"status": 200, "headers": []}

    h.path = environ.get("PATH_INFO") or "/"
    qs = environ.get("QUERY_STRING") or ""
    if qs:
        h.path = h.path + "?" + qs
    h.command = (environ.get("REQUEST_METHOD") or "GET").upper()
    h.request_version = "HTTP/1.1"
    h.headers = _headers_from_environ(environ)
    h.rfile = io.BytesIO(body_bytes)
    h.wfile = capture
    h.client_address = (environ.get("REMOTE_ADDR") or "127.0.0.1", 0)
    h.close_connection = True

    def send_response(code, message=None):
        state["status"] = int(code)

    def send_response_only(code, message=None):
        state["status"] = int(code)

    def send_header(keyword, value):
        state["headers"].append((str(keyword), str(value)))

    def end_headers():
        pass

    def send_error(code, message=None, explain=None):
        state["status"] = int(code)
        text = (message or _reasons.get(int(code), "Error")).encode("utf-8")
        state["headers"] = [("Content-Type", "text/plain; charset=utf-8"),
                            ("Content-Length", str(len(text)))]
        capture.write(text)

    def log_message(fmt, *args):  # keep hosted logs quiet, like the PC build
        pass

    h.send_response = send_response
    h.send_response_only = send_response_only
    h.send_header = send_header
    h.end_headers = end_headers
    h.send_error = send_error
    h.log_message = log_message
    h._wsgi_state = state
    h._wsgi_capture = capture
    return h


def application(environ, start_response):
    """PEP 3333 entry point. PythonAnywhere's WSGI file imports this."""
    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    try:
        n = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        n = 0
    stream = environ.get("wsgi.input")
    body_bytes = stream.read(n) if (stream is not None and n > 0) else b""

    handler = _make_handler(environ, body_bytes)
    state = handler._wsgi_state
    try:
        if method == "GET":
            handler.do_GET()
        elif method == "POST":
            handler.do_POST()
        else:
            # BaseHTTPRequestHandler answers unimplemented verbs with 501.
            handler.send_error(501, "Unsupported method (%r)" % method)
    except Exception:
        traceback.print_exc()
        state["status"] = 500
        state["headers"] = [("Content-Type", "application/json; charset=utf-8")]
        handler._wsgi_capture = _Capture()
        handler._wsgi_capture.write(
            b'{"error": "internal server error - the mill office copy keeps working; please retry"}')

    body = handler._wsgi_capture.body()
    status = state["status"]
    headers = [(k, v) for (k, v) in state["headers"]
               if k.lower() != "content-length"]
    headers.append(("Content-Length", str(len(body))))
    reason = _reasons.get(status, "")
    start_response("%d %s" % (status, reason), headers)
    return [body]
