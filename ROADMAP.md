# Roadmap

Objetivo: evolucionar por iteraciones pequeñas, verificables y con pruebas.

- [ ] Iteración 0: Esqueleto
  - [x] Estructura de carpetas, docs y tests smoke
  - [x] Validación mínima de matrículas en `core.py`
  - [x] Endpoint `/health` (sin dependencias obligatorias)
- [ ] Iteración 1: Núcleo simple
  - [ ] `LockerAssigner` en memoria (sin persistencia)
  - [ ] Endpoints JSON mínimos (`assign`, `lookup`, `release`) detrás de feature-flag
  - [ ] Pruebas de comportamiento básico
- [ ] Iteración 2: Persistencia básica
  - [ ] Guardado/lectura JSON atómico en `assignments.json`
  - [ ] `.gitignore` mantiene fuera los datos
  - [ ] Scripts de backup manual
- [ ] Iteración 3: UI ligera
  - [ ] Página web mínima (HTML/JS) consumiendo la API
  - [ ] Validación en frontend
- [ ] Iteración 4+: Clientes, metadatos, administración
  - [ ] Catálogo de clientes (JSON) y endpoints
  - [ ] Registro básico de llaves/VIN

Notas: no acoplarse al repo de referencia; mantener independencia y claridad.
