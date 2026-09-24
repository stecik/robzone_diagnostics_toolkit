"""``robzone-diag status``: one read-only snapshot of the robot's state and pose."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from robzone_diag import report
from robzone_diag.commands import _robot
from robzone_diag.config import ConfigError
from robzone_diag.exitcodes import ExitCode
from robzone_diag.models.base import ModelDefinition
from robzone_diag.models.registry import UnknownModelError
from robzone_diag.protocols.hct import messages
from robzone_diag.protocols.hct.client import HctClient, HctConnectionError, Received

STATUS_WAIT_S = 3.0


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "status",
        help="read the robot's current state, battery, error code and reported position",
        description=(
            "Connect to the robot on the local network (TCP 8888) and read one snapshot: "
            "state, battery, error code, firmware and the robot's own position estimate. "
            "Read-only: only a keepalive ping and read-only queries are sent. Close the "
            "RobZone app first; the robot may serve one client at a time."
        ),
    )
    _robot.add_arguments(parser)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        model, credentials = _robot.resolve(args)
    except (ConfigError, _robot.RobotSetupError, UnknownModelError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return ExitCode.USAGE
    try:
        status, pose = read_snapshot(HctClient(credentials, args.timeout))
    except (HctConnectionError, TimeoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(_connection_hint(), file=sys.stderr)
        return ExitCode.ERROR
    if args.json:
        results = {"status": _raw(status), "pose": _raw(pose)}
        print(json.dumps(report.envelope("status", {"host": credentials.host}, results), indent=2))
    else:
        print(render(model, status, pose))
    return ExitCode.OK if status or pose else ExitCode.NOT_FOUND


def read_snapshot(client: HctClient) -> tuple[Received | None, Received | None]:
    with client:
        client.ping()
        status = client.wait_for("status", STATUS_WAIT_S)
        if status is None:
            client.send_query(messages.state_query())
            status = client.wait_for("status", STATUS_WAIT_S)
        pose = client.request(messages.map_query())
    return status, pose


def render(model: ModelDefinition | None, status: Received | None, pose: Received | None) -> str:
    lines = [""]
    if status:
        s = messages.StatusReport.from_value(status.value)
        lines += [
            f"State:            {_robot.label(model, 'work_state', s.work_state)}",
            f"Battery:          {s.battery if s.battery is not None else '?'} %",
            f"Error code:       {_robot.label(model, 'error', s.error)}",
            f"Firmware:         {s.firmware or 'not reported'}",
            f"Relocalisation:   {_robot.label(model, 'reloca_notice', s.relocalisation_notice)}",
        ]
    else:
        lines.append("State:            no status report received")
    if pose:
        p = messages.MapReport.from_value(pose.value)
        position = f"x={p.robot_pos[0]}, y={p.robot_pos[1]}" if p.robot_pos else "not reported"
        lines += [
            f"Reported position: {position} (map cells, robot's own estimate)",
            f"Reported heading:  {_value(p.heading_deg)}°",
            f"Map:               {p.map_width}x{p.map_height} cells, "
            f"{'empty' if p.empty_map else 'has data'}, session {p.session or '?'}",
        ]
    return "\n".join(lines)


def _value(value: Any) -> str:
    return "?" if value is None else str(value)


def _raw(received: Received | None) -> dict[str, Any] | None:
    if received is None:
        return None
    value = messages.strip_secrets(received.value)
    return {k: v for k, v in value.items() if k not in ("map", "track")}


def _connection_hint() -> str:
    return (
        "Check: the robot is on and its Wi-Fi LED is solid blue; ROBZONE_DIAG_HOST is its "
        "current IP; the RobZone app is closed (the robot may accept one client at a time)."
    )
