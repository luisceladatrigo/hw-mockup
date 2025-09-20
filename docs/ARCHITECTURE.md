# Arquitectura (borrador)

Este proyecto incluye dos apps Flask simples para simular un flujo cliente→“hardware” (mock) antes de disponer de la placa real.

## Capas
- Cliente/Orquestador (`client_app.py`):
  - UI web responsive para registrar armarios y trazar coordenadas.
  - API propia para gestionar topología en memoria y reenviar órdenes.
- Servidor simulado (`hw_server.py`):
  - API + UI que muestra dos tiras (filas/columnas) y resalta índices activos.
- Scripts (`scripts/`): tareas locales (testing, release, tooling).
- Docs (`docs/`): decisiones, arquitectura y diario de desarrollo.

## Principios
- Iteraciones pequeñas con pruebas.
- Persistencia (si aplica) se evaluará más adelante; por ahora, estado en memoria.
- API clara y estable; implementación interna evolutiva.

## Flujo (trazador 3+3)
- El usuario abre el cliente en 127.0.0.1:5000.
- Añade armarios registrando la URL de su `hw_server`.
- La UI hace POST a `/api/trace` (cliente) con `{ cabinet, {row,col,on,color} }`.
- El cliente reenvía el JSON a `hw_server/api/trace` usando urllib (stdlib).
- El servidor actualiza su estado (on/color/row/col) y la UI del servidor lo pinta.

## Contratos API
- Servidor (`hw_server.py`):
  - `POST /api/trace` → `{ ok:true }` o `{ error:"..." }`. Valida:
    - `color`: `#RRGGBB` o nombre simple (red, green, blue, yellow, orange, purple, magenta, cyan, white)
    - `on`: booleano
    - `row`, `col`: enteros o null, dentro de 0..len-1
  - `GET /api/state` → `{ cabinet_id, row_len, col_len, row, col, on, color, ts }`
  - Compat: `POST /api/led` (set color + on/off global)
- Cliente (`client_app.py`):
  - `POST /api/cabinets` (valida `/api/state`) y `GET /api/cabinets`
  - `POST /api/trace` (reenvía a `hw_server`)

## Sustitución por hardware real
- Si la ESP32 ofrece el mismo contrato HTTP, el cliente seguirá funcionando sin cambios.
- Si usas otro transporte (p. ej., MQTT), podrías sustituir el reenvío en `client_app.py` por una publicación MQTT manteniendo la misma UI.

## Por qué 3+3 (crosshair)
- Complejidad lineal O(R+C) frente a O(R×C) de un grid completo.
- Escala naturalmente cuando el armario crece en filas/columnas.
- Mantiene el mismo color en ambas tiras para coherencia con el eje Z del sistema.
