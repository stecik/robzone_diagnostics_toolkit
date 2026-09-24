"""Wire-protocol codecs. Protocols are shared between models, not owned by one."""

# Protocol IDs used by ModelDefinition.protocol, with a human-readable description.
PROTOCOLS: dict[str, str] = {
    "hct-lan": "HCT Robot LAN protocol (JSON over TCP 8888)",
}


def describe(protocol_id: str | None) -> str:
    if protocol_id is None:
        return "unknown (under investigation)"
    return PROTOCOLS.get(protocol_id, protocol_id)
