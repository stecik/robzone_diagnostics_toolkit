# Experiment 02: capture the RobZone app's traffic

**Goal:**

- Test [H3](../hypotheses.md): does the RobZone app talk to the robot on TCP 8888
  with the Clouds Robot/Sencor-style JSON protocol?
- If it does, learn the exact framing, protocol version and read-only queries our
  firmware uses.
- In both cases, record which cloud hosts the app contacts.

**Why the phone:** the computer cannot see traffic between the phone and the robot
on Wi-Fi. A capture app on the phone can.

**Risk to the robot:** none. We only record what the official app does anyway.

**Privacy: the capture contains secrets.** Expect the robot's `authCode` and
device ID, account tokens and cloud hostnames. Keep it in `captures/`, which is
gitignored. Never commit it or post it publicly.

## Tool

[PCAPdroid](https://github.com/emanuele-f/PCAPdroid) is an open-source Android
capture app. It runs as a local VPN and does not need root. Install it from Google
Play or F-Droid.

## Steps

1. Configure PCAPdroid:
   - **Target apps:** select only **RobZone**.
   - **Dump mode:** "PCAP file".
2. Start the capture in PCAPdroid.
3. In the RobZone app, do only read-only things:
   - open the robot
   - wait for the status and map to load (about 30 s)
   - open the map screen
   - leave the app
4. Stop the capture. Copy the `.pcap` file to your PC as
   `captures/02-app-idle.pcap`.
5. Optional, only if you want to: repeat while you start a short cleaning run from
   the app, stop it, and send the robot to the dock. Save that capture as
   `captures/02-app-control.pcap`. It shows which commands the app sends.

## What to report back

- Where the files are saved. Do not paste their contents into chat; I will analyse
  them locally.
- The RobZone app version and the robot firmware version, if the app shows them.

## How to read the outcome

| Observation | Interpretation | Next step |
|---|---|---|
| Phone → robot:8888 with 20-byte header + JSON | H3 confirmed | Implement read-only `status` (state query) and `map`/pose query, then `monitor` logging the pose over time |
| Only TLS to cloud hosts, nothing to 8888 | App uses cloud only; robot port 8888 unused by the app | Check whether robot talks to the cloud in the same format; consider APK analysis |
| Plain TCP to a cloud host on 20008 or similar | Cloud relay of the same protocol | Decode the relay messages; still read-only |
