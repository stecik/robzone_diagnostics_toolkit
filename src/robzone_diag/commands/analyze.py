"""``robzone-diag analyze``: measurements computed from a ``monitor`` log."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from robzone_diag.analysis.heading import PoseSample, StationarySegment, stationary_segments
from robzone_diag.exitcodes import ExitCode


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "analyze",
        help="compute measurements (e.g. heading drift at standstill) from a monitor log",
        description=(
            "Read a JSONL log written by 'monitor' and report measurements. Currently: "
            "for every stretch where the reported position does not change, how fast the "
            "reported heading changes. Offline; does not contact the robot."
        ),
        epilog="Example: uv run robzone-diag analyze captures/run.jsonl",
    )
    parser.add_argument("log", type=Path, help="JSONL file written by 'robzone-diag monitor'")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        samples = load_pose_samples(args.log)
    except OSError as exc:
        print(f"error: cannot read {args.log}: {exc}", file=sys.stderr)
        return ExitCode.ERROR
    segments = stationary_segments(samples)
    if args.json:
        print(json.dumps([_as_dict(s) for s in segments], indent=2))
    else:
        print(render(samples, segments))
    return ExitCode.OK if segments else ExitCode.NOT_FOUND


def load_pose_samples(path: Path) -> list[PoseSample]:
    samples: list[PoseSample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        pose = record.get("pose") if record.get("kind") == "map" else None
        if not pose:
            continue
        position = tuple(pose["robot_pos"]) if pose.get("robot_pos") else None
        samples.append(PoseSample(record.get("elapsed_s", 0.0), position, pose.get("heading_deg")))
    return samples


def render(samples: list[PoseSample], segments: list[StationarySegment]) -> str:
    lines = [
        "",
        f"Pose samples: {len(samples)}",
        "",
        "Heading while the reported position is constant:",
    ]
    if not segments:
        lines.append("  no stationary stretch of 5+ samples found")
    for s in segments:
        lines += [
            f"  position {s.position}, {s.duration_s:.0f} s, {s.samples} samples:",
            f"      heading changes {s.rate_deg_per_s:+.2f} °/s "
            f"({s.rate_deg_per_s * 60:+.0f} °/min), {s.total_change_deg:+.0f}° in total; "
            f"linear within ±{s.max_residual_deg:.1f}°",
        ]
    lines += [
        "",
        "Interpretation: a robot that is physically still should report a nearly constant",
        "heading. A steady change points at the heading estimate (e.g. gyroscope bias), but",
        "first confirm the robot really did not move. No pass/fail threshold is applied yet.",
    ]
    return "\n".join(lines)


def _as_dict(segment: StationarySegment) -> dict:
    return {
        "position": list(segment.position),
        "start_s": segment.start_s,
        "end_s": segment.end_s,
        "samples": segment.samples,
        "rate_deg_per_s": round(segment.rate_deg_per_s, 4),
        "total_change_deg": round(segment.total_change_deg, 1),
        "max_residual_deg": round(segment.max_residual_deg, 2),
    }
