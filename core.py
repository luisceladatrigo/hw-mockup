"""
Core mínimo para WT32 Mockup.

Arrancamos con muy poco: versión, validación de matrícula y stubs que
podremos reemplazar por una implementación real en iteraciones siguientes.
"""

from __future__ import annotations

import re

__version__ = "0.1.0"


PLATE_RE = re.compile(r"^[A-Z0-9-]{3,10}$")


def sanitize_plate(plate: str) -> str:
    if not isinstance(plate, str):
        return ""
    p = plate.strip().replace(" ", "").upper()
    return p if PLATE_RE.fullmatch(p or " ") else ""


class LockerAssigner:
    """Esqueleto: asignador en memoria (sin persistencia, ni hashing).

    Implementación deliberadamente mínima para permitir pruebas tempranas.
    """

    def __init__(self) -> None:
        self._map: dict[str, int] = {}

    def assign(self, raw_plate: str) -> tuple[int, bool]:
        p = sanitize_plate(raw_plate)
        if not p:
            raise ValueError("Matricula invalida. Use 3-10 caracteres A-Z, 0-9 o '-'.")
        if p in self._map:
            return self._map[p], False
        # Colocar siempre en el siguiente índice libre (simple y determinista por ahora)
        idx = 0
        used = set(self._map.values())
        while idx in used:
            idx += 1
        self._map[p] = idx
        return idx, True

    def lookup(self, raw_plate: str) -> int | None:
        p = sanitize_plate(raw_plate)
        if not p:
            raise ValueError("Matricula invalida. Use 3-10 caracteres A-Z, 0-9 o '-'.")
        return self._map.get(p)

    def release(self, raw_plate: str) -> bool:
        p = sanitize_plate(raw_plate)
        if not p:
            raise ValueError("Matricula invalida. Use 3-10 caracteres A-Z, 0-9 o '-'.")
        return self._map.pop(p, None) is not None

