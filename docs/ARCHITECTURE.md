# Arquitectura (borrador)

Este proyecto replica la estructura del repo de referencia, pero inicia desde un núcleo mínimo y crecerá iterativamente.

## Capas
- Core (`core.py`): lógica de dominio mínima. Mantener libre de frameworks.
- Web (`web_app.py`): entrega HTTP opcional. No es requisito para importar el módulo.
- Scripts (`scripts/`): tareas locales (testing, release, tooling).
- Docs (`docs/`): decisiones, arquitectura y diario de desarrollo.

## Principios
- Iteraciones pequeñas con pruebas.
- Persistencia como una concern opcional a introducir más adelante.
- API estable hacia fuera, implementación interna evolutiva.

## Datos (futuro)
- `assignments.json`: estado de asignaciones (lectura/escritura atómica).
- Backups rotativos en `backups/` (opt-in, scripts primero).

