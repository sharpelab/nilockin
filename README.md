# nilockin

Multi-channel software lock-in amplifier for the NI USB-6363. Reads up to 32 analog input channels, demodulates at a reference frequency, and reports amplitude and phase.

## Setup

```bash
uv sync
uv run nilockin
```

Requires NI-DAQmx drivers installed on the host machine.
