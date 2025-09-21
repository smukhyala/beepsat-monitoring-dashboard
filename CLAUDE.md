# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Beep-Sat Demo** repository, containing complete PyCubed satellite software examples that demonstrate a simple beaconing CubeSat performing routine tasks. The project is designed for satellite/aerospace development using CircuitPython on PyCubed hardware.

## Repository Structure

- `software_example_beepsat/basic/` - Basic implementation with core functionality
- `software_example_beepsat/advanced/` - Enhanced version with fault handling, low power mode, SD card logging, and over-the-air commands
- Both versions contain identical structure:
  - `main.py` - Entry point that loads and schedules all tasks
  - `Tasks/` - Individual task modules (beacon, battery monitoring, IMU, etc.)
  - `lib/` - Hardware drivers and the Tasko async framework

## Development Commands

This project uses **CircuitPython** and runs directly on PyCubed hardware. There are no traditional build/compile steps:

### Testing
```bash
# Run unit tests for the Tasko framework
python -m unittest software_example_beepsat/basic/lib/tasko/test/test_loop.py
python -m unittest software_example_beepsat/advanced/lib/tasko/test/test_loop.py
```

### Deployment
- Copy files directly to the PyCubed board's filesystem
- The `main.py` file automatically runs on hardware boot
- Use CircuitPython's REPL for interactive debugging

## Code Architecture

### Task-Based Architecture
The system uses a custom async framework called **Tasko** for task scheduling:

- **Main Loop** (`main.py`): Dynamically imports all task files from `Tasks/` directory and schedules them
- **Task Framework** (`lib/tasko/`): Custom event loop with support for:
  - Fixed-rate task scheduling 
  - Deferred task execution
  - Priority-based execution
  - Async/await patterns

### Task System
- All tasks inherit from `template_task.Task` base class
- Tasks define: `priority`, `frequency` (Hz), `name`, `color` (for debug output)
- Tasks implement `async def main_task(self)` method
- Tasks are auto-discovered and scheduled by filename in `Tasks/` directory

### Hardware Abstraction
- **PyCubed Class** (`lib/pycubed.py`): Main satellite hardware interface
  - NVM (Non-Volatile Memory) counters and flags for persistent state
  - Hardware component initialization (radio, IMU, GPS, etc.)
  - Power management and battery monitoring
- **Hardware Drivers** (`lib/`): Individual component drivers (ADM1176, BMX160, BQ25883, etc.)

### Advanced Features (advanced/ version only)
- **Command & Data Handling** (`cdh.py`): Over-the-air command processing with security commands
- **Fault Tolerance**: Exception handling with automatic reset on critical failures
- **Logging**: Data persistence to SD card
- **Power Management**: Low power modes and shutdown capabilities

### Key Differences Between Versions
- **Basic**: Simple task execution with minimal error handling
- **Advanced**: Production-ready with comprehensive fault tolerance, logging, and remote command capabilities

## Important Notes

- **Antenna Safety**: Beacon transmission is disabled by default (`ANTENNA_ATTACHED = False` in beacon_task.py)
- **Hardware Dependencies**: Code designed specifically for PyCubed mainboard-v05 with CircuitPython 7.0.0+
- **Security**: Advanced version includes command authentication for critical operations like shutdown/reset