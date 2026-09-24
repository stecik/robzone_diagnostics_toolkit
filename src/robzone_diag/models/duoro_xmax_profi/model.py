"""Robzone DUORO X-MAX PROFI / HOMEVAC.

Change a capability state only together with evidence in ``research/`` (and, for
VERIFIED, a test on a physical unit recorded in ``docs/supported-models.md``).
"""

from robzone_diag.models.base import Capability, CapabilityState, ModelDefinition, SupportLevel
from robzone_diag.protocols.hct import PROTOCOL_ID as HCT_LAN

# Implemented by the HCT LAN client (status/monitor) but not yet verified on hardware.
_EXPERIMENTAL = {
    Capability.DEVICE_INFO,  # firmware version in the status push
    Capability.STATUS,
    Capability.BATTERY,
    Capability.ERROR_CODES,  # raw code only; meanings unknown for this model
    Capability.POSE,  # robotPos + deg from the map/pose reply
}

MODEL = ModelDefinition(
    model_id="duoro-xmax-profi",
    manufacturer="Robzone",
    name="DUORO X-MAX PROFI / HOMEVAC",
    support=SupportLevel.ACTIVE_DEVELOPMENT,
    protocol=HCT_LAN,
    capabilities={
        capability: CapabilityState.EXPERIMENTAL
        if capability in _EXPERIMENTAL
        else CapabilityState.TBD
        for capability in Capability
    },
    tested_hardware=(
        "1 unit (maintainer's own). Hardware revision: unknown. Firmware: 7.6.2716(332)."
    ),
    notes=(
        "The only model the maintainer physically owns.",
        "Map and trajectory are logged raw by 'monitor' but not decoded yet.",
        "No raw LiDAR, wheel encoder or IMU data was seen in the LAN protocol.",
        "No verified LAN fingerprint yet: discovery reports this model as UNKNOWN.",
    ),
    labels={
        # Observed in experiment 02: 2 before a cleaning run started, 1 while cleaning.
        # Other values are unknown for this firmware; related robots use different sets.
        "work_state": {1: "cleaning", 2: "idle / standby"},
        "error": {0: "no error"},
    },
    fingerprint=None,
)
