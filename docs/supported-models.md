# Supported models

This list matches the model registry in the code: `uv run robzone-diag models`.

A model appears here only after its integration has been implemented. A capability
is marked **Verified** only after it has been tested on a physical unit. Owning a
device, or a similar product name, is not support.

## Capability states

| State | Meaning |
|---|---|
| TBD | Not investigated yet |
| Experimental | Implemented, not yet verified on a physical device |
| Verified | Implemented and verified on a physical device |
| Unsupported | Confirmed not exposed by this model integration |

## Models

| Model | Model ID | Support | Discovery | Basic telemetry | LiDAR | Odometry | Navigation | Tested hardware |
|---|---|---|---|---|---|---|---|---|
| Robzone DUORO X-MAX PROFI / HOMEVAC | `duoro-xmax-profi` | Active development | TBD | TBD | TBD | TBD | TBD | 1 unit (maintainer) |

### Robzone DUORO X-MAX PROFI / HOMEVAC

- **The only model the maintainer physically has.** It is the reference device for
  this project.
- "HOMEVAC" is the optional self-emptying station, not a different robot. See
  [research/sources.md](../research/sources.md).
- Official app: RobZone (`com.robzone.robe`).
- Protocol: not identified. Tuya is a hypothesis under test: see
  [research/hypotheses.md](../research/hypotheses.md).
- Hardware revision: unknown. Firmware version: unknown. App version used in tests:
  not recorded yet.

**Tests performed on hardware:**

| Date | Test | Result |
|---|---|---|
| 2026-09-24 | LAN fingerprint ([experiment 01](../research/experiments/01-lan-discovery.md)) | Robot identified by the router DHCP list (`udhcp 1.27.2`) and confirmed by switching it off. Embedded Linux (TTL 64). TCP 22 (OpenSSH 7.6), 53, 8000 (Mongoose 6.11) and 8888 open. No Tuya broadcasts. This is a research observation, not a verified capability. |

Generic LAN discovery (`discover`, `scan`) works on any network. It is not a model
capability: *identifying* this model on the LAN stays TBD until a fingerprint has
been verified.
