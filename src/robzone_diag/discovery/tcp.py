"""TCP connect scan with passive banner capture (we never send data to open ports)."""

from __future__ import annotations

import errno
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum

# Conventional uses of ports, shown as hints only. An open port proves nothing about the
# service behind it until its traffic is examined.
PORT_HINTS: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    53: "DNS",
    80: "HTTP",
    443: "HTTPS",
    554: "RTSP (camera streaming)",
    1883: "MQTT",
    1935: "RTMP",
    5000: "HTTP (often dev/UPnP servers)",
    5555: "Android Debug Bridge (ADB)",
    6668: "Tuya local protocol",
    6669: "Tuya-related (unverified)",
    8000: "HTTP (alternate)",
    8080: "HTTP (alternate)",
    8081: "HTTP (alternate)",
    8443: "HTTPS (alternate)",
    8554: "RTSP (alternate)",
    8883: "MQTT over TLS",
    8888: "HTTP (alternate); JSON control on Sencor/Clouds Robot vacuums",
    9000: "HTTP (alternate)",
    9090: "HTTP (alternate)",
    10000: "various",
    49152: "UPnP (typical dynamic port)",
}

COMMON_PORTS: tuple[int, ...] = tuple(sorted(PORT_HINTS))
_REFUSED = {errno.ECONNREFUSED, 10061}  # 10061 = WSAECONNREFUSED on Windows


class PortState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"  # host answered with a reset
    FILTERED = "filtered"  # no answer within the timeout


@dataclass(frozen=True)
class PortResult:
    port: int
    state: PortState
    banner: bytes | None = None


def parse_port_spec(spec: str) -> list[int]:
    """``"common"``, ``"all"``, or a list like ``"22,80,6000-6700"``."""
    spec = spec.strip().lower()
    if spec == "common":
        return list(COMMON_PORTS)
    if spec == "all":
        return list(range(1, 65536))
    ports: set[int] = set()
    for part in spec.split(","):
        start, _, end = part.strip().partition("-")
        low, high = int(start), int(end or start)
        if not 1 <= low <= high <= 65535:
            raise ValueError(f"invalid port range '{part}'")
        ports.update(range(low, high + 1))
    return sorted(ports)


DEFAULT_TIMEOUT = 3.0
# Small Wi-Fi modules (observed on a Tuya device) silently drop SYNs when flooded with
# parallel connections, which makes open ports look filtered. Keep concurrency low.
DEFAULT_WORKERS = 8


def scan(
    host: str,
    ports: list[int],
    timeout: float = DEFAULT_TIMEOUT,
    workers: int = DEFAULT_WORKERS,
    grab_banner: bool = True,
    retries: int = 1,
) -> list[PortResult]:
    """Scan ``ports``; ports with no answer are retried with minimal concurrency."""
    results = {r.port: r for r in _scan_once(host, ports, timeout, workers, grab_banner)}
    for _ in range(retries):
        silent = [p for p, r in results.items() if r.state is PortState.FILTERED]
        if not silent:
            break
        for result in _scan_once(host, silent, timeout, 2, grab_banner):
            results[result.port] = result
    return [results[p] for p in ports]


def _scan_once(
    host: str, ports: list[int], timeout: float, workers: int, grab_banner: bool
) -> list[PortResult]:
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ports)))) as pool:
        return list(pool.map(lambda port: probe_port(host, port, timeout, grab_banner), ports))


def probe_port(host: str, port: int, timeout: float, grab_banner: bool) -> PortResult:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        code = sock.connect_ex((host, port))
        if code in _REFUSED:
            return PortResult(port, PortState.CLOSED)
        if code != 0:
            return PortResult(port, PortState.FILTERED)
        return PortResult(port, PortState.OPEN, _read_banner(sock) if grab_banner else None)


def _read_banner(sock: socket.socket, limit: int = 256) -> bytes | None:
    """Some services (SSH, Telnet, FTP) speak first; we only listen."""
    try:
        data = sock.recv(limit)
    except OSError:
        return None
    return data or None
