# Robzone diagnostics toolkit

`robzone-diag` is an open diagnostic toolkit for Robzone robotic vacuum cleaners.

It works **alongside** the official Robzone app, not instead of it. Keep using the
app for cleaning, maps and schedules. This tool is for the technical diagnostics
the app does not show. The aim is to go from a symptom to a measurement, then to
the faulty component, and then to a cheap targeted repair.

> **Project status: early development (v0.1).**
>
> What works today:
> - LAN discovery (`discover`)
> - TCP port scan (`scan`)
> - the model registry (`models`)
>
> Robot telemetry and automated diagnosis (`diagnose`) do not exist yet. They will
> be built once the robot's protocol is understood. Nothing in this README claims
> otherwise.

## Supported models

| Model | Model ID | Status |
|---|---|---|
| Robzone DUORO X-MAX PROFI / HOMEVAC | `duoro-xmax-profi` | Active development. Every capability is still TBD. |

This is the only model the maintainer physically owns. For details, and for what
has actually been verified, see [docs/supported-models.md](docs/supported-models.md).
If you own a different Robzone model, you can help: see
[CONTRIBUTING.md](CONTRIBUTING.md).

## The problem this project starts from

The reference robot, a DUORO X-MAX PROFI, loses its localisation. These are the
owner's observations; they do not yet point to any specific component:

- The LiDAR spins. The robot drives straight and turns normally under manual control.
- On a new map, the first 2–3 minutes look correct.
- After a few minutes, the position shown on the map starts to drift away from the
  real position.
- Walls then appear doubled or shifted, false protrusions show up, and the map
  eventually falls apart.
- Example: the map shows the robot at the dock while it is physically elsewhere.

Candidate causes, none confirmed:

- the LiDAR or its communication
- wheel odometry (an encoder)
- the IMU
- sensor communication
- SLAM/firmware
- the app or cloud layer

## Diagnostic plan

We work from least to most invasive. We do not buy spare parts until the evidence
points at one of them.

| Phase | What | Status |
|---|---|---|
| 1 | LAN discovery: ARP, UDP broadcasts, open ports | **tool ready, awaiting robot measurements** |
| 2 | Tuya test: is it Tuya? Which data points (DPs) can be read locally? | pending phase 1 |
| 3 | Network capture (idle, cleaning, mapping, manual drive, docking, map collapse) | planned |
| 4 | App (APK) analysis: endpoints, SDKs, map/trajectory formats | planned |
| 5 | Minimal read-only client: `info`, `status`, `monitor` | planned |
| 6 | Synchronised JSONL logger (pose, state, errors, map updates) | planned |
| 7 | Automated `diagnose` with PASS/WARN/FAIL/UNKNOWN/UNSUPPORTED | planned |
| 8 | Hardware: passive UART sniffing of the LiDAR ↔ mainboard link | only if needed |

Hypotheses and evidence: [research/hypotheses.md](research/hypotheses.md).
Sources: [research/sources.md](research/sources.md).

## Requirements

- Windows, macOS or Linux.
- [uv](https://docs.astral.sh/uv/getting-started/installation/). It downloads a
  suitable Python (3.11+) by itself. To install uv:
  - Windows (PowerShell):
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
  - macOS / Linux:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- Git, to clone the repository.
- A computer on the **same local network as the robot**. The robot uses 2.4 GHz
  Wi-Fi; your computer can be on 5 GHz or Ethernet of the same router. It must
  not be on a guest network or a VPN.

## Installation

```bash
git clone https://github.com/stecik/robzone_diagnostics_toolkit.git
cd robzone_diagnostics_toolkit
uv sync
```

Check that it works:

```bash
uv run robzone-diag --help
```

You can also run it without cloning:

```bash
uvx --from git+https://github.com/stecik/robzone_diagnostics_toolkit robzone-diag --help
```

## Commands

Every command has `--help`, for example `uv run robzone-diag discover --help`. Add
`-v` (or `-vv`) before the command for more log output, e.g.
`uv run robzone-diag -v discover`.

### `models`: which models the tool knows

```bash
uv run robzone-diag models
```

Lists each known model with its support level and the state of every capability:

| State | Meaning |
|---|---|
| TBD | Not investigated yet |
| Experimental | Implemented, not yet verified on a physical device |
| Verified | Verified on a physical device |
| Unsupported | Confirmed not exposed |

Add `--json` for machine-readable output.

### `discover`: find devices on your network

```bash
uv run robzone-diag discover --output captures/discover.json
```

What it does:

- **Listens** for 30 s (`--duration`) on UDP 6666, 6667 and 7000 for device
  broadcasts. It decodes Tuya LAN announcements (protocol, device ID, product key).
- Reads your computer's **ARP table**, i.e. the IP → MAC list of nearby devices.
- Looks up hostnames via reverse DNS.

Traffic it sends:

- One empty UDP datagram to each host that broadcast, so your computer learns that
  host's MAC address. `--no-arp` skips this.
- With `--tuya-request`, the standard Tuya discovery request every 6 s. This is the
  same request the Tuya app sends. Protocol 3.5 devices answer only to it.

Before running it:

- The robot is on and connected. The Wi-Fi LED is solid blue.
- Your computer is on the same network.
- On Windows, the first run may show a **Windows Defender Firewall** prompt for
  Python. Allow it on **private networks**, otherwise broadcasts are blocked.

Successful output looks like this (addresses shortened):

```
Hosts that sent broadcasts:
  192.168.1.50      a8:80:55:xx:xx:xx
      Broadcasts: 2 on UDP 6667
      Tuya announcement: protocol 3.4, encrypted broadcast, device ID <...>, product key <...>
      Model: UNKNOWN (no verified fingerprint matches; see: robzone-diag models)

Other hosts in this computer's ARP table (no broadcasts heard): 7
  192.168.1.1      d8:21:da:xx:xx:xx  router.lan
```

What the output means:

- **Model: UNKNOWN** is expected today. No Robzone model has a verified network
  fingerprint yet, and the tool never guesses a model from weak hints such as a MAC
  vendor prefix.
- A **Tuya announcement** shows only that *some* device on your LAN speaks Tuya.
  Plugs, bulbs and cameras often do. Check that it is the robot: compare the MAC
  with your router's DHCP list, or switch the robot off and run `discover` again.

Options:

- `--redact`: masks MACs (keeping the vendor prefix), hostnames and device IDs, for
  output you want to post publicly.
- `--json`: prints the full report to the terminal.
- `--output FILE`: saves the report. Keep raw reports in `captures/`, which is
  gitignored.

### `scan`: which TCP ports a device has open

```bash
uv run robzone-diag scan 192.168.1.50
uv run robzone-diag scan 192.168.1.50 --ports all --output captures/scan-all.json
```

- It connects to each port and closes the connection. It sends no data, only
  records a banner if the service sends one first.
- It only accepts private LAN addresses.
- `--ports`:
  - `common` (the default): 24 ports that IoT devices often use
  - `all`: 1–65535, which can take 10+ minutes
  - a list such as `6668,8000-9000`
- Port names in the output are **conventions**, not proof of the service behind
  them.
- Small Wi-Fi devices drop connections when probed too fast. Keep the defaults
  (8 parallel connections, 3 s timeout). If ports show as "No answer", retry with
  `--workers 2 --timeout 5`.

## Interpreting results

Two kinds of status appear in this project:

- **Capability states** (`models`): TBD / Experimental / Verified / Unsupported
  describe how far a model integration has been established.
- **Test results**, used by the future `diagnose` command:

  | Result | Meaning |
  |---|---|
  | PASS | This specific check met its verified conditions. It does not mean the whole component is healthy. |
  | WARN | Anomaly found; needs further checking. |
  | FAIL | This check demonstrably failed. The likely cause is reported separately, with evidence. |
  | UNKNOWN | Not enough reliable data to conclude. |
  | UNSUPPORTED | The model integration does not provide the needed data. This is not a device fault. |

  When a device that has the capability simply cannot be reached, the result is
  UNKNOWN, not UNSUPPORTED.

Exit codes are stable:

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | Runtime error, e.g. a network error or a port that cannot be bound |
| 2 | Invalid arguments |
| 3 | Ran correctly but found nothing |
| 130 | Interrupted with Ctrl+C |

## Troubleshooting

**`discover` hears nothing:**

- On Windows, check that the network is **Private**:
  ```powershell
  Get-NetConnectionProfile
  ```
  On a *Public* profile, Windows blocks inbound broadcasts. Also allow Python
  through the firewall on private networks.
- Make sure you are not on a guest Wi-Fi or a VPN. Some routers have "AP/client
  isolation", which blocks traffic between Wi-Fi clients; turn it off for the
  diagnosis.
- Listen for longer (`--duration 120`) and try `--tuya-request`.
- No Tuya announcement does **not** prove the robot does not use Tuya. Protocol
  3.5 devices stay silent unless asked, and firewalls can drop broadcasts.

**`Could not listen on UDP 6667`:** another program uses the port. Close other Tuya
tools, e.g. a running TinyTuya scan or Home Assistant on the same computer.

**The robot is not in the ARP table:** your computer has not talked to it recently.
Find its IP in the router's DHCP list, then run `scan <ip>`, or ping it first.

**`scan` shows every port as "No answer":** the robot may be offline or asleep, or
the address is wrong. Check that the Wi-Fi LED is solid blue, check the IP, and
retry with `--workers 2 --timeout 5`.

## Safety and privacy

- **Read-only by design.** Commands only listen, read and open/close connections.
  Anything that could change robot configuration, reset it, change calibration or
  firmware, or enter a service mode will only ever be added as a separate, clearly
  marked command that requires explicit confirmation.
- `scan` refuses non-private addresses. Only scan devices you own.
- Raw reports can contain MAC addresses, device IDs and hostnames. Keep them in
  `captures/` (gitignored). Use `--redact` and review the output before sharing.
- Never publish Tuya `local_key`s, account tokens, Wi-Fi passwords or packet
  captures. The `.gitignore` blocks common file names (`devices.json`, `*.pcap`,
  `*.apk`, `.env`, …).

## Project layout and contributing

The code is split into model-agnostic parts and model-specific parts:

- model-agnostic: `discovery/`, `protocols/`
- model-specific: `models/<model>/`

Adding a model means adding one package and one registry entry. See
[CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, adding a model, protocol
parsers, sanitizing captures and the PR checklist.

## License

Not chosen yet.
