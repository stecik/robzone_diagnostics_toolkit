"""``robzone-diag discover``: find devices on the LAN, passively by default."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from robzone_diag import redact, report
from robzone_diag.discovery import lan, udp
from robzone_diag.discovery.hosts import HostRecord, build_host_records
from robzone_diag.exitcodes import ExitCode
from robzone_diag.models.registry import identify
from robzone_diag.protocols.tuya import broadcast as tuya

log = logging.getLogger(__name__)

TUYA_REQUEST_INTERVAL = 6.0  # same cadence as TinyTuya's scanner


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "discover",
        help="find devices on the local network (passive by default)",
        description=(
            "Listen for UDP broadcasts on the local network, decode known formats "
            "(currently Tuya LAN discovery), and list the hosts in this computer's "
            "ARP table. The only traffic sent is one empty UDP datagram to each host that "
            "broadcast (so the OS learns its MAC address via ARP; skip with --no-arp) and, "
            "if --tuya-request is given, the standard Tuya discovery request."
        ),
        epilog="Example: uv run robzone-diag discover --duration 60 --output captures/d.json",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="how long to listen for broadcasts (default: 30)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        action="append",
        default=[],
        metavar="PORT",
        help="also listen on this UDP port (repeatable)",
    )
    parser.add_argument(
        "--tuya-request",
        action="store_true",
        help=(
            "every 6 s, broadcast the standard Tuya discovery request to UDP 7000 "
            "(the same request the Tuya/Smart Life app sends; needed for protocol 3.5 devices)"
        ),
    )
    parser.add_argument(
        "--no-arp", action="store_true", help="do not read the ARP table or resolve MAC addresses"
    )
    parser.add_argument(
        "--no-resolve", action="store_true", help="do not look up hostnames via reverse DNS"
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="mask MAC addresses, hostnames and device IDs (for sharing output publicly)",
    )
    parser.add_argument("--json", action="store_true", help="print the full JSON report to stdout")
    parser.add_argument("--output", type=Path, metavar="FILE", help="save the JSON report to FILE")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    if args.duration <= 0:
        print("error: --duration must be positive", file=sys.stderr)
        return ExitCode.USAGE
    local_addresses = lan.local_ipv4_addresses()
    ports = sorted(set(tuya.DISCOVERY_PORTS) | set(args.udp_port))
    periodic = _tuya_request(local_addresses) if args.tuya_request else None
    if args.tuya_request and periodic is None:
        print("error: no local IPv4 address found; cannot send --tuya-request", file=sys.stderr)
        return ExitCode.ERROR

    _progress(f"Listening for UDP broadcasts on ports {_join(ports)} for {args.duration:g} s ...")
    _progress("(Ctrl+C stops early and still prints what was found.)")
    heard: set[str] = set()
    listened = udp.listen(
        ports,
        args.duration,
        periodic,
        on_datagram=lambda d: _announce(d, heard),
        on_tick=lambda elapsed, count: _progress(
            f"  ... {elapsed:.0f}/{args.duration:g} s, {count} datagram(s) so far"
        ),
    )
    if listened.interrupted:
        _progress(f"Interrupted after {listened.listened_s:.0f} s; showing what was found.")
    if not listened.bound_ports:
        print("error: could not listen on any UDP port (see messages above)", file=sys.stderr)
        return ExitCode.ERROR

    if not args.no_arp:
        lan.prime_arp_cache(_broadcaster_ips(listened.datagrams, local_addresses))
    neighbours = [] if args.no_arp else lan.read_neighbour_table()
    records = build_host_records(neighbours, listened.datagrams, local_addresses)
    if not args.no_resolve:
        for ip, name in lan.reverse_lookup([r.ip for r in records]).items():
            next(r for r in records if r.ip == ip).hostname = name

    document = report.envelope(
        "discover",
        _parameters(args, ports),
        _results(records, listened, local_addresses, args.redact),
    )
    if args.output:
        report.write_json(args.output, document)
    if args.json:
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        print(render(records, listened, local_addresses, args))
    if args.output:
        _progress(f"Report saved to {args.output}")
    if listened.interrupted:
        return ExitCode.INTERRUPTED
    return ExitCode.OK if records else ExitCode.NOT_FOUND


def _tuya_request(local_addresses: list[str]) -> udp.PeriodicSend | None:
    if not local_addresses:
        return None
    source = local_addresses[0]
    payload = tuya.build_devinfo_request(source)
    return udp.PeriodicSend(
        payload, ("255.255.255.255", tuya.PORT_APP), source, TUYA_REQUEST_INTERVAL
    )


def _broadcaster_ips(datagrams: list[udp.Datagram], local_addresses: list[str]) -> list[str]:
    return sorted({d.source_ip for d in datagrams} - set(local_addresses))


def _announce(datagram: udp.Datagram, heard: set[str]) -> None:
    key = f"{datagram.source_ip}:{datagram.local_port}"
    if key not in heard:
        heard.add(key)
        _progress(f"  heard {datagram.source_ip} on UDP {datagram.local_port}")


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _join(values) -> str:
    return ", ".join(str(v) for v in values)


# ---------------------------------------------------------------- human output


def render(
    records: list[HostRecord],
    listened: udp.ListenResult,
    local_addresses: list[str],
    args: argparse.Namespace,
) -> str:
    broadcasters = [r for r in records if r.broadcast_count]
    quiet = [r for r in records if not r.broadcast_count]
    lines = [
        "",
        f"This computer:        {_join(local_addresses) or 'no IPv4 address found'}",
        f"Listened on UDP:      {_join(listened.bound_ports)} for {listened.listened_s:.0f} s"
        + (" (interrupted)" if listened.interrupted else ""),
        f"Tuya request sent:    {'yes' if args.tuya_request else 'no (add --tuya-request)'}",
    ]
    for port, error in sorted(listened.bind_errors.items()):
        lines.append(f"Could not listen on UDP {port}: {error}")
    lines += ["", "Hosts that sent broadcasts:"]
    lines += [line for r in broadcasters for line in _render_broadcaster(r, args.redact)] or [
        "  none heard"
    ]
    lines += ["", f"Other hosts in this computer's ARP table (no broadcasts heard): {len(quiet)}"]
    lines += [f"  {_host_line(r, args.redact)}" for r in quiet]
    lines += ["", _summary(records, broadcasters), "", *_next_steps(broadcasters)]
    return "\n".join(lines)


def _render_broadcaster(record: HostRecord, redacted: bool) -> list[str]:
    lines = [f"  {_host_line(record, redacted)}"]
    udp_sources = sorted(s.replace("udp:", "UDP ") for s in record.sources if s.startswith("udp:"))
    lines.append(f"      Broadcasts: {record.broadcast_count} on {_join(udp_sources)}")
    for announcement in record.tuya_announcements:
        lines.append(f"      Tuya announcement: {_describe_tuya(announcement, redacted)}")
    if record.tuya_app_requests:
        lines.append(
            f"      Sent {record.tuya_app_requests} Tuya discovery request(s): "
            "a Tuya-based app runs on this host (e.g. a phone)"
        )
    if record.undecoded_datagrams:
        lines.append(
            f"      Undecoded datagrams kept for analysis: {len(record.undecoded_datagrams)}"
        )
    lines.append(f"      Model: {_describe_model(record)}")
    return lines


def _host_line(record: HostRecord, redacted: bool) -> str:
    mac = (redact.mac(record.mac) if redacted else record.mac) or "MAC unknown"
    if record.mac and lan.is_locally_administered(record.mac):
        mac += " (randomised)"
    name = (redact.hostname(record.hostname) if redacted else record.hostname) or ""
    return f"{record.ip:<15}  {mac:<30}  {name}".rstrip()


def _describe_tuya(announcement: dict[str, Any], redacted: bool) -> str:
    data = redact.payload(announcement) if redacted else announcement
    parts = [
        f"protocol {data.get('version', '?')}",
        "encrypted broadcast" if data.get("encrypted") else "plain broadcast",
        f"device ID {data.get('gwId', '?')}",
        f"product key {data.get('productKey', '?')}",
    ]
    return ", ".join(parts)


def _describe_model(record: HostRecord) -> str:
    matches = identify(record)
    if len(matches) == 1:
        return f"{matches[0].manufacturer} {matches[0].name} (support: {matches[0].support})"
    if matches:
        return "AMBIGUOUS: " + ", ".join(m.model_id for m in matches)
    return "UNKNOWN (no verified fingerprint matches; see: robzone-diag models)"


def _summary(records: list[HostRecord], broadcasters: list[HostRecord]) -> str:
    tuya_hosts = sum(1 for r in records if r.speaks_tuya)
    return (
        f"Summary: {len(records)} host(s) seen, {len(broadcasters)} sent broadcasts, "
        f"{tuya_hosts} sent Tuya device announcements."
    )


def _next_steps(broadcasters: list[HostRecord]) -> list[str]:
    lines = [
        "Next steps:",
        "  1. Identify your robot's IP: router DHCP client list, or device info in the app.",
        "  2. Scan its TCP ports:  uv run robzone-diag scan <robot-ip>",
    ]
    if not any(r.speaks_tuya for r in broadcasters):
        lines.append(
            "  No Tuya announcements heard. That alone does not rule out Tuya: "
            "try again with --tuya-request, and see README troubleshooting."
        )
    return lines


# ---------------------------------------------------------------- JSON output


def _parameters(args: argparse.Namespace, ports: list[int]) -> dict[str, Any]:
    return {
        "duration_s": args.duration,
        "udp_ports": ports,
        "tuya_request": args.tuya_request,
        "arp": not args.no_arp,
        "resolve": not args.no_resolve,
        "redacted": args.redact,
    }


def _results(
    records: list[HostRecord],
    listened: udp.ListenResult,
    local_addresses: list[str],
    redacted: bool,
) -> dict[str, Any]:
    return {
        "local_addresses": local_addresses,
        "bound_udp_ports": listened.bound_ports,
        "udp_bind_errors": {str(k): v for k, v in listened.bind_errors.items()},
        "listened_s": round(listened.listened_s, 1),
        "interrupted": listened.interrupted,
        "datagrams_received": len(listened.datagrams),
        "hosts": [_host_dict(r, redacted) for r in records],
    }


def _host_dict(record: HostRecord, redacted: bool) -> dict[str, Any]:
    announcements = record.tuya_announcements
    return {
        "ip": record.ip,
        "mac": redact.mac(record.mac) if redacted else record.mac,
        "mac_randomised": lan.is_locally_administered(record.mac) if record.mac else None,
        "hostname": redact.hostname(record.hostname) if redacted else record.hostname,
        "sources": sorted(record.sources),
        "broadcast_count": record.broadcast_count,
        "tuya_announcements": [redact.payload(a) for a in announcements]
        if redacted
        else announcements,
        "tuya_app_requests": record.tuya_app_requests,
        "undecoded_datagrams": [
            {
                "received_at": d.received_at,
                "source_port": d.source_port,
                "local_port": d.local_port,
                "length": len(d.data),
                # Raw bytes may embed identifiers, so they are dropped when redacting.
                "hex": None if redacted else d.data.hex(),
            }
            for d in record.undecoded_datagrams
        ],
        "model_matches": [m.model_id for m in identify(record)],
    }
