"""Heading behaviour while the robot's reported position does not change.

A robot standing still should report a (nearly) constant heading. A steady linear
change instead is what integrating an uncompensated gyroscope bias looks like.
This module only measures; it does not decide what is "too much".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

MIN_SEGMENT_SAMPLES = 5


@dataclass(frozen=True)
class PoseSample:
    elapsed_s: float
    position: tuple[int, int] | None
    heading_deg: float | None


@dataclass(frozen=True)
class StationarySegment:
    position: tuple[int, int]
    start_s: float
    end_s: float
    samples: int
    rate_deg_per_s: float
    max_residual_deg: float

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    @property
    def total_change_deg(self) -> float:
        return self.rate_deg_per_s * self.duration_s


def unwrap(headings: Iterable[float]) -> list[float]:
    """Remove 360° jumps (the robot reports headings in a wrapping range, e.g. -90..270)."""
    result: list[float] = []
    offset = 0.0
    for heading in headings:
        if result:
            step = heading + offset - result[-1]
            if step > 180:
                offset -= 360
            elif step < -180:
                offset += 360
        result.append(heading + offset)
    return result


def stationary_segments(samples: list[PoseSample]) -> list[StationarySegment]:
    """Runs of samples with an identical reported position, with a linear heading fit."""
    segments: list[StationarySegment] = []
    run: list[PoseSample] = []
    for sample in [s for s in samples if s.position is not None and s.heading_deg is not None]:
        if run and sample.position != run[-1].position:
            segments += _fit(run)
            run = []
        run.append(sample)
    segments += _fit(run)
    return segments


def _fit(run: list[PoseSample]) -> list[StationarySegment]:
    if len(run) < MIN_SEGMENT_SAMPLES:
        return []
    times = [s.elapsed_s for s in run]
    headings = unwrap(s.heading_deg for s in run)  # type: ignore[misc]
    rate, intercept = _linear_fit(times, headings)
    residual = max(abs(h - (intercept + rate * t)) for t, h in zip(times, headings, strict=True))
    return [StationarySegment(run[0].position, times[0], times[-1], len(run), rate, residual)]  # type: ignore[arg-type]


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator
    return slope, mean_y - slope * mean_x
