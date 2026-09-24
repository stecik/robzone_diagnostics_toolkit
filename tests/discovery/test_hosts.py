import json

import tinytuya
from tinytuya.core import udp_helper

from robzone_diag.discovery.hosts import build_host_records
from robzone_diag.discovery.lan import Neighbour
from robzone_diag.discovery.udp import Datagram
from robzone_diag.protocols.tuya import broadcast as tb

ANNOUNCEMENT = {"ip": "192.168.0.50", "gwId": "bf00000000000000test", "version": "3.4"}


def _tuya_frame(payload: dict) -> bytes:
    body = b"\x00\x00\x00\x00" + udp_helper.encrypt(json.dumps(payload).encode(), tb.UDP_KEY)
    msg = tinytuya.TuyaMessage(0, 0x13, 0, body, 0, True, tb.PREFIX_55AA, True)
    return tinytuya.pack_message(msg)


def _datagram(ip: str, port: int, data: bytes) -> Datagram:
    return Datagram("2026-01-01T00:00:00.000+00:00", ip, 50000, port, data)


def test_merges_arp_and_broadcasts_per_host():
    frame = _tuya_frame(ANNOUNCEMENT)
    records = build_host_records(
        [
            Neighbour("192.168.0.50", "a8:80:55:00:00:02"),
            Neighbour("192.168.0.1", "d8:21:da:00:00:01"),
        ],
        [_datagram("192.168.0.50", 6667, frame), _datagram("192.168.0.50", 6667, frame)],
        local_addresses=["192.168.0.10"],
    )
    assert [r.ip for r in records] == ["192.168.0.1", "192.168.0.50"]
    robot = records[1]
    assert robot.mac == "a8:80:55:00:00:02"
    assert robot.broadcast_count == 2
    assert len(robot.tuya_announcements) == 1  # repeated announcement deduplicated
    assert robot.tuya_announcements[0]["gwId"] == ANNOUNCEMENT["gwId"]


def test_ignores_own_broadcasts_and_counts_app_requests():
    request = tb.build_devinfo_request("192.168.0.20")
    records = build_host_records(
        [],
        [_datagram("192.168.0.10", 7000, request), _datagram("192.168.0.20", 7000, request)],
        local_addresses=["192.168.0.10"],
    )
    assert [r.ip for r in records] == ["192.168.0.20"]
    assert records[0].tuya_app_requests == 1
    assert not records[0].speaks_tuya


def test_keeps_undecodable_datagrams_for_analysis():
    records = build_host_records([], [_datagram("192.168.0.60", 6667, b"\x01\x02")], [])
    assert records[0].undecoded_datagrams[0].data == b"\x01\x02"
