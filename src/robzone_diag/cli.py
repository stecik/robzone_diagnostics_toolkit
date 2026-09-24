"""Command-line entry point: ``robzone-diag <command>``."""

from __future__ import annotations

import argparse
import logging
import sys

from robzone_diag import __version__
from robzone_diag.commands import (
    analyze,
    discover,
    import_credentials,
    models,
    monitor,
    scan,
    status,
)
from robzone_diag.exitcodes import ExitCode

COMMANDS = (models, discover, scan, import_credentials, status, monitor, analyze)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robzone-diag",
        description=(
            "Diagnostic toolkit for Robzone robotic vacuum cleaners. Read-only: it "
            "listens, reads and probes, but never changes robot settings."
        ),
        epilog="Run 'robzone-diag <command> --help' for details on a command.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="show more log messages (-vv for debug output)",
    )
    subparsers = parser.add_subparsers(title="commands", metavar="<command>")
    for command in COMMANDS:
        command.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    if not hasattr(args, "handler"):
        parser.print_help()
        return ExitCode.USAGE
    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return ExitCode.INTERRUPTED
    except OSError as exc:
        logging.getLogger(__name__).debug("Unhandled OS error", exc_info=True)
        print(f"error: {exc}", file=sys.stderr)
        return ExitCode.ERROR


def _configure_logging(verbosity: int) -> None:
    level = logging.WARNING - 10 * min(verbosity, 2)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


if __name__ == "__main__":
    sys.exit(main())
