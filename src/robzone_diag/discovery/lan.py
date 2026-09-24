"""Local network facts: this computer's addresses and the OS neighbour (ARP) table."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Matches "aa-bb-cc-dd-ee-ff", "aa:bb:cc:dd:ee:ff" and macOS' "a:b:c:d:e:f".
_MAC_RE = re.compile(r"\b([0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5})\b")
_IPV4_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


@dataclass(frozen=True)
class Neighbour:
    ip: str
    mac: str


def local_ipv4_addresses() -> list[str]:
    """Best-effort list of this computer's IPv4 addresses, primary route first."""
    found: list[str] = []
    primary = _primary_ipv4()
    if primary:
        found.append(primary)
    try:
        for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
            if addr not in found and not addr.startswith("127."):
                found.append(addr)
    except OSError:
        pass
    return found


def _primary_ipv4() -> str | None:
    # connect() on a UDP socket only selects a route; no packet is sent.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 9))  # TEST-NET-1, never routed to a real host
            return sock.getsockname()[0]
        except OSError:
            return None


def normalize_mac(raw: str) -> str:
    return ":".join(part.zfill(2) for part in re.split(r"[:-]", raw.lower()))


def is_unicast_host_mac(mac: str) -> bool:
    first_octet = int(mac[:2], 16)
    return mac not in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00") and not first_octet & 0x01


def is_locally_administered(mac: str) -> bool:
    """True for randomised/private MACs (phones often use these); no vendor OUI then."""
    return bool(int(mac[:2], 16) & 0x02)


def parse_neighbour_table(text: str) -> list[Neighbour]:
    """Parse ``arp -a`` (Windows, macOS, Linux) or ``/proc/net/arp`` output, any locale."""
    result: dict[str, Neighbour] = {}
    for line in text.splitlines():
        ip_match = _IPV4_RE.search(line)
        mac_match = _MAC_RE.search(line)
        if not ip_match or not mac_match:
            continue
        ip = ip_match.group(1)
        mac = normalize_mac(mac_match.group(1))
        if not _is_host_ip(ip) or not is_unicast_host_mac(mac):
            continue
        result.setdefault(ip, Neighbour(ip, mac))
    return sorted(result.values(), key=lambda n: ipaddress.IPv4Address(n.ip))


def _is_host_ip(ip: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        return False
    return not (addr.is_multicast or addr.is_loopback or addr.is_unspecified or ip.endswith(".255"))


def read_neighbour_table() -> list[Neighbour]:
    """Read the OS ARP cache. Only hosts this computer talked to recently appear here."""
    proc_arp = Path("/proc/net/arp")
    if sys.platform.startswith("linux") and proc_arp.exists():
        return parse_neighbour_table(proc_arp.read_text())
    try:
        completed = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, errors="replace", timeout=10
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("Could not read the ARP table: %s", exc)
        return []
    return parse_neighbour_table(completed.stdout)


def prime_arp_cache(ips: list[str], settle: float = 1.0) -> None:
    """Make the OS resolve MACs for ``ips`` by sending each one empty UDP datagram.

    The datagram goes to the discard port (9); its only purpose is the ARP request the
    OS sends before it. Devices ignore it.
    """
    if not ips:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for ip in ips:
            try:
                sock.sendto(b"", (ip, 9))
            except OSError as exc:
                log.debug("ARP priming for %s failed: %s", ip, exc)
    time.sleep(settle)


def reverse_lookup(ips: list[str], timeout: float = 3.0) -> dict[str, str]:
    """Reverse-DNS names (often the DHCP hostname from the router). Missing = no name."""
    if not ips:
        return {}
    names: dict[str, str] = {}
    pool = ThreadPoolExecutor(max_workers=min(32, len(ips)))
    futures = {pool.submit(_lookup, ip): ip for ip in ips}
    done, _ = wait(futures, timeout=timeout)
    for future in done:
        name = future.result()
        if name:
            names[futures[future]] = name
    pool.shutdown(wait=False, cancel_futures=True)
    return names


def _lookup(ip: str) -> str | None:
    try:
        name = socket.gethostbyaddr(ip)[0]
    except OSError:
        return None
    return None if name == ip else name


def is_private_address(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private and not addr.is_loopback and not addr.is_multicast
