Diario de desarrollo
====================

2025-09-20
- Arranque del repositorio con dos aplicaciones Flask: client_app (UI) y hw_server (mock de armario con tiras 3+3).
- Definicion de endpoints basicos en hw_server: /api/trace, /api/state y compat /api/led.
- UI basica en client_app: registrar armarios, enviar trazas.

2025-09-21 (manana)
- Refinado de la UI (client_app) y soporte de multiples marcas (bitmap) en hw_server via POST /api/marks.
- Persistencia simple de topologia en topology.json.

2025-09-21 (tarde)
- Desacople del cliente: creacion del SDK ligero keycar_client (core + transport HTTP).
- client_app reenvia el bitmap a hw_server a traves del core (push_marks), manteniendo el comportamiento de pintado.
- Ajustes en docs/ENDPOINTS.md: contratos actualizados y ejemplos.

2025-09-21 (noche)
- hw_server: incorpora argparse con flags --host/--port/--id/--rows/--cols/--cycle-ms y equivalentes por entorno.
- Verificacion multi-armario: A en 5001 y B en 5002 con IDs distintos.
- Preparacion para futura integracion con orquestador unico sin romper la UI.

Notas
- Se prioriza claridad y contratos estables. El core expone helpers minimos hoy (push_marks) y deja placeholders para on/off atomicos.
- Se evita dependencias externas (urllib) para facilitar despliegues y pruebas locales.

