"""Tuya broadcast decoder tests.

Frames are built with TinyTuya (an independent implementation) so the tests
check wire compatibility, not just that our encoder agrees with our decoder.
All device identifiers are synthetic.
"""

import json

import pytest
import tinytuya
from tinytuya.core import message_helper, udp_helper

from robzone_diag.protocols.tuya import broadcast as tb

SYNTHETIC = {
    "ip": "192.168.0.50",
    "gwId": "bf00000000000000test",
    "active": 2,
    "ability": 0,
    "mode": 0,
    "encrypt": True,
    "productKey": "testproductkey00",
    "version": "3.3",
}


def _pack(prefix: int, payload: bytes, cmd: int = 0x13, retcode: int | None = 0, key=None) -> bytes:
    if prefix == tb.PREFIX_55AA:
        # TinyTuya's packer omits the retcode; device-sent frames carry it in the payload.
        payload = (retcode or 0).to_bytes(4, "big") + payload
    msg = tinytuya.TuyaMessage(0, cmd, retcode, payload, 0, True, prefix, True)
    return message_helper.pack_message(msg, hmac_key=key)


def test_decodes_plain_55aa_v31():
    frame = _pack(tb.PREFIX_55AA, json.dumps(SYNTHETIC).encode())
    result = tb.decode_broadcast(frame)
    assert result.frame == "55AA"
    assert not result.encrypted
    assert result.checksum_ok
    assert result.payload == SYNTHETIC


def test_decodes_encrypted_55aa_v33():
    encrypted = udp_helper.encrypt(json.dumps(SYNTHETIC).encode(), udp_helper.udpkey)
    frame = _pack(tb.PREFIX_55AA, encrypted)
    result = tb.decode_broadcast(frame)
    assert result.encrypted
    assert result.checksum_ok
    assert result.payload == SYNTHETIC


def test_decodes_6699_v35():
    payload = dict(SYNTHETIC, version="3.5")
    frame = _pack(tb.PREFIX_6699, json.dumps(payload).encode(), retcode=None, key=udp_helper.udpkey)
    result = tb.decode_broadcast(frame)
    assert result.frame == "6699"
    assert result.payload == payload


def test_udp_key_matches_tinytuya():
    assert udp_helper.udpkey == tb.UDP_KEY


def test_tinytuya_decodes_the_same_55aa_frame():
    frame = _pack(tb.PREFIX_55AA, udp_helper.encrypt(json.dumps(SYNTHETIC).encode(), tb.UDP_KEY))
    assert json.loads(udp_helper.decrypt_udp(frame)) == SYNTHETIC


def test_devinfo_request_is_readable_by_tinytuya():
    frame = tb.build_devinfo_request("192.168.0.10")
    assert json.loads(udp_helper.decrypt_udp(frame)) == {"from": "app", "ip": "192.168.0.10"}
    assert tb.is_devinfo_request(tb.decode_broadcast(frame))


def test_detects_corrupted_crc():
    frame = bytearray(_pack(tb.PREFIX_55AA, json.dumps(SYNTHETIC).encode()))
    frame[-8] ^= 0xFF
    assert tb.decode_broadcast(bytes(frame)).checksum_ok is False


def test_rejects_tampered_6699():
    frame = bytearray(_pack(tb.PREFIX_6699, b'{"a":1}', retcode=None, key=udp_helper.udpkey))
    frame[40] ^= 0xFF
    with pytest.raises(tb.TuyaDecodeError):
        tb.decode_broadcast(bytes(frame))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello world",
        b"\x00\x00\x55\xaa\x00",
        bytes(range(32)),
        b"M-SEARCH * HTTP/1.1\r\n\r\n",
    ],
)
def test_rejects_non_tuya_datagrams(data):
    with pytest.raises(tb.TuyaDecodeError):
        tb.decode_broadcast(data)
