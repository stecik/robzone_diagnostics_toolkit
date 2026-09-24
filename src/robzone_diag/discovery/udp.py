"""Passive UDP listener for LAN broadcasts, with an optional periodic sender."""

from __future__ import annotations

import logging
import selectors
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

log = logging.getLogger(__name__)

MAX_DATAGRAM = 65535


@dataclass(frozen=True)
class Datagram:
    received_at: str  # ISO 8601, UTC
    source_ip: str
    source_port: int
    local_port: int
    data: bytes


@dataclass
class ListenResult:
    datagrams: list[Datagram]
    bound_ports: list[int]
    bind_errors: dict[int, str]


@dataclass(frozen=True)
class PeriodicSend:
    """A datagram to broadcast every ``interval`` seconds while listening."""

    payload: bytes
    destination: tuple[str, int]
    source_ip: str
    interval: float


def listen(
    ports: list[int],
    duration: float,
    periodic: PeriodicSend | None = None,
    on_datagram: Callable[[Datagram], None] | None = None,
) -> ListenResult:
    selector = selectors.DefaultSelector()
    result = ListenResult([], [], {})
    sockets = [s for s in (_bind(port, result) for port in ports) if s is not None]
    for sock in sockets:
        selector.register(sock, selectors.EVENT_READ)
    sender = _open_sender(periodic) if periodic else None
    try:
        _loop(selector, duration, periodic, sender, result, on_datagram)
    finally:
        for sock in sockets:
            sock.close()
        if sender:
            sender.close()
        selector.close()
    return result


def _bind(port: int, result: ListenResult) -> socket.socket | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.bind(("", port))
    except OSError as exc:
        sock.close()
        result.bind_errors[port] = str(exc)
        log.warning("Cannot listen on UDP %d: %s", port, exc)
        return None
    sock.setblocking(False)
    result.bound_ports.append(port)
    return sock


def _open_sender(periodic: PeriodicSend) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind((periodic.source_ip, 0))
    return sock


def _loop(selector, duration, periodic, sender, result, on_datagram) -> None:
    deadline = time.monotonic() + duration
    next_send = time.monotonic()
    while (now := time.monotonic()) < deadline:
        if sender and now >= next_send:
            _send(sender, periodic)
            next_send = now + periodic.interval
        wake = min(deadline, next_send) if sender else deadline
        if not selector.get_map():
            time.sleep(max(0.0, wake - now))
            continue
        for key, _ in selector.select(timeout=max(0.0, wake - now)):
            datagram = _receive(key.fileobj)
            if datagram:
                result.datagrams.append(datagram)
                if on_datagram:
                    on_datagram(datagram)


def _send(sender: socket.socket, periodic: PeriodicSend) -> None:
    try:
        sender.sendto(periodic.payload, periodic.destination)
    except OSError as exc:
        log.warning("Broadcast to %s:%d failed: %s", *periodic.destination, exc)


def _receive(sock: socket.socket) -> Datagram | None:
    try:
        data, (ip, port) = sock.recvfrom(MAX_DATAGRAM)
    except (BlockingIOError, ConnectionResetError):
        return None
    local_port = sock.getsockname()[1]
    received_at = datetime.now(UTC).isoformat(timespec="milliseconds")
    return Datagram(received_at, ip, port, local_port, data)
