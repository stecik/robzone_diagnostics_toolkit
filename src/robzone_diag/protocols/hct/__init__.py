"""HCT Robot LAN protocol: JSON over TCP 8888.

Used by the Robzone DUORO X-MAX PROFI (RobZone app, cloud ``*.hctrobot.com``) and,
with variations, by related white-label robots. Reconstructed from captures of the
official app; see ``research/protocols/hct-lan-8888.md``.
"""

PROTOCOL_ID = "hct-lan"
DEFAULT_PORT = 8888
