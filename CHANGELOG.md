# Changelog

Formato basado en "Keep a Changelog" y versionado segun SemVer.

## [Unreleased]
- Cliente/Servidor simulados con Flask (cliente UI + hw_server con API y UI).
- Documentacion base (README, ROADMAP, docs/).

## [0.2.0] - 2025-09-21
### Added
- SDK ligero `keycar_client` (core/service, models, errors, transport HTTP).
- Metodo `push_marks` y helper `push_marks_to(url, marks)` para compatibilidad inmediata con hw_server.
- `docs/DEVLOG.md` (diario) y actualizacion de `docs/ENDPOINTS.md`.

### Changed
- client_app: `/api/mark` ahora reenvia el bitmap a traves del core manteniendo el comportamiento de pintado.

### Fixed
- hw_server: ahora respeta flags `--host/--port/--id/--rows/--cols/--cycle-ms` (argparse).

## [0.1.0] - 2025-09-20
- Commit inicial (esqueleto Flask).


