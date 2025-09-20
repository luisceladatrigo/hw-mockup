# Endpoints y Contratos

Este documento recoge los endpoints HTTP del mock, con formatos de petición y respuesta, y ejemplos con `curl`.

## hw_server.py (por armario)

- POST `/api/trace`
  - Body JSON:
    ```json
    { "row": 0, "col": 2, "on": true, "color": "#00ff00" }
    ```
    - `row`, `col`: `int` o `null`. Deben estar en rango `[0..ROW_LEN-1]` y `[0..COL_LEN-1]` si se proporcionan.
    - `on`: `bool`. Si es `false`, apaga ambas tiras y limpia `row/col`.
    - `color`: `"#RRGGBB"` o nombre (red, green, blue, yellow, orange, purple, magenta, cyan, white). Requerido si `on=true`.
  - Respuesta:
    ```json
    { "ok": true }
    ```
  - Errores: `400` `{ "error": "mensaje" }` (p. ej., color inválido, índice fuera de rango).

- GET `/api/state`
  - Respuesta:
    ```json
    {
      "cabinet_id": "A",
      "row_len": 3,
      "col_len": 3,
      "row": 1,
      "col": 2,
      "on": true,
      "color": "#00ff00",
      "ts": 1710000000
    }
    ```

- Compat: POST `/api/led`
  - Body: `{ "color": "#RRGGBB"|"red", "on": true|false }`
  - Efecto: `on=false` apaga ambas tiras (limpia `row/col`); `on=true` solo ajusta color global.

## client_app.py (Cliente/Orquestador)

- POST `/api/cabinets`
  - Body: `{ "id": "A", "url": "http://127.0.0.1:5001" }`
  - Acción: consulta `url/api/state` para validar y registra el armario en memoria.
  - Respuesta: `{ "ok": true, "cabinet": { "id": "A", "url": "...", "row_len": 3, "col_len": 3 } }`
  - Efecto: persiste en `topology.json` (ruta en `TOPOLOGY_FILE` o por defecto en el raíz del proyecto).

- GET `/api/cabinets`
  - Respuesta: `{ "items": [ { "id": "A", "url": "...", "row_len": 3, "col_len": 3 } ] }`
  - Fuente: topología en memoria (previamente cargada desde `topology.json`, si existe).

- DELETE `/api/cabinets/{id}`
  - Acción: elimina un armario registrado por su `id` y guarda `topology.json`.
  - Respuesta: `{ "ok": true }` o `404` si no existe.

- POST `/api/trace`
  - Body: `{ "cabinet": "A", "command": { "row": 1, "col": 2, "on": true, "color": "#00ff00" } }`
  - Acción: reenvía el `command` a `A/api/trace`. Devuelve `{ "ok": true }` si el `hw_server` responde 2xx.

## Ejemplos curl

Registrar armario A:
```
curl -s -X POST http://127.0.0.1:5000/api/cabinets \
  -H "Content-Type: application/json" \
  -d '{"id":"A","url":"http://127.0.0.1:5001"}'
```

Trazar coordenada en A (fila 1, col 2, verde):
```
curl -s -X POST http://127.0.0.1:5000/api/trace \
  -H "Content-Type: application/json" \
  -d '{"cabinet":"A","command":{"row":1,"col":2,"on":true,"color":"#00ff00"}}'
```

Apagar A:
```
curl -s -X POST http://127.0.0.1:5000/api/trace \
  -H "Content-Type: application/json" \
  -d '{"cabinet":"A","command":{"on":false,"color":"red"}}'
```
