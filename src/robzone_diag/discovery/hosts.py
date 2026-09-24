"""Combine evidence from all discovery sources into one record per LAN host."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any

from robzone_diag.discovery.lan import Neighbour
from robzone_diag.discovery.udp import Datagram
from robzone_diag.protocols.tuya import broadcast as tuya

MAX_RAW_DATAGRAMS_PER_HOST = 20


@dataclass
class HostRecord:
    ip: str
    mac: str | None = None
    hostname: str | None = None
    sources: set[str] = field(default_factory=set)
    # Distinct decoded Tuya announcements (a device repeats the same one every few seconds).
    tuya_announcements: list[dict[str, Any]] = field(default_factory=list)
    broadcast_count: int = 0
    # Discovery requests sent by a Tuya-based app on this host (typically a phone).
    tuya_app_requests: int = 0
    undecoded_datagrams: list[Datagram] = field(default_factory=list)

    @property
    def speaks_tuya(self) -> bool:
        return bool(self.tuya_announcements)


def build_host_records(
    neighbours: list[Neighbour],
    datagrams: list[Datagram],
    local_addresses: list[str],
    hostnames: dict[str, str] | None = None,
) -> list[HostRecord]:
    hosts: dict[str, HostRecord] = {}

    def host(ip: str) -> HostRecord:
        return hosts.setdefault(ip, HostRecord(ip))

    for neighbour in neighbours:
        record = host(neighbour.ip)
        record.mac = neighbour.mac
        record.sources.add("arp")
    for datagram in datagrams:
        if datagram.source_ip in local_addresses:
            continue  # our own broadcasts looping back
        _add_datagram(host(datagram.source_ip), datagram)
    for ip, name in (hostnames or {}).items():
        if ip in hosts:
            hosts[ip].hostname = name
    return sorted(hosts.values(), key=lambda h: ipaddress.IPv4Address(h.ip))


def _add_datagram(record: HostRecord, datagram: Datagram) -> None:
    record.sources.add(f"udp:{datagram.local_port}")
    record.broadcast_count += 1
    if datagram.local_port in tuya.DISCOVERY_PORTS:
        try:
            decoded = tuya.decode_broadcast(datagram.data)
        except tuya.TuyaDecodeError:
            pass
        else:
            if tuya.is_devinfo_request(decoded):
                record.tuya_app_requests += 1  # an app asking, not a device announcing
                return
            announcement = {
                "frame": decoded.frame,
                "encrypted": decoded.encrypted,
                **decoded.payload,
            }
            if announcement not in record.tuya_announcements:
                record.tuya_announcements.append(announcement)
            return
    if len(record.undecoded_datagrams) < MAX_RAW_DATAGRAMS_PER_HOST:
        record.undecoded_datagrams.append(datagram)
