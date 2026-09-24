import json

import pytest

from robzone_diag.cli import main
from robzone_diag.exitcodes import ExitCode


def test_no_command_prints_help_and_returns_usage(capsys):
    assert main([]) == ExitCode.USAGE
    assert "discover" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["models", "discover", "scan"])
def test_every_command_has_help(command, capsys):
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_models_json(capsys):
    assert main(["models", "--json"]) == ExitCode.OK
    models = json.loads(capsys.readouterr().out)
    assert models[0]["model_id"] == "duoro-xmax-profi"
    assert models[0]["support"] == "Active development"


def test_scan_refuses_public_addresses(capsys):
    assert main(["scan", "8.8.8.8"]) == ExitCode.USAGE
    assert "not a private LAN address" in capsys.readouterr().err


def test_scan_rejects_bad_port_spec(capsys):
    assert main(["scan", "192.168.0.1", "--ports", "99999"]) == ExitCode.USAGE
