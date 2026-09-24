import socket
import threading

import pytest

from robzone_diag.discovery import tcp


def test_port_spec_parsing():
    assert tcp.parse_port_spec("22,80,6666-6668") == [22, 80, 6666, 6667, 6668]
    assert tcp.parse_port_spec("common") == list(tcp.COMMON_PORTS)
    assert len(tcp.parse_port_spec("all")) == 65535


@pytest.mark.parametrize("spec", ["0", "70000", "90-80", "abc"])
def test_port_spec_rejects_invalid(spec):
    with pytest.raises(ValueError):
        tcp.parse_port_spec(spec)


def test_scan_detects_open_port_and_banner_on_localhost():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]

        def accept_and_greet():
            conn, _ = server.accept()
            conn.sendall(b"SSH-2.0-test\r\n")
            conn.close()

        thread = threading.Thread(target=accept_and_greet)
        thread.start()
        [result] = tcp.scan("127.0.0.1", [port], timeout=2).results
        thread.join()
    assert result.state is tcp.PortState.OPEN
    assert result.banner == b"SSH-2.0-test\r\n"


def test_scan_reports_closed_port_on_localhost():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    # Windows retries SYNs to a refusing loopback port for ~2 s before reporting it.
    [result] = tcp.scan("127.0.0.1", [free_port], timeout=6, retries=0).results
    assert result.state is tcp.PortState.CLOSED


def test_skips_retry_when_too_many_ports_are_silent(monkeypatch):
    calls = []

    def silent(host, port, timeout, grab_banner):
        calls.append(port)
        return tcp.PortResult(port, tcp.PortState.FILTERED)

    monkeypatch.setattr(tcp, "probe_port", silent)
    monkeypatch.setattr(tcp, "MAX_RETRY_PORTS", 3)
    outcome = tcp.scan("192.168.0.50", list(range(1, 11)))
    assert outcome.retry_skipped
    assert len(calls) == 10  # no second pass


def test_ctrl_c_returns_ports_probed_so_far(monkeypatch):
    monkeypatch.setattr(
        tcp, "probe_port", lambda h, p, t, g: tcp.PortResult(p, tcp.PortState.CLOSED)
    )
    monkeypatch.setattr(tcp, "PROGRESS_INTERVAL", 0.0)

    def interrupt(done, total):
        raise KeyboardInterrupt

    outcome = tcp.scan("192.168.0.50", list(range(1, 50)), workers=1, on_progress=interrupt)
    assert outcome.interrupted
    assert 0 < len(outcome.results) <= 49
