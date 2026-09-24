# Experiment 01: LAN discovery and service fingerprint

**Goal:** find the robot on the LAN and see which network services it exposes. This
tests hypothesis [H1](../hypotheses.md) (does it use Tuya?).

**Risk:** none to the robot.
- Discovery only listens. It also sends one empty UDP datagram to each host that
  broadcast, so the OS learns that host's MAC address.
- `--tuya-request` sends the same discovery request the Tuya app sends.
- `scan` opens and closes TCP connections. It sends no data.

## Setup

1. Robot on its dock and switched on. The Wi-Fi LED is **solid blue** (connected).
2. Your computer is on the **same Wi-Fi/LAN** as the robot. It must not be on a guest
   network, and not on a VPN.
3. Write down your robot's IP address and MAC address.
   - Where to look: your router's DHCP client list, or the device info screen in the
     app if it has one.
   - For sharing, keep only the first three MAC octets (e.g. `a8:80:55:xx:xx:xx`).

## Steps

Run these from the repository directory. Each `discover` run takes about 60 s.

**A. Robot on (baseline)**

```powershell
uv run robzone-diag discover --duration 60 --output captures/01a-robot-on.json
```

**B. Robot off**

Switch the robot off with its main switch, then run:

```powershell
uv run robzone-diag discover --duration 60 --output captures/01b-robot-off.json
```

If the robot is the Tuya host seen in A, its announcements must disappear here.

**C. Robot on again, active Tuya request**

Switch the robot back on and wait for solid blue, then run:

```powershell
uv run robzone-diag discover --duration 60 --tuya-request --output captures/01c-tuya-request.json
```

**D. TCP ports of the robot**

Replace `<robot-ip>`, then run:

```powershell
uv run robzone-diag scan <robot-ip> --output captures/01d-scan-common.json
```

**E. All TCP ports**

This can take 10+ minutes:

```powershell
uv run robzone-diag scan <robot-ip> --ports all --output captures/01e-scan-all.json
```

## What to report back

- The printed output of A–E. Add `--redact` if you prefer. Redacted IDs are stable
  pseudonyms, so runs can still be compared.
- Your robot's IP and MAC vendor prefix, as the router or app shows them.
- Do you have other Tuya / Smart Life / "smart home" Wi-Fi devices at home? For
  example plugs, bulbs or cameras.
- The Wi-Fi LED state during each step.

## How to read the outcome

| Observation | Interpretation | Next step |
|---|---|---|
| Tuya host = robot's IP/MAC, and it disappears in B | H1 strongly supported: the robot's Wi-Fi module speaks Tuya LAN protocol | Phase 2: identify DPs over TCP 6668 (needs the device's local key; read-only) |
| Robot has TCP 8888 open and no Tuya announcement | Sencor/Clouds Robot-style protocol is more likely | Phase 3: capture app↔robot traffic |
| Robot visible in ARP but nothing open and no broadcasts | Cloud-only device | Phase 3 (traffic capture) + Phase 4 (APK) |
| Robot not visible at all | Network problem (wrong network, AP/client isolation, firewall) | README troubleshooting |

## Results

### 2026-09-24: preliminary run by the maintainer

The maintainer ran this at development time, before the protocol above existed. The
robot's identity was **not** checked.

- One host on the maintainer's LAN sent encrypted Tuya announcements on UDP 6667:
  - protocol version 3.4
  - MAC vendor prefix `a8:80:55`
- `scan` of that host (common ports) found **TCP 6668 open** and every other common
  port closed.
- Tooling lesson: with 200 parallel connections the host dropped SYNs, so every port
  looked "filtered". The defaults were lowered to 8 workers, a 3 s timeout, and one
  retry.
- Still unknown: whether this host is the robot. Steps A–E will answer that.
