"""Robzone DUORO X-MAX PROFI / HOMEVAC.

Every capability starts as TBD. Change a state only together with evidence in
``research/`` (and, for VERIFIED, a test on a physical unit recorded in
``docs/supported-models.md``).
"""

from robzone_diag.models.base import Capability, CapabilityState, ModelDefinition, SupportLevel

MODEL = ModelDefinition(
    model_id="duoro-xmax-profi",
    manufacturer="Robzone",
    name="DUORO X-MAX PROFI / HOMEVAC",
    support=SupportLevel.ACTIVE_DEVELOPMENT,
    protocol="HCT Robot LAN protocol, TCP 8888 (identified from app traffic; no client yet)",
    capabilities={capability: CapabilityState.TBD for capability in Capability},
    tested_hardware=(
        "1 unit (maintainer's own). Hardware revision: unknown. Firmware: 7.6.2716(332)."
    ),
    notes=(
        "The only model the maintainer physically owns.",
        "Status, battery, error codes, pose, map and trajectory were seen in the official "
        "app's traffic; they stay TBD until this tool implements and verifies them.",
        "No verified LAN fingerprint yet: discovery reports this model as UNKNOWN.",
    ),
    fingerprint=None,
)
