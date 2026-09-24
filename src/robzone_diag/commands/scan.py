"""``robzone-diag scan``: TCP port scan of one host on the local network."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any

from robzone_diag import redact, report
from robzone_diag.discovery import lan, tcp
from robzone_diag.exitcodes import ExitCode


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "scan",
        help="check which TCP ports are open on one device (e.g. the robot)",
        description=(
            "TCP connect scan of a single host on your local network. Open ports are "
            "reported with any banner the service sends on its own; no data is sent to "
            "the device. Only private (LAN) addresses are accepted."
        ),
        epilog=(
            "Examples:\n"
            "  uv run robzone-diag scan 192.168.1.50\n"
            "  uv run robzone-diag scan 192.168.1.50 --ports all --output captures/scan.json\n"
            "  uv run robzone-diag scan 192.168.1.50 --ports 6668,8000-9000"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host", help="IP address (or hostname) of the device on your LAN")
    parser.add_argument(
        "--ports",
        default="common",
        metavar="SPEC",
        help=(
            f"'common' (default: {len(tcp.COMMON_PORTS)} ports often used by IoT devices), "
            "'all' (1-65535, can take 10+ minutes), or a list such as 22,80,6000-7000"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=tcp.DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"per-port timeout (default: {tcp.DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=tcp.DEFAULT_WORKERS,
        help=(
            f"parallel connections (default: {tcp.DEFAULT_WORKERS}; small devices drop "
            "connections when this is high, making open ports look silent)"
        ),
    )
    parser.add_argument("--no-banner", action="store_true", help="do not wait for service banners")
    parser.add_argument("--redact", action="store_true", help="mask the MAC address in output")
    parser.add_argument("--json", action="store_true", help="print the full JSON report to stdout")
    parser.add_argument("--output", type=Path, metavar="FILE", help="save the JSON report to FILE")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        ports = tcp.parse_port_spec(args.ports)
    except ValueError as exc:
        print(f"error: --ports: {exc}", file=sys.stderr)
        return ExitCode.USAGE
    try:
        ip = socket.gethostbyname(args.host)
    except OSError as exc:
        print(f"error: cannot resolve '{args.host}': {exc}", file=sys.stderr)
        return ExitCode.ERROR
    if not lan.is_private_address(ip):
        print(
            f"error: {ip} is not a private LAN address; this tool only scans your own network",
            file=sys.stderr,
        )
        return ExitCode.USAGE

    print(
        f"Scanning {len(ports)} TCP port(s) on {ip} (timeout {args.timeout:g} s) ...",
        file=sys.stderr,
    )
    try:
        results = tcp.scan(ip, ports, args.timeout, args.workers, not args.no_banner)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return ExitCode.INTERRUPTED
    mac = next((n.mac for n in lan.read_neighbour_table() if n.ip == ip), None)

    document = report.envelope(
        "scan",
        {"host": ip, "ports": args.ports, "port_count": len(ports), "timeout_s": args.timeout},
        _results(ip, redact.mac(mac) if args.redact else mac, results),
    )
    if args.output:
        report.write_json(args.output, document)
    if args.json:
        print(json.dumps(document, indent=2))
    else:
        print(render(ip, redact.mac(mac) if args.redact else mac, results))
    if args.output:
        print(f"Report saved to {args.output}", file=sys.stderr)
    return ExitCode.OK


def _count(results: list[tcp.PortResult], state: tcp.PortState) -> int:
    return sum(1 for r in results if r.state is state)


def render(ip: str, mac: str | None, results: list[tcp.PortResult]) -> str:
    open_ports = [r for r in results if r.state is tcp.PortState.OPEN]
    lines = ["", f"Host: {ip}   MAC: {mac or 'unknown'}", "", "Open TCP ports:"]
    for result in open_ports:
        hint = tcp.PORT_HINTS.get(result.port, "no common use known")
        lines.append(f"  {result.port:>5}/tcp   conventionally: {hint}")
        if result.banner:
            lines.append(f"             banner: {_printable(result.banner)}")
    if not open_ports:
        lines.append("  none")
    closed = _count(results, tcp.PortState.CLOSED)
    filtered = _count(results, tcp.PortState.FILTERED)
    lines += ["", f"Closed (refused): {closed}   No answer (filtered): {filtered}"]
    if not open_ports and not closed:
        lines.append(
            "No port answered at all: the host may be offline, asleep, on another network, "
            "or dropping connections. Check the IP and that the robot is on Wi-Fi."
        )
    lines.append(
        "Port names are conventions only; what actually runs there is unverified until examined."
    )
    return "\n".join(lines)


def _printable(data: bytes) -> str:
    text = data.decode("ascii", errors="replace")
    return "".join(ch if ch.isprintable() else "." for ch in text)[:120]


def _results(ip: str, mac: str | None, results: list[tcp.PortResult]) -> dict[str, Any]:
    return {
        "host": ip,
        "mac": mac,
        "open": [
            {
                "port": r.port,
                "hint": tcp.PORT_HINTS.get(r.port),
                "banner_hex": r.banner.hex() if r.banner else None,
            }
            for r in results
            if r.state is tcp.PortState.OPEN
        ],
        "closed_count": _count(results, tcp.PortState.CLOSED),
        "filtered_count": _count(results, tcp.PortState.FILTERED),
    }
