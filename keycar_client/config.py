"""Configuracion basica del cliente.

Se mantiene deliberadamente minimalista. Si en el futuro se soportan
varios transportes (HTTP, IPC, etc.), aqui se podrian agregar mas campos.
"""

from dataclasses import dataclass


@dataclass
class KeyCarConfig:
    """Config para transporte HTTP del cliente."""
    base_url: str = "http://127.0.0.1:8080"
    timeout_s: float = 2.0
    retries: int = 1
