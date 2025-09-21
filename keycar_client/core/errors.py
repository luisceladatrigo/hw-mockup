class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class TransportError(DomainError):
    pass


class OrchestratorError(DomainError):
    pass

