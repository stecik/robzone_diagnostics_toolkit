"""Process exit codes. These are part of the public interface: do not renumber."""

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    ERROR = 1  # runtime failure (network error, cannot bind, unreadable file, ...)
    USAGE = 2  # invalid command-line arguments (argparse also uses 2)
    NOT_FOUND = 3  # the command ran correctly but found nothing (no hosts, no device)
    INTERRUPTED = 130  # Ctrl+C
