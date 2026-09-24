import socket

from robzone_diag.discovery import udp


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_receives_datagrams(monkeypatch):
    port = _free_udp_port()
    monkeypatch.setattr(udp, "TICK_INTERVAL", 0.05)

    def send_once(elapsed, count):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(b"hello", ("127.0.0.1", port))

    result = udp.listen([port], 0.5, on_tick=send_once)
    assert result.bound_ports == [port]
    assert result.datagrams and result.datagrams[0].data == b"hello"
    assert not result.interrupted


def test_ctrl_c_returns_partial_result(monkeypatch):
    monkeypatch.setattr(udp, "TICK_INTERVAL", 0.05)

    def interrupt(elapsed, count):
        raise KeyboardInterrupt

    result = udp.listen([_free_udp_port()], 30, on_tick=interrupt)
    assert result.interrupted
    assert result.listened_s < 5
