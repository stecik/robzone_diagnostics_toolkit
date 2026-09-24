"""20-byte frame header + optional JSON body.

Header layout (all integers little-endian), as observed on TCP 8888::

    0-3   total frame length including the header
    4-7   message type (see constants below)
    8-11  flags; requests carry the next sequence number in bytes 10-11
    12-15 sequence number; replies echo the request's value
    16-19 extra (999 in keepalive acks, otherwise 0)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

HEADER = struct.Struct("<I4s4sII")
HEADER_SIZE = HEADER.size
MAX_FRAME_SIZE = 4 * 1024 * 1024

PING = bytes.fromhex("0001c800")
PING_ACK = bytes.fromhex("1101c800")
REQUEST = bytes.fromhex("fa00c800")
REPLY = bytes.fromhex("fa000000")
NOTIFY = bytes.fromhex("fb000000")

TYPE_NAMES = {
    PING: "ping",
    PING_ACK: "ping-ack",
    REQUEST: "request",
    REPLY: "reply",
    NOTIFY: "notification",
}

_PING_FLAGS = bytes.fromhex("00000100")


class FrameError(ValueError):
    """The byte stream does not follow the frame format (desynchronised or not HCT)."""


@dataclass(frozen=True)
class Frame:
    type: bytes
    flags: bytes
    seq: int
    extra: int = 0
    body: bytes = b""

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type, f"unknown-{self.type.hex()}")

    def encode(self) -> bytes:
        length = HEADER_SIZE + len(self.body)
        return HEADER.pack(length, self.type, self.flags, self.seq, self.extra) + self.body


def ping(seq: int) -> Frame:
    return Frame(PING, _PING_FLAGS, seq)


def request(seq: int, body: bytes) -> Frame:
    flags = b"\x00\x00" + ((seq + 1) & 0xFFFF).to_bytes(2, "little")
    return Frame(REQUEST, flags, seq, 0, body)


class FrameDecoder:
    """Incremental decoder: feed received bytes, get complete frames back."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self._buffer += data
        frames: list[Frame] = []
        while len(self._buffer) >= HEADER_SIZE:
            length, kind, flags, seq, extra = HEADER.unpack_from(self._buffer)
            if not HEADER_SIZE <= length <= MAX_FRAME_SIZE:
                raise FrameError(f"implausible frame length {length}")
            if len(self._buffer) < length:
                break
            body = bytes(self._buffer[HEADER_SIZE:length])
            del self._buffer[:length]
            frames.append(Frame(kind, flags, seq, extra, body))
        return frames

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)
