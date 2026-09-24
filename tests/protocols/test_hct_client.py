"""Client tests against a fake robot that replays captured (sanitized) frames."""

import argparse
import json
import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest
from hct_fixtures import FAKE_AUTH, FAKE_DEVICE, frame_bytes

from robzone_diag.commands import monitor, status
from robzone_diag.protocols.hct import frames, messages
from robzone_diag.protocols.hct.client import HctClient, HctConnectionError


class FakeRobot:
    """Answers pings like the real robot and replies to map queries with the captured pose."""

    def __init__(self, push_status: bool = True):
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen()
        self.port = self.server.getsockname()[1]
        self.push_status = push_status
        self.received: list[frames.Frame] = []
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            conn, _ = self.server.accept()
        except OSError:
            return  # server closed before any client connected
        decoder = frames.FrameDecoder()
        with conn:
            while data := conn.recv(65536):
                for frame in decoder.feed(data):
                    self.received.append(frame)
                    conn.sendall(self._answer(frame))

    def _answer(self, frame: frames.Frame) -> bytes:
        if frame.type == frames.PING:
            ack = frames.FrameDecoder().feed(frame_bytes("ping_ack"))[0]
            out = frames.Frame(ack.type, ack.flags, frame.seq, ack.extra).encode()
            return out + (frame_bytes("status_push") if self.push_status else b"")
        reply = frames.FrameDecoder().feed(frame_bytes("map_reply_with_pose"))[0]
        return frames.Frame(reply.type, reply.flags, frame.seq, 0, reply.body).encode()

    def close(self):
        self.server.close()


@pytest.fixture
def robot():
    fake = FakeRobot()
    yield fake
    fake.close()


def _client(port: int) -> HctClient:
    return HctClient(messages.Credentials("127.0.0.1", FAKE_AUTH, FAKE_DEVICE, port), timeout=3)


def test_status_snapshot_reads_status_and_pose(robot):
    got_status, got_pose = status.read_snapshot(_client(robot.port))
    assert messages.StatusReport.from_value(got_status.value).battery == 60
    assert messages.MapReport.from_value(got_pose.value).robot_pos == (367, 367)
    sent = [f.type_name for f in robot.received]
    assert sent == ["ping", "request"]  # nothing but a ping and one read-only query


def test_only_read_only_queries_reach_the_robot(robot):
    with _client(robot.port) as client:
        client.ping()
        client.request(messages.map_query())
    for frame in robot.received:
        if frame.body:
            value = json.loads(frame.body)["value"]
            assert value["transitCmd"] in messages.READ_ONLY_TRANSIT_COMMANDS


def test_connection_refused_is_reported():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(HctConnectionError):
        _client(port).connect()


def test_monitor_writes_jsonl_without_secrets(robot):
    with tempfile.TemporaryDirectory() as tmp:
        _check_monitor_log(robot, Path(tmp) / "run.jsonl")


def _check_monitor_log(robot, log):
    summary = monitor.Summary()
    with log.open("w", encoding="utf-8") as out:
        recorder = monitor.Recorder(out, None, summary, keep_map=True)
        client = _client(robot.port)
        client.connect()
        args = argparse.Namespace(interval=0.2)
        try:
            monitor._session(client, args.interval, _deadline(0.7), recorder, summary)
        finally:
            client.close()
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    kinds = {r["kind"] for r in records}
    assert {"status", "map"} <= kinds
    pose = next(r for r in records if r["kind"] == "map")["pose"]
    assert pose["robot_pos"] == [367, 367]
    text = log.read_text(encoding="utf-8")
    assert FAKE_AUTH not in text and FAKE_DEVICE not in text
    assert summary.pose_reports >= 2


def _deadline(seconds: float) -> float:
    return time.monotonic() + seconds
