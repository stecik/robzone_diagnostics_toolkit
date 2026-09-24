"""The list of known models. Adding a model = one import and one entry in ``MODELS``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from robzone_diag.models import duoro_xmax_profi
from robzone_diag.models.base import ModelDefinition

if TYPE_CHECKING:
    from robzone_diag.discovery.hosts import HostRecord

MODELS: tuple[ModelDefinition, ...] = (duoro_xmax_profi.MODEL,)


class UnknownModelError(LookupError):
    pass


def all_models() -> tuple[ModelDefinition, ...]:
    return MODELS


def get_model(model_id: str) -> ModelDefinition:
    for model in MODELS:
        if model.model_id == model_id:
            return model
    known = ", ".join(m.model_id for m in MODELS)
    raise UnknownModelError(f"Unknown model '{model_id}'. Known models: {known}")


def identify(host: HostRecord) -> list[ModelDefinition]:
    """Models whose verified fingerprint matches ``host``. More than one match means ambiguity."""
    return [m for m in MODELS if m.fingerprint is not None and m.fingerprint(host)]
