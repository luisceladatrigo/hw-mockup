from __future__ import annotations

"""Fachada principal del cliente (SDK).

Expone operaciones de alto nivel e interna un transporte HTTP. Mantiene
la API estable para que apps (como client_app) no dependan de detalles
de red ni endpoints exactos.
"""

from typing import Iterable, List

from keycar_client.core.models import Coord, ApplyResult, HealthStatus
from keycar_client.core.errors import ValidationError
from keycar_client.transport.http_client import HttpTransportClient
from keycar_client.config import KeyCarConfig


class KeyCarClient:
    """Cliente de alto nivel para orquestar encendido/apagado y health."""

    def __init__(self, config: KeyCarConfig | None = None) -> None:
        self._cfg = config or KeyCarConfig()
        self._transport = HttpTransportClient(self._cfg)

    @staticmethod
    def _normalize_coords(coords: Iterable[dict | Coord]) -> List[Coord]:
        """Acepta dicts o Coord y devuelve una lista de Coord validas."""
        out: List[Coord] = []
        for c in coords:
            if isinstance(c, Coord):
                out.append(c)
            elif isinstance(c, dict):
                required = {"a", "x", "y", "z"}
                if not required.issubset(c.keys()):
                    raise ValidationError("coord missing keys a,x,y,z")
                out.append(Coord.from_mapping(c))
            else:
                raise ValidationError("invalid coord type")
        return out

    def set_on(self, coords: Iterable[dict | Coord]) -> ApplyResult:
        """Enciende coordenadas (placeholder mientras se definen endpoints)."""
        norm = self._normalize_coords(coords)
        return self._transport.set_on(norm)

    def set_off(self, coords: Iterable[dict | Coord]) -> ApplyResult:
        """Apaga coordenadas (placeholder mientras se definen endpoints)."""
        norm = self._normalize_coords(coords)
        return self._transport.set_off(norm)

    def health(self) -> HealthStatus:
        """Consulta health del destino (si existe)."""
        return self._transport.health()

    # Compatibilidad: reenviar el bitmap completo a hw_server
    def push_marks(self, marks: list[dict]) -> dict:
        if not isinstance(marks, list):
            raise ValidationError("marks must be a list")
        return self._transport.push_marks(marks)

    # Ayuda de compatibilidad: POST directo a <url>/api/marks sin config
    @staticmethod
    def push_marks_to(url: str, marks: list[dict]) -> bool:
        import json as _json
        import urllib.request as _ur
        import urllib.error as _ue
        if not isinstance(url, str) or not url:
            raise ValidationError("url requerido")
        if not isinstance(marks, list):
            raise ValidationError("marks must be a list")
        full = url.rstrip('/') + '/api/marks'
        data = _json.dumps({"marks": marks}).encode("utf-8")
        req = _ur.Request(full, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with _ur.urlopen(req, timeout=5) as resp:
                return 200 <= getattr(resp, 'status', 200) < 300
        except _ue.HTTPError:
            return False
        except Exception:
            return False
