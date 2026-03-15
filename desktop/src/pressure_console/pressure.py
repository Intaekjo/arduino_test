from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .constants import ADC_MAX, GRAPH_WINDOW_SECONDS, MAX_PRESSURE_BAR, MAX_VOLTAGE


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def voltage_from_adc(adc: int) -> float:
    limited = max(0, min(adc, ADC_MAX))
    return (limited * MAX_VOLTAGE) / ADC_MAX


def pressure_from_voltage(voltage: float) -> float:
    limited = clamp(voltage, 0.0, MAX_VOLTAGE)
    return clamp((limited / MAX_VOLTAGE) * MAX_PRESSURE_BAR, 0.0, MAX_PRESSURE_BAR)


def pressure_from_adc(adc: int) -> float:
    return pressure_from_voltage(voltage_from_adc(adc))


@dataclass(frozen=True, slots=True)
class PressurePoint:
    timestamp: float
    pressure_bar: float


class RollingWindowBuffer:
    def __init__(self, window_seconds: float = GRAPH_WINDOW_SECONDS) -> None:
        self.window_seconds = window_seconds
        self._points: deque[PressurePoint] = deque()

    def append(self, timestamp: float, pressure_bar: float) -> None:
        self._points.append(PressurePoint(timestamp=timestamp, pressure_bar=pressure_bar))
        self._trim(timestamp)

    def clear(self) -> None:
        self._points.clear()

    def values(self) -> list[PressurePoint]:
        return list(self._points)

    def relative_points(self) -> tuple[list[float], list[float]]:
        if not self._points:
            return [], []
        newest = self._points[-1].timestamp
        xs = [point.timestamp - newest for point in self._points]
        ys = [point.pressure_bar for point in self._points]
        return xs, ys

    def _trim(self, newest_timestamp: float) -> None:
        cutoff = newest_timestamp - self.window_seconds
        while self._points and self._points[0].timestamp < cutoff:
            self._points.popleft()

