# Security assessment: Robzone DUORO X-MAX PROFI (maintainer's unit)

Date: 2026-09-24.

**Scope:** defensive only.
- Sources are public vulnerability databases, matched against what this project
  measured over the LAN (experiments 01 and 02).
- No exploitation, no password guessing, no fuzzing.

## Versions reported by the robot / app

| Component | Version | Notes |
|---|---|---|
| Wi-Fi module | `1.0.51(2026)` | shown in the app |
| System (Linux) | `1.20.219(21101819)`, label `system3308` | Most likely a Rockchip **RK3308** SoC (inferred from the label). The build string looks like a 2021-10-18 date. |
| MCU | `7.6.2716(332)` | also reported in the LAN protocol (`version` in the status push) |

## Exposed services (measured) and known issues

**TCP 22, `OpenSSH_7.6`.** Password and keyboard-interactive login are enabled.

- No known pre-auth remote code execution for 7.6.
- CVE-2024-6387 ("regreSSHion") affects 8.5p1–9.7p1 and below 4.4p1, **not 7.6**
  ([NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-6387),
  [Qualys](https://www.qualys.com/2024/07/01/cve-2024-6387/regresshion.txt)).
- Applicable, but not RCE:
  - username enumeration, [CVE-2018-15473](https://nvd.nist.gov/vuln/detail/CVE-2018-15473),
    CVSS 5.3
  - Terrapin, [CVE-2023-48795](https://nvd.nist.gov/vuln/detail/CVE-2023-48795),
    needs a man-in-the-middle
  - post-auth scp injection, [CVE-2020-15778](https://nvd.nist.gov/vuln/detail/CVE-2020-15778),
    disputed
- The practical risk is brute force against password login from inside the LAN.
- The vendor may have backported fixes. This is not verifiable without access.

**TCP 8000, `Mongoose/6.11`** (Cesanta embedded web server, 2018 era).

- 6.11 is within the affected range (≤ 6.13) of HTTP-core use-after-free bugs
  rated CVSS 9.8:
  [CVE-2018-20353](https://nvd.nist.gov/vuln/detail/CVE-2018-20353) and
  [CVE-2018-20354](https://nvd.nist.gov/vuln/detail/CVE-2018-20354).
- Further CGI and MQTT bugs apply only if those features are compiled in (unknown).
- **This is the weakest service on the device.** Treat port 8000 as reachable by
  anyone on the same network.

**TCP 53, DNS.** The software is unknown, so it cannot be assessed.

**BusyBox 1.27.2.** udhcpc is affected by
[CVE-2018-20679](https://nvd.nist.gov/vuln/detail/CVE-2018-20679) and
[CVE-2019-5747](https://nvd.nist.gov/vuln/detail/CVE-2019-5747). These are memory
leaks via a malicious DHCP server on the same LAN, not RCE.

## Weaknesses by design (no CVE)

- **TCP 8888 local control is plaintext with a static `authCode`.**
  - Anyone who sees one app↔robot exchange on the LAN can read the robot's
    state and map, and control it.
  - The same design is documented for related robots (Proscenic 790T,
    [robotbona](https://github.com/felix-engelmann/robotbona)).
- **Plaintext cloud relay (TCP 20008) carries the account token.**
  - Anyone on the network path between phone and cloud can capture it, e.g. on
    public Wi-Fi.
  - The closest analogue with a CVE:
    [CVE-2019-12820](https://nvd.nist.gov/vuln/detail/CVE-2019-12820) (another
    robot vacuum sending credentials over plain HTTP).
- **No firmware updates since about 2021** for the system image. The vendor is not
  expected to fix any of the above.

No public advisory or CVE was found for HCT Robot / Haocheng, Robzone, Sencor,
Proscenic or the RK3308 BSP.

## Threat model

- The robot has no internet-facing port as long as the router does no port
  forwarding or UPnP mapping to it. It only connects **out** to `*.hctrobot.com`.
- All listed service vulnerabilities therefore need an attacker **inside the home
  network**: a Wi-Fi guest, a compromised PC or phone, or another IoT device.
- Worst case, with the robot compromised:
  - the attacker gets your floor plan and control of the vacuum;
  - the attacker gets a Linux box inside your LAN to attack other devices from.
- The robot has no camera. Whether it has a microphone is unknown.

## Recommended mitigations (owner's choice)

1. Check the router: **no port forwarding and no UPnP mapping** to the robot's IP.
   Disable UPnP if nothing needs it.
2. When diagnostics are finished, move the robot to an **isolated guest/IoT Wi-Fi**
   with client isolation.
   - Main LAN devices then cannot reach it, and it cannot reach them.
   - Trade-off: the app will control it via the cloud relay instead of LAN, and
     this tool must run from the same isolated network.
3. Use a **unique password** for the RobZone account, and assume its token can be
   exposed.
4. Don't use the RobZone app on public or untrusted Wi-Fi.
5. Optionally block the robot's internet access entirely. See the cloud discussion;
   the effect on local control is untested.
