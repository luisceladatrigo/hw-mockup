# WT32 Mockup (Proyecto paralelo a key-car-group)

Proyecto base, mínimo y extensible, para construir un experimento paralelo al repositorio `key-car-group`. Este repo arranca con una estructura limpia y archivos de trabajo para un desarrollo iterativo, evitando acoplarse al clon de referencia.

Estado: inicial (MVP vacío). La intención es evolucionar por iteraciones pequeñas y verificables.

## Objetivos
- Mantener una estructura clara (docs, tests, scripts, web, core).
- Partir de un núcleo mínimo y crecer por iteraciones.
- Facilitar pruebas y despliegue local en Windows.

## Estructura
- `core.py`: Núcleo mínimo del dominio (versión, validación básica, stubs).
- `web_app.py`: App web mínima (solo /health por ahora). No requiere instalar Flask para importar el módulo.
- `tests/`: Pruebas unitarias iniciales (smoke y validaciones).
- `docs/`: Documentación de arquitectura, decisiones y diario de desarrollo.
- `scripts/`: Utilidades para ejecutar tests, linters o tareas locales.
- `static/`: Recursos estáticos para la web (vacío al inicio).

## Requisitos
- Python 3.9+ (recomendado 3.11+).
- Opcional (web): `pip install flask` para ejecutar `web_app.py` con endpoints HTTP.

## Uso rápido
- Pruebas: `python -m unittest -v`
- Web (si tienes Flask): `python web_app.py` y abrir `http://127.0.0.1:5000/health`

## Guía de desarrollo
- Flujo: trabajar en `CHANGELOG.md` (sección Unreleased) y en el `docs/DEVLOG.md` por iteración.
- Commits: recomendamos Conventional Commits (feat, fix, chore, docs, test, refactor, perf, build, ci).
- Roadmap: ver `ROADMAP.md` para iteraciones y alcance planeado.

## Notas
- El clon `key-car-group/` solo se usa como referencia y está excluido por `.gitignore`.
- Este proyecto no copia código, sino que replica el “shape” (estructura y disciplina) y empieza desde cero.
