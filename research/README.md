# Research log

Reverse-engineering notes for Robzone robots. Everything here must be reproducible
by someone who was not there: state what was measured, how, on which unit, and
link sources.

| File | Contents |
|---|---|
| [hypotheses.md](hypotheses.md) | Open questions, with the evidence for and against each |
| [sources.md](sources.md) | Verified facts from manuals, app stores and open-source projects, with links |
| [experiments/](experiments/) | Step-by-step experiment protocols and their recorded results |
| [protocols/](protocols/) | Wire-protocol notes reconstructed from captures |
| [security-assessment.md](security-assessment.md) | Known vulnerabilities of the exposed services and mitigations (defensive) |

Rules:

- Separate **observation** ("UDP 6667 broadcast decoded as Tuya protocol 3.4") from
  **interpretation** ("so the robot uses Tuya").
- Never paste device IDs, local keys, MAC addresses (beyond the vendor prefix),
  Wi-Fi names or public IPs. Put unsanitized notes in `research/private/` (gitignored).
- Date entries (YYYY-MM-DD) and name the unit, firmware and app version if known.
