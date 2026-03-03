"""Digital lock-in demodulation.

Pure math — no hardware or GUI dependencies.
"""

import numpy as np


def compute_buffer_size(freq: float, sample_rate: float, num_cycles: int = 1) -> int:
    """Compute the number of samples for an integer number of reference cycles.

    Args:
        freq: Reference frequency in Hz.
        sample_rate: DAQ sample rate in Hz.
        num_cycles: Number of complete cycles per buffer.

    Returns:
        Number of samples (guaranteed to be num_cycles * round(sample_rate / freq)).
    """
    samples_per_cycle = round(sample_rate / freq)
    return samples_per_cycle * num_cycles


def make_reference(n_samples: int, num_cycles: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Generate normalized sin/cos reference arrays for demodulation.

    Args:
        n_samples: Total number of samples (should be num_cycles * samples_per_cycle).
        num_cycles: Number of complete cycles in the buffer.

    Returns:
        (sin_ref, cos_ref) each of length n_samples, normalized so that
        dot(ref, signal) yields the signal amplitude at the reference frequency.
    """
    phase = 2.0 * np.pi * num_cycles * np.arange(n_samples) / n_samples
    sin_ref = np.sin(phase)
    cos_ref = np.cos(phase)
    sin_ref /= np.sum(sin_ref**2)
    cos_ref /= np.sum(cos_ref**2)
    return sin_ref, cos_ref


def demod(data: np.ndarray, sin_ref: np.ndarray, cos_ref: np.ndarray) -> tuple[float, float]:
    """Demodulate a signal against sin/cos references.

    Args:
        data: 1D array of samples (length must match references).
        sin_ref: Normalized sin reference from make_reference.
        cos_ref: Normalized cos reference from make_reference.

    Returns:
        (X, Y) — in-phase and quadrature components.
    """
    x = float(np.dot(sin_ref, data))
    y = float(np.dot(cos_ref, data))
    return x, y
