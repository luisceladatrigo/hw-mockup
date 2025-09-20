# Arquitectura (borrador)

Este proyecto incluye dos apps Flask simples para simular un flujo cliente→“hardware” (mock) antes de disponer de la placa real.

## Capas
- Cliente (`client_app.py`): UI web responsive. Envía órdenes (color/on/slot) a un servidor.
- Servidor simulado (`hw_server.py`): API + UI que muestra un LED virtual con el estado actual.
- Scripts (`scripts/`): tareas locales (testing, release, tooling).
- Docs (`docs/`): decisiones, arquitectura y diario de desarrollo.

## Principios
- Iteraciones pequeñas con pruebas.
- Persistencia (si aplica) se evaluará más adelante; por ahora, estado en memoria.
- API clara y estable; implementación interna evolutiva.

## Flujo
- El usuario abre el cliente en 127.0.0.1:5000.
- La UI hace POST a `/send` (cliente) con color/on/slot y la URL del servidor.
- El cliente reenvía (proxy) el JSON a `http://127.0.0.1:5001/api/led` usando urllib (stdlib).
- El servidor actualiza su estado en memoria y responde `{ok:true}`.
- La página del servidor (127.0.0.1:5001) refresca cada 1s y pinta el LED.

## Contrato API del servidor simulado
- `POST /api/led` → {ok:true} o {error:"..."}. Valida:
  - `color`: `#RRGGBB` o nombre simple (red, green, blue, yellow, orange, purple, magenta, cyan, white)
  - `on`: booleano
  - `slot`: entero >= 0 (opcional)
- `GET /api/state` → {on, color, slot, ts}

## Sustitución por hardware real
- Si la ESP32 ofrece el mismo contrato HTTP, el cliente seguirá funcionando sin cambios.
- Si usas otro transporte (p. ej., MQTT), podrías sustituir el reenvío en `client_app.py` por una publicación MQTT manteniendo la misma UI.

