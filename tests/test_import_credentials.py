from hct_fixtures import FAKE_AUTH, FAKE_DEVICE, FAKE_HOST, frame_bytes

from robzone_diag.commands.import_credentials import find_credentials, mask, update_env_text


def test_finds_credentials_in_captured_app_request():
    capture = b"\xd4\xc3\xb2\xa1 junk " + frame_bytes("map_query_from_app") + b" more junk"
    assert find_credentials(capture) == {(FAKE_HOST, FAKE_AUTH, FAKE_DEVICE)}


def test_ignores_robot_replies_and_unrelated_bytes():
    assert (
        find_credentials(frame_bytes("status_push") + frame_bytes("map_reply_with_pose")) == set()
    )


def test_updates_env_in_place_and_keeps_other_lines():
    text = "# comment\nROBZONE_DIAG_HOST=10.0.0.1\nOTHER=1\n"
    updated = update_env_text(text, {"ROBZONE_DIAG_HOST": "192.168.0.50", "ROBZONE_DIAG_X": "y"})
    assert updated == "# comment\nROBZONE_DIAG_HOST=192.168.0.50\nOTHER=1\nROBZONE_DIAG_X=y\n"


def test_mask_hides_all_but_two_characters():
    assert mask("abcdef") == "ab****"
