"""
client_app.py
=================

Aplicación Flask que actúa como "cliente" (la interfaz de control que verás
en la demo). Esta app no controla hardware real; en su lugar, envía peticiones
HTTP a un "servidor de hardware simulado" (hw_server.py) que hace de ESP32.

Objetivo: mantener este cliente estable para que, cuando tengas la placa real,
puedas sustituir el servidor simulado por el hardware real sin tocar la UI.

Cómo funciona (resumen):
- Esta app sirve una página web (/) con una UI muy simple y responsive.
- La UI permite elegir un color, encender/apagar y (opcional) indicar un "slot".
- Al pulsar "Enviar", el navegador hace POST a /send (en esta app).
- El endpoint /send reenvía la orden al servidor de hardware simulado
  (por defecto http://127.0.0.1:5001/api/led) usando solo la librería estándar.

Requisitos:
- Python 3.9+ (recomendado 3.11+)
- Flask (instalación: pip install flask)

Ejecución local sugerida:
1) En una terminal: python hw_server.py   (escucha en 127.0.0.1:5001)
2) En otra terminal: python client_app.py (escucha en 127.0.0.1:5000)
3) Abre http://127.0.0.1:5000 para usar la UI del cliente.
4) Abre http://127.0.0.1:5001 para ver el LED simulado.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict

from flask import Flask, jsonify, request, Response


app = Flask(__name__)


def default_server_base() -> str:
    """Devuelve la URL base del servidor simulado.

    Puedes cambiarlo con la variable de entorno MOCK_SERVER_BASE.
    Ejemplo: MOCK_SERVER_BASE=http://192.168.1.50:5001
    """
    return os.environ.get("MOCK_SERVER_BASE", "http://127.0.0.1:5001")


@app.get("/")
def index() -> Response:
    """Sirve una UI HTML muy simple y responsive.

    La UI permite:
    - Elegir color (selector de color + colores rápidos predefinidos)
    - Encender/Apagar (toggle)
    - Indicar slot opcional
    - Configurar la URL del servidor (guardada en localStorage)
    """
    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Cliente – Simulador LED</title>
      <style>
        :root {{ --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; --accent:#3b82f6; }}
        body {{ margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }}
        .wrap {{ max-width:900px; margin:0 auto; padding:16px; }}
        .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 28px rgba(0,0,0,0.35); }}
        h1 {{ font-size:20px; margin:0 0 8px; }}
        label {{ display:block; margin:8px 0 4px; color:var(--muted); }}
        input, select, button {{ padding:8px; border-radius:8px; border:1px solid var(--border); background:#0f172a; color:var(--fg); }}
        input[type="number"] {{ width: 120px; }}
        .row {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin:8px 0; }}
        .btn {{ background:var(--accent); border-color:var(--accent); cursor:pointer; }}
        .btn:hover {{ opacity:.95; }}
        .pill {{ display:inline-block; padding:6px 10px; border-radius:999px; background:#1f2937; cursor:pointer; border:1px solid var(--border); margin-right:6px; }}
        .status {{ margin-top:10px; min-height:1.4em; }}
        .ok {{ color:#34d399; }}
        .err {{ color:#f87171; }}
        footer {{ color:var(--muted); margin-top:12px; font-size:12px; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>Cliente – Simulador LED</h1>
          <p>Esta interfaz envía órdenes a un servidor que emula una ESP32 con un LED virtual. Ajusta el color, enciende/apaga y pulsa "Enviar".</p>

          <div class="row">
            <div>
              <label for="server">Servidor (URL base)</label>
              <input id="server" type="text" placeholder="http://127.0.0.1:5001" style="width:320px;" />
            </div>
            <div>
              <label for="slot">Slot (opcional)</label>
              <input id="slot" type="number" placeholder="5" min="0" />
            </div>
          </div>

          <div class="row">
            <div>
              <label>Color rápido</label>
              <span class="pill" data-color="red"   style="color:#fff;">Rojo</span>
              <span class="pill" data-color="green" style="color:#fff;">Verde</span>
              <span class="pill" data-color="blue"  style="color:#fff;">Azul</span>
              <span class="pill" data-color="yellow" style="color:#222; background:#f59e0b; border-color:#b45309;">Amarillo</span>
              <span class="pill" data-color="#ffffff" style="color:#222;">Blanco</span>
              <span class="pill" data-color="#ff00ff" style="color:#fff;">Magenta</span>
            </div>
          </div>

          <div class="row">
            <div>
              <label for="color">Color (selector)</label>
              <input id="color" type="color" value="#00ff80" />
            </div>
            <div>
              <label for="on">Estado</label>
              <select id="on">
                <option value="true">Encendido</option>
                <option value="false">Apagado</option>
              </select>
            </div>
            <div>
              <button class="btn" id="sendBtn">Enviar</button>
            </div>
          </div>

          <div id="status" class="status"></div>
        </div>
        <footer>Consejo: abre también el servidor simulado en <code>http://127.0.0.1:5001</code> para ver el LED.</footer>
      </div>

      <script>
        // Guardar/cargar URL del servidor en localStorage para comodidad
        (function initServerField() {{
          const key = 'server_base';
          const input = document.getElementById('server');
          const def = {json.dumps(default_server_base())};
          input.value = localStorage.getItem(key) || def;
          input.addEventListener('input', function() {{ localStorage.setItem(key, input.value.trim()); }});
        }})();

        // Píldoras de color rápido
        (function bindPills() {{
          document.querySelectorAll('.pill').forEach(function(el) {{
            el.addEventListener('click', function() {{
              const v = el.getAttribute('data-color') || '#ffffff';
              const inp = document.getElementById('color');
              // Si es nombre, no siempre se puede reflejar en <input type=color>,
              // pero mantenemos el valor del input, el POST usará el nombre.
              if (v.startsWith('#')) {{ inp.value = v; }}
              inp.setAttribute('data-selected', v);
            }});
          }});
        }})();

        function readPayload() {{
          const server = String(document.getElementById('server').value || '').trim();
          let slotRaw = String(document.getElementById('slot').value || '').trim();
          const on = document.getElementById('on').value === 'true';
          const colorPicker = document.getElementById('color');
          // Preferir el color elegido por píldora si existe, sino el del picker
          const color = String(colorPicker.getAttribute('data-selected') || colorPicker.value || '').trim();
          const payload = {{ color: color, on: on }};
          if (slotRaw !== '') {{
            const n = Number(slotRaw);
            if (Number.isInteger(n) && n >= 0) payload.slot = n;
          }}
          return {{ server, payload }};
        }}

        async function send() {{
          const st = document.getElementById('status');
          st.className = 'status';
          st.textContent = 'Enviando...';
          try {{
            const {{ server, payload }} = readPayload();
            const res = await fetch('/send', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ server: server, command: payload }}) }});
            const data = await res.json();
            if (!res.ok || !data.ok) throw new Error(data.error || 'Fallo');
            st.className = 'status ok';
            st.textContent = 'OK: LED actualizado en el servidor.';
          }} catch (e) {{
            st.className = 'status err';
            st.textContent = 'Error: ' + (e && e.message ? e.message : e);
          }}
        }}

        document.getElementById('sendBtn').addEventListener('click', send);
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.post("/send")
def send() -> Response:
    """Recibe la orden desde la UI y la reenvía al servidor de hardware.

    Formato de entrada (JSON):
    {
      "server": "http://127.0.0.1:5001",
      "command": {"color": "#RRGGBB" | "red", "on": true/false, "slot": 5?}
    }

    Respuesta (JSON): {"ok": true} o {"error": "..."}
    """
    payload = request.get_json(silent=True) or {}
    server = str(payload.get("server") or "").strip() or default_server_base()
    command = payload.get("command") or {}
    if not isinstance(command, dict):
        return jsonify({"error": "command debe ser un objeto"}), 400

    # Validación mínima en cliente (el servidor hará su propia validación)
    color = str(command.get("color") or "").strip()
    if not color:
        return jsonify({"error": "color requerido"}), 400
    on = bool(command.get("on", True))
    slot = command.get("slot")
    if slot is not None:
        try:
            slot = int(slot)
            if slot < 0:
                raise ValueError
        except Exception:
            return jsonify({"error": "slot debe ser entero >= 0"}), 400

    # Construir request hacia el servidor simulado
    url = server.rstrip("/") + "/api/led"
    body: Dict[str, Any] = {"color": color, "on": bool(on)}
    if slot is not None:
        body["slot"] = int(slot)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            # Si el servidor respondió 200 OK, devolvemos ok
            if 200 <= resp.status < 300:
                return jsonify({"ok": True})
            # Manejo conservador: leer mensaje de error si lo hay
            text = resp.read().decode("utf-8", errors="ignore")
            return jsonify({"error": f"Servidor devolvio {resp.status}: {text}"}), 502
    except urllib.error.HTTPError as he:  # Errores HTTP (4xx/5xx)
        try:
            text = he.read().decode("utf-8", errors="ignore")
        except Exception:
            text = str(he)
        return jsonify({"error": f"HTTPError {he.code}: {text}"}), 502
    except urllib.error.URLError as ue:  # Errores de conexión/timeout
        return jsonify({"error": f"No se pudo conectar al servidor: {ue.reason}"}), 502
    except Exception as ex:
        return jsonify({"error": f"Fallo al contactar servidor: {ex}"}), 500


def main() -> None:
    """Punto de entrada para ejecutar el cliente en local."""
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()

