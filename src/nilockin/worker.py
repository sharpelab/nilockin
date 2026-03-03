"""Acquisition worker thread.

Runs a blocking read loop — either from real NI DAQ hardware or from a
synthetic signal generator (dummy mode). Demodulates each buffer and emits
results to the GUI thread via Qt signal.
"""

import math
import threading
import time

import numpy as np
from PySide6.QtCore import QThread, Signal

from nilockin.lockin import compute_buffer_size, demod, make_reference

# Dummy mode: synthetic signal parameters
_DUMMY_TRUE_FREQ = 17.76  # Hz — the "real" signal frequency
_DUMMY_AMPLITUDE = 2.5  # V
_DUMMY_NOISE_STD = 0.3  # V


class AcquisitionWorker(QThread):
    """Worker thread that reads DAQ data and demodulates it.

    Signals:
        result: (raw_data, X, Y, R, P) emitted once per demod cycle.
    """

    result = Signal(object, float, float, float, float)

    def __init__(self, freq: float, sample_rate: float, *, dummy: bool = False) -> None:
        super().__init__()
        self._dummy = dummy
        self._running = False
        self._config_event = threading.Event()

        # Current config — read by the worker loop, written by update_config
        self._freq = freq
        self._sample_rate = sample_rate

        # Built from config at the start of each loop (or on config change)
        self._buffer_size = 0
        self._sin_ref = np.array([])
        self._cos_ref = np.array([])
        self._rebuild_reference()

        # Dummy mode state
        self._dummy_phase = 0.0

    def update_config(self, freq: float, sample_rate: float) -> None:
        """Request a config change. Thread-safe — takes effect next cycle."""
        self._freq = freq
        self._sample_rate = sample_rate
        self._config_event.set()

    def stop(self) -> None:
        """Signal the worker to stop after the current cycle."""
        self._running = False

    def run(self) -> None:
        self._running = True
        task = None

        if not self._dummy:
            from nilockin.daq import create_ai_task

            task = create_ai_task(channels=1, sample_rate=self._sample_rate)
            task.start()

        try:
            while self._running:
                if self._config_event.is_set():
                    self._config_event.clear()
                    self._rebuild_reference()
                    if task is not None:
                        task.stop()
                        task.close()
                        from nilockin.daq import create_ai_task

                        task = create_ai_task(channels=1, sample_rate=self._sample_rate)
                        task.start()

                if self._dummy:
                    data = self._generate_dummy()
                    time.sleep(self._buffer_size / self._sample_rate)
                else:
                    assert task is not None
                    raw = task.read(number_of_samples_per_channel=self._buffer_size)
                    data = np.array(raw, dtype=np.float64)

                x, y = demod(data, self._sin_ref, self._cos_ref)
                r = math.sqrt(x * x + y * y)
                p = math.degrees(math.atan2(y, x))
                self.result.emit(data, x, y, r, p)
        finally:
            if task is not None:
                task.stop()
                task.close()

    def _rebuild_reference(self) -> None:
        self._buffer_size = compute_buffer_size(self._freq, self._sample_rate)
        self._sin_ref, self._cos_ref = make_reference(self._buffer_size)

    def _generate_dummy(self) -> np.ndarray:
        """Generate a synthetic sine + noise signal for testing."""
        t = np.arange(self._buffer_size) / self._sample_rate
        signal = _DUMMY_AMPLITUDE * np.sin(2.0 * np.pi * _DUMMY_TRUE_FREQ * t + self._dummy_phase)
        signal += np.random.default_rng().normal(0, _DUMMY_NOISE_STD, self._buffer_size)
        # Advance phase so consecutive buffers are continuous
        self._dummy_phase += 2.0 * np.pi * _DUMMY_TRUE_FREQ * self._buffer_size / self._sample_rate
        self._dummy_phase %= 2.0 * np.pi
        return signal
