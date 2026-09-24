import re
from pathlib import Path

import pytest

from robzone_diag.discovery.hosts import HostRecord
from robzone_diag.models.base import Capability, CapabilityState
from robzone_diag.models.registry import UnknownModelError, all_models, get_model, identify

REPO = Path(__file__).resolve().parents[1]


def test_model_ids_are_unique_kebab_case():
    ids = [m.model_id for m in all_models()]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i) for i in ids)


def test_every_model_declares_every_capability():
    for model in all_models():
        assert set(model.capabilities) == set(Capability), model.model_id


def test_unverified_model_is_never_auto_identified():
    model = get_model("duoro-xmax-profi")
    assert model.fingerprint is None
    assert CapabilityState.VERIFIED not in model.capabilities.values()
    assert identify(HostRecord("192.168.0.50")) == []


def test_unknown_model_lookup_fails_clearly():
    with pytest.raises(UnknownModelError, match="duoro-xmax-profi"):
        get_model("does-not-exist")


def test_supported_models_doc_lists_every_registered_model():
    doc = (REPO / "docs" / "supported-models.md").read_text(encoding="utf-8")
    for model in all_models():
        assert f"`{model.model_id}`" in doc, f"{model.model_id} missing from supported-models.md"
