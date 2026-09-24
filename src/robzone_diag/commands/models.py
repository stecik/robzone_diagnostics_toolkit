"""``robzone-diag models``: list model integrations and how verified each capability is."""

from __future__ import annotations

import argparse
import json

from robzone_diag.exitcodes import ExitCode
from robzone_diag.models.base import (
    CAPABILITY_LABELS,
    CAPABILITY_STATE_MEANING,
    ModelDefinition,
)
from robzone_diag.models.registry import all_models


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "models",
        help="list Robzone models this tool knows and their verified capabilities",
        description=(
            "List Robzone models known to this tool. For each model, every capability "
            "is marked TBD (not investigated), Experimental (implemented, not verified "
            "on hardware), Verified (verified on a physical unit) or Unsupported "
            "(confirmed not exposed)."
        ),
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    models = all_models()
    if args.json:
        print(json.dumps([_as_dict(m) for m in models], indent=2))
    else:
        print(render(models))
    return ExitCode.OK


def render(models: tuple[ModelDefinition, ...]) -> str:
    lines = ["Known Robzone models:", ""]
    for model in models:
        lines += [
            f"{model.name}",
            f"    Manufacturer:    {model.manufacturer}",
            f"    Model ID:        {model.model_id}",
            f"    Support:         {model.support}",
            f"    Protocol:        {model.protocol or 'unknown (under investigation)'}",
            f"    Tested hardware: {model.tested_hardware}",
            "    Capabilities:",
        ]
        width = max(len(label) for label in CAPABILITY_LABELS.values())
        for capability, label in CAPABILITY_LABELS.items():
            lines.append(f"        {label:<{width}}  {model.state(capability)}")
        lines += [f"    Note: {note}" for note in model.notes]
        lines.append("")
    lines.append("Capability states:")
    lines += [f"    {state:<12} {meaning}" for state, meaning in CAPABILITY_STATE_MEANING.items()]
    return "\n".join(lines)


def _as_dict(model: ModelDefinition) -> dict:
    return {
        "model_id": model.model_id,
        "manufacturer": model.manufacturer,
        "name": model.name,
        "support": str(model.support),
        "protocol": model.protocol,
        "tested_hardware": model.tested_hardware,
        "capabilities": {str(c): str(model.state(c)) for c in CAPABILITY_LABELS},
        "notes": list(model.notes),
    }
