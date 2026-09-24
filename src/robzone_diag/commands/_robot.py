"""Shared plumbing for commands that talk to a robot: model choice and credentials."""

from __future__ import annotations

import argparse
from pathlib import Path

from robzone_diag import config
from robzone_diag.models.base import ModelDefinition
from robzone_diag.models.registry import get_model
from robzone_diag.protocols import describe
from robzone_diag.protocols.hct import DEFAULT_PORT
from robzone_diag.protocols.hct import PROTOCOL_ID as HCT_LAN
from robzone_diag.protocols.hct.messages import Credentials


class RobotSetupError(ValueError):
    pass


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        metavar="MODEL_ID",
        help="model ID (see 'robzone-diag models'); default: ROBZONE_DIAG_MODEL from .env",
    )
    parser.add_argument("--host", help="robot IP address; default: ROBZONE_DIAG_HOST from .env")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=config.DEFAULT_ENV_FILE,
        metavar="FILE",
        help="settings file with the robot's credentials (default: .env)",
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, metavar="SECONDS", help="network timeout (default: 5)"
    )


def resolve(args: argparse.Namespace) -> tuple[ModelDefinition | None, Credentials]:
    settings = config.load_settings(args.env_file)
    model_id = args.model or settings.get(config.PREFIX + "MODEL")
    model = get_model(model_id) if model_id else None
    if model and model.protocol != HCT_LAN:
        raise RobotSetupError(
            f"{model.name} uses {describe(model.protocol)}, which this command does not support"
        )
    host = args.host or settings.get(config.PREFIX + "HOST")
    if not host:
        raise RobotSetupError("robot IP unknown: pass --host or set ROBZONE_DIAG_HOST in .env")
    auth_code, device_id = config.require(settings, "AUTH_CODE", "DEVICE_ID")
    return model, Credentials(host, auth_code, device_id, DEFAULT_PORT)


def label(model: ModelDefinition | None, kind: str, value: int | None) -> str:
    if value is None:
        return "not reported"
    meaning = model.label(kind, value) if model else None
    if meaning:
        return f"{meaning} ({value})"
    return f"{value} (meaning unknown{'' if model else '; pass --model for labels'})"
