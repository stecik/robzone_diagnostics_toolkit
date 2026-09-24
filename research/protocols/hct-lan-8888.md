# HCT Robot LAN protocol (TCP 8888)

Observed on 2026-09-24 between the RobZone app (Android) and a Robzone DUORO X-MAX
PROFI:

- robot firmware `7.6.2716(332)`
- app protocol `"version":"5.0.9"`
- capture: `captures/02-app-idle.pcap` (private)

The cloud behind it is `*.hctrobot.com`, which is why this document calls it the
**HCT Robot** protocol. Related public implementations use the same family with
small variations: [jerzik/robzone_xclean](https://github.com/jerzik/robzone_xclean),
[ha-SencorRobotics](https://github.com/MichalTichy/ha-SencorRobotics) and
[proscenic-790t-local](https://github.com/JakobFischer2574/proscenic-790t-local).

Everything below is what **our** capture shows unless a source is linked. Meanings
marked *(inferred)* are guesses from context.

## Transport

- The app is the client. It connects to `robot:8888` over plain TCP, not TLS.
- In our capture the app kept one connection open for the whole session. It
  briefly opened and closed an earlier connection too.
- Frames are a 20-byte header followed by an optional UTF-8 JSON body.

## Frame header (20 bytes)

| Bytes | Meaning |
|---|---|
| 0–3 | Total frame length including the header, uint32 little-endian |
| 4–7 | Message type (see below) |
| 8–11 | Flags / control *(inferred)* |
| 12–15 | Sequence number, uint32 LE. A reply echoes the sequence number of its request. |
| 16–19 | Extra field: `e7030000` (= 999) in keepalive acks, else 0 |

Message types seen:

| Bytes 4–7 | Direction | Body | Meaning |
|---|---|---|---|
| `0001c800` | app → robot | none | Keepalive ping. Bytes 8–11 = `00000100`. |
| `1101c800` | robot → app | none | Keepalive ack; echoes the ping sequence number |
| `fa00c800` | app → robot | JSON | Request. Bytes 8–11 = `0000`+u16 (the next sequence number). |
| `fa000000` | robot → app | JSON | Reply to a request |
| `fb000000` | robot → app | JSON | Unsolicited notification (own sequence counter) |

On the cloud relay (TCP 20008) the same messages appear with prefixes
`1000c800`/`1100c800` (login/ack) and `fb00c800`.

## Request envelope

```json
{"cmd":"0",
 "control":{"authCode":"<10 chars>","deviceIp":"<robot ip>","devicePort":"8888",
            "targetId":"<16 chars>","targetType":"3"},
 "seq":"0",
 "value":{"transitCmd":"<id>", ...},
 "version":"5.0.9"}
```

- `authCode` and `targetId` identify the robot to the app account. **They are
  secrets.** Keep them in `.env` only.
- `targetType` is `3` on the LAN and `1` via the cloud.

## Commands seen

| transitCmd | Direction | Value fields | Effect |
|---|---|---|---|
| `133` | app → robot | `mapWidth`, `mapHeight`, `centerPoint`, `mapSign` (base64), `trackNum` (base64) | **Read-only.** Map/pose query. The app sends it every 5 s. |
| `134` | robot → app | see below | Reply to 133 |
| `98` | app → cloud | `opCmd:"state"` | **Read-only.** State query. Seen only on the cloud relay so far. |
| `100` | app → robot | `start:"1"` | Starts cleaning (actuating) |
| `102` | app → robot | `pause:"1"` | Pauses (actuating) |

Notifications (`noteCmd`, robot → app):

| noteCmd | Meaning | Fields |
|---|---|---|
| `102` | State, pushed on change | `workState`, `workMode`, `battery`, `error`, `fan`, `brush`, `direction`, `waterTank`, `mopMode`, `version` (firmware), `extParam` (JSON string) |
| `101` | Cleaning-session update | `clearSign`, `clearArea`, `clearTime`, `clearModule`, `clearId` |
| `109` | Push text for the phone, e.g. "XMAX Profi/Homevac začíná uklízet" ("XMAX Profi/Homevac is starting to clean") | cloud only |

`extParam` keys observed include:

- `relocaNotice` (0 throughout; *inferred*: a relocalisation notice)
- `mapUpdateSign`
- `hadWork`
- `workType`
- `cleanModule`
- voice settings

## Map/pose reply (transitCmd 134)

| Field | Observed | Meaning *(inferred unless stated)* |
|---|---|---|
| `robotPos` | `"367,367"` … `"327,357"`, and once empty | Robot position in map cells |
| `deg` | `254`, `-79`, `151`, `199`, … | Heading in degrees; the value range is not normalised |
| `mapWidth`/`mapHeight` | `700` | Map size in cells |
| `blockSize` | `10000` | Cells per block, i.e. 100×100 → a 7×7 block grid |
| `mapSign` | base64 of 49 × uint16 | Per-block version counters. The app echoes its known versions and the robot sends only the changed blocks *(inferred)*. |
| `map` | base64, growing (3064 → 4848 chars) | Changed map blocks. Encoding not decoded yet. |
| `trackNum` / `track` | uint16 count / base64 | Incremental trajectory: the app sends the count it has, the robot sends the new points |
| `centerPoint`, `leftMaxPoint`, `rightMaxPoint` | `500,500`, `0,0`, `700,700` | Map geometry |
| `emptyMap` | `1` at start, then `0` | A new map was created |
| `clearSign` | `YYYY-MM-DD-hh-mm-ss-N` | Cleaning-session ID (robot clock) |
| `clearArea` / `clearTime` | area units / minutes | Session progress |
| `doTime` | increasing by 5 per poll | Robot uptime counter in seconds |

## Why this matters for the drift diagnosis

`robotPos` + `deg` + `track` are the robot's **own pose estimate**, and `map` is its
SLAM map. Logging them over a whole run lets us:

1. find the moment the reported pose starts to diverge, by comparing it with the
   dock position and physical reference points;
2. see whether the trajectory jumps (a relocalisation) or drifts smoothly (odometry
   or IMU);
3. check `relocaNotice`, `error` and `workState` changes at that moment.

This protocol does not expose raw LiDAR, wheel encoders or the IMU. Those still
need either a shell on the robot (SSH is open) or UART on the hardware.
