# Hypotheses

Status values:

- **open**: not tested yet
- **supported**: evidence points this way, but the hypothesis is not proven
- **confirmed**: proven by measurement
- **rejected**: disproven by measurement

## H1. The X-MAX PROFI's Wi-Fi module uses the Tuya platform

**Status: rejected for the robot itself (2026-09-24).** The robot and the app use
the HCT Robot platform (`*.hctrobot.com`) and its JSON protocol on TCP 8888. See H3.
The "SmartLife" pairing AP name remains unexplained.

Evidence for:

- The app manual (page 14) tells you to join a pairing AP named „SmartLife-číslo".
  `SmartLife-XXXX` is the usual AP name of Tuya devices in AP pairing mode. See
  [sources.md](sources.md).

Evidence against:

- 2026-09-24: the host believed to be the robot (DHCP name `udhcp 1.27.2`) looks
  like this:
  - it runs embedded Linux (TTL 64, OpenSSH 7.6)
  - it sends **no** Tuya broadcasts
  - TCP 6668 is **not** open
  - see [experiments/01](experiments/01-lan-discovery.md)
- The Tuya announcements we did decode come from a different host (TTL 255,
  another MAC vendor).
- The RobZone app's developer is Shenzhen Haocheng, not Tuya Inc.

Remaining ways Tuya could still be involved:

- The Tuya Linux SDK can run without LAN broadcasts.
- The pairing AP name may simply be reused.

What would decide it:

- The APK: does it embed the Tuya SDK? (phase 4)
- A traffic capture: cloud hostnames. (phase 3)

## H3. The robot uses the Clouds Robot / Sencor-family local protocol on TCP 8888

**Status: confirmed (2026-09-24).** The RobZone app talks to the robot directly on
TCP 8888 using this protocol family. See the
[protocol notes](protocols/hct-lan-8888.md) and [experiment 02](experiments/02-app-traffic-capture.md).

- The robot candidate has TCP 8888 open.
- [ha-SencorRobotics](https://github.com/MichalTichy/ha-SencorRobotics) controls
  Sencor/Cleanmate/Proscenic robots over TCP 8888 with JSON messages. The Sencor app
  comes from the same developer as the RobZone app.
- Nothing has been sent to 8888 yet. The protocol needs an `authCode` and a device
  ID, which that project takes from an app capture.

A closer relative now exists: [jerzik/robzone_xclean](https://github.com/jerzik/robzone_xclean),
a LAN integration for another Robzone robot (DUORO XCLEAN 5) using the same framing.
See [sources.md](sources.md).

What would decide it: capture the RobZone app's own traffic on the phone
([experiment 02](experiments/02-app-traffic-capture.md)) and compare the framing.
If it matches, read-only state and pose queries (`transitCmd` 98 / 133 in the
Sencor variant) become the first real telemetry source.

## H4. The robot's Linux system is reachable over SSH

**Status: observed. SSH is open. Credentials are unknown.**

- If we had shell access, logs, sensor daemons and possibly raw LiDAR/odometry
  streams could be read directly on the robot. That would be the most direct path
  to diagnosing the map drift.
- Logging in means trying credentials, and that is not a read-only step. It is
  **not** done without the owner's explicit decision.

## H2. Map drift comes from the LiDAR, odometry, IMU, SLAM or the app/cloud

**Status: open. Leading lead: heading estimate / IMU (branch C).**

- The robot reports its own pose (`robotPos`, `deg`), trajectory, map increments,
  state and error codes over TCP 8888. `status`, `monitor` and `analyze` read them.
- 2026-09-24 ([experiment 03](experiments/03-heading-at-standstill.md)), runs A–D:
  - The robot stood physically still (confirmed), and its reported heading drifted
    linearly at **+1.53 °/s**.
  - The rate was identical after a power cycle.
  - A manual 90° rotation was reported as about 94°, so `deg` is the heading and the
    gyro responds to real rotation.
  - The reported position stayed constant, so the drift does not come from the
    wheels.
- Current reading: an **uncompensated gyroscope bias**, i.e. branch C: IMU or its
  calibration.
- Not yet shown: that the bias causes the map breakdown during cleaning (run E).

Two routes could give us one:

- If H3 is confirmed, the 8888 protocol may expose the pose, the map and error
  codes.
- If H4 is possible, logs on the robot itself may show the sensor state.

Whether raw sensor data (odometry, IMU, raw LiDAR) is exposed at all is unknown.
