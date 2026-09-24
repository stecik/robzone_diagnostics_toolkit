"""Decoder for Tuya LAN discovery broadcasts (UDP 6666 / 6667 / 7000).

Tuya Wi-Fi devices periodically broadcast a small JSON document describing
themselves (device ID, IP, protocol version, product key). The frame formats
and the well-known broadcast key below follow TinyTuya, the reference open
implementation:

- https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/udp_helper.py
- https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/message_helper.py
- https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/header.py

Frame formats:

``55AA`` (protocol 3.1 - 3.4)::

    prefix(4)=0x000055AA seqno(4) cmd(4) length(4) retcode(4) payload crc32(4) suffix(4)

    ``length`` counts retcode + payload + crc + suffix. The payload is plain JSON
    (3.1, port 6666) or AES-128-ECB encrypted with ``UDP_KEY`` (3.3+, port 6667).

``6699`` (protocol 3.5, port 7000)::

    prefix(4)=0x00006699 reserved(2) seqno(4) cmd(4) length(4) iv(12) ciphertext tag(16)
    suffix(4)=0x00009966

    AES-128-GCM with ``UDP_KEY``; the 14 header bytes after the prefix are the
    associated data. ``length`` counts iv + ciphertext + tag.
"""

from __future__ import annotations

import binascii
import json
import os
import struct
from dataclasses import dataclass
from hashlib import md5
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Public, well-known key shared by all Tuya devices for LAN broadcasts (not a secret).
UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

PORT_V31 = 6666
PORT_V33 = 6667
PORT_APP = 7000
DISCOVERY_PORTS = (PORT_V31, PORT_V33, PORT_APP)

PREFIX_55AA = 0x000055AA
SUFFIX_55AA = 0x0000AA55
PREFIX_6699 = 0x00006699
SUFFIX_6699 = 0x00009966

CMD_REQ_DEVINFO = 0x25  # app -> broadcast, asks protocol 3.5 devices to announce themselves

_HEADER_55AA = struct.Struct(">4I")
_HEADER_6699 = struct.Struct(">IHIII")
_IV_LEN = 12
_TAG_LEN = 16

# Keys in a decoded broadcast that identify one physical device.
DEVICE_IDENTIFIER_KEYS = frozenset({"gwId", "devId", "id", "uuid", "mac"})


class TuyaDecodeError(ValueError):
    """Raised when a datagram is not a decodable Tuya broadcast."""


@dataclass(frozen=True)
class TuyaBroadcast:
    frame: str  # "55AA", "6699" or "raw"
    command: int | None
    encrypted: bool
    checksum_ok: bool | None  # None when the frame has no checksum/tag of its own
    payload: dict[str, Any]


def decode_broadcast(data: bytes) -> TuyaBroadcast:
    prefix = int.from_bytes(data[:4], "big") if len(data) >= 4 else None
    if prefix == PREFIX_55AA:
        return _decode_55aa(data)
    if prefix == PREFIX_6699:
        return _decode_6699(data)
    # Some firmwares broadcast a bare encrypted blob without framing.
    return TuyaBroadcast("raw", None, True, None, _parse_json(_decrypt_ecb(data)))


def build_devinfo_request(local_ip: str, seqno: int = 0) -> bytes:
    """Build the broadcast the Tuya app sends to UDP 7000 to wake protocol 3.5 devices."""
    payload = json.dumps({"from": "app", "ip": local_ip}).encode()
    length = _IV_LEN + len(payload) + _TAG_LEN
    header = _HEADER_6699.pack(PREFIX_6699, 0, seqno, CMD_REQ_DEVINFO, length)
    iv = os.urandom(_IV_LEN)
    sealed = AESGCM(UDP_KEY).encrypt(iv, payload, header[4:])
    return header + iv + sealed + SUFFIX_6699.to_bytes(4, "big")


def is_devinfo_request(broadcast: TuyaBroadcast) -> bool:
    """True for app-originated discovery requests (including our own echo)."""
    return broadcast.command == CMD_REQ_DEVINFO or broadcast.payload.get("from") == "app"


def _decode_55aa(data: bytes) -> TuyaBroadcast:
    if len(data) < _HEADER_55AA.size:
        raise TuyaDecodeError("55AA frame shorter than its header")
    _, _, cmd, length = _HEADER_55AA.unpack_from(data)
    end = _HEADER_55AA.size + length
    if length < 12 or len(data) < end:
        raise TuyaDecodeError(f"55AA frame truncated (declares {length} bytes)")
    crc, suffix = struct.unpack_from(">2I", data, end - 8)
    if suffix != SUFFIX_55AA:
        raise TuyaDecodeError(f"55AA frame has wrong suffix {suffix:08X}")
    checksum_ok = crc == binascii.crc32(data[: end - 8]) & 0xFFFFFFFF
    body = data[_HEADER_55AA.size + 4 : end - 8]  # skip retcode
    if body[:1] == b"{" and body[-1:] == b"}":
        return TuyaBroadcast("55AA", cmd, False, checksum_ok, _parse_json(body))
    return TuyaBroadcast("55AA", cmd, True, checksum_ok, _parse_json(_decrypt_ecb(body)))


def _decode_6699(data: bytes) -> TuyaBroadcast:
    if len(data) < _HEADER_6699.size:
        raise TuyaDecodeError("6699 frame shorter than its header")
    _, _, _, cmd, length = _HEADER_6699.unpack_from(data)
    end = _HEADER_6699.size + length
    if length < _IV_LEN + _TAG_LEN or len(data) < end + 4:
        raise TuyaDecodeError(f"6699 frame truncated (declares {length} bytes)")
    iv = data[_HEADER_6699.size : _HEADER_6699.size + _IV_LEN]
    sealed = data[_HEADER_6699.size + _IV_LEN : end]
    try:
        plain = AESGCM(UDP_KEY).decrypt(iv, sealed, data[4 : _HEADER_6699.size])
    except InvalidTag as exc:
        raise TuyaDecodeError("6699 frame failed AES-GCM authentication") from exc
    if plain[:1] != b"{" and plain[4:5] == b"{":
        plain = plain[4:]  # leading retcode
    return TuyaBroadcast("6699", cmd, True, True, _parse_json(plain.rstrip(b"\x00")))


def _decrypt_ecb(data: bytes) -> bytes:
    if not data or len(data) % 16:
        raise TuyaDecodeError("ciphertext is not a whole number of AES blocks")
    decryptor = Cipher(algorithms.AES(UDP_KEY), modes.ECB()).decryptor()
    padded = decryptor.update(data) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    try:
        return unpadder.update(padded) + unpadder.finalize()
    except ValueError as exc:
        raise TuyaDecodeError("not encrypted with the Tuya broadcast key") from exc


def _parse_json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TuyaDecodeError("payload is not JSON") from exc
    if not isinstance(value, dict):
        raise TuyaDecodeError("payload is not a JSON object")
    return value
