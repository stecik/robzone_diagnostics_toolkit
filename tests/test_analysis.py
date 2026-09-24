import pytest

from robzone_diag.analysis.heading import PoseSample, stationary_segments, unwrap


def test_unwrap_removes_360_degree_jumps():
    assert unwrap([250, 268, -85, -80]) == [250, 268, 275, 280]
    assert unwrap([170, -170, -150]) == [170, 190, 210]


def test_measures_linear_drift_across_the_wrap():
    # 1.5 deg/s at a fixed position, reported in the robot's -90..270 range.
    samples = []
    for i in range(20):
        heading = (250 + 1.5 * 3 * i + 90) % 360 - 90
        samples.append(PoseSample(3.0 * i, (330, 353), heading))
    [segment] = stationary_segments(samples)
    assert segment.rate_deg_per_s == pytest.approx(1.5, abs=0.01)
    assert segment.max_residual_deg < 1


def test_splits_segments_when_position_changes_and_skips_short_runs():
    still = [PoseSample(float(i), (1, 1), 0.0) for i in range(6)]
    moving = [PoseSample(10.0 + i, (i, i), 0.0) for i in range(4)]
    still2 = [PoseSample(20.0 + i, (9, 9), 2.0 * i) for i in range(5)]
    segments = stationary_segments(still + moving + still2)
    assert [s.position for s in segments] == [(1, 1), (9, 9)]
    assert segments[0].rate_deg_per_s == 0
    assert segments[1].rate_deg_per_s == pytest.approx(2.0)


def test_ignores_samples_without_pose():
    samples = [PoseSample(float(i), None, None) for i in range(10)]
    assert stationary_segments(samples) == []
