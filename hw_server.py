"""
hw_server.py
=================

Servidor Flask que simula un "hardware" (p. ej., una ESP32) con un LED.
Expone una API muy simple que el cliente (client_app.py) invoca para encender
o apagar el LED en un color dado. También muestra una página web que representa
el estado del LED visualmente (un círculo de color) para la demo.

Objetivo: poder validar la UI y el contrato de la API antes de tener la placa
real. Más tarde, se puede reemplazar este servidor por la ESP32 siempre que
respete el mismo contrato HTTP.

API (contrato mínimo):
- POST /api/led {"color":"#RRGGBB"|"red", "on":true/false, "slot":int?}
  -> {"ok": true}  (o {"error": "..."}, 400)
- GET /api/state -> {"on":bool, "color":"#RRGGBB", "slot":int|null, "ts":int}

Requisitos:
- Python 3.9+ (recomendado 3.11+)
- Flask (instalación: pip install flask)

Ejecución local:
  python hw_server.py  (escucha en 127.0.0.1:5001)
  Abre http://127.0.0.1:5001 para ver el "LED" virtual.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, Response


app = Flask(__name__)


# --------------------------
# Estado en memoria del LED
# --------------------------

COLOR_NAMES: Dict[str, str] = {
    # Mapa de nombres sencillos a HEX. Amplía a gusto.
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#f59e0b",
    "orange": "#f97316",
    "purple": "#8b5cf6",
    "magenta": "#ff00ff",
    "cyan": "#06b6d4",
    "white": "#ffffff",
}

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class LedState:
    """Estructura simple para guardar el estado del LED en memoria.

    - on: True/False si el LED está encendido.
    - color: cadena HEX #RRGGBB (siempre normalizada a HEX internamente).
    - slot: opcional, sin semántica en este mock (solo demostrativo).
    - ts: timestamp Unix de la última actualización.
    """

    def __init__(self) -> None:
        self.on: bool = False
        self.color: str = "#000000"  # negro cuando está apagado
        self.slot: Optional[int] = None
        self.ts: int = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {"on": self.on, "color": self.color, "slot": self.slot, "ts": self.ts}


LED = LedState()


def normalize_color(value: str) -> Optional[str]:
    """Convierte un color aceptado a HEX #RRGGBB.

    Acepta:
    - HEX ya válido (#RRGGBB)
    - Nombres simples definidos en COLOR_NAMES
    Devuelve HEX o None si no es válido.
    """
    if not isinstance(value, str):
        return None
    v = value.strip()
    if HEX_RE.fullmatch(v):
        return v.lower()
    low = v.lower()
    if low in COLOR_NAMES:
        return COLOR_NAMES[low]
    return None


@app.get("/")
def home() -> Response:
    """Página demo: muestra un círculo cuyo color refleja el estado del LED."""
    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Servidor de Hardware Simulado</title>
      <style>
        :root {{ --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; }}
        body {{ margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }}
        .wrap {{ max-width:900px; margin:0 auto; padding:16px; }}
        .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 28px rgba(0,0,0,0.35); }}
        h1 {{ font-size:20px; margin:0 0 8px; }}
        .led {{ width:180px; height:180px; border-radius:50%; border:6px solid #222; box-shadow: inset 0 0 30px rgba(0,0,0,0.5), 0 0 30px rgba(0,0,0,0.3); margin: 12px auto; background:#000; }}
        .row {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin:8px 0; justify-content:center; }}
        .muted {{ color:var(--muted); }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>Servidor de Hardware Simulado</h1>
          <p>Este servidor emula una ESP32 con un LED. La UI del cliente envía órdenes a <code>/api/led</code>.</p>
          <div class="led" id="led"></div>
          <div class="row muted" id="info"></div>
        </div>
      </div>
      <script>
        async function refresh() {{
          try {{
            const res = await fetch('/api/state');
            const data = await res.json();
            const led = document.getElementById('led');
            const info = document.getElementById('info');
            const on = !!data.on;
            const color = String(data.color||'#000000');
            led.style.background = on ? color : '#000000';
            info.textContent = 'on=' + on + ' | color=' + color + ' | slot=' + (data.slot==null?'(sin)':data.slot) + ' | ts=' + (data.ts||'-');
          }} catch (e) {{ /* ignorar errores de red para la demo */ }}
        }}
        setInterval(refresh, 1000);
        refresh();
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.post("/api/led")
def api_led() -> Response:
    """Recibe una orden para encender/apagar el LED con un color.

    Entrada (JSON): {"color":"#RRGGBB"|"red", "on":true/false, "slot":int?}
    Respuesta (JSON): {"ok": true} o {"error":"..."}
    """
    payload = request.get_json(silent=True) or {}
    color_raw = payload.get("color")
    on_raw = payload.get("on")
    slot_raw = payload.get("slot")

    # Validación básica de tipos y valores
    color_hex = normalize_color(color_raw)
    if not color_hex:
        return jsonify({"error": "color invalido (usa #RRGGBB o nombres como 'red', 'green', ...)"}), 400
    on = bool(on_raw) if isinstance(on_raw, (bool, int)) else False
    slot: Optional[int] = None
    if slot_raw is not None:
        try:
            slot = int(slot_raw)
            if slot < 0:
                raise ValueError
        except Exception:
            return jsonify({"error": "slot debe ser entero >= 0"}), 400

    # Actualizar estado en memoria
    LED.on = on
    LED.color = color_hex if on else "#000000"
    LED.slot = slot
    LED.ts = int(time.time())
    return jsonify({"ok": True})


@app.get("/api/state")
def api_state() -> Response:
    """Devuelve el estado actual del LED (on/color/slot/ts)."""
    return jsonify(LED.to_dict())


def main() -> None:
    """Punto de entrada: arranca el servidor simulado en el puerto 5001."""
    app.run(host="127.0.0.1", port=5001, debug=False)


if __name__ == "__main__":
    main()

