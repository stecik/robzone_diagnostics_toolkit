# Experiment 03: reported heading while the robot stands still

**Goal:** check whether the robot's own heading estimate (`deg` in the map/pose
reply) stays constant when the robot does not move.

A steady drift at standstill points at the gyroscope or at how its bias is
compensated (decision branch C in the project brief). That would also explain a map
that rotates, doubles walls and falls apart after a few minutes.

**Risk:** none.
- `monitor` sends only keepalive pings and the read-only map/pose query.
- Nothing in the experiment needs robot commands.

## Protocol

For every run:

- Close the RobZone app.
- Do not touch the robot unless the step says so.
- Save each log with `--output`.

**A. Paused away from the dock**

Robot paused in the room, where the app left it:

```powershell
uv run robzone-diag monitor --model duoro-xmax-profi --interval 3 --duration 180 --no-map --output captures/03a-paused.jsonl
```

**B. Charging on the dock**

```powershell
uv run robzone-diag monitor --model duoro-xmax-profi --interval 3 --duration 180 --no-map --output captures/03b-docked.jsonl
```

**C. After a power cycle**

1. Switch the robot off with its main switch.
2. Switch it on, on the dock.
3. Leave it completely still for 2 minutes, so the gyro can calibrate.
4. Run the same command, saving to `captures/03c-after-powercycle.jsonl`.

**D. Does `deg` really mean heading?**

1. Start the monitor, saving to `captures/03d-rotate.jsonl`.
2. Wait about 30 s.
3. Rotate the robot slowly by hand, about **90° clockwise**, flat on the floor.
   Do not lift it.
4. Wait another 30 s.

If `deg` is the heading, it must jump by about 90° on top of any drift.

Analyse each log:

```powershell
uv run robzone-diag analyze captures/03a-paused.jsonl
```

## Results

### 2026-09-24, run A (preliminary)

Conditions:

- Robot paused in the room after a 2-minute cleaning run (experiment 02).
- State `idle / standby (2)`.
- Firmware `7.6.2716(332)`.
- **Confirmed by the maintainer:** the robot stood physically still for the whole run.
  It did not move, clean or beep.

```
position (330, 353), 88 s, 30 samples:
    heading changes +1.53 °/s (+92 °/min), +134° in total; linear within ±1.6°
```

What the data shows:

- The reported position stayed constant.
- The reported heading grew **linearly by about 1.5 °/s**, i.e. more than a quarter
  turn per minute. It wrapped from 268 to -85, so the reported range is -90..270.
- An earlier 20 s run showed the same rate.

Interpretation, **not proven**:

- A still robot should report a nearly constant heading. A perfectly linear change
  is the signature of integrating a constant gyroscope bias.
- If this holds while the robot is really still, the heading estimate is wrong by
  about 90°/min whenever the LiDAR SLAM does not correct it. That fits a map that
  looks right at first and then rotates and doubles.

Limits:

- We do not know whether a paused robot keeps its SLAM running.
- We do not know whether a healthy X-MAX PROFI would report a frozen heading here.
- We have no second unit to compare with.
- The meaning of `deg` is inferred; step D tests it.

### 2026-09-24, run B: on the dock, charging

| Measurement | Value |
|---|---|
| State | `5`, observed right after "charging started"; now labelled "charging" |
| Heading | constant, 0 °/s over 178 s |
| Reported position | (330, 353), the pause position from run A, **not** the dock |

The robot had been carried back to the dock physically, but its reported position
did not change. On the dock the robot does not update its pose at all, so run B
says nothing about the gyroscope. Step C was therefore changed: the robot has to be
in a paused cleaning session, as in run A.

### 2026-09-24, run C: after a power cycle, paused

Procedure:

1. Main switch off, wait 10 s, on. Robot left on the dock.
2. Wait for solid blue Wi-Fi LED, plus 2 more minutes untouched.
3. Start cleaning from the app, pause it after about 15 s, close the app.
4. Robot untouched; the maintainer confirmed it stood still.

```
position (366, 387), 178 s, 60 samples:
    heading changes +1.53 °/s (+92 °/min), +272° in total; linear within ±1.4°
```

This is the **same rate as run A**, after a fresh boot and calibration opportunity.
The bias is constant and reproducible, and a power cycle does not remove it.

### 2026-09-24, run D: manual 90° rotation

Procedure:

1. Same paused session as run C.
2. After about 35 s, the maintainer rotated the robot by hand, flat on the floor,
   about 90° clockwise.
3. Polling every 2 s.

| Time | Heading (unwrapped) | Note |
|---|---|---|
| 1–33 s | 0 → 48 | drift about +1.5 °/s |
| 33.5–39.5 s | 48 → −36 | **manual rotation**: −84° in total, about −94° after removing the drift |
| 40–120 s | −36 → 88 | drift continues at the same rate |

Other observations:

- The reported position stayed at (366, 387) throughout; the rotation was in place.
- `analyze` reports ±49° residual for this run because the segment contains the
  rotation. Splitting segments at heading jumps is a to-do for the tool.

### 2026-09-24, run E: cleaning in a small arena, one pause

Setup:

- Arena about 1.50 × 1.65 m, closed on all sides by furniture. The dock sits in one
  corner.
- The session continued an existing map. The robot had been carried to the dock
  while paused, so `relocaNotice` was 1 from the start.
- Log: `captures/03e-cleaning-run.jsonl` (private).

Timeline (local time):

| Time | Event |
|---|---|
| 17:53 | Cleaning from the dock. The robot drives about two laps along the arena perimeter. |
| 17:58:31 | Paused by the maintainer, 20–30 cm in front of the dock. The reported pose puts it about 25 cells (about 45 cm) from its docked position. |
| 17:58–17:59:41 | Paused. The heading drifts +1.42 °/s at a constant position, about 100° in total. |
| 17:59:35 | Resumed with the robot's button. The state goes to 1 (cleaning); the pose stays frozen at the paused value. |
| **18:00:12** | `relocaNotice` goes 1 → **2**. The pose jumps to (374, 367), heading −27°. Clean time, trajectory and map are reset. |
| after | The robot drives erratically, "zig-zag". The maintainer observed it did not follow the usual systematic pattern. |

The app then showed: **„Změna oblasti selhala. Mapa ztracena. Začne nový úklid"**
("Area change failed. Map lost. A new cleaning will start."). This confirms that
`relocaNotice = 2` means *relocalisation failed, map lost*.

Other observations:

- Trajectory format decoded (`track` field): `04 04`, a uint32 counter, a uint16
  count, then uint16 (x, y) pairs in map cells.
- The perimeter laps give a map scale of about 1.8 cm per cell. This is a rough
  estimate from the arena size.
- While driving, the reported heading agrees with the direction of motion (y axis
  points down) within about ±40° at 3 s sampling. The SLAM pose is internally
  consistent while moving.

Interpretation, not proven, **one occurrence**:

- The heading drifted about 100° during the 1-minute pause.
- After resuming, the LiDAR scan could not be matched to the old map with that
  wrong heading, so relocalisation failed and the robot started a new map.
- Any stop has this effect: pausing, the robot waiting, or possibly the robot
  stopping by itself.

### 2026-09-24, run F: clean start, uninterrupted cleaning in the arena

Setup:

- Same arena as run E.
- The old map was deleted in the app, so the run started from an empty map. The
  robot started on the dock.
- The robot was not touched until the end.
- Log: `captures/03f-clean-run.jsonl` (private).

Timeline (local time):

| Time | Observation (owner) | Robot's own data |
|---|---|---|
| 18:06 | on the dock | pose (367, 367), heading 90°, empty map |
| 18:09:29 | passing next to the dock | 7 cells (about 13 cm) from the start pose: **matches** |
| 18:09:41 | crosses the arena away from the dock | about 45 cells (about 80 cm) from the dock: **matches** |
| 18:11:01 | "cleaning finished", should return to the dock | state 3, then 4 (returning). It circles about 12–16 cells from where it thinks the dock is. |
| 18:11–18:15 | lost: on the opposite side, bumps into things, then reverses at the dock but cannot dock | when physically at the dock, it reports 40–55 cells (about 70–95 cm) away |
| 18:15 | put on the dock by hand, "charging started" | pose (384, 345), **heading −60°**; the charger is recorded at (384, 345) |

The robot was docked the same way at the start and at the end: same physical place,
same physical orientation. Yet after about 10 minutes of uninterrupted cleaning:

- **The position error is about 28 cells (about 50 cm).**
- **The heading error is about 150°**: 90° at the start, −60° at the end.
- `relocaNotice` stayed 0 throughout: the robot did not notice it was lost.
- The app map (screenshot) shows about 4 m² for a floor of about 2.5 m², with
  smeared and duplicated outlines. The dock icon is in the middle of the map,
  although the dock stands in a corner.
- The robot's own trajectory is internally smooth, with no jumps. The error
  accumulates gradually and does not come from a single relocalisation event.

### Conclusion so far (runs A–F)

1. `deg` **is** the robot's heading estimate. A clockwise rotation decreases it, so
   positive means counter-clockwise.
2. The gyroscope **responds correctly to real rotation**: a hand rotation of about
   90° was reported as about 94°. So the gyroscope is alive and its scale factor is
   roughly right.
3. At standstill the heading drifts by a **constant +1.53 °/s** (counter-clockwise).
   The rate is identical before and after a power cycle.
4. The reported position does not change at standstill. So the wheel odometry
   reports no motion, and the drift is not wheel slip.

Interpretation, **not proven**:

- The robot is not removing the gyroscope's zero-rate offset (bias).
- Possible causes:
  - calibration fails
  - stored calibration data is wrong
  - the sensor's offset has grown beyond what the firmware compensates
- Raw MEMS gyroscopes often have offsets of this order before calibration
  (unverified; depends on the part). A robot is expected to calibrate the offset
  away while standing still.

5. During cleaning the error builds up anyway (run F): about 150° of heading and
   about 50 cm of position error after 10 minutes of uninterrupted cleaning, while
   the robot believes it is localised. The resulting map matches the owner's
   symptoms.
6. A pause makes it worse (run E). About 100° of heading drift during a 1-minute
   stop was followed by failed relocalisation and a lost map.

**Current diagnosis (decision branch C): the heading estimate is faulty because the
gyroscope's zero-rate offset is not compensated.**

- The LiDAR SLAM corrects part of the error while the robot moves: 1.5 °/s over
  10 min would be about 900°, and about 150° remained.
- It cannot keep up, so the map rotates and duplicates.

What remains open:

- Whether the gyro chip itself is faulty (offset out of spec or drifting), or its
  calibration or the firmware's compensation is. There is no reset or calibration
  function in the app, manual or online. The maintainer's search found none, and
  removing the battery did not help.
- Whether a marginal LiDAR also contributes. A healthy LiDAR SLAM in a small, simple
  arena would be expected to hold heading better. This is not measurable over the
  LAN protocol.

Next steps:

1. **Hardware, least invasive first.**
   1. Open the robot and photograph the mainboard.
   2. Identify the IMU chip (marking) and whether it sits on the mainboard or on a
      separate small board with a connector.
   3. Look up its datasheet zero-rate offset. Check the board for mechanical
      damage, loose mounting or cracked solder near the IMU.
2. **Software, needs the owner's decision.** SSH (OpenSSH 7.6) is open on the robot.
   A shell could show IMU logs and calibration files. Getting one means trying
   credentials, which is not a read-only step.
3. **Tooling.** Turn "heading drift at standstill" into a repeatable
   `diagnose` check. Thresholds should come from a healthy unit, which we do not
   have yet.
