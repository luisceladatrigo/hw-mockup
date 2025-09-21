from __future__ import annotations

"""Modelos del SDK del cliente (DTOs) en formato simple.

Se usan desde el core y los transportes. Mantenerlos ligeros ayuda a
testear y a integrar en otros proyectos sin dependencias extra.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class Coord:
    """Coordenada generica usada por el orquestador.

    Campos:
    - a: indice de agrupacion o armario
    - x, y, z: posicion entera (no negativa)
    """
    a: int
    x: int
    y: int
    z: int

    @staticmethod
    def from_mapping(m: Dict[str, Any]) -> "Coord":
        """Construye una Coord a partir de un diccionario JSON-like."""
        return Coord(a=int(m["a"]), x=int(m["x"]), y=int(m["y"]), z=int(m["z"]))


@dataclass
class Failure:
    """Fallo individual asociado a una coordenada."""
    coord: Coord
    reason: str


@dataclass
class ApplyResult:
    """Resultado de aplicar un lote de operaciones (on/off)."""
    ok_count: int
    fail_count: int
    failures: List[Failure]


@dataclass
class HealthStatus:
    """Estado de salud simple del destino."""
    ok: bool
    detail: str = ""
