from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class Coord:
    a: int
    x: int
    y: int
    z: int

    @staticmethod
    def from_mapping(m: Dict[str, Any]) -> "Coord":
        return Coord(a=int(m["a"]), x=int(m["x"]), y=int(m["y"]), z=int(m["z"]))


@dataclass
class Failure:
    coord: Coord
    reason: str


@dataclass
class ApplyResult:
    ok_count: int
    fail_count: int
    failures: List[Failure]


@dataclass
class HealthStatus:
    ok: bool
    detail: str = ""

