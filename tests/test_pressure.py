from __future__ import annotations

import pytest

from pressure_console.pressure import RollingWindowBuffer, pressure_from_adc, pressure_from_voltage, voltage_from_adc


def test_pressure_mapping_endpoints() -> None:
    assert voltage_from_adc(0) == pytest.approx(0.0)
    assert pressure_from_voltage(0.0) == pytest.approx(0.0)
    assert pressure_from_voltage(5.0) == pytest.approx(10.0)
    assert pressure_from_adc(1023) == pytest.approx(10.0)


def test_pressure_mapping_midpoint() -> None:
    assert pressure_from_voltage(2.5) == pytest.approx(5.0)


def test_rolling_window_trims_old_points() -> None:
    buffer = RollingWindowBuffer(window_seconds=10.0)
    buffer.append(0.0, 1.0)
    buffer.append(4.0, 2.0)
    buffer.append(10.5, 3.0)

    values = buffer.values()
    assert [point.pressure_bar for point in values] == [2.0, 3.0]


def test_relative_points_are_newest_relative() -> None:
    buffer = RollingWindowBuffer(window_seconds=10.0)
    buffer.append(8.0, 4.0)
    buffer.append(10.0, 6.0)

    x_values, y_values = buffer.relative_points()
    assert x_values == pytest.approx([-2.0, 0.0])
    assert y_values == pytest.approx([4.0, 6.0])

