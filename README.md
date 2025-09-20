# WT32 Mockup

Esqueleto mínimo para un proyecto iterativo. Ahora incluye dos apps Flask para un mock cliente/servidor que simula el encendido de un LED como si fuera una ESP32.

## Estructura
- `client_app.py`: Cliente con UI web responsive. Permite elegir color, encender/apagar y enviar la orden al servidor simulado.
- `hw_server.py`: Servidor de hardware simulado. Expone un API y una UI que muestra un LED virtual con el color actual.
- `docs/`: Documentación (arquitectura y diario de desarrollo).
- `scripts/`: Utilidades locales.
- `static/`: Recursos estáticos (vacío).

## Requisitos
- Python 3.9+ (recomendado 3.11+)
- Flask: `pip install flask`

## Uso rápido
1) En una terminal: `python hw_server.py` (servidor simulado en `http://127.0.0.1:5001`)
2) En otra terminal: `python client_app.py` (cliente en `http://127.0.0.1:5000`)
3) Abre el cliente en `http://127.0.0.1:5000`, configura la URL del servidor si es necesario (por defecto `http://127.0.0.1:5001`), elige color y estado, y pulsa “Enviar”.
4) Abre el servidor en `http://127.0.0.1:5001` para ver el LED virtual cambiar.

Variables de entorno útiles:
- `MOCK_SERVER_BASE` en `client_app.py` para cambiar la URL por defecto del servidor (p. ej., `http://192.168.1.50:5001`).

Contrato API (resumen):
- Servidor simulado (`hw_server.py`):
  - `POST /api/led` body `{ "color": "#RRGGBB"|"red", "on": true, "slot": 5? }` → `{ "ok": true }`
  - `GET /api/state` → `{ "on": true, "color": "#RRGGBB", "slot": 5 | null, "ts": 1710000000 }`
  - Acepta HEX o nombres sencillos: red, green, blue, yellow, orange, purple, magenta, cyan, white.

Notas de diseño:
- El cliente reenvía la orden al servidor usando solo librería estándar (urllib). Así evitamos CORS y dependencias extra.
- Más adelante, puedes reemplazar `hw_server.py` por tu ESP32 si mantiene el mismo contrato HTTP.

## Desarrollo
- Iteraciones pequeñas. Mantener `CHANGELOG.md` y `docs/DEVLOG.md` al día.
