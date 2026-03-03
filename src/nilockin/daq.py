"""NI DAQ interface for the USB-6363."""

import nidaqmx
import nidaqmx.constants
import numpy as np
from nidaqmx.constants import AcquisitionType, RegenerationMode, TerminalConfiguration


def create_ai_task(
    device: str = "Dev1",
    channels: int = 1,
    sample_rate: float = 2000.0,
    *,
    sync_to_ao: bool = False,
) -> nidaqmx.Task:
    """Create and configure an analog input task.

    Args:
        device: NI device name (e.g. "Dev1", "ni6363").
        channels: Number of AI channels to configure (0 through channels-1).
        sample_rate: Per-channel sample rate in Hz.
        sync_to_ao: If True, AI starts on the AO start trigger so both
            tasks are phase-aligned from sample 0.

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
        samps_per_chan=int(sample_rate * 4),
    )
    if sync_to_ao:
        task.triggers.start_trigger.cfg_dig_edge_start_trigger(f"/{device}/ao/StartTrigger")  # ty: ignore[unresolved-attribute]
    return task


def create_ao_task(
    device: str = "Dev1",
    channel: int = 0,
    sample_rate: float = 2000.0,
    samples_per_cycle: int = 100,
) -> nidaqmx.Task:
    """Create an analog output task with regeneration (hardware looping).

    Args:
        device: NI device name.
        channel: AO channel number (0-3 on the 6363).
        sample_rate: Output sample rate in Hz.
        samples_per_cycle: Number of samples in one waveform cycle.

    Returns:
        Configured but not yet started nidaqmx.Task.
    """
    task = nidaqmx.Task("nilockin_ao")
    task.ao_channels.add_ao_voltage_chan(
        f"{device}/ao{channel}",
        min_val=-10.0,
        max_val=10.0,
    )
    task.timing.cfg_samp_clk_timing(
        rate=sample_rate,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=samples_per_cycle * 5,
    )
    # Regeneration: hardware loops the buffer indefinitely after one write.
    task.out_stream.regen_mode = RegenerationMode.ALLOW_REGENERATION
    return task


def write_ao_sine(task: nidaqmx.Task, samples_per_cycle: int, amplitude: float) -> None:
    """Write a single sine cycle to the AO task buffer.

    Args:
        task: A configured AO task (not yet started, or stopped).
        samples_per_cycle: Number of samples in one period.
        amplitude: Peak amplitude in volts (clipped to ±10V).
    """
    amplitude = float(np.clip(amplitude, -10.0, 10.0))
    n_repeats = 5
    n_samples = samples_per_cycle * n_repeats
    phase = 2.0 * np.pi * n_repeats * np.arange(n_samples) / n_samples
    waveform = amplitude * np.sin(phase)
    task.write(waveform, auto_start=False)
