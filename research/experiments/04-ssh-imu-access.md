# Experiment 04: SSH access for raw IMU diagnostics

Date: 2026-09-24. Reference unit: DUORO X-MAX PROFI.
Previously observed firmware: `7.6.2716(332)`; not re-read during this experiment.

## Goal and authorization

The owner selected SSH investigation to obtain raw gyroscope measurements and
distinguish a sensor problem from calibration or firmware compensation. The owner
confirmed that they do not have service login credentials.

## Observations

- SSH is reachable on the configured robot address, TCP 22.
- The server identifies itself as `OpenSSH_7.6`. Key exchange succeeded using
  `curve25519-sha256`, an Ed25519 host key, and `chacha20-poly1305@openssh.com`.
- The host key was saved locally in gitignored `captures/04-ssh-known-hosts`.
- A `root` authentication-method probe was rejected; the server advertised
  `publickey,password,keyboard-interactive`. This does not prove that the account
  exists or that root password login is permitted.
- Three password attempts were rejected: the generic `root/root` guess, then the
  two root password variants published in the Congatudo setup guide for other
  robot models. No dictionary scan was run. The relation between those models and
  this robot is unverified.
- Every password attempt returned `Configured password was not accepted`.
- No shell was obtained. The requested `id; uname -a` command never ran.
- No raw IMU samples, calibration files, or internal logs were obtained. No robot
  configuration was changed by our commands; authentication can itself create
  server log entries.
- `adb devices` found no attached Android device. The local ADB server started.

## What the earlier measurements do and do not establish

The repeatable drift establishes a fault in the reported heading estimate. It is
consistent with uncompensated gyroscope bias, but that causal explanation remains
a hypothesis until the signal path is inspected. A reported 90-degree turn alone
does not establish the raw gyroscope's scale factor: `deg` is a processed pose
estimate. Likewise, stationary reported x/y does not validate wheel encoders during
motion. Start/end heading differences are modulo 360 degrees and cannot establish
how much rotation SLAM corrected during the intervening run.

For useful discrimination we need:

1. IMU identity and the source of the measurements: direct sensor registers, MCU
   output, or an already corrected/fused stream.
2. Timestamped angular velocity on the available axes, units/scale, sample rate,
   temperature if available, and applied offsets/calibration status.
3. Stationary recordings and controlled turns, followed by comparison of raw and
   corrected values. Repeatability across warm-up and restart matters.

A stable nonzero raw zero-rate output alone does not prove a defective chip. Its
size and stability must be compared with the identified part's specification and
the firmware's compensation. No chip-specific fault threshold is established yet.

## Next access path

The least invasive remaining investigation is static analysis of the owner's
installed RobZone APK (`com.robzone.robe`) and, if obtainable, its exact firmware
image. Look for documented service/debug interfaces and firmware download metadata.
Finding either is uncertain; an APK need not contain SSH credentials or raw IMU
commands. Downloading firmware for offline inspection does not require flashing it.

To obtain the installed APK, connect the Android phone over USB, enable USB
debugging, and authorize this PC. After `adb devices` identifies the phone, query
the package paths and pull the APK files into gitignored captures. Account data
and tokens are not needed for this initial static inspection.

If software access cannot be established, a service credential or physical console
is needed. A report of serial-console access on a Proscenic 790T is only a lead;
it does not verify this robot's PCB, pinout, voltage, or login behavior.

After obtaining a shell, first identify the OS, sensor drivers, running processes,
and existing diagnostic logs. Do not open an in-use serial device blindly: reading
it can consume data needed by the navigation process. Prefer an existing telemetry
or logging interface before considering instrumentation.

## Sources checked

- [Congatudo robot setup](https://congatudo.cloud/installation/robot-setup/):
  publishes two default root credential variants for named Conga models; both
  failed here. No claim of Robzone compatibility.
- [Proscenic 790T investigation, author report](https://community.home-assistant.io/t/proscenic-790t-integration/82969/90):
  reports a serial root console and subsequent SSH access after setting a password
  on that author's device. Not reproduced on this unit.

## Follow-up: owner's installed Android APK

The owner connected and authorized their Android phone over USB. `pm path` returned
one APK for `com.robzone.robe`; it was pulled without changing the installed app.

- App version: `5.0.9`, versionCode `1782268063` (package manager output).
- APK size: 74,832,662 bytes.
- APK SHA-256:
  `af3e542dcf687fec06c1dc01f2b2204507d164cc92fdcaf6b3b093fbb474fec2`.
- Local artifact: `captures/04-apk/robzone-5.0.9.apk` (gitignored).
- JADX 1.5.6 produced partial Java/resources under
  `captures/04-apk/decompiled`; it finished with 4,727 errors, not a clean
  decompilation. The APK contains `assets/ijiami.ajm` and architecture-specific
  `assets/ijm_lib/*/libexec.so`. Many app method bodies appear as empty stubs or
  `return null`, with invalid debug information. Those bodies cannot be treated as
  the app's actual runtime behavior.
- Android rejected `run-as com.robzone.robe`: package not debuggable. No private
  app storage was extracted. The app's external files/cache search returned no
  regular files within depth 3.

### Concrete leads in the readable code

Paths below are relative to `captures/04-apk/decompiled/sources/com/baole/blap/`.

| Evidence | Meaning and limitation |
|---|---|
| `module/deviceinfor/api/ConnectApi.java:398` | POST `robot/getRobotVersionForceInfoList.do`, returning a list of `VersionData`. Request construction is hidden. |
| `module/deviceinfor/api/ConnectApi.java:401` | POST `robot/getRobotWifiUpdateInfo.do`, returning `VersionData`. This is metadata, not yet a firmware file URL. |
| `module/deviceinfor/bean/VersionData.java:16` | Fields include `softVer`, `updateUrls`, `url`; nested `FirmVersionInfo` includes firmware version, module, size, sign and URL. |
| `network/tool/BLRobotControlParamModelTool.java:345` | `setUploadLog(...)` exists, but its implementation and wire command are hidden. |
| `module/deviceinfor/activity/PlatFormOptionActivity.java:218` | A `tv_upload_log` UI field exists. The RobZone Czech asset translates `CL_OPN_UploadRobotLog` as "Nahrat zaznam" (diacritics omitted here). Availability on this model is unverified. |
| `module/deviceinfor/api/ConnectApi.java:440` | POST `/common/uploadLog.do` exists. Its relationship to the robot-log command is not established; no upload was triggered. |
| `server/HttpRobotClient.java:95` | Despite the name `getRobotInfo.do` and GET method, parameters include Wi-Fi password and cloud configuration. This is a provisioning lead, not a verified read-only diagnostic endpoint; it was not called. |

Searches of readable app sources and all five DEX string tables found no usable SSH
login or raw-IMU/calibration interface. The visible `GYROSCOPE` constant is a robot
category, and Unity's `toggleGyroscopeSensor` is not evidence of robot telemetry.
Because code is protected, absence from these searches does not establish that an
interface cannot exist.

The initial logcat snapshot was restricted to the running RobZone process. It had
180 lines, with no firmware URL, update metadata, or IMU values. The earlier PCAP
files also yielded no firmware-download URL in the plaintext search. The owner was
asked to open robot information and the firmware-update screen, without starting
an update, to check whether that reveals useful metadata in the app's log.

### Firmware screen checked after the owner's confirmation

The UI hierarchy was read with Android `uiautomator dump` and saved locally as
`captures/04-apk/firmware-screen.xml`. Only RobZone UI text was inspected.

| Module shown by the app | Current version |
|---|---|
| `wifi` | `1.0.51(2026)` |
| `system3308` | `1.20.219(21101819)` |
| `mcu` | `7.6.2716(332)` |

The app labels all three as the latest version. This records what the UI displayed,
not an independent verification of update availability. The version previously
reported over the LAN is thus labelled **MCU** in the app, not the entire Linux
system's version.

The post-confirmation RobZone-only logcat snapshot had 122 lines and no matches for
`http`, `firmware`, `updateUrls`, `version`, `getRobotVersion`, or `getRobotUpdate`.
Opening the update page did not provide a firmware download URL through logcat.

`system3308` suggests a possible Rockchip RK3308 platform, but the CPU is not
confirmed. The [Firefly RK3308B FAQ](https://wiki.t-firefly.com/en/ROC-RK3308B-CC-PLUS/faq.html)
documents an example SSH root password of `123` for its development-board build.
One connection using that candidate **timed out**, so the credential was not
validated or rejected by this robot. A separate OpenSSH connectivity check with a
5-second timeout also failed before authentication. Do not count this as another
rejected password or evidence of account lockout.

The phone remained connected to the expected Wi-Fi subnet. The owner was asked to
confirm the robot's power and current IP in the app. Raw IMU, SSH access, a firmware
image, and the hardware-versus-calibration diagnosis remain unresolved.

### Retry after the owner powered the robot back on

The owner confirmed that they had switched the robot off to consider opening it,
then switched it back on. On retry the same SSH host key was accepted and the
server explicitly rejected `root/123`. Two further bounded candidates,
`root/firefly` and `root/rockchip`, were also rejected. These candidates come from
development-board documentation/discussion, not a verified Robzone service manual:
[Firefly minimal-system documentation](https://wiki.t-firefly.com/en/Core-3308Y/ubuntu_minimal_support.html)
and [RK3308B support discussion](https://bbs.t-firefly.com/forum.php?mod=viewthread&tid=3106).

There have now been six explicit password rejections in this investigation, plus
the earlier authentication-method probe and connection timeouts. No shell command
has executed on the robot.

The APK's `res/xml/network_security_config.xml` only enables cleartext traffic and
does not explicitly trust user-installed CA certificates. Custom trust-manager
classes exist, but protected method bodies prevent determining which cloud client
uses them. Capturing HTTPS metadata is therefore a separate, uncertain next step;
plain packet capture does not decrypt TLS, and no certificate/proxy was installed
on the phone in this investigation. Neither the phone nor the robot was rooted or
flashed.
