from __future__ import annotations

import json
import time
from typing import List, Dict, Any

import urllib.request
import urllib.error

from keycar_client.core.models import Coord, ApplyResult, Failure, HealthStatus
from keycar_client.core.errors import TransportError, OrchestratorError
from keycar_client.config import KeyCarConfig


class HttpTransportClient:
    def __init__(self, cfg: KeyCarConfig) -> None:
        self.cfg = cfg

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = self.cfg.base_url.rstrip("/") + path
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")

        attempts = max(1, self.cfg.retries + 1)
        last_err: Exception | None = None
        for _ in range(attempts):
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as resp:
                    body = resp.read()
                    if not body:
                        return {}
                    return json.loads(body.decode("utf-8"))
            except urllib.error.HTTPError as e:
                # Pass through orchestrator-provided error payloads when possible
                try:
                    detail = e.read().decode("utf-8")
                except Exception:
                    detail = str(e)
                raise OrchestratorError(detail)
            except Exception as e:
                last_err = e
                time.sleep(0.1)
        raise TransportError(str(last_err) if last_err else "transport error")

    def set_on(self, coords: List[Coord]) -> ApplyResult:
        # Placeholder behavior: success count equals number of coords
        return ApplyResult(ok_count=len(coords), fail_count=0, failures=[])

    def set_off(self, coords: List[Coord]) -> ApplyResult:
        # Placeholder behavior mirroring set_on
        return ApplyResult(ok_count=len(coords), fail_count=0, failures=[])

    def health(self) -> HealthStatus:
        res = self._request("GET", "/health")
        ok = bool(res.get("ok", True))
        return HealthStatus(ok=ok, detail=str(res.get("detail", "")))

    # New: push a full marks set to a hw_server compatible endpoint
    def push_marks(self, marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {"marks": marks}
        # hw_server expects POST /api/marks
        return self._request("POST", "/api/marks", payload)


def _parse_apply_result(res: Dict[str, Any]) -> ApplyResult:
    ok_count = int(res.get("ok_count", 0))
    failures_list = []
    for f in res.get("failures", []) or []:
        try:
            coord = Coord.from_mapping(f.get("coord", {}))
        except Exception:
            # If coord cannot be parsed, skip with generic placeholder
            continue
        failures_list.append(Failure(coord=coord, reason=str(f.get("reason", "error"))))
    return ApplyResult(ok_count=ok_count, fail_count=len(failures_list), failures=failures_list)
