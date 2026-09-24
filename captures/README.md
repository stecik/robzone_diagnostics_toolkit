# captures/

Local working directory for raw diagnostic output: `discover`/`scan` JSON reports,
packet captures, telemetry sessions.

**Everything in this directory except this README is gitignored**, because raw
output can contain MAC addresses, device IDs, hostnames and other identifiers.

- Save output here: `uv run robzone-diag discover --output captures/discover.json`
- To share output publicly (GitHub issue, PR), re-run with `--redact` and review the
  file yourself before posting.
- Material used by automated tests goes to `tests/fixtures/` instead, and only in
  minimal, sanitized form (see [CONTRIBUTING.md](../CONTRIBUTING.md#sanitizing-captures)).
