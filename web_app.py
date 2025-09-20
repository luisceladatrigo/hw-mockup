from __future__ import annotations

"""
App web mínima. Diseñada para importar incluso sin Flask instalado.
Solo expone /health si Flask está disponible.
"""

from typing import Any

try:
    from flask import Flask, jsonify
except Exception:  # pragma: no cover - import opcional
    Flask = None  # type: ignore
    jsonify = None  # type: ignore

from core import __version__


if Flask is not None:  # pragma: no cover
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"ok": True, "version": __version__})

    def main() -> None:
        app.run(host="127.0.0.1", port=5000, debug=False)

    if __name__ == "__main__":
        main()
else:
    # Modo sin Flask: no definimos app ejecutable, pero permitir import.
    def main() -> None:  # pragma: no cover
        raise SystemExit("Flask no está instalado. Ejecuta: pip install flask")

