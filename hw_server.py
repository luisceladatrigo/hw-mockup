"""
hw_server.py
=================

Servidor Flask que simula un "hardware" (p. ej., una WT32/ESP32) con trazador
de coordenadas basado en dos tiras (3+3 en este MVP):
- Tira de filas: Ã­ndices 0..ROW_LEN-1
- Tira de columnas: Ã­ndices 0..COL_LEN-1

Ambas tiras usan el mismo color (esencia del sistema: color comÃºn como "Z").
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

ConfiguraciÃ³n por variables de entorno (opcionales):
- CABINET_ID (por defecto "CAB")
- ROW_LEN (por defecto 3)
- COL_LEN (por defecto 3)
- PORT (por defecto 5001)

EjecuciÃ³n local (ejemplos):
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
    # Mapa de nombres sencillos a HEX. AmplÃ­a a gusto.
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
# Velocidad de alternancia entre colores en segmentos con colisiÃ³n (ms)
CYCLE_MS = _env_int("CYCLE_MS", 1000)


class MarksState:
    """Permite mÃºltiples marcas simultÃ¡neas.

    Cada marca representa una coordenada con un color comÃºn para tiras
    laterales (fila izquierda y columna superior) y una cruz en la intersecciÃ³n.
    Estructura: marks: dict[id -> {row:int, col:int, color:str, ts:int}]
    """

    def __init__(self) -> None:
        self.marks: Dict[str, Dict[str, Any]] = {}
        self.ts: int = int(time.time())

    def set_mark(self, mid: str, row: int, col: int, color: str) -> None:
        self.marks[mid] = {"row": int(row), "col": int(col), "color": color, "ts": int(time.time())}
        self.ts = int(time.time())

    def del_mark(self, mid: str) -> bool:
        ok = self.marks.pop(mid, None) is not None
        if ok:
            self.ts = int(time.time())
        return ok

    def clear(self) -> None:
        self.marks.clear()
        self.ts = int(time.time())

    def replace_all(self, items: list[dict[str, Any]]) -> None:
        self.marks.clear()
        for it in items:
            try:
                row = int(it.get("row"))
                col = int(it.get("col"))
                mid = str(it.get("id") or "").strip() or f"r{row}c{col}"
                color = str(it.get("color") or "")
                if not (0 <= row < ROW_LEN and 0 <= col < COL_LEN):
                    continue
                color_hex = normalize_color(color)
                if not color_hex:
                    continue
                self.marks[mid] = {"row": row, "col": col, "color": color_hex, "ts": int(time.time())}
            except Exception:
                continue
        self.ts = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cabinet_id": CABINET_ID,
            "row_len": int(ROW_LEN),
            "col_len": int(COL_LEN),
            "marks": [ {"id": k, "row": v["row"], "col": v["col"], "color": v["color"], "ts": v["ts"]}
                        for k, v in self.marks.items() ],  # respeta orden de inserciÃ³n
            "ts": int(self.ts),
        }


STATE = MarksState()


def normalize_color(value: str) -> Optional[str]:
    """Convierte un color aceptado a HEX #RRGGBB.

    Acepta:
    - HEX ya vÃ¡lido (#RRGGBB)
    - Nombres simples definidos en COLOR_NAMES
    Devuelve HEX o None si no es vÃ¡lido.
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
    """PÃ¡gina demo: muestra dos tiras (filas y columnas) y su estado.

    Visualizamos dos filas de "LEDs" (divs). Si STATE.on es true, encendemos
    el Ã­ndice seleccionado en cada tira con el color actual.
    """
    html = """
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>HW Simulado â€“ <<CAB>></title>
      <style>
        :root { --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; --grid:#222; --grid2:#333; }
        body { margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }
        .wrap { max-width:900px; margin:0 auto; padding:16px; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 28px rgba(0,0,0,0.35); }
        h1 { font-size:20px; margin:0 0 8px; }
        .board { display:block; margin: 12px auto; background: #0c1426; border-radius: 10px; box-shadow: inset 0 0 18px rgba(0,0,0,0.45); }
        .legend { display:flex; gap:8px; justify-content:center; margin-top:8px; font-size:12px; color:var(--muted); }
        .info { color:var(--muted); text-align:center; margin-top:8px; font-size:12px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>HW Simulado â€“ <<CAB>></h1>
          <svg id="board" class="board"></svg>
          <div class="legend"><span>Los segmentos iluminados representan las tiras reales (fila y columna). La intersecciÃ³n se marca con una cruz.</span></div>
          <div class="info" id="info"></div>
        </div>
      </div>
      <script>
        const CYCLE_MS = <<CYCLE_MS>>;
        function clear(el) { while (el.firstChild) { el.removeChild(el.firstChild); } }

        function drawBoard(svg, rows, cols, marks) {
          const cell = 60;          // tamaÃ±o de casillero
          const pad = 20;           // margen
          const w = cols*cell + pad*2;
          const h = rows*cell + pad*2;
          svg.setAttribute('width', String(w));
          svg.setAttribute('height', String(h));
          clear(svg);

          // Fondo
          const bg = document.createElementNS('http://www.w3.org/2000/svg','rect');
          bg.setAttribute('x', '0'); bg.setAttribute('y','0');
          bg.setAttribute('width', String(w)); bg.setAttribute('height', String(h));
          bg.setAttribute('fill', '#0c1426');
          svg.appendChild(bg);

          // Rejilla (bordes de celdas)
          const stroke1 = '#202937';
          const stroke2 = '#2b3647';
          for (let i=0; i<=cols; i++) {
            const x = pad + i*cell;
            const v = document.createElementNS('http://www.w3.org/2000/svg','line');
            v.setAttribute('x1', String(x)); v.setAttribute('y1', String(pad));
            v.setAttribute('x2', String(x)); v.setAttribute('y2', String(h-pad));
            v.setAttribute('stroke', i===0||i===cols ? stroke1 : stroke2);
            v.setAttribute('stroke-width', i===0||i===cols ? '3' : '2');
            svg.appendChild(v);
          }
          for (let j=0; j<=rows; j++) {
            const y = pad + j*cell;
            const hl = document.createElementNS('http://www.w3.org/2000/svg','line');
            hl.setAttribute('x1', String(pad)); hl.setAttribute('y1', String(y));
            hl.setAttribute('x2', String(w-pad)); hl.setAttribute('y2', String(y));
            hl.setAttribute('stroke', j===0||j===rows ? stroke1 : stroke2);
            hl.setAttribute('stroke-width', j===0||j===rows ? '3' : '2');
            svg.appendChild(hl);
          }

          // Resolver colisiones por segmento: alternar (cycle) o dividir (split)
          const topMap = {};  // col -> [colors]
          const leftMap = {}; // row -> [colors]
          (marks||[]).forEach(function(m){
            if (!Number.isInteger(m.row) || !Number.isInteger(m.col)) return;
            if (m.row<0||m.row>=rows||m.col<0||m.col>=cols) return;
            const col=m.col, row=m.row, color=String(m.color||'#00ff00');
            (topMap[col]=topMap[col]||[]).push(color);
            (leftMap[row]=leftMap[row]||[]).push(color);
          });
          function drawTop(col, colors){
            const cx=pad+col*cell+cell/2, yTop=pad-8, total=cell*0.6, x1=cx-total/2, x2=cx+total/2, n=Math.max(1,colors.length);
            if (n>1) {
              const idx=Math.floor(Date.now()/CYCLE_MS) % n; // alterna cada segundo
              const seg=document.createElementNS('http://www.w3.org/2000/svg','line');
              seg.setAttribute('x1', String(x1)); seg.setAttribute('y1', String(yTop));
              seg.setAttribute('x2', String(x2)); seg.setAttribute('y2', String(yTop));
              seg.setAttribute('stroke', colors[idx]); seg.setAttribute('stroke-width','6'); seg.setAttribute('stroke-linecap','round');
              svg.appendChild(seg);
            } else {
              const seg=document.createElementNS('http://www.w3.org/2000/svg','line');
              seg.setAttribute('x1', String(x1)); seg.setAttribute('y1', String(yTop));
              seg.setAttribute('x2', String(x2)); seg.setAttribute('y2', String(yTop));
              seg.setAttribute('stroke', colors[0]||'#00ff00'); seg.setAttribute('stroke-width','6'); seg.setAttribute('stroke-linecap','round');
              svg.appendChild(seg);
            }
          }
          function drawLeft(row, colors){
            const cy=pad+row*cell+cell/2, xLeft=pad-8, total=cell*0.6, y1=cy-total/2, y2=cy+total/2, n=Math.max(1,colors.length);
            if (n>1) {
              const idx=Math.floor(Date.now()/CYCLE_MS) % n;
              const seg=document.createElementNS('http://www.w3.org/2000/svg','line');
              seg.setAttribute('x1', String(xLeft)); seg.setAttribute('y1', String(y1));
              seg.setAttribute('x2', String(xLeft)); seg.setAttribute('y2', String(y2));
              seg.setAttribute('stroke', colors[idx]); seg.setAttribute('stroke-width','6'); seg.setAttribute('stroke-linecap','round');
              svg.appendChild(seg);
            } else {
              const seg=document.createElementNS('http://www.w3.org/2000/svg','line');
              seg.setAttribute('x1', String(xLeft)); seg.setAttribute('y1', String(y1));
              seg.setAttribute('x2', String(xLeft)); seg.setAttribute('y2', String(y2));
              seg.setAttribute('stroke', colors[0]||'#00ff00'); seg.setAttribute('stroke-width','6'); seg.setAttribute('stroke-linecap','round');
              svg.appendChild(seg);
            }
          }
          Object.keys(topMap).forEach(function(c){ drawTop(parseInt(c), topMap[c]); });
          Object.keys(leftMap).forEach(function(r){ drawLeft(parseInt(r), leftMap[r]); });
          // Cruces por marca
          (marks||[]).forEach(function(m){
            const cxc = pad + m.col*cell + cell/2;
            const cyc = pad + m.row*cell + cell/2;
            const d = cell*0.45;
            const l1 = document.createElementNS('http://www.w3.org/2000/svg','line');
            l1.setAttribute('x1', String(cxc-d)); l1.setAttribute('y1', String(cyc-d));
            l1.setAttribute('x2', String(cxc+d)); l1.setAttribute('y2', String(cyc+d));
            l1.setAttribute('stroke', m.color); l1.setAttribute('stroke-width', '5'); l1.setAttribute('stroke-linecap','round');
            const l2 = document.createElementNS('http://www.w3.org/2000/svg','line');
            l2.setAttribute('x1', String(cxc+d)); l2.setAttribute('y1', String(cyc-d));
            l2.setAttribute('x2', String(cxc-d)); l2.setAttribute('y2', String(cyc+d));
            l2.setAttribute('stroke', m.color); l2.setAttribute('stroke-width', '5'); l2.setAttribute('stroke-linecap','round');
            svg.appendChild(l1); svg.appendChild(l2);
          });
        }
        async function refresh() {{
          try {{
            const res = await fetch('/api/state');
            const data = await res.json();
            const info = document.getElementById('info');
            const svg = document.getElementById('board');
            drawBoard(svg, data.row_len, data.col_len, data.marks||[]);
            info.textContent = 'cabinet=' + data.cabinet_id + ' | on=' + (!!data.on) + ' | color=' + (data.color||'-') + ' | row=' + (data.row==null?'(none)':data.row) + ' | col=' + (data.col==null?'(none)':data.col) + ' | ts=' + (data.ts||'-');
          }} catch (e) {{ /* ignorar errores */ }}
        }}
        setInterval(refresh, 800);
        refresh();
      </script>
    </body>
    </html>
    """
    html = html.replace("<<CAB>>", CABINET_ID).replace("<<CYCLE_MS>>", str(CYCLE_MS))
    return Response(html, mimetype="text/html")


@app.post("/api/led")
def api_led() -> Response:
    """Compatibilidad: encender una marca 'default' o apagar todas.

    Entrada: {"color":"#RRGGBB"|"red", "on":true/false}
    on=false: borra todas las marcas.
    on=true: coloca/actualiza la marca "default" en (row=0,col=0).
    """
    payload = request.get_json(silent=True) or {}
    color_raw = payload.get("color")
    on_raw = payload.get("on")

    color_hex = normalize_color(color_raw)
    if not color_hex:
        return jsonify({"error": "color invalido (usa #RRGGBB o nombres como 'red', 'green', ...)"}), 400
    on = bool(on_raw) if isinstance(on_raw, (bool, int)) else False

    if not on:
        STATE.clear()
        return jsonify({"ok": True})
    # on=true: por compat, usar 0,0
    STATE.set_mark("default", 0, 0, color_hex)
    return jsonify({"ok": True})


@app.post("/api/trace")
def api_trace() -> Response:
    """Compat: establece/borra una Ãºnica marca 'default'."""
    payload = request.get_json(silent=True) or {}
    on_raw = payload.get("on")
    color_raw = payload.get("color")
    row_raw = payload.get("row")
    col_raw = payload.get("col")

    on = bool(on_raw) if isinstance(on_raw, (bool, int)) else False
    if not on:
        STATE.del_mark("default")
        return jsonify({"ok": True})
    color_hex = normalize_color(color_raw)
    if not color_hex:
        return jsonify({"error": "color requerido y valido"}), 400
    try:
        row_val = int(row_raw)
        col_val = int(col_raw)
    except Exception:
        return jsonify({"error": "row/col requeridos"}), 400
    if not (0 <= row_val < ROW_LEN):
        return jsonify({"error": f"row fuera de rango (0..{ROW_LEN-1})"}), 400
    if not (0 <= col_val < COL_LEN):
        return jsonify({"error": f"col fuera de rango (0..{COL_LEN-1})"}), 400
    STATE.set_mark("default", row_val, col_val, color_hex)
    return jsonify({"ok": True})


@app.post("/api/mark")
def api_mark() -> Response:
    """Gestiona mÃºltiples marcas.

    Entrada: {"id":str, "row":int, "col":int, "color":"#RRGGBB"|"red", "on":bool}
    on=true -> set/update; on=false -> delete id.
    """
    payload = request.get_json(silent=True) or {}
    on = bool(payload.get("on", True))
    try:
        row = int(payload.get("row"))
        col = int(payload.get("col"))
    except Exception:
        if not on:
            mid_only = str(payload.get("id") or "").strip()
            if not mid_only:
                return jsonify({"error": "id o (row,col) requeridos"}), 400
            STATE.del_mark(mid_only)
            return jsonify({"ok": True})
        return jsonify({"error": "row/col requeridos"}), 400
    mid = str(payload.get("id") or "").strip() or f"r{row}c{col}"
    if not on:
        STATE.del_mark(mid)
        return jsonify({"ok": True})
    if not (0 <= row < ROW_LEN) or not (0 <= col < COL_LEN):
        return jsonify({"error": "row/col fuera de rango"}), 400
    color = normalize_color(payload.get("color"))
    if not color:
        return jsonify({"error": "color invalido"}), 400
    STATE.set_mark(mid, row, col, color)
    return jsonify({"ok": True})


@app.post("/api/marks")
def api_marks() -> Response:
    """Reemplaza todas las marcas de una vez (modo 'bitmap').

    Entrada: {"marks": [ {"id":"m1","row":1,"col":2,"color":"#00ff00"}, ... ]}
    """
    payload = request.get_json(silent=True) or {}
    items = payload.get("marks")
    if not isinstance(items, list):
        return jsonify({"error": "marks debe ser lista"}), 400
    STATE.replace_all(items)
    return jsonify({"ok": True, "count": len(STATE.marks)})


@app.get("/api/state")
def api_state() -> Response:
    """Devuelve el estado actual: tamaÃ±o del grid y lista de marcas activas."""
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


