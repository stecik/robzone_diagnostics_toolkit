"""``robzone-diag import-credentials``: take the robot's LAN credentials from a capture.

The RobZone app sends ``authCode``, the robot's IP and its device ID in plain JSON to
TCP 8888. They appear verbatim in a packet capture of the app (e.g. PCAPdroid), so a
byte search is enough; no pcap parsing library is needed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from robzone_diag import config
from robzone_diag.exitcodes import ExitCode

_REQUEST = re.compile(
    rb'"control":\{"authCode":"([A-Za-z0-9]+)","deviceIp":"([0-9.]+)","devicePort":"8888",'
    rb'"targetId":"([A-Za-z0-9]+)","targetType":"3"\}'
)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "import-credentials",
        help="read the robot's LAN credentials from a capture of the RobZone app",
        description=(
            "Search a packet capture (e.g. a PCAPdroid .pcap of the RobZone app) for the "
            "app's requests to the robot on TCP 8888 and store the robot's IP, auth code "
            "and device ID in the .env file. Values are printed masked. The capture itself "
            "is not modified or uploaded anywhere."
        ),
        epilog="Example: uv run robzone-diag import-credentials captures/app.pcap",
    )
    parser.add_argument("capture", type=Path, help="capture file (.pcap / .pcapng)")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=config.DEFAULT_ENV_FILE,
        metavar="FILE",
        help="settings file to update (default: .env)",
    )
    parser.add_argument(
        "--model",
        default="duoro-xmax-profi",
        metavar="MODEL_ID",
        help="model ID to store as ROBZONE_DIAG_MODEL (default: duoro-xmax-profi)",
    )
    parser.set_defaults(handler=run)


def find_credentials(data: bytes) -> set[tuple[str, str, str]]:
    """Distinct (host, auth_code, device_id) triples found in app requests."""
    return {
        (ip.decode(), auth.decode(), device.decode()) for auth, ip, device in _REQUEST.findall(data)
    }


def update_env_text(text: str, values: dict[str, str]) -> str:
    """Replace or append ``KEY=value`` lines, keeping everything else unchanged."""
    lines = text.splitlines()
    remaining = dict(values)
    for i, line in enumerate(lines):
        key = line.partition("=")[0].strip()
        if key in remaining:
            lines[i] = f"{key}={remaining.pop(key)}"
    if remaining and not text:
        lines.append("# Local secrets for robzone-diag. Gitignored. Never commit or share.")
    lines += [f"{k}={v}" for k, v in remaining.items()]
    return "\n".join(lines) + "\n"


def mask(value: str) -> str:
    return value[:2] + "*" * max(0, len(value) - 2)


def run(args: argparse.Namespace) -> int:
    try:
        data = args.capture.read_bytes()
    except OSError as exc:
        print(f"error: cannot read {args.capture}: {exc}", file=sys.stderr)
        return ExitCode.ERROR
    found = find_credentials(data)
    if not found:
        print(
            "No RobZone app request to TCP 8888 found in this capture. Capture while the app "
            "is open on the same Wi-Fi as the robot and shows the robot's map.",
            file=sys.stderr,
        )
        return ExitCode.NOT_FOUND
    if len(found) > 1:
        print(
            f"error: {len(found)} different robots/credentials found; capture one robot only",
            file=sys.stderr,
        )
        return ExitCode.ERROR
    host, auth_code, device_id = found.pop()
    values = {
        config.PREFIX + "HOST": host,
        config.PREFIX + "AUTH_CODE": auth_code,
        config.PREFIX + "DEVICE_ID": device_id,
        config.PREFIX + "MODEL": args.model,
    }
    existing = args.env_file.read_text(encoding="utf-8") if args.env_file.is_file() else ""
    args.env_file.write_text(update_env_text(existing, values), encoding="utf-8")
    print(f"Robot IP:  {host}")
    print(f"Auth code: {mask(auth_code)}")
    print(f"Device ID: {mask(device_id)}")
    print(f"Saved to {args.env_file}. Keep this file private (it is gitignored).")
    return ExitCode.OK
