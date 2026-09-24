# Verified sources

Checked 2026-09-24. "Verified" means the statement was read in the linked source,
not that it was confirmed on a robot.

## Robzone DUORO X-MAX PROFI / HOMEVAC

- Product page: <https://robzone.cz/products/duoro-x-max-profi>. It says
  "Laserová navigace" (laser navigation). The fetched page text names no app,
  protocol or Wi-Fi band.
- The manuals page <https://robzone.cz/pages/manualy/> lists the model as
  "DUORO X-MAX PROFI | HOMEVAC".
  - Device manual: [DXM_Profi_navod.pdf](https://a1q0ehe0nlbnrjn9.public.blob.vercel-storage.com/DXM_Profi_navod.pdf).
    **HOMEVAC** is the optional self-emptying station, not a separate robot. The
    diagram labels a "laserový lidar". Pairing: hold the main button about 3 s until
    it flashes blue.
  - Wi-Fi LED in the device manual:
    - fast blue = starting up
    - slow blue = connecting
    - solid blue = connected
    - fast red = connection error
  - The table of contents lists troubleshooting and technical-specification pages,
    but those pages are missing from the published PDF. There is no error-code table
    and no factory-reset procedure.
  - App manual: [DXM_app-navod-CZ.pdf](https://a1q0ehe0nlbnrjn9.public.blob.vercel-storage.com/DXM_app-navod-CZ.pdf).
    Text I extracted myself:
    - page 14: during pairing, join the Wi-Fi named **„SmartLife-číslo"**
      ("SmartLife-number")
    - page 15: an Android prompt reads „RobzoneRobot nemá přístup k internetu"
      ("RobzoneRobot has no internet access")
- <https://robzone.com/pages/mobile-application-robzone> says Robzone apps need
  **2.4 GHz** Wi-Fi.

## Mobile app

- The **RobZone** app: Google Play package
  [`com.robzone.robe`](https://play.google.com/store/apps/details?id=com.robzone.robe),
  [iOS id1437376073](https://apps.apple.com/cz/app/robzone/id1437376073). Robzone
  lists it for the X-Max Profi/Homevac.
- The App Store developer is 深圳豪成智能科技有限公司 (Shenzhen Haocheng Intelligent
  Technology), not Tuya Inc. The same developer publishes SENCOR Robotics,
  Cleanmate, FinluxBot and other white-label robot apps.
- Another app, "RobZone Robot" (`com.robzoneapp.android`), is listed for other models
  (X-Go, X-Comfort).

## Tuya local protocol (reference: TinyTuya)

- Ports ([const.py](https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/const.py)):
  - UDP 6666: v3.1 broadcasts
  - UDP 6667: v3.3+ encrypted broadcasts
  - UDP 7000: app / v3.5
  - TCP 6668: local control
- Broadcast key
  ([udp_helper.py](https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/udp_helper.py)):
  `md5(b"yGAdlopoPVldABfn")`.
- Frame formats
  ([message_helper.py](https://github.com/jasonacox/tinytuya/blob/master/tinytuya/core/message_helper.py)):
  - 55AA frames carry a CRC32.
  - 6699 frames use AES-GCM, with header bytes 4–18 as associated data.
  - Our decoder in `src/robzone_diag/protocols/tuya/broadcast.py` is tested against
    frames built by TinyTuya 1.20.
- Protocol 3.5 devices announce themselves only when asked (REQ_DEVINFO broadcast
  to UDP 7000), per [tinytuya discussion #260](https://github.com/jasonacox/tinytuya/discussions/260).
- Tuya Sweeper SDK ([docs](https://developer.tuya.com/en/docs/app-development/sweeper?id=Kceufzfwecnk1)):
  - For laser robots, the full map and path go to cloud storage as files, and MQTT
    tells the app where they are.
  - So on a Tuya laser robot, map data would **not** cross the LAN on TCP 6668.
- Tuya robot-vacuum standard DPs
  ([TuyaOS DP doc](https://developer.tuya.com/en/docs/iot-device-dev/basic_dp_interactive?id=Kf765i4rk91k1)):
  - DP 1 `switch_go`, DP 2 `pause`, DP 3 `switch_charge`, DP 4 `mode`,
    DP 5 `status`, DP 28 `total_error`
  - Older devices number these differently, so check the mapping on each device.

## Other LAN protocols worth recognising

- **Clouds Robot / Sencor family** (same app developer as RobZone):
  - [ha-SencorRobotics](https://github.com/MichalTichy/ha-SencorRobotics/blob/master/custom_components/sencor/connection.py)
    talks JSON over **TCP 8888**.
  - Each message has a 20-byte header (little-endian total length first) and needs
    an `authCode` taken from an app capture.
- **Xiaomi miio**: UDP 54321 hello packet
  ([python-miio](https://github.com/rytilahti/python-miio/blob/master/miio/miioprotocol.py)).
