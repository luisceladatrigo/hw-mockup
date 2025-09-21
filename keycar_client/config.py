from dataclasses import dataclass


@dataclass
class KeyCarConfig:
    base_url: str = "http://127.0.0.1:8080"
    timeout_s: float = 2.0
    retries: int = 1

