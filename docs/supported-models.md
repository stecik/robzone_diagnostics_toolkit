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
| Robzone DUORO X-MAX PROFI / HOMEVAC | `duoro-xmax-profi` | Active development | TBD | Battery: Verified. State, error, firmware: Experimental | TBD | TBD | Experimental (reported pose only) | 1 unit (maintainer) |

### Robzone DUORO X-MAX PROFI / HOMEVAC

- **The only model the maintainer physically has.** It is the reference device for
  this project.
- "HOMEVAC" is the optional self-emptying station, not a different robot. See
  [research/sources.md](../research/sources.md).
- Official app: RobZone (`com.robzone.robe`).
- Protocol: **HCT Robot LAN protocol, JSON over TCP 8888**. It was identified from
  the official app's traffic. This tool has a read-only client for it. See
  [research/protocols/hct-lan-8888.md](../research/protocols/hct-lan-8888.md).
- `status` and `monitor` read state, battery, error code, firmware and pose. These
  are **Experimental**: implemented and seen working, not yet cross-checked. Map
  and trajectory are logged raw but not decoded, so they stay TBD. The LAN protocol
  exposes no raw LiDAR, encoder or IMU data.
- Hardware revision: unknown.
- Firmware versions, as shown in the app:
  - Wi-Fi `1.0.51(2026)`
  - system `1.20.219(21101819)`, labelled `system3308` (likely a Rockchip RK3308
    SoC)
  - MCU `7.6.2716(332)`, also reported by the robot
- RobZone app protocol version: `5.0.9`.
- Security notes: [research/security-assessment.md](../research/security-assessment.md).

**Tests performed on hardware:**

| Date | Test | Result |
|---|---|---|
| 2026-09-24 | LAN fingerprint ([experiment 01](../research/experiments/01-lan-discovery.md)) | Robot identified by the router DHCP list (`udhcp 1.27.2`) and confirmed by switching it off. Embedded Linux (TTL 64). TCP 22 (OpenSSH 7.6), 53, 8000 (Mongoose 6.11) and 8888 open. No Tuya broadcasts. This is a research observation, not a verified capability. |
| 2026-09-24 | App traffic capture ([experiment 02](../research/experiments/02-app-traffic-capture.md)) | The app talks to the robot on TCP 8888 (JSON). The robot reports state, battery, error, `robotPos`/`deg`, the map and the trajectory. Cloud: `*.hctrobot.com`. |
| 2026-09-24 | `status` / `monitor` with this tool | Read-only client works: state, battery, error, firmware and pose read over LAN. The battery value matched the app (57–58 %), so **Battery is Verified**. The others stay Experimental. |
| 2026-09-24 | Heading at standstill ([experiment 03](../research/experiments/03-heading-at-standstill.md)) | Runs A–D. At standstill the heading drifts +1.53 °/s. The rate is the same after a power cycle, and the robot was confirmed physically still. A manual 90° rotation was reported as about 94°, so `deg` is the heading. On the dock the pose is not updated. |
| 2026-09-24 | Cleaning runs in a 1.5 × 1.65 m arena (runs E, F) | Run E: a 1-minute pause led to failed relocalisation (`relocaNotice` 2, app: "Mapa ztracena"). Run F: after 10 minutes of uninterrupted cleaning, on the same dock, the robot reported about 150° of heading error and about 50 cm of position error. It failed to dock, and its map was smeared and duplicated. |

Generic LAN discovery (`discover`, `scan`) works on any network. It is not a model
capability: *identifying* this model on the LAN stays TBD until a fingerprint has
been verified.
