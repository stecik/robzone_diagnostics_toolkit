"""Model definitions: what a model integration claims, and how verified the claims are."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from robzone_diag.discovery.hosts import HostRecord


class SupportLevel(StrEnum):
    ACTIVE_DEVELOPMENT = "Active development"
    EXPERIMENTAL = "Experimental"
    SUPPORTED = "Supported"


class Capability(StrEnum):
    """A kind of data a model integration may expose. Diagnostics declare what they need."""

    DISCOVERY = "discovery"
    DEVICE_INFO = "device_info"
    STATUS = "status"
    BATTERY = "battery"
    ERROR_CODES = "error_codes"
    DOCKING_STATUS = "docking_status"
    POSE = "pose"
    MAP = "map"
    TRAJECTORY = "trajectory"
    LIDAR_STATUS = "lidar_status"
    LIDAR_RAW_SCAN = "lidar_raw_scan"
    WHEEL_ODOMETRY = "wheel_odometry"
    WHEEL_ENCODER_RAW = "wheel_encoder_raw"
    IMU = "imu"


CAPABILITY_LABELS: Mapping[Capability, str] = {
    Capability.DISCOVERY: "LAN discovery / identification",
    Capability.DEVICE_INFO: "Device info (firmware, hardware)",
    Capability.STATUS: "Status telemetry",
    Capability.BATTERY: "Battery",
    Capability.ERROR_CODES: "Error codes",
    Capability.DOCKING_STATUS: "Docking status",
    Capability.POSE: "Reported position / heading",
    Capability.MAP: "Map data",
    Capability.TRAJECTORY: "Trajectory",
    Capability.LIDAR_STATUS: "LiDAR status",
    Capability.LIDAR_RAW_SCAN: "LiDAR raw scan",
    Capability.WHEEL_ODOMETRY: "Wheel odometry",
    Capability.WHEEL_ENCODER_RAW: "Wheel encoder raw data",
    Capability.IMU: "IMU (gyroscope / accelerometer)",
}


class CapabilityState(StrEnum):
    """How far an integration's claim about a capability has been established."""

    TBD = "TBD"  # not investigated yet
    EXPERIMENTAL = "Experimental"  # implemented, not yet verified on a physical device
    VERIFIED = "Verified"  # implemented and verified on a physical device
    UNSUPPORTED = "Unsupported"  # confirmed not exposed by this integration


CAPABILITY_STATE_MEANING: Mapping[CapabilityState, str] = {
    CapabilityState.TBD: "not investigated yet",
    CapabilityState.EXPERIMENTAL: "implemented, not yet verified on a physical device",
    CapabilityState.VERIFIED: "implemented and verified on a physical device",
    CapabilityState.UNSUPPORTED: "confirmed not exposed by this model integration",
}


@dataclass(frozen=True)
class ModelDefinition:
    model_id: str
    manufacturer: str
    name: str
    support: SupportLevel
    protocol: str | None  # protocol ID from robzone_diag.protocols.PROTOCOLS; None = unknown
    capabilities: Mapping[Capability, CapabilityState]
    tested_hardware: str
    notes: tuple[str, ...] = ()
    # Human-readable meanings of model-specific enum values, e.g.
    # {"work_state": {1: "cleaning"}}. Only values actually observed on this model.
    labels: Mapping[str, Mapping[int, str]] = field(default_factory=dict)
    # Returns True only on strong evidence that a discovered host is this model.
    # None means no verified fingerprint exists yet, so the model is never auto-detected.
    fingerprint: Callable[[HostRecord], bool] | None = field(default=None, compare=False)

    def state(self, capability: Capability) -> CapabilityState:
        return self.capabilities.get(capability, CapabilityState.TBD)

    def label(self, kind: str, value: int | None) -> str | None:
        return None if value is None else self.labels.get(kind, {}).get(value)
