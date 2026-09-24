import base64
import json

import pytest
from hct_fixtures import FAKE_AUTH, FAKE_DEVICE, FAKE_HOST, frame_bytes

from robzone_diag.protocols.hct import frames, messages

CREDS = messages.Credentials(FAKE_HOST, FAKE_AUTH, FAKE_DEVICE)


def _decode(name: str) -> frames.Frame:
    [frame] = frames.FrameDecoder().feed(frame_bytes(name))
    return frame


@pytest.mark.parametrize(
    "name", ["ping", "ping_ack", "status_push", "map_query_from_app", "map_reply_with_pose"]
)
def test_captured_frames_decode_and_reencode_identically(name):
    raw = frame_bytes(name)
    assert _decode(name).encode() == raw


def test_frame_types_match_observations():
    assert _decode("ping").type_name == "ping"
    assert _decode("ping_ack").type_name == "ping-ack"
    assert _decode("status_push").type_name == "notification"
    assert _decode("map_query_from_app").type_name == "request"
    assert _decode("map_reply_with_pose").type_name == "reply"


def test_decoder_handles_arbitrary_chunking():
    stream = frame_bytes("ping_ack") + frame_bytes("status_push") + frame_bytes("ping_ack")
    decoder = frames.FrameDecoder()
    decoded = []
    for i in range(0, len(stream), 7):
        decoded += decoder.feed(stream[i : i + 7])
    assert [f.type_name for f in decoded] == ["ping-ack", "notification", "ping-ack"]
    assert decoder.pending_bytes == 0


def test_decoder_rejects_desynchronised_stream():
    with pytest.raises(frames.FrameError):
        frames.FrameDecoder().feed(b"\x05\x00\x00\x00" + bytes(16))


def test_our_map_query_matches_the_app_byte_for_byte():
    app = _decode("map_query_from_app")
    ours = frames.request(app.seq, messages.encode_request(CREDS, messages.map_query()))
    assert ours.body == app.body
    assert ours.encode() == app.encode()


def test_ping_header_matches_the_app():
    app = _decode("ping")
    assert frames.ping(app.seq).encode() == frame_bytes("ping")


@pytest.mark.parametrize("command", ["100", "102", "104", "108", None])
def test_refuses_to_encode_actuating_commands(command):
    with pytest.raises(messages.MessageError):
        messages.encode_request(CREDS, {"transitCmd": command, "start": "1"})


def test_parses_status_push():
    value = messages.payload(messages.decode_body(_decode("status_push").body))
    status = messages.StatusReport.from_value(value)
    assert status.work_state == 2
    assert status.battery == 60
    assert status.error == 0
    assert status.firmware == "7.6.2716(332)"
    assert status.relocalisation_notice == 0


def test_parses_pose_reply():
    reply = _decode("map_reply_with_pose")
    pose = messages.MapReport.from_value(messages.payload(messages.decode_body(reply.body)))
    assert pose.robot_pos == (367, 367)
    assert pose.heading_deg == 254
    assert (pose.map_width, pose.map_height) == (700, 700)
    assert pose.empty_map is True


def test_pose_parser_tolerates_missing_position():
    pose = messages.MapReport.from_value({"robotPos": "", "deg": "x"})
    assert pose.robot_pos is None
    assert pose.heading_deg is None


def test_strip_secrets_removes_identifiers():
    document = messages.decode_body(_decode("map_query_from_app").body)
    stripped = json.dumps(messages.strip_secrets(document))
    for secret in (FAKE_AUTH, FAKE_DEVICE, FAKE_HOST):
        assert secret not in stripped


def test_decodes_track_points():
    # Layout seen in a real capture: 04 04, counter, count, then (x, y) uint16 pairs.
    raw = bytes.fromhex("0404" + "00000000" + "0300" + "75016f01" + "76016f01" + "91016f01")
    track = messages.decode_track(base64.b64encode(raw).decode())
    assert track.counter == 0
    assert track.points == [(373, 367), (374, 367), (401, 367)]


def test_track_decoder_tolerates_bad_input():
    assert messages.decode_track("") is None
    assert messages.decode_track("not base64!") is None
    assert messages.decode_track("BAQ=") is None  # too short
