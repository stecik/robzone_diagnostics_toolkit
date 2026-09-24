"""Loader for sanitized HCT frames captured from a real robot and app."""

import json
from pathlib import Path

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "hct" / "duoro-xmax-profi-7.6.2716.json"
)
FAKE_HOST, FAKE_AUTH, FAKE_DEVICE = "192.168.0.50", "AAAAAAAAAA", "0000000000000000"


def frame_bytes(name: str) -> bytes:
    return bytes.fromhex(json.loads(FIXTURE.read_text(encoding="utf-8"))["frames"][name])
