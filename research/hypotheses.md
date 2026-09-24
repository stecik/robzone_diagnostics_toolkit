# Hypotheses

Status values:

- **open**: not tested yet
- **supported**: evidence points this way, but the hypothesis is not proven
- **confirmed**: proven by measurement
- **rejected**: disproven by measurement

## H1. The X-MAX PROFI's Wi-Fi module uses the Tuya platform

**Status: open. The evidence is mixed.**

Evidence for:

- The app manual (page 14) tells you to join a pairing AP named „SmartLife-číslo".
  `SmartLife-XXXX` is the usual AP name of Tuya devices in AP pairing mode. See
  [sources.md](sources.md).
- 2026-09-24: `robzone-diag discover` on the maintainer's LAN decoded a Tuya
  protocol 3.4 announcement from one host, and that host has TCP 6668 open.
  **We have not confirmed that this host is the robot.** Other Tuya devices may be
  on that LAN. See [experiments/01-lan-discovery.md](experiments/01-lan-discovery.md).

Evidence against / alternatives:

- The RobZone app's developer is Shenzhen Haocheng, not Tuya Inc. The same
  developer's Sencor app talks to its robots with a non-Tuya JSON protocol on
  TCP 8888.
- The app might embed the Tuya SDK under its own branding. This is common with
  OEM apps. Checking it needs the APK (phase 4).

What would decide it:

1. Show that the host announcing Tuya 3.4 is the robot. Compare its MAC with the
   robot's MAC, or power the robot off and check that the announcements stop.
2. Scan the robot for TCP 6668 and TCP 8888.

## H2. Map drift comes from the LiDAR, odometry, IMU, SLAM or the app/cloud

**Status: open.** We have no telemetry access yet.

If H1 is confirmed, the Tuya Sweeper SDK suggests where to look:

- maps and paths travel as cloud files
- live state travels as DPs

Whether any sensor-level data (odometry, IMU, raw LiDAR) is exposed at all is
unknown. It is likely that it is **not** exposed over the network. In that case the
decision tree falls back to the reported pose and map versus reality, and then to
hardware (UART) for raw sensor data.
