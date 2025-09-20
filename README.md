# WT32 Mockup

Esqueleto mínimo para un proyecto iterativo. Ahora incluye dos apps Flask para un mock cliente/servidor que simula trazados de coordenadas con tiras LED (modo “trazador” 3+3 por armario) como si fueran WT32/ESP32 reales.

## Estructura
- `client_app.py`: Cliente/Orquestador con UI web responsive. Permite registrar armarios (urls de sus `hw_server`), elegir uno y trazar coordenadas `row/col` con un color común (encendido/apagado).
- `hw_server.py`: Servidor de hardware simulado por armario. Expone un API y una UI que muestra dos tiras (filas y columnas) resaltando los índices activos con el color actual.
- `docs/`: Documentación (arquitectura y diario de desarrollo).
- `scripts/`: Utilidades locales.
- `static/`: Recursos estáticos (vacío).

## Requisitos
- Python 3.9+ (recomendado 3.11+)
- Flask: `pip install flask`

## Uso rápido
Escenario A: Un solo armario
1) Terminal 1: `python hw_server.py` (usa por defecto `PORT=5001`, `ROW_LEN=3`, `COL_LEN=3`, `CABINET_ID="CAB"`)
2) Terminal 2: `python client_app.py` (cliente/orquestador en `http://127.0.0.1:5000`)
3) En el cliente: añade el armario con URL `http://127.0.0.1:5001`, selecciónalo, define `row`/`col`, color y on/off, y pulsa Enviar.
4) En el servidor: abre `http://127.0.0.1:5001` para ver dos tiras y el índice encendido en cada una.

Escenario B: Dos armarios (A y B)
- Armario A: `CABINET_ID=A ROW_LEN=3 COL_LEN=3 PORT=5001`
- Armario B: `CABINET_ID=B ROW_LEN=3 COL_LEN=3 PORT=5002`

PowerShell (Windows):
```
$env:CABINET_ID='A'; $env:ROW_LEN=3; $env:COL_LEN=3; $env:PORT=5001; python hw_server.py
# En otra consola
$env:CABINET_ID='B'; $env:ROW_LEN=3; $env:COL_LEN=3; $env:PORT=5002; python hw_server.py
# Cliente
python client_app.py
```

Variables de entorno (hw_server):
- `CABINET_ID` (string, opcional; por defecto `CAB`).
- `ROW_LEN` (int, opcional; por defecto `3`).
- `COL_LEN` (int, opcional; por defecto `3`).
- `PORT` (int, opcional; por defecto `5001`).

Contrato API (resumen)
- Servidor simulado (`hw_server.py`):
  - `POST /api/trace` → body `{ row:int|null, col:int|null, on:bool, color:"#RRGGBB"|"red" }` → `{ ok:true }`
    - color común para ambas tiras; `on=false` apaga ambas y limpia `row/col`.
  - `GET /api/state` → `{ cabinet_id, row_len, col_len, row, col, on, color, ts }`
  - Compatibilidad: `POST /api/led` (set color y on/off global sin tocar row/col cuando `on=true`).
- Cliente/Orquestador (`client_app.py`):
  - `POST /api/cabinets` → registra armario tras validar `hw_server` (`/api/state`).
    Body `{ id:"A", url:"http://127.0.0.1:5001" }` → `{ ok:true, cabinet:{...} }`
  - `GET /api/cabinets` → lista `{ items:[{id,url,row_len,col_len}, ...] }`
  - `POST /api/trace` → body `{ cabinet:"A", command:{ row, col, on, color } }` → reenvía a `hw_server`.

Notas de diseño
- El cliente/orquestador reenvía órdenes usando solo librería estándar (urllib). Evitamos CORS desde el navegador y dependencias extra.
- “Trazador” 3+3: dos tiras (filas y columnas). Complejidad O(R+C), no O(R×C); escala lineal cuando el armario crezca.
- Cuando llegue la WT32, basta con respetar el contrato HTTP o introducir un adaptador (HTTP→MQTT) manteniendo la UI intacta.

Ejemplos rápidos (curl)
- Registrar armario:
```
curl -s -X POST http://127.0.0.1:5000/api/cabinets \
  -H "Content-Type: application/json" \
  -d '{"id":"A","url":"http://127.0.0.1:5001"}'
```
- Trazar coordenada (fila 1, columna 2, verde):
```
curl -s -X POST http://127.0.0.1:5000/api/trace \
  -H "Content-Type: application/json" \
  -d '{"cabinet":"A","command":{"row":1,"col":2,"on":true,"color":"#00ff00"}}'
```
- Apagar ambas tiras:
```
curl -s -X POST http://127.0.0.1:5000/api/trace \
  -H "Content-Type: application/json" \
  -d '{"cabinet":"A","command":{"on":false,"color":"red"}}'
```

## Desarrollo
- Iteraciones pequeñas. Mantener `CHANGELOG.md` y `docs/DEVLOG.md` al día.
