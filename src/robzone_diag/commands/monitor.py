"""``robzone-diag monitor``: log the robot's state and pose over time to JSONL."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from robzone_diag.commands import _robot
from robzone_diag.config import ConfigError
from robzone_diag.exitcodes import ExitCode
from robzone_diag.models.base import ModelDefinition
from robzone_diag.models.registry import UnknownModelError
from robzone_diag.protocols.hct import messages
from robzone_diag.protocols.hct.client import HctClient, HctConnectionError, Received

PING_INTERVAL_S = 10.0  # the app pinged roughly every 10 s
RECONNECT_DELAY_S = 5.0
RECORD_SCHEMA = 1


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "monitor",
        help="log state, battery, errors and the robot's reported position over time",
        description=(
            "Poll the robot's map/pose report every few seconds (like the app does) and "
            "log every message to a JSONL file for later analysis. Read-only. Reconnects "
            "automatically. Close the RobZone app while monitoring. Stop with Ctrl+C."
        ),
        epilog="Example: uv run robzone-diag monitor --output captures/run.jsonl",
    )
    _robot.add_arguments(parser)
    parser.add_argument(
        "--output", type=Path, metavar="FILE", help="append records to this JSONL file"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="seconds between pose queries (default: 5, as the app)",
    )
    parser.add_argument(
        "--duration", type=float, metavar="SECONDS", help="stop after this long (default: never)"
    )
    parser.add_argument(
        "--no-map",
        action="store_true",
        help="do not store raw map/trajectory data (it describes your home's floor plan)",
    )
    parser.set_defaults(handler=run)


@dataclass
class Summary:
    started: float = field(default_factory=time.monotonic)
    queries: int = 0
    pose_reports: int = 0
    status_reports: int = 0
    disconnects: int = 0
    errors_seen: set[int] = field(default_factory=set)
    reloc_notices: int = 0
    work_states: list[int] = field(default_factory=list)


def run(args: argparse.Namespace) -> int:
    if args.interval <= 0 or (args.duration is not None and args.duration <= 0):
        print("error: --interval and --duration must be positive", file=sys.stderr)
        return ExitCode.USAGE
    try:
        model, credentials = _robot.resolve(args)
    except (ConfigError, _robot.RobotSetupError, UnknownModelError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return ExitCode.USAGE

    output = args.output.open("a", encoding="utf-8") if args.output else None
    summary = Summary()
    recorder = Recorder(output, model, summary, keep_map=not args.no_map)
    print(
        f"Monitoring {credentials.host} every {args.interval:g} s. Ctrl+C to stop.", file=sys.stderr
    )
    try:
        _monitor(HctClient(credentials, args.timeout), args, recorder, summary)
    except KeyboardInterrupt:
        recorder.event("stopped", "Ctrl+C")
    finally:
        if output:
            output.close()
    print(render_summary(summary, args.output))
    return ExitCode.OK if summary.pose_reports or summary.status_reports else ExitCode.NOT_FOUND


def _monitor(client: HctClient, args, recorder: Recorder, summary: Summary) -> None:
    deadline = time.monotonic() + args.duration if args.duration else float("inf")
    while time.monotonic() < deadline:
        try:
            client.connect()
            recorder.event("connected", client.credentials.host)
            _session(client, args.interval, deadline, recorder, summary)
        except HctConnectionError as exc:
            summary.disconnects += 1
            recorder.event("disconnected", str(exc))
            time.sleep(min(RECONNECT_DELAY_S, max(0.0, deadline - time.monotonic())))
        finally:
            client.close()


def _session(client, interval, deadline, recorder: Recorder, summary: Summary) -> None:
    next_ping = next_query = time.monotonic()
    while (now := time.monotonic()) < deadline:
        if now >= next_ping:
            client.ping()
            next_ping = now + PING_INTERVAL_S
        if now >= next_query:
            client.send_query(messages.map_query())
            summary.queries += 1
            next_query = now + interval
        wait = max(0.0, min(next_ping, next_query, deadline) - time.monotonic())
        for received in client.drain(wait=min(wait, 1.0)):
            recorder.record(received)


class Recorder:
    """Writes one JSON line per message and prints a short human-readable line."""

    def __init__(
        self,
        output: IO[str] | None,
        model: ModelDefinition | None,
        summary: Summary,
        keep_map: bool,
    ) -> None:
        self.output, self.model, self.summary, self.keep_map = output, model, summary, keep_map

    def event(self, name: str, detail: str) -> None:
        self._write({"kind": "event", "event": name, "detail": detail})
        print(f"{_clock()}  [{name}] {detail}", file=sys.stderr)

    def record(self, received: Received) -> None:
        kind = received.kind
        if kind in ("ping-ack", "ping"):
            return
        raw = messages.strip_secrets(received.value)
        if not self.keep_map:
            raw = {k: v for k, v in raw.items() if k not in ("map", "track")}
        entry: dict[str, Any] = {"kind": kind, "frame": received.frame.type_name, "raw": raw}
        if kind == "status":
            status = messages.StatusReport.from_value(received.value)
            entry["status"] = _status_dict(status)
            self._on_status(status)
        elif kind == "map":
            pose = messages.MapReport.from_value(received.value)
            entry["pose"] = _pose_dict(pose)
            self._on_pose(pose)
        self._write(entry, received.at)

    def _on_status(self, status: messages.StatusReport) -> None:
        s = self.summary
        reloc = status.relocalisation_notice
        s.status_reports += 1
        if status.error:
            s.errors_seen.add(status.error)
        if status.relocalisation_notice:
            s.reloc_notices += 1
        if status.work_state is not None and (
            not s.work_states or s.work_states[-1] != status.work_state
        ):
            s.work_states.append(status.work_state)
        print(
            f"{_clock()}  status: {_robot.label(self.model, 'work_state', status.work_state)}, "
            f"battery {status.battery}%, error {_robot.label(self.model, 'error', status.error)}, "
            f"relocalisation {_robot.label(self.model, 'reloca_notice', reloc)}",
            file=sys.stderr,
        )

    def _on_pose(self, pose: messages.MapReport) -> None:
        self.summary.pose_reports += 1
        position = f"({pose.robot_pos[0]},{pose.robot_pos[1]})" if pose.robot_pos else "(none)"
        print(
            f"{_clock()}  pose {position:>11} heading {pose.heading_deg}°  "
            f"area {pose.clean_area}  time {pose.clean_time_s} s  "
            f"map {len(pose.map_b64)} B  track {len(pose.track_b64)} B",
            file=sys.stderr,
        )

    def _write(self, entry: dict[str, Any], at: float | None = None) -> None:
        if not self.output:
            return
        stamp = datetime.fromtimestamp(at or time.time(), UTC).isoformat(timespec="milliseconds")
        line = {
            "schema": RECORD_SCHEMA,
            "t": stamp,
            "elapsed_s": round(time.monotonic() - self.summary.started, 3),
            **entry,
        }
        self.output.write(json.dumps(line, ensure_ascii=False) + "\n")
        self.output.flush()


def _status_dict(status: messages.StatusReport) -> dict[str, Any]:
    data = asdict(status)
    data["relocalisation_notice"] = status.relocalisation_notice
    return data


def _pose_dict(pose: messages.MapReport) -> dict[str, Any]:
    data = asdict(pose)
    data.pop("map_b64")
    data.pop("track_b64")
    data["map_b64_len"], data["track_b64_len"] = len(pose.map_b64), len(pose.track_b64)
    return data


def _clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


def render_summary(summary: Summary, output: Path | None) -> str:
    elapsed = time.monotonic() - summary.started
    lines = [
        "",
        f"Monitored for {elapsed:.0f} s",
        f"  Pose reports:     {summary.pose_reports} of {summary.queries} queries answered",
        f"  Status reports:   {summary.status_reports}",
        f"  Work states seen: {', '.join(map(str, summary.work_states)) or 'none'}",
        f"  Error codes seen: {', '.join(map(str, sorted(summary.errors_seen))) or 'none'}",
        f"  relocaNotice > 0: {summary.reloc_notices} time(s)",
        f"  Disconnects:      {summary.disconnects}",
    ]
    if output:
        lines.append(f"  Log:              {output} (contains your map; keep it private)")
    return "\n".join(lines)
