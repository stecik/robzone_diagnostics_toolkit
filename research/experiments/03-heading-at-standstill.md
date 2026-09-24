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

Next steps:

1. Run steps B, C and D.
2. If the drift persists after a power cycle on the dock, run a monitored cleaning
   run from the dock. Mark the moment the map visibly breaks, then compare it with
   the heading and trajectory logs.
