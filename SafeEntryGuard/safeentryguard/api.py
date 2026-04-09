from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .guard import SafeEntryGuard


def _json_response(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def create_server(guard: SafeEntryGuard, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "SafeEntryGuardHTTP/0.1"

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                _json_response(
                    self,
                    {
                        "ok": True,
                        "project_name": guard.config.project_name,
                        "entity_count": guard.inspect_truth()["entity_count"],
                    },
                )
                return
            if parsed.path == "/truth/summary":
                _json_response(self, guard.inspect_truth())
                return
            _json_response(self, {"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8-sig"))
            except Exception:
                _json_response(self, {"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
                return

            if parsed.path == "/filter":
                prompt = str(payload.get("prompt") or "")
                response = str(payload.get("response") or "")
                if not prompt:
                    _json_response(self, {"error": "missing_prompt"}, status=HTTPStatus.BAD_REQUEST)
                    return
                result = guard.filter_answer(
                    prompt=prompt,
                    response=response,
                    expected_entity=str(payload.get("expected_entity") or ""),
                    requested_entry_types=list(payload.get("requested_entry_types") or []),
                    intent=str(payload.get("intent") or ""),
                    prompt_id=str(payload.get("prompt_id") or ""),
                    model=str(payload.get("model") or ""),
                    context=dict(payload.get("context") or {}),
                )
                _json_response(self, result)
                return

            if parsed.path == "/filter/batch":
                items = list(payload.get("items") or [])
                limit = int(payload.get("limit") or 0)
                filtered_rows, summary = guard.filter_rows(items, limit=limit)
                _json_response(self, {"summary": summary, "items": filtered_rows})
                return

            _json_response(self, {"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    return ThreadingHTTPServer((host, port), Handler)


def serve(guard: SafeEntryGuard, host: str, port: int) -> None:
    server = create_server(guard, host, port)
    print(f"SafeEntryGuard API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
