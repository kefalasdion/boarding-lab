"""Small local HTTP/JSON server for the simulator UI."""

from __future__ import annotations

import json
import hashlib
import mimetypes
import threading
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from .comparison import (
    compact_public_comparison,
    run_comparison,
    run_comparison_monte_carlo,
)
from .engine import MODEL_STATUS, MODEL_VERSION, SCHEMA_VERSION, run_flight
from .monte_carlo import run_monte_carlo
from .provenance import load_parameter_registry
from .serialization import canonical_json_bytes, to_primitive
from .strategies import strategy_catalog
from .validation import ScenarioValidationError, load_default_scenario

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
MAX_BODY_BYTES = 1_000_000
SIMULATION_SLOTS = threading.BoundedSemaphore(2)
PUBLIC_DOCUMENTS = {
    "SOURCES.md",
    "VALIDATION_PLAN.md",
    "RESULT_SCHEMA.md",
    "RESEARCH.md",
}


class SimulatorHandler(BaseHTTPRequestHandler):
    server_version = "PassengerBoardingSimulator/1.0"

    def log_message(self, format_string: str, *args: Any) -> None:
        return

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        cache_control: str = "no-store",
        etag: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        if etag is not None:
            self.send_header("ETag", etag)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        self._send_bytes(status, canonical_json_bytes(payload), "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length header.") from error
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("JSON request body is empty or too large.")
        try:
            value = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Request body is not valid UTF-8 JSON.") from error
        if not isinstance(value, dict):
            raise ValueError("JSON request body must be an object.")
        return value

    def _validation_error(self, error: ScenarioValidationError) -> None:
        self._send_json(
            HTTPStatus.BAD_REQUEST,
            {
                "error": "validation_error",
                "issues": [to_primitive(issue) for issue in error.issues],
            },
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/config":
            self._send_json(
                HTTPStatus.OK,
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "modelVersion": MODEL_VERSION,
                    "modelStatus": MODEL_STATUS,
                    "defaultScenario": load_default_scenario(),
                    "strategies": strategy_catalog(),
                    "parameterProvenance": load_parameter_registry(),
                },
            )
            return
        if path.startswith("/api/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {
            "/api/run",
            "/api/monte-carlo",
            "/api/compare",
            "/api/compare-monte-carlo",
        }:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not SIMULATION_SLOTS.acquire(blocking=False):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "busy", "message": "The simulator is already running two requests."},
            )
            return
        try:
            payload = self._read_json()
            if path == "/api/run":
                result = run_flight(payload.get("scenario", {}), payload.get("seed"))
            elif path == "/api/monte-carlo":
                result = run_monte_carlo(
                    payload.get("scenario", {}),
                    payload.get("runs"),
                    payload.get("baseSeed"),
                )
            elif path == "/api/compare":
                result = compact_public_comparison(
                    run_comparison(payload.get("scenario", {}), payload.get("seed"))
                )
            else:
                result = run_comparison_monte_carlo(
                    payload.get("scenario", {}),
                    payload.get("runs"),
                    payload.get("baseSeed"),
                )
            self._send_json(HTTPStatus.OK, result)
        except ScenarioValidationError as error:
            self._validation_error(error)
        except ValueError as error:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_request", "message": str(error)},
            )
        except Exception:
            traceback.print_exc()
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal_error", "message": "The local simulation request failed."},
            )
        finally:
            SIMULATION_SLOTS.release()

    def _serve_static(self, raw_path: str) -> None:
        decoded = unquote(raw_path)
        relative = PurePosixPath(decoded.lstrip("/"))
        if any(part in {"..", ""} for part in relative.parts):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return
        if str(relative) in {"", "."}:
            relative = PurePosixPath("index.html")
        static_root = (
            PROJECT_ROOT
            if len(relative.parts) == 1 and relative.name in PUBLIC_DOCUMENTS
            else WEB_ROOT
        )
        candidate = static_root.joinpath(*relative.parts).resolve()
        try:
            candidate.relative_to(static_root.resolve())
        except ValueError:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return
        if not candidate.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        body = candidate.read_bytes()
        if relative.parts and relative.parts[0] == "data":
            etag = f'"{hashlib.sha256(body).hexdigest()}"'
            if self.headers.get("If-None-Match") == etag:
                self._send_bytes(
                    HTTPStatus.NOT_MODIFIED,
                    b"",
                    content_type,
                    cache_control="public, max-age=3600",
                    etag=etag,
                )
                return
            self._send_bytes(
                HTTPStatus.OK,
                body,
                content_type,
                cache_control="public, max-age=3600",
                etag=etag,
            )
            return
        self._send_bytes(HTTPStatus.OK, body, content_type)


def make_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), SimulatorHandler)
