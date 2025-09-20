"""
hw_server.py
=================

Servidor Flask que simula un "hardware" (p. ej., una WT32/ESP32) con trazador
de coordenadas basado en dos tiras (3+3 en este MVP):
- Tira de filas: índices 0..ROW_LEN-1
- Tira de columnas: índices 0..COL_LEN-1

Ambas tiras usan el mismo color (esencia del sistema: color común como "Z").
Al apagar, se apagan ambas tiras.

Contratos soportados:
- POST /api/trace {"row": int|null, "col": int|null, "on": bool, "color": "#RRGGBB"|"red"}
  -> {"ok": true}
- GET /api/state -> {
     "cabinet_id": str, "row_len": int, "col_len": int,
     "row": int|null, "col": int|null, "on": bool, "color": "#RRGGBB",
     "ts": int
   }

Compatibilidad (opcional):
- POST /api/led {"color":"#RRGGBB"|"red", "on":true/false}
  -> {"ok": true}
  (Ajusta el color y encendido global, sin cambiar row/col cuando on=true; si on=false, apaga ambas.)

Configuración por variables de entorno (opcionales):
- CABINET_ID (por defecto "CAB")
- ROW_LEN (por defecto 3)
- COL_LEN (por defecto 3)
- PORT (por defecto 5001)

Ejecución local (ejemplos):
  # Armario A
  $env:CABINET_ID="A"; $env:ROW_LEN=3; $env:COL_LEN=3; $env:PORT=5001; python hw_server.py
  # Armario B
  $env:CABINET_ID="B"; $env:ROW_LEN=3; $env:COL_LEN=3; $env:PORT=5002; python hw_server.py

Abre http://127.0.0.1:PORT para ver las dos tiras y el estado.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, Response


app = Flask(__name__)


# --------------------------
# Estado en memoria (trazador 3+3)
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


def _env_int(name: str, default: int) -> int:
    try:
        v = int(os.environ.get(name, str(default)))
        return v
    except Exception:
        return default


CABINET_ID = os.environ.get("CABINET_ID", "CAB")
ROW_LEN = max(1, _env_int("ROW_LEN", 3))
COL_LEN = max(1, _env_int("COL_LEN", 3))


class CrosshairState:
    """Estado de dos tiras: fila y columna.

    - on: True/False (apaga/enciende ambas tiras)
    - color: HEX #RRGGBB (mismo color para ambas tiras por esencia del sistema)
    - row: índice activo de tira de filas (o None)
    - col: índice activo de tira de columnas (o None)
    - ts: timestamp Unix de última actualización
    """

    def __init__(self) -> None:
        self.on: bool = False
        self.color: str = "#000000"
        self.row: Optional[int] = None
        self.col: Optional[int] = None
        self.ts: int = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cabinet_id": CABINET_ID,
            "row_len": int(ROW_LEN),
            "col_len": int(COL_LEN),
            "row": (int(self.row) if self.row is not None else None),
            "col": (int(self.col) if self.col is not None else None),
            "on": bool(self.on),
            "color": self.color,
            "ts": int(self.ts),
        }


STATE = CrosshairState()


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
    """Página demo: muestra dos tiras (filas y columnas) y su estado.

    Visualizamos dos filas de "LEDs" (divs). Si STATE.on es true, encendemos
    el índice seleccionado en cada tira con el color actual.
    """
    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>HW Simulado – {CABINET_ID}</title>
      <style>
        :root {{ --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; --off:#0a0a0a; }}
        body {{ margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }}
        .wrap {{ max-width:900px; margin:0 auto; padding:16px; }}
        .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 28px rgba(0,0,0,0.35); }}
        h1 {{ font-size:20px; margin:0 0 8px; }}
        .strip {{ display:flex; gap:10px; justify-content:center; margin: 8px 0; }}
        .dot {{ width:42px; height:42px; border-radius:10px; background:var(--off); border:2px solid #222; box-shadow: inset 0 0 10px rgba(0,0,0,0.4); display:flex; align-items:center; justify-content:center; font-size:12px; color:#999; }}
        .info {{ color:var(--muted); text-align:center; margin-top:8px; font-size:12px; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>HW Simulado – {CABINET_ID}</h1>
          <div class="strip" id="rows"></div>
          <div class="strip" id="cols"></div>
          <div class="info" id="info"></div>
        </div>
      </div>
      <script>
        function makeDots(containerId, n) {{
          const el = document.getElementById(containerId);
          el.innerHTML='';
          for (let i=0;i<n;i++) {{
            const d = document.createElement('div');
            d.className = 'dot';
            d.id = containerId + '-dot-' + i;
            d.textContent = i;
            el.appendChild(d);
          }}
        }}
        async function refresh() {{
          try {{
            const res = await fetch('/api/state');
            const data = await res.json();
            const info = document.getElementById('info');
            // Crear dots si cambió la longitud
            if (!document.getElementById('rows-dot-0') || document.querySelectorAll('#rows .dot').length !== data.row_len) {{
              makeDots('rows', data.row_len);
            }}
            if (!document.getElementById('cols-dot-0') || document.querySelectorAll('#cols .dot').length !== data.col_len) {{
              makeDots('cols', data.col_len);
            }}
            // Reset
            document.querySelectorAll('.dot').forEach(function(d) {{ d.style.background='var(--off)'; d.style.color='#999'; d.style.borderColor = '#222'; }});
            // Encender seleccion si on=true
            if (data.on) {{
              const color = String(data.color||'#000000');
              if (Number.isInteger(data.row) && data.row >=0 && data.row < data.row_len) {{
                const r = document.getElementById('rows-dot-' + data.row);
                if (r) {{ r.style.background = color; r.style.color='#111'; r.style.borderColor = color; }}
              }}
              if (Number.isInteger(data.col) && data.col >=0 && data.col < data.col_len) {{
                const c = document.getElementById('cols-dot-' + data.col);
                if (c) {{ c.style.background = color; c.style.color='#111'; c.style.borderColor = color; }}
              }}
            }}
            info.textContent = 'cabinet=' + data.cabinet_id + ' | on=' + (!!data.on) + ' | color=' + (data.color||'-') + ' | row=' + (data.row==null?'(none)':data.row) + ' | col=' + (data.col==null?'(none)':data.col) + ' | ts=' + (data.ts||'-');
          }} catch (e) {{ /* ignorar errores */ }}
        }}
        setInterval(refresh, 800);
        refresh();
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.post("/api/led")
def api_led() -> Response:
    """Compatibilidad: ajustar encendido/apagado y color global (sin coordenadas).

    Entrada: {"color":"#RRGGBB"|"red", "on":true/false}
    Si on=false: apaga ambas tiras y limpia row/col.
    Si on=true: ajusta el color; no cambia row/col.
    """
    payload = request.get_json(silent=True) or {}
    color_raw = payload.get("color")
    on_raw = payload.get("on")

    color_hex = normalize_color(color_raw)
    if not color_hex:
        return jsonify({"error": "color invalido (usa #RRGGBB o nombres como 'red', 'green', ...)"}), 400
    on = bool(on_raw) if isinstance(on_raw, (bool, int)) else False

    STATE.on = on
    STATE.color = color_hex if on else "#000000"
    if not on:
        STATE.row = None
        STATE.col = None
    STATE.ts = int(time.time())
    return jsonify({"ok": True})


@app.post("/api/trace")
def api_trace() -> Response:
    """Establece la coordenada a trazar con un color común para ambas tiras.

    Entrada (JSON): {"row": int|null, "col": int|null, "on": bool, "color": "#RRGGBB"|"red"}
    Reglas:
    - color común para ambas tiras.
    - on=false apaga ambas tiras y limpia row/col.
    - row/col pueden ser null para no seleccionar esa tira.
    - Si se proveen, deben estar en rango [0..len-1].
    """
    payload = request.get_json(silent=True) or {}
    on_raw = payload.get("on")
    color_raw = payload.get("color")
    row_raw = payload.get("row")
    col_raw = payload.get("col")

    on = bool(on_raw) if isinstance(on_raw, (bool, int)) else False
    color_hex = normalize_color(color_raw)
    if not color_hex and on:
        return jsonify({"error": "color requerido y valido cuando on=true"}), 400

    # Validar row/col si no son None
    row_val: Optional[int] = None
    col_val: Optional[int] = None
    if row_raw is not None:
        try:
            row_val = int(row_raw)
            if row_val < 0 or row_val >= ROW_LEN:
                return jsonify({"error": f"row fuera de rango (0..{ROW_LEN-1})"}), 400
        except Exception:
            return jsonify({"error": "row debe ser entero o null"}), 400
    if col_raw is not None:
        try:
            col_val = int(col_raw)
            if col_val < 0 or col_val >= COL_LEN:
                return jsonify({"error": f"col fuera de rango (0..{COL_LEN-1})"}), 400
        except Exception:
            return jsonify({"error": "col debe ser entero o null"}), 400

    if not on:
        STATE.on = False
        STATE.color = "#000000"
        STATE.row = None
        STATE.col = None
        STATE.ts = int(time.time())
        return jsonify({"ok": True})

    # on=true
    STATE.on = True
    STATE.color = color_hex or STATE.color
    STATE.row = row_val
    STATE.col = col_val
    STATE.ts = int(time.time())
    return jsonify({"ok": True})


@app.get("/api/state")
def api_state() -> Response:
    """Devuelve el estado actual (cabinet, longitudes, fila, columna, on, color, ts)."""
    return jsonify(STATE.to_dict())


def main() -> None:
    """Punto de entrada: arranca el servidor simulado en el puerto indicado."""
    try:
        port = int(os.environ.get("PORT", "5001"))
    except Exception:
        port = 5001
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
