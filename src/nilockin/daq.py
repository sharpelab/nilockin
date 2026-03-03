"""NI DAQ interface for the USB-6363."""

import nidaqmx
import nidaqmx.constants
from nidaqmx.constants import AcquisitionType, TerminalConfiguration


def create_ai_task(
    device: str = "Dev1",
    channels: int = 32,
    sample_rate: float = 2000.0,
    samples_per_read: int = 2000,
) -> nidaqmx.Task:
    """Create and configure an analog input task.

    Args:
        device: NI device name (e.g. "Dev1", "ni6363").
        channels: Number of AI channels to configure (0 through channels-1).
        sample_rate: Per-channel sample rate in Hz.
        samples_per_read: Number of samples per channel per read.

    Returns:
        Configured but not yet started nidaqmx.Task.
    """
    task = nidaqmx.Task("nilockin_ai")
    task.ai_channels.add_ai_voltage_chan(
        f"{device}/ai0:{channels - 1}",
        terminal_config=TerminalConfiguration.RSE,
        min_val=-10.0,
        max_val=10.0,
    )
    task.timing.cfg_samp_clk_timing(
        rate=sample_rate,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=samples_per_read * 4,
    )
    return task
