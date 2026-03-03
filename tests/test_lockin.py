"""Tests for the lock-in demodulation math."""

import numpy as np
import pytest

from nilockin.lockin import compute_buffer_size, demod, make_reference


class TestComputeBufferSize:
    def test_integer_ratio(self) -> None:
        # 100 Hz at 1000 Hz sample rate = exactly 10 samples/cycle
        assert compute_buffer_size(100.0, 1000.0) == 10

    def test_rounds_to_nearest(self) -> None:
        # 17.76 Hz at 2000 Hz → 2000/17.76 = 112.6 → rounds to 113
        buf = compute_buffer_size(17.76, 2000.0)
        assert buf == 113

    def test_multiple_cycles(self) -> None:
        buf_1 = compute_buffer_size(100.0, 1000.0, num_cycles=1)
        buf_5 = compute_buffer_size(100.0, 1000.0, num_cycles=5)
        assert buf_5 == buf_1 * 5


class TestDemod:
    def test_pure_sine_amplitude(self) -> None:
        """A pure sine at the reference frequency should give X ≈ amplitude, Y ≈ 0."""
        n = compute_buffer_size(10.0, 1000.0)
        sin_ref, cos_ref = make_reference(n)
        amplitude = 2.5
        signal = amplitude * np.sin(2.0 * np.pi * np.arange(n) / n)
        x, y = demod(signal, sin_ref, cos_ref)
        assert x == pytest.approx(amplitude, abs=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)

    def test_pure_cosine_gives_y(self) -> None:
        """A pure cosine at the reference frequency should give X ≈ 0, Y ≈ amplitude."""
        n = compute_buffer_size(10.0, 1000.0)
        sin_ref, cos_ref = make_reference(n)
        amplitude = 3.0
        signal = amplitude * np.cos(2.0 * np.pi * np.arange(n) / n)
        x, y = demod(signal, sin_ref, cos_ref)
        assert x == pytest.approx(0.0, abs=1e-10)
        assert y == pytest.approx(amplitude, abs=1e-10)

    def test_noise_floor(self) -> None:
        """Pure noise should demod to near zero."""
        n = compute_buffer_size(10.0, 1000.0)
        sin_ref, cos_ref = make_reference(n)
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 1.0, n)
        x, y = demod(noise, sin_ref, cos_ref)
        # With 100 samples, noise floor is roughly 1/sqrt(N) ≈ 0.1
        assert abs(x) < 0.5
        assert abs(y) < 0.5

    def test_dc_rejection(self) -> None:
        """A DC offset should not appear in the demodulated output."""
        n = compute_buffer_size(10.0, 1000.0)
        sin_ref, cos_ref = make_reference(n)
        signal = np.full(n, 5.0)  # pure DC
        x, y = demod(signal, sin_ref, cos_ref)
        assert x == pytest.approx(0.0, abs=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)

    def test_off_frequency_rejection(self) -> None:
        """A sine at a different frequency should be rejected."""
        n = compute_buffer_size(10.0, 1000.0)
        sin_ref, cos_ref = make_reference(n)
        # Signal at 20 Hz (2nd harmonic), reference at 10 Hz
        signal = 2.0 * np.sin(2.0 * np.pi * 2 * np.arange(n) / n)
        x, y = demod(signal, sin_ref, cos_ref)
        assert x == pytest.approx(0.0, abs=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)

    def test_multi_cycle(self) -> None:
        """Demod with multiple cycles should give the same result."""
        num_cycles = 5
        n = compute_buffer_size(10.0, 1000.0, num_cycles=num_cycles)
        sin_ref, cos_ref = make_reference(n, num_cycles=num_cycles)
        amplitude = 1.7
        signal = amplitude * np.sin(2.0 * np.pi * num_cycles * np.arange(n) / n)
        x, y = demod(signal, sin_ref, cos_ref)
        assert x == pytest.approx(amplitude, abs=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)
