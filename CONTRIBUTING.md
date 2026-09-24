# Contributing

Contributions are welcome. This matters most from owners of Robzone models other
than the DUORO X-MAX PROFI, since the maintainer has only that one robot.

## Development setup

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs
the right Python for you.

```bash
git clone https://github.com/stecik/robzone_diagnostics_toolkit.git
cd robzone_diagnostics_toolkit
uv sync                 # creates .venv with runtime + dev dependencies
uv run pytest           # run the tests
uv run ruff check .     # lint
uv run ruff format .    # format
```

Tests must pass without network access or a robot. Anything hardware-dependent
belongs in a fixture: a recorded, sanitized sample.

## Project layout

```
src/robzone_diag/
  cli.py              argument parsing and dispatch only
  commands/           one module per subcommand (register + run + output rendering)
  discovery/          model-agnostic LAN discovery: ARP, UDP listener, TCP scan
  protocols/          wire-protocol codecs, shared by any model that uses them
    tuya/             Tuya LAN protocol (broadcast decoder only)
    hct/              HCT Robot LAN protocol, TCP 8888: frames, messages, read-only client
  analysis/           offline measurements on monitor logs (e.g. heading drift)
  config.py           settings from environment / .env (secrets never on the command line)
  models/             everything model-specific (capabilities, enum labels)
    base.py           ModelDefinition, Capability, CapabilityState, SupportLevel
    registry.py       MODELS tuple, get_model(), identify()
    duoro_xmax_profi/ one package per model
  report.py           JSON report envelope
  redact.py           masking identifiers for public sharing
  exitcodes.py        stable process exit codes
tests/                pytest; fixtures must be sanitized
research/             reverse-engineering log: hypotheses, sources, experiments
docs/                 user and contributor documentation
captures/             local raw output, gitignored
```

Rules:

- Model-specific knowledge lives only under `models/<model>/`. Do not scatter
  `if model == ...` checks through the core.
- Protocol code lives under `protocols/<protocol>/`. It is shared, so if two models
  speak Tuya, both use `protocols/tuya`.
- Keep it simple: add abstraction only when a second real implementation needs it.

## Adding support for a new model

You should not need to understand the whole codebase. Most work happens in
`src/robzone_diag/models/<your_model>/`.

1. **Create the model package.** Copy `models/duoro_xmax_profi/` to
   `models/<your_model>/`. Give it a kebab-case `model_id`, the exact name
   printed on the device or its box, and `SupportLevel.ACTIVE_DEVELOPMENT`.
2. **Register it.** Import it in `models/registry.py` and add it to `MODELS`.
3. **Declare capabilities honestly.** Start with every capability at
   `CapabilityState.TBD`.
   - `EXPERIMENTAL`: code exists but has not been verified on hardware.
   - `VERIFIED`: tested on a physical unit.
   - `UNSUPPORTED`: you confirmed the data is not exposed.
4. **Fingerprint (optional; only with strong evidence).** Set `fingerprint` to a
   function `HostRecord -> bool`.
   - It must return `True` only on evidence that is unique to the model, for example
     a Tuya `productKey` seen on several units of that model.
   - A MAC vendor prefix alone is **not** enough: one Wi-Fi module vendor serves
     thousands of products.
   - When unsure, leave it `None`. Users can still choose the model by hand.
5. **Connect the protocol.** Reuse an existing module in `protocols/` if the device
   speaks it. Otherwise add `protocols/<name>/` with its own tests.
6. **Model-specific interpretation.** Model-specific data point maps, error-code
   tables and so on go in the model package, e.g. `models/<your_model>/datapoints.py`.
7. **Add fixtures and tests.**
   - Fixtures are minimal sanitized samples in `tests/fixtures/<your_model>/`: one
     datagram, one status response, a few lines of a session.
   - Add parser tests that use them.
8. **Update the docs.**
   - Add a row and a section to [docs/supported-models.md](docs/supported-models.md).
     A test checks that every registered model ID appears there.
   - Record evidence in `research/`.
9. **Open the Pull Request** (see below).

## Adding a protocol parser

- Put it in `src/robzone_diag/protocols/<protocol>/`. Keep it pure: bytes in,
  dataclasses out, no sockets.
- Cite the source of every format detail in the docstring: an open-source
  implementation, a vendor doc, or your own capture in `research/`.
- Test against **independently produced** data. Use real sanitized captures, or
  frames built by a reference implementation (see `tests/protocols/`, which uses
  TinyTuya). A test that only checks your encoder against your decoder proves little.
- Include negative tests: truncated frames, wrong checksums, unrelated traffic.

## Adding a diagnostic test

*(The `diagnose` framework does not exist yet. It will be built once there is real
telemetry to evaluate. These rules already apply.)*

- Each test declares the capabilities it needs. When the model's integration does
  not provide one, the result is **UNSUPPORTED**, not a failure.
- A test returns exactly one of the following. Report the likely cause separately,
  with evidence.

  | Result | Meaning |
  |---|---|
  | PASS | The executed check met its verified conditions. It does not mean the whole component is healthy. |
  | WARN | An anomaly that needs further checking. |
  | FAIL | The check demonstrably failed. |
  | UNKNOWN | Not enough reliable data to conclude, e.g. a lost connection or an incomplete recording. |
  | UNSUPPORTED | The model integration does not expose the needed data. |

- Thresholds must come from measurements, and those measurements must be
  documented in `research/`.

## Sanitizing captures

Raw captures and reports can contain Wi-Fi names, MAC addresses, device IDs, Tuya
`local_key`s, account tokens, public IPs and hostnames with personal names.

- Save raw material in `captures/`. It is gitignored.
- For sharing, use `--redact` on `discover`/`scan`:
  - MACs keep only their vendor prefix.
  - Device IDs and hostnames become stable pseudonyms.
  - Raw datagram bytes are dropped.
- **Always review the file yourself** before publishing. Redaction is best-effort.
- For fixtures, rewrite identifiers with obviously fake values
  (`bf00000000000000test`, `192.168.0.50`, `a8:80:55:00:00:02`). Then recompute
  checksums or re-encrypt, so the frame stays valid.
- Never commit `.pcap`/`.pcapng` files, APKs, TinyTuya `devices.json`/`snapshot.json`
  (they contain local keys) or `.env`. `.gitignore` blocks the common names.

## Documenting hardware

When you report on a unit, record:

- the exact model name on the label
- hardware revision
- firmware version, as shown in the app
- app name and version
- the Wi-Fi module marking, if the robot is opened
- purchase region and year

Take photos of PCBs and labels without serial numbers, or cover the serial numbers.

## Pull Request checklist

- [ ] `uv run pytest` and `uv run ruff check .` pass
- [ ] New or changed capabilities are backed by evidence in `research/`
- [ ] `docs/supported-models.md` updated (model, states, tested hardware, firmware)
- [ ] Fixtures are minimal and sanitized; no raw captures, keys or personal data
- [ ] README updated if a user-visible command or step changed
- [ ] PR description says which physical unit, firmware and app version you tested on,
      or states that you tested only against fixtures
