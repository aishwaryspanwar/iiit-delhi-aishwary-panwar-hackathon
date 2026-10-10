import gzip
import json
import mimetypes
import re
import sys
import traceback
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from src.api import service
from src.riskengine.config import REPO_ROOT

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
MAX_BODY_BYTES = 8192
GZIP_MIN_BYTES = 1024
DATASET = r"(?P<dataset>[a-z0-9_]+)"

Handler = Callable[[dict[str, str], dict[str, list[str]], object], object]

ROUTES: list[tuple[str, re.Pattern[str], Handler]] = [
    ("GET", re.compile(r"^/api/health$"), lambda p, q, b: service.health()),
    ("GET", re.compile(r"^/api/meta$"), lambda p, q, b: service.meta()),
    ("GET", re.compile(r"^/api/datasets$"), lambda p, q, b: service.datasets()),
    ("GET", re.compile(r"^/api/portfolio$"), lambda p, q, b: service.portfolio()),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/summary$"), lambda p, q, b: service.summary(p["dataset"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/events$"), lambda p, q, b: service.events(p["dataset"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/events/(?P<item>[^/]+)$"), lambda p, q, b: service.event_detail(p["dataset"], p["item"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/signals$"), lambda p, q, b: service.signals(p["dataset"], q)),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/signals/(?P<item>[^/]+)$"), lambda p, q, b: service.signal_detail(p["dataset"], p["item"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/entities$"), lambda p, q, b: service.entities(p["dataset"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/entities/(?P<item>[^/]+)$"), lambda p, q, b: service.entity_detail(p["dataset"], p["item"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/stress$"), lambda p, q, b: service.stress(p["dataset"])),
    ("GET", re.compile(rf"^/api/datasets/{DATASET}/stress/(?P<item>[^/]+)$"), lambda p, q, b: service.stress_detail(p["dataset"], p["item"])),
    ("POST", re.compile(r"^/api/score$"), lambda p, q, b: service.score(b)),
]


def resolve(method: str, path: str) -> tuple[Handler, dict[str, str]] | None:
    for route_method, pattern, handler in ROUTES:
        match = pattern.match(path)
        if match and route_method == method:
            return handler, {k: unquote(v) for k, v in match.groupdict().items()}
    return None


def path_exists(path: str) -> bool:
    return any(pattern.match(path) for _, pattern, _ in ROUTES)


def static_file(path: str, root: Path = FRONTEND_DIST) -> Path | None:
    if not root.is_dir():
        return None
    base = root.resolve()
    candidate = (base / unquote(path).lstrip("/")).resolve()
    if candidate.is_relative_to(base) and candidate.is_file():
        return candidate
    index = base / "index.html"
    return index if index.is_file() else None


class ApiRequestHandler(BaseHTTPRequestHandler):
    server_version = "RiskEngineAPI/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def dispatch(self, method: str) -> None:
        url = urlsplit(self.path)
        if not url.path.startswith("/api/"):
            self.serve_static(method, url.path)
            return
        route = resolve(method, url.path)
        if route is None:
            status = HTTPStatus.METHOD_NOT_ALLOWED if path_exists(url.path) else HTTPStatus.NOT_FOUND
            self.send_json(status, {"error": "Unknown endpoint" if status == HTTPStatus.NOT_FOUND else "Method not allowed"})
            return
        handler, params = route
        try:
            body = self.read_body() if method == "POST" else None
            payload = handler(params, parse_qs(url.query), body)
        except service.BadRequest as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except service.NotFound as error:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": str(error)})
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "The risk engine could not complete this request"})
        else:
            self.send_json(HTTPStatus.OK, payload)

    def read_body(self) -> object:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as error:
            raise service.BadRequest("Invalid Content-Length") from error
        if length <= 0:
            raise service.BadRequest("Request body is required")
        if length > MAX_BODY_BYTES:
            raise service.BadRequest("Request body is too large")
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            raise service.BadRequest("Request body must be JSON")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise service.BadRequest("Request body is not valid JSON") from error

    def send_json(self, status: HTTPStatus, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_bytes(status, data, "application/json; charset=utf-8", "no-store")

    def send_bytes(self, status: HTTPStatus, data: bytes, content_type: str, cache: str) -> None:
        compress = len(data) >= GZIP_MIN_BYTES and "gzip" in (self.headers.get("Accept-Encoding") or "")
        if compress:
            data = gzip.compress(data, compresslevel=5)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        if compress:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self, method: str, path: str) -> None:
        if method != "GET":
            self.send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"})
            return
        target = static_file(path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "React build not found. Run npm run build in frontend/, or use npm run dev."})
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        cache = "no-cache" if target.name == "index.html" else "public, max-age=31536000, immutable"
        self.send_bytes(HTTPStatus.OK, target.read_bytes(), content_type, cache)

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[api] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ApiRequestHandler)
    server.daemon_threads = True
    return server
