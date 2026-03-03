# nilockin

Multi-channel software lock-in amplifier for the NI USB-6363.

## Quick Start

```bash
uv sync
uv run nilockin          # launch GUI
uv run pytest            # run tests
```

## Dev Setup

```bash
git config core.hooksPath hooks/   # enable pre-commit (ruff + ty)
```

## Architecture

- `src/nilockin/app.py` — PySide6 GUI
- `src/nilockin/daq.py` — NI DAQ hardware interface (nidaqmx)
- `tests/` — pytest suite

## Dependencies

- **nidaqmx**: Official NI Python driver. Requires NI-DAQmx runtime on the host.
- **PySide6**: Qt GUI framework.
- **numpy**: Numeric computation.

## Conventions

- Python 3.13+, uv + hatchling
- Ruff for linting/formatting (120 char lines)
- ty for type checking
- Pre-commit hook auto-fixes staged files
