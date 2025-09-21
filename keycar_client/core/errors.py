"""Jerarquia de errores del dominio/SDK.

Se diferencian errores de validacion local, de transporte (red/timeouts)
y errores reportados por el orquestador/destino.
"""


class DomainError(Exception):
    """Error base del dominio del cliente."""
    pass


class ValidationError(DomainError):
    """Entrada invalida en el cliente (shape/tipos/rango)."""
    pass


class TransportError(DomainError):
    """Fallo de transporte (timeouts, DNS, conexion rechazada)."""
    pass


class OrchestratorError(DomainError):
    """El destino respondio con error semantico o HTTP 4xx/5xx."""
    pass
