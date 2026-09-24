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
    Capability.ERROR_CODES,  # raw code only; meanings unknown for this model
    Capability.POSE,  # robotPos + deg from the map/pose reply
}

# Verified on the maintainer's unit: see docs/supported-models.md for the test.
_VERIFIED = {
    Capability.BATTERY,  # 2026-09-24: status() value matched the RobZone app (57-58 %)
}

MODEL = ModelDefinition(
    model_id="duoro-xmax-profi",
    manufacturer="Robzone",
    name="DUORO X-MAX PROFI / HOMEVAC",
    support=SupportLevel.ACTIVE_DEVELOPMENT,
    protocol=HCT_LAN,
    capabilities={
        capability: CapabilityState.VERIFIED
        if capability in _VERIFIED
        else CapabilityState.EXPERIMENTAL
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
        # Observed: 2 before a cleaning run started and while paused (exp. 02/03),
        # 1 while cleaning (exp. 02), 5 on the dock after "charging started" (exp. 03B).
        # Other values are unknown for this firmware; related robots use different sets.
        "work_state": {1: "cleaning", 2: "idle / standby", 5: "charging"},
        "error": {0: "no error"},
        # extParam.relocaNotice. 2 coincided with the app message "Změna oblasti selhala.
        # Mapa ztracena. Začne nový úklid" (exp. 03E); 1 was set after the robot had been
        # carried while paused (inferred: relocalisation pending).
        "reloca_notice": {
            0: "none",
            1: "robot was moved, relocalisation pending (inferred)",
            2: "relocalisation failed, map lost",
        },
    },
    fingerprint=None,
)
