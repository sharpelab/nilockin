"""nilockin GUI — real-time lock-in amplifier display."""

import argparse
import collections
import sys

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from nilockin.worker import AcquisitionWorker

_HISTORY_LEN = 200


class MainWindow(QMainWindow):
    def __init__(self, *, dummy: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("nilockin")
        self._dummy = dummy

        # Demod history (rolling buffers)
        self._x_hist: collections.deque[float] = collections.deque(maxlen=_HISTORY_LEN)
        self._y_hist: collections.deque[float] = collections.deque(maxlen=_HISTORY_LEN)
        self._r_hist: collections.deque[float] = collections.deque(maxlen=_HISTORY_LEN)

        self._init_layout()

        freq = self._freq_spin.value()
        rate = self._rate_spin.value()
        ao_amp = self._ao_amp_spin.value()
        self._worker = AcquisitionWorker(freq, rate, dummy=dummy, ao_amplitude=ao_amp)
        self._worker.result.connect(self._on_result)
        self._update_status()

    def start(self) -> None:
        self._worker.start()

    def closeEvent(self, event: object) -> None:
        self._worker.stop()
        self._worker.wait(5000)
        super().closeEvent(event)  # type: ignore[arg-type]

    # ── Slots ──

    def _on_result(self, data: object, x: float, y: float, r: float, p: float) -> None:
        raw = data if isinstance(data, np.ndarray) else np.asarray(data)

        # Raw waveform
        t_ms = np.arange(len(raw)) / self._rate_spin.value() * 1000.0
        self._raw_curve.setData(t_ms, raw)

        # Demod history
        self._x_hist.append(x)
        self._y_hist.append(y)
        self._r_hist.append(r)
        xs = np.array(self._x_hist)
        ys = np.array(self._y_hist)
        rs = np.array(self._r_hist)
        idx = np.arange(len(xs))
        self._x_curve.setData(idx, xs)
        self._y_curve.setData(idx, ys)
        self._r_curve.setData(idx, rs)

        # Status readouts
        self._x_readout.setText(f"X: {x:+.4f}")
        self._y_readout.setText(f"Y: {y:+.4f}")
        self._r_readout.setText(f"R: {r:.4f}")
        self._p_readout.setText(f"P: {p:+.1f}\u00b0")

    def _on_config_changed(self) -> None:
        freq = self._freq_spin.value()
        rate = self._rate_spin.value()
        ao_amp = self._ao_amp_spin.value()
        self._worker.update_config(freq, rate, ao_amp)
        self._x_hist.clear()
        self._y_hist.clear()
        self._r_hist.clear()
        self._update_status()

    def _update_status(self) -> None:
        from nilockin.lockin import compute_buffer_size

        freq = self._freq_spin.value()
        rate = self._rate_spin.value()
        buf = compute_buffer_size(freq, rate)
        actual_freq = rate / (buf)
        self._status_label.setText(f"Buffer: {buf} samples | Actual freq: {actual_freq:.3f} Hz | Rate: {rate:.0f} Hz")

    # ── Layout ──

    def _init_layout(self) -> None:
        central = QWidget()
        layout = QVBoxLayout()

        # Plots
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        plots = QHBoxLayout()

        self._raw_plot = pg.PlotWidget(title="Raw Waveform")
        self._raw_plot.setLabel("bottom", "Time", units="ms")
        self._raw_plot.setLabel("left", "Voltage", units="V")
        self._raw_curve = self._raw_plot.plot(pen="b")
        plots.addWidget(self._raw_plot)

        self._demod_plot = pg.PlotWidget(title="Demodulated Signal")
        self._demod_plot.setLabel("bottom", "Cycle")
        self._demod_plot.setLabel("left", "Amplitude", units="V")
        self._demod_plot.addLegend()
        self._x_curve = self._demod_plot.plot(pen="b", name="X")
        self._y_curve = self._demod_plot.plot(pen="r", name="Y")
        self._r_curve = self._demod_plot.plot(pen=pg.mkPen("k", width=2), name="R")
        plots.addWidget(self._demod_plot)

        layout.addLayout(plots)

        # Controls
        controls = QHBoxLayout()

        config_box = QGroupBox("Configuration")
        config_layout = QHBoxLayout()
        config_box.setLayout(config_layout)

        config_layout.addWidget(QLabel("Freq (Hz):"))
        self._freq_spin = QDoubleSpinBox()
        self._freq_spin.setRange(0.1, 1000.0)
        self._freq_spin.setDecimals(2)
        self._freq_spin.setValue(17.76)
        self._freq_spin.setKeyboardTracking(False)
        self._freq_spin.valueChanged.connect(self._on_config_changed)
        config_layout.addWidget(self._freq_spin)

        config_layout.addWidget(QLabel("Rate (Hz):"))
        self._rate_spin = QDoubleSpinBox()
        self._rate_spin.setRange(100.0, 100000.0)
        self._rate_spin.setDecimals(0)
        self._rate_spin.setValue(2000.0)
        self._rate_spin.setKeyboardTracking(False)
        self._rate_spin.valueChanged.connect(self._on_config_changed)
        config_layout.addWidget(self._rate_spin)

        config_layout.addWidget(QLabel("AO Amp (V):"))
        self._ao_amp_spin = QDoubleSpinBox()
        self._ao_amp_spin.setRange(0.0, 10.0)
        self._ao_amp_spin.setDecimals(3)
        self._ao_amp_spin.setValue(0.0)
        self._ao_amp_spin.setSingleStep(0.1)
        self._ao_amp_spin.setKeyboardTracking(False)
        self._ao_amp_spin.valueChanged.connect(self._on_config_changed)
        config_layout.addWidget(self._ao_amp_spin)

        controls.addWidget(config_box)

        readout_box = QGroupBox("Readout")
        readout_layout = QHBoxLayout()
        readout_box.setLayout(readout_layout)
        self._x_readout = QLabel("X: —")
        self._y_readout = QLabel("Y: —")
        self._r_readout = QLabel("R: —")
        self._p_readout = QLabel("P: —")
        for label in (self._x_readout, self._y_readout, self._r_readout, self._p_readout):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumWidth(100)
            readout_layout.addWidget(label)
        controls.addWidget(readout_box)

        layout.addLayout(controls)

        # Status bar
        self._status_label = QLabel()
        self.statusBar().addWidget(self._status_label)

        central.setLayout(layout)
        self.setCentralWidget(central)


def main() -> None:
    parser = argparse.ArgumentParser(description="nilockin — digital lock-in amplifier")
    parser.add_argument("--dummy", action="store_true", help="Use synthetic signal instead of real DAQ hardware")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow(dummy=args.dummy)
    window.start()
    window.show()
    sys.exit(app.exec())
