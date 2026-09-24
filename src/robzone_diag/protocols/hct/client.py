"""Blocking, single-threaded read-only client for the HCT Robot LAN protocol."""

from __future__ import annotations

import logging
import socket
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from robzone_diag.protocols.hct import frames, messages

log = logging.getLogger(__name__)

# Arbitrary starting point; the app used values around 10000 and the robot echoes them.
DEFAULT_FIRST_SEQ = 0x2710


class HctConnectionError(ConnectionError):
    pass


@dataclass(frozen=True)
class Received:
    """One frame from the robot, with its JSON body decoded when it has one."""

    at: float  # time.time()
    frame: frames.Frame
    document: dict[str, Any] | None

    @property
    def value(self) -> dict[str, Any]:
        return messages.payload(self.document) if self.document else {}

    @property
    def kind(self) -> str:
        value = self.value
        if value.get("noteCmd") == messages.NOTE_STATUS:
            return "status"
        if value.get("noteCmd") == messages.NOTE_SESSION:
            return "session"
        if value.get("transitCmd") == messages.TRANSIT_MAP_REPLY:
            return "map"
        return self.frame.type_name


class HctClient:
    def __init__(self, credentials: messages.Credentials, timeout: float = 5.0) -> None:
        self.credentials = credentials
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._decoder = frames.FrameDecoder()
        self._seq = DEFAULT_FIRST_SEQ
        self._backlog: list[Received] = []

    # ------------------------------------------------------------ connection

    def connect(self) -> None:
        address = (self.credentials.host, self.credentials.port)
        try:
            self._sock = socket.create_connection(address, timeout=self.timeout)
        except OSError as exc:
            raise HctConnectionError(f"cannot connect to {address[0]}:{address[1]}: {exc}") from exc
        self._decoder = frames.FrameDecoder()
        log.info("Connected to %s:%d", *address)

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self) -> HctClient:
        self.connect()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------ sending

    def ping(self) -> None:
        self._send(frames.ping(self._next_seq()))

    def send_query(self, value: dict[str, str]) -> int:
        """Send a read-only query; returns its sequence number for matching the reply."""
        seq = self._next_seq()
        self._send(frames.request(seq, messages.encode_request(self.credentials, value)))
        return seq

    def request(self, value: dict[str, str], timeout: float | None = None) -> Received:
        """Send a query and wait for the reply with the same sequence number.

        Frames that arrive meanwhile (notifications) are kept and returned by ``drain``.
        """
        seq = self.send_query(value)
        deadline = time.monotonic() + (timeout or self.timeout)
        while time.monotonic() < deadline:
            for received in self._read(deadline - time.monotonic()):
                if received.frame.type == frames.REPLY and received.frame.seq == seq:
                    return received
                self._backlog.append(received)
        raise TimeoutError(f"no reply to transitCmd {value.get('transitCmd')} within timeout")

    # ------------------------------------------------------------ receiving

    def drain(self, wait: float = 0.0) -> list[Received]:
        """Return frames received so far, waiting up to ``wait`` seconds for more."""
        collected, self._backlog = self._backlog, []
        deadline = time.monotonic() + wait
        while True:
            remaining = deadline - time.monotonic()
            collected += self._read(max(remaining, 0.0))
            if remaining <= 0:
                return collected

    def wait_for(self, kind: str, timeout: float) -> Received | None:
        """Wait for the first frame of ``kind`` (e.g. "status"); others go to the backlog."""
        deadline = time.monotonic() + timeout
        for received in self._backlog:
            if received.kind == kind:
                self._backlog.remove(received)
                return received
        while time.monotonic() < deadline:
            for received in self._read(deadline - time.monotonic()):
                if received.kind == kind:
                    return received
                self._backlog.append(received)
        return None

    def _read(self, timeout: float) -> Iterator[Received]:
        sock = self._require_socket()
        sock.settimeout(max(timeout, 0.001))
        try:
            data = sock.recv(65536)
        except TimeoutError:
            return iter(())
        except OSError as exc:
            raise HctConnectionError(f"connection lost: {exc}") from exc
        if not data:
            raise HctConnectionError("robot closed the connection")
        now = time.time()
        try:
            decoded = self._decoder.feed(data)
        except frames.FrameError as exc:
            raise HctConnectionError(f"protocol stream desynchronised: {exc}") from exc
        return iter([Received(now, frame, _decode(frame)) for frame in decoded])

    # ------------------------------------------------------------ helpers

    def _send(self, frame: frames.Frame) -> None:
        try:
            self._require_socket().sendall(frame.encode())
        except OSError as exc:
            raise HctConnectionError(f"send failed: {exc}") from exc

    def _require_socket(self) -> socket.socket:
        if self._sock is None:
            raise HctConnectionError("not connected")
        return self._sock

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        return self._seq


def _decode(frame: frames.Frame) -> dict[str, Any] | None:
    if not frame.body:
        return None
    try:
        return messages.decode_body(frame.body)
    except messages.MessageError:
        log.debug("Non-JSON body in %s frame (%d bytes)", frame.type_name, len(frame.body))
        return None
