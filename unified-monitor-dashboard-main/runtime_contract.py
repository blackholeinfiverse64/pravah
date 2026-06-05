"""Compatibility runtime contract module.

Control plane and decision engine should import from this module to avoid
schema drift across integration layers.
"""

from schemas import Alert, RuntimePayload, ValidationError, runtime_contract_schema

__all__ = [
    "Alert",
    "RuntimePayload",
    "ValidationError",
    "runtime_contract_schema",
]
