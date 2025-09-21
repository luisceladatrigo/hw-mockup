"""
client_app.py
=================

Cliente + Orquestador sencillo para coordinar armarios (hw_server) y realizar
trazados de coordenadas (row/col) con un color común. La UI permite:
- Registrar armarios (id + URL de su hw_server)
- Elegir un armario, definir row/col, color y on/off
- Enviar /api/trace al hw_server elegido

Sin persistencia: la topología vive en memoria (se pierde al reiniciar). El
objetivo es mantener todo muy simple para demo y preparar el camino para luego
reemplazar hw_server por WT32 reales sin tocar la UI.

Requisitos:
- Python 3.9+ (recomendado 3.11+)
- Flask (instalación: pip install flask)

Ejecución local sugerida:
1) Lanza uno o más hw_server.py (p.ej., A en 5001 y B en 5002)
2) En otra terminal: python client_app.py (escucha en 127.0.0.1:5000)
3) Abre http://127.0.0.1:5000 para usar la UI (añade armarios y traza)
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.request
import urllib.error
from typing import Any, Dict
import time

from flask import Flask, jsonify, request, Response


app = Flask(__name__)

# Estado deseado (en memoria) del orquestador por armario
# Estructura: DESIRED[cabinet_id] = { "marks": { key -> {row,col,color,ts} } }
# Donde key = f"r{row}c{col}" (coordenada como clave)
DESIRED: Dict[str, Dict[str, Any]] = {}

# Archivo de persistencia ligero (JSON) para la topología.
TOPOLOGY_FILE = os.environ.get("TOPOLOGY_FILE", "topology.json")

# Topología en memoria: server_id -> {url, row_len, col_len, alias}
CABINETS: Dict[str, Dict[str, Any]] = {}


def load_topology(path: str = TOPOLOGY_FILE) -> None:
    """Carga `topology.json` si existe y rellena CABINETS.

    Estructura esperada (alias opcional):
    {
      "schema_version": 1,
      "cabinets": [ {"id": "A", "url": "http://...", "row_len": 3, "col_len": 3, "alias": "Armario A"}, ... ]
    }
    """
    global CABINETS
    if not os.path.exists(path):
        CABINETS = {}
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("cabinets", []) if isinstance(data, dict) else []
        mem: Dict[str, Dict[str, Any]] = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            cid = str(it.get("id") or "").strip()
            url = str(it.get("url") or "").strip()
            try:
                rlen = int(it.get("row_len", 0))
                clen = int(it.get("col_len", 0))
            except Exception:
                rlen = 0; clen = 0
            alias = str(it.get("alias") or "").strip()
            if cid and url and rlen > 0 and clen > 0 and cid not in mem:
                mem[cid] = {"url": url, "row_len": rlen, "col_len": clen, "alias": alias}
        CABINETS = mem
    except Exception:
        CABINETS = {}


def save_topology(path: str = TOPOLOGY_FILE) -> None:
    """Guarda CABINETS a `topology.json` de forma atómica (best-effort)."""
    data = {
        "schema_version": 1,
        "cabinets": [
            {"id": cid, "url": meta.get("url"), "row_len": int(meta.get("row_len", 0)), "col_len": int(meta.get("col_len", 0)), "alias": meta.get("alias", "")}
            for cid, meta in sorted(CABINETS.items(), key=lambda kv: kv[0])
        ],
    }
    try:
        d = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(d, exist_ok=True)
        # Escribir en tmp y reemplazar
        with tempfile.NamedTemporaryFile("w", delete=False, dir=d, encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tmp_path = tf.name
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort: si falla, ignoramos para no romper la demo.
        pass


# Cargar topología al iniciar
load_topology()


@app.get("/")
def index() -> Response:
    """UI responsive para gestionar armarios y trazar coordenadas."""
    html = """
    <!doctype html>
    <html lang=es>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Cliente/Orquestador – Trazador</title>
      <style>
        :root { --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; --accent:#3b82f6; }
        body { margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }
        .wrap { max-width:900px; margin:0 auto; padding:16px; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:0 10px 28px rgba(0,0,0,0.35); }
        h1 { font-size:20px; margin:0 0 8px; }
        label { display:block; margin:8px 0 4px; color:var(--muted); }
        input, select, button { padding:8px; border-radius:8px; border:1px solid var(--border); background:#0f172a; color:var(--fg); }
        input[type=number] { width:120px; }
        .row { display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin:8px 0; }
        .btn { background:var(--accent); border-color:var(--accent); cursor:pointer; }
        .btn:hover { opacity:.95; }
        .pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#1f2937; cursor:pointer; border:1px solid var(--border); margin-right:6px; }
        .status { margin-top:10px; min-height:1.4em; }
        .ok { color:#34d399; }
        .err { color:#f87171; }
        footer { color:var(--muted); margin-top:12px; font-size:12px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>Cliente/Orquestador – Trazador</h1>
          <p>Registra armarios (URL de su hw_server) y traza coordenadas (row/col) con un color común. La topología vive en memoria.</p>

          <h3 style="margin-top:8px;">Armarios</h3>
          <div class="row">
            <div>
              <label for="cab_id">ID del armario</label>
              <input id="cab_id" type="text" placeholder="A" style="width:120px;" />
            </div>
            <div>
              <label for="cab_url">URL del hw_server</label>
              <input id="cab_url" type="text" placeholder="http://127.0.0.1:5001" style="width:320px;" />
            </div>
            <div style="align-self:flex-end;">
              <button class="btn" id="addCabBtn">Añadir</button>
            </div>
          </div>
          <div class="row">
            <label for="cab_select">Selecciona armario</label>
            <select id="cab_select" style="min-width:220px;"></select>
            <button id="refreshCabs">Refrescar</button>
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
              <label for="mark_id">ID marca</label>
              <input id="mark_id" type="text" placeholder="m1" style="width:120px;" />
            </div>
            <div>
              <label for="row">Fila (row)</label>
              <input id="row" type="number" placeholder="0" min="0" />
            </div>
            <div>
              <label for="col">Columna (col)</label>
              <input id="col" type="number" placeholder="0" min="0" />
            </div>
            <div>
              <button class="btn" id="sendBtn">Enviar</button>
            </div>
          </div>

          <div id="status" class="status"></div>
        </div>
        <footer>Consejo: abre el/los hw_server registrados para ver el trazado.</footer>
      </div>

      <script>
        async function loadCabinets() {
          try {
            const res = await fetch('/api/cabinets');
            const data = await res.json();
            const sel = document.getElementById('cab_select');
            sel.innerHTML = '';
            (data.items||[]).forEach(function(c) {
              const opt = document.createElement('option');
              opt.value = c.id;
              opt.textContent = (c.alias ? (c.alias + ' [' + c.id + ']') : c.id) + ' @ ' + c.url + ' (R=' + c.row_len + ', C=' + c.col_len + ')';
              opt.setAttribute('data-row-len', String(c.row_len||0));
              opt.setAttribute('data-col-len', String(c.col_len||0));
              sel.appendChild(opt);
            });
          } catch (e) { /* ignore */ }
        }
        document.getElementById('refreshCabs').addEventListener('click', loadCabinets);
        // Añadir info de límites y botón eliminar si no existen
        (function ensureControls(){
          const sel = document.getElementById('cab_select');
          const ref = document.getElementById('refreshCabs');
          if (ref && !document.getElementById('limits')) {
            const span = document.createElement('span');
            span.id = 'limits';
            span.style.marginLeft = '10px';
            span.style.color = '#9ca3af';
            ref.parentNode.insertBefore(span, ref.nextSibling);
          }
          if (ref && !document.getElementById('delCabBtn')) {
            const btn = document.createElement('button');
            btn.id = 'delCabBtn';
            btn.textContent = 'Eliminar';
            btn.style.marginLeft = 'auto';
            btn.style.background = '#7f1d1d';
            btn.style.borderColor = '#7f1d1d';
            ref.parentNode.appendChild(btn);
            btn.addEventListener('click', async function(){
              const id = sel && sel.value ? sel.value : '';
              const st = document.getElementById('status');
              if (!id) { st.className='status err'; st.textContent='Error: selecciona un armario para eliminar'; return; }
              try {
                const res = await fetch('/api/cabinets/' + encodeURIComponent(id), { method:'DELETE' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error||'Fallo');
                st.className='status ok'; st.textContent='Armario eliminado: ' + id;
                loadCabinets();
              } catch(e) { st.className='status err'; st.textContent='Error: ' + (e.message||e); }
            });
          }
          try { sel.addEventListener('change', updateLimits); } catch(e) {}
        })();

        function updateLimits(){
          const sel = document.getElementById('cab_select');
          const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
          const lim = document.getElementById('limits');
          if (!opt || !lim) return;
          const r = Number(opt.getAttribute('data-row-len')||'0');
          const c = Number(opt.getAttribute('data-col-len')||'0');
          lim.textContent = (r && c) ? ('Límites: row 0..'+(r-1)+', col 0..'+(c-1)) : '';
        }
        document.getElementById('addCabBtn').addEventListener('click', async function() {
          const id = String(document.getElementById('cab_id').value||'').trim();
          const url = String(document.getElementById('cab_url').value||'').trim();
          const st = document.getElementById('status');
          st.className='status'; st.textContent='Registrando...';
          try {
            const res = await fetch('/api/cabinets', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id, url}) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error||'Fallo');
            st.className='status ok'; st.textContent='Armario añadido: ' + id;
            document.getElementById('cab_id').value='';
            document.getElementById('cab_url').value='';
            loadCabinets();
          } catch(e) { st.className='status err'; st.textContent='Error: ' + (e.message||e); }
        });

        (function bindPills() {
          document.querySelectorAll('.pill').forEach(function(el) {
            el.addEventListener('click', function() {
              const v = el.getAttribute('data-color') || '#ffffff';
              const inp = document.getElementById('color');
              if (v.startsWith('#')) { inp.value = v; }
              inp.setAttribute('data-selected', v);
            });
          });
        })();

        function readPayload() {
          const cabSel = document.getElementById('cab_select');
          const cabinet = cabSel && cabSel.value ? cabSel.value : '';
          const on = document.getElementById('on').value === 'true';
          const colorPicker = document.getElementById('color');
          const color = String(colorPicker.getAttribute('data-selected') || colorPicker.value || '').trim();
          const markId = String((document.getElementById('mark_id')||{}).value||'').trim();
          let row = document.getElementById('row').value;
          let col = document.getElementById('col').value;
          row = (row===''? null : Number(row));
          col = (col===''? null : Number(col));
          return { cabinet, payload: { id: markId, on, color, row, col } };
        }

        async function send() {
          const st = document.getElementById('status');
          st.className = 'status';
          st.textContent = 'Enviando...';
          try {
            const { cabinet, payload } = readPayload();
            if (!cabinet) throw new Error('Selecciona un armario');
            const body = { cabinet, id: payload.id, row: payload.row, col: payload.col, color: payload.color, on: payload.on };
            const res = await fetch('/api/mark', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await res.json();
            if (!res.ok || !data.ok) throw new Error(data.error || 'Fallo');
            st.className = 'status ok';
            st.textContent = 'OK: Trazado enviado al armario ' + cabinet + '.';
          } catch (e) {
            st.className = 'status err';
            st.textContent = 'Error: ' + (e && e.message ? e.message : e);
          }
        }

        document.getElementById('sendBtn').addEventListener('click', send);
        loadCabinets();
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.get("/api/cabinets")
def api_cabinets_list() -> Response:
    """Lista la topología en memoria (armarios registrados).

    Respuesta:
    {"items": [{"id": str, "url": str, "row_len": int, "col_len": int}, ...]}
    """
    items = []
    for cid, meta in CABINETS.items():
        items.append({
            "id": cid,
            "url": meta.get("url"),
            "row_len": meta.get("row_len"),
            "col_len": meta.get("col_len"),
            "alias": meta.get("alias", ""),
        })
    return jsonify({"items": items})


@app.post("/api/cabinets")
def api_cabinets_add() -> Response:
    """Registra un armario (valida consultando /api/state del hw_server).

    Entrada: {"alias": str?, "url": str}
    - Usa el `cabinet_id` reportado por el hw_server como ID real.
    - Guarda alias (opcional), url y tamaños.
    """
    payload = request.get_json(silent=True) or {}
    alias = str(payload.get("alias") or payload.get("id") or "").strip()
    url = str(payload.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url requerida"}), 400
    # Consultar /api/state para obtener cabinet_id y tamaños
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        server_id = str(data.get("cabinet_id") or "").strip()
        row_len = int(data.get("row_len", 0))
        col_len = int(data.get("col_len", 0))
        if (not server_id) or row_len <= 0 or col_len <= 0:
            return jsonify({"error": "respuesta invalida del hw_server"}), 400
    except Exception as ex:
        return jsonify({"error": f"no se pudo validar hw_server: {ex}"}), 502
    CABINETS[server_id] = {"url": url.rstrip("/"), "row_len": row_len, "col_len": col_len, "alias": alias}
    save_topology()
    return jsonify({"ok": True, "cabinet": {"id": server_id, "alias": alias, "url": CABINETS[server_id]["url"], "row_len": row_len, "col_len": col_len}})


@app.delete("/api/cabinets/<cid>")
def api_cabinets_delete(cid: str) -> Response:
    """Elimina un armario registrado y guarda la topología.

    Respuesta: {"ok": true} o 404 si no existe.
    """
    cid = str(cid or "").strip()
    if cid in CABINETS:
        CABINETS.pop(cid, None)
        save_topology()
        return jsonify({"ok": True})
    return jsonify({"error": "armario no registrado"}), 404


# Nota: /api/trace eliminado del flujo. Usar /api/mark o /api/marks.


@app.post("/api/mark")
def api_mark() -> Response:
    """Reenvía una marca (on/off) al hw_server del armario seleccionado.

    Entrada: {"cabinet": "A", "id": "m1"?, "row":int, "col":int, "color":"#RRGGBB"|"red", "on":bool}
    """
    payload = request.get_json(silent=True) or {}
    cabinet = str(payload.get("cabinet") or "").strip()
    if not cabinet:
        return jsonify({"error": "cabinet requerido"}), 400
    meta = CABINETS.get(cabinet)
    if not meta:
        return jsonify({"error": "armario no registrado"}), 404
    on = bool(payload.get("on", True))
    # Actualizar desired del orquestador (clave por coordenada)
    cab = DESIRED.setdefault(cabinet, {"marks": {}})
    try:
        row = int(payload.get("row")); col = int(payload.get("col"))
    except Exception:
        return jsonify({"error": "row/col requeridos"}), 400
    key = str(payload.get("id") or "").strip() or f"r{row}c{col}"
    if not on:
        cab["marks"].pop(key, None)
    else:
        color = str(payload.get("color") or "").strip()
        if not color:
            return jsonify({"error": "color requerido"}), 400
        cab["marks"][key] = {"row": row, "col": col, "color": color, "ts": 0}
    # Empujar estado completo al hw_server
    marks = [ {"id": k, **v} for k, v in cab["marks"].items() ]
    url = meta["url"] + "/api/marks"
    data = json.dumps({"marks": marks}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if 200 <= resp.status < 300:
                return jsonify({"ok": True})
            text = resp.read().decode("utf-8", errors="ignore")
            return jsonify({"error": f"hw_server devolvio {resp.status}: {text}"}), 502
    except urllib.error.HTTPError as he:
        try:
            text = he.read().decode("utf-8", errors="ignore")
        except Exception:
            text = str(he)
        return jsonify({"error": f"HTTPError {he.code}: {text}"}), 502
    except urllib.error.URLError as ue:
        return jsonify({"error": f"no se pudo conectar al hw_server: {ue.reason}"}), 502
    except Exception as ex:
        return jsonify({"error": f"fallo al reenviar: {ex}"}), 500


def main() -> None:
    """Punto de entrada para ejecutar el cliente/orquestador en local."""
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()

@app.get("/panel")
def marks_panel() -> Response:
    html = """
    <!doctype html>
    <html lang=es>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Panel de Marcas</title>
      <style>
        :root { --bg:#0b1220; --fg:#d1d5db; --muted:#9ca3af; --card:#111827; --border:#1f2937; --accent:#3b82f6; }
        body { margin:0; font-family: system-ui, Arial, sans-serif; background:var(--bg); color:var(--fg); }
        .wrap { max-width:900px; margin:0 auto; padding:16px; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; }
        .row { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:8px 0; }
        input, select, button { padding:8px; border-radius:8px; border:1px solid var(--border); background:#0f172a; color:var(--fg); }
        input[type=number]{ width:110px; }
        .btn { background:var(--accent); border-color:var(--accent); cursor:pointer; }
        .status { margin-top:10px; min-height:1.4em; }
        .ok { color:#34d399; } .err { color:#f87171; }
      </style>
    </head>
    <body>
      <div class=wrap>
        <div class=card>
          <h2>Panel de Marcas</h2>
          <div class=row>
            <label for=cab>Armario</label>
            <select id=cab style="min-width:250px;"></select>
            <button id=refresh>Refrescar</button>
          </div>
          <div class=row>
            <label for=mid>ID</label>
            <input id=mid type=text placeholder=m1 />
            <label for=row>row</label>
            <input id=row type=number min=0 />
            <label for=col>col</label>
            <input id=col type=number min=0 />
            <label for=col>color</label>
            <input id=color type=color value="#00ff80" />
            <select id=on><option value=true>On</option><option value=false>Off</option></select>
            <button class=btn id=send>Enviar</button>
          </div>
          <div id=status class=status></div>
          <div class=row>
            <button id=listar>Listar marcas</button>
          </div>
          <ul id=lista></ul>
        </div>
      </div>
      <script>
        async function loadCabs(){ const r=await fetch('/api/cabinets'); const d=await r.json(); const s=document.getElementById('cab'); s.innerHTML=''; (d.items||[]).forEach(c=>{ const o=document.createElement('option'); o.value=c.id; o.textContent=(c.alias?c.alias+' ['+c.id+']':c.id)+' @ '+c.url; o.setAttribute('data-r', c.row_len||0); o.setAttribute('data-c', c.col_len||0); s.appendChild(o); }); }
        document.getElementById('refresh').onclick=loadCabs; loadCabs();
        document.getElementById('send').onclick=async function(){ const st=document.getElementById('status'); st.className='status'; st.textContent='Enviando...'; try{ const cab=document.getElementById('cab').value; const mid=(document.getElementById('mid').value||'default'); const row=parseInt(document.getElementById('row').value); const col=parseInt(document.getElementById('col').value); const color=String(document.getElementById('color').value||''); const on=(document.getElementById('on').value==='true'); const res=await fetch('/api/mark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cabinet:cab,id:mid,row, col, color, on})}); const d=await res.json(); if(!res.ok||!d.ok) throw new Error(d.error||'Fallo'); st.className='status ok'; st.textContent='OK'; } catch(e){ const st=document.getElementById('status'); st.className='status err'; st.textContent='Error: '+(e.message||e);} }
        document.getElementById('listar').onclick=async function(){ const cab=document.getElementById('cab').value; const ul=document.getElementById('lista'); ul.innerHTML='...'; try{ const r=await fetch('/api/cab_state?cabinet='+encodeURIComponent(cab)); const d=await r.json(); if(!r.ok) throw new Error(d.error||'Fallo'); ul.innerHTML=''; (d.marks||[]).forEach(m=>{ const li=document.createElement('li'); const b=document.createElement('button'); b.textContent='Eliminar'; b.onclick=async ()=>{ const x=await fetch('/api/mark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cabinet:cab,id:m.id,on:false})}); const j=await x.json(); if(!x.ok) alert(j.error||'Fallo'); else li.remove(); }; li.textContent=(m.id||'(id)')+' -> ('+m.row+','+m.col+') '+(m.color||''); li.appendChild(b); ul.appendChild(li); }); } catch(e){ ul.innerHTML='Error'; } }
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@app.get("/api/cab_state")
def api_cab_state() -> Response:
    cab = request.args.get("cabinet", type=str)
    if not cab:
        return jsonify({"error": "cabinet requerido"}), 400
    meta = CABINETS.get(cab)
    if not meta:
        return jsonify({"error": "armario no registrado"}), 404
    try:
        req = urllib.request.Request(meta["url"].rstrip("/") + "/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return jsonify(data)
    except Exception as ex:
        return jsonify({"error": f"no se pudo consultar: {ex}"}), 502
