"""JSON message bodies: building read-only requests and parsing robot reports.

Only messages observed in captures are implemented. Field meanings marked
"inferred" in ``research/protocols/hct-lan-8888.md`` are passed through raw; the
model layer decides how to label enum values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# The "version" string the RobZone app sent in its requests (captured 2026-09-24).
APP_PROTOCOL_VERSION = "5.0.9"

TRANSIT_STATE_QUERY = "98"
TRANSIT_MAP_QUERY = "133"
TRANSIT_MAP_REPLY = "134"
NOTE_STATUS = "102"
NOTE_SESSION = "101"

# Commands this client is allowed to send. Everything else (start, pause, dock, drive,
# settings) is deliberately absent: robzone-diag is read-only.
READ_ONLY_TRANSIT_COMMANDS = frozenset({TRANSIT_STATE_QUERY, TRANSIT_MAP_QUERY})

# Keys that identify the account or the physical unit. Stripped before logging.
SECRET_KEYS = frozenset(
    {"authCode", "targetId", "deviceId", "deviceIp", "userId", "token", "appKey", "clearId"}
)


class MessageError(ValueError):
    pass


@dataclass(frozen=True)
class Credentials:
    host: str
    auth_code: str
    device_id: str
    port: int = 8888


def encode_request(credentials: Credentials, value: dict[str, str]) -> bytes:
    """Serialise a request exactly like the app does (sorted keys, compact separators)."""
    if value.get("transitCmd") not in READ_ONLY_TRANSIT_COMMANDS:
        raise MessageError(f"refusing to send non-read-only command {value.get('transitCmd')!r}")
    document = {
        "cmd": "0",
        "control": {
            "authCode": credentials.auth_code,
            "deviceIp": credentials.host,
            "devicePort": str(credentials.port),
            "targetId": credentials.device_id,
            "targetType": "3",
        },
        "seq": "0",
        "value": value,
        "version": APP_PROTOCOL_VERSION,
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def map_query() -> dict[str, str]:
    """The map/pose query as the app sends it at the start of a session."""
    return {
        "centerPoint": "500,500",
        "mapHeight": "700",
        "mapSign": "AAA=",
        "mapWidth": "700",
        "trackNum": "AAA=",
        "transitCmd": TRANSIT_MAP_QUERY,
    }


def state_query() -> dict[str, str]:
    """State query; seen on the cloud relay, documented as read-only for Sencor robots."""
    return {"opCmd": "state", "transitCmd": TRANSIT_STATE_QUERY}


def decode_body(body: bytes) -> dict[str, Any]:
    try:
        document = json.loads(body.decode("utf-8").rstrip("\x00"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MessageError("frame body is not JSON") from exc
    if not isinstance(document, dict):
        raise MessageError("frame body is not a JSON object")
    return document


def strip_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: strip_secrets(v) for k, v in value.items() if k not in SECRET_KEYS}
    if isinstance(value, list):
        return [strip_secrets(v) for v in value]
    return value


def payload(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("value")
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class StatusReport:
    """``noteCmd`` 102, pushed by the robot on connect and on every state change."""

    work_state: int | None
    work_mode: int | None
    battery: int | None
    error: int | None
    fan: int | None
    brush: int | None
    direction: int | None
    water_tank: int | None
    mop_mode: int | None
    firmware: str | None
    ext: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> StatusReport:
        return cls(
            work_state=_int(value.get("workState")),
            work_mode=_int(value.get("workMode")),
            battery=_int(value.get("battery")),
            error=_int(value.get("error")),
            fan=_int(value.get("fan")),
            brush=_int(value.get("brush")),
            direction=_int(value.get("direction")),
            water_tank=_int(value.get("waterTank")),
            mop_mode=_int(value.get("mopMode")),
            # The cloud relay calls it "version1"; the LAN push calls it "version".
            firmware=value.get("version") or value.get("version1") or None,
            ext=_json_object(value.get("extParam")),
        )

    @property
    def relocalisation_notice(self) -> int | None:
        return _int(self.ext.get("relocaNotice"))


@dataclass(frozen=True)
class MapReport:
    """``transitCmd`` 134: the robot's own pose estimate plus map/track increments."""

    robot_pos: tuple[int, int] | None
    heading_deg: int | None
    map_width: int | None
    map_height: int | None
    empty_map: bool | None
    is_move: int | None
    session: str | None
    clean_area: int | None
    clean_time_s: int | None  # clearTime; grew by 5 per 5 s poll in captures
    uptime_s: int | None
    charger_pos: str | None
    map_b64: str
    track_b64: str

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> MapReport:
        empty = _int(value.get("emptyMap"))
        return cls(
            robot_pos=_point(value.get("robotPos")),
            heading_deg=_int(value.get("deg")),
            map_width=_int(value.get("mapWidth")),
            map_height=_int(value.get("mapHeight")),
            empty_map=None if empty is None else bool(empty),
            is_move=_int(value.get("isMove")),
            session=value.get("clearSign") or None,
            clean_area=_int(value.get("clearArea")),
            clean_time_s=_int(value.get("clearTime")),
            uptime_s=_int(value.get("doTime")),
            charger_pos=value.get("chargerPos") or None,
            map_b64=value.get("map") or "",
            track_b64=value.get("track") or "",
        )


def _int(raw: Any) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _point(raw: Any) -> tuple[int, int] | None:
    parts = str(raw or "").split(",")
    if len(parts) != 2:
        return None
    x, y = _int(parts[0]), _int(parts[1])
    return None if x is None or y is None else (x, y)


def _json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw) if isinstance(raw, str) and raw else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
