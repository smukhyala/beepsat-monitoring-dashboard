# 🛰️ BeepSat Real-Time Monitoring Dashboard

A comprehensive satellite monitoring system with real-time telemetry visualization, built for the PyCubed BeepSat demonstration platform.

## 🌟 Features

- **Real-Time Telemetry** - Live satellite data streaming at 2Hz
- **Interactive Dashboard** - Professional mission control interface
- **Multi-Sensor Monitoring** - Battery, radio, IMU, system health
- **Hardware Emulation** - Complete satellite simulation without physical hardware
- **Live Visualization** - 4-panel real-time graphing system
- **Mission Control** - Start/stop missions with live mission timer

## 🚀 Quick Start

### Prerequisites
```bash
pip install streamlit plotly pandas
```

### Run the Dashboard
```bash
git clone https://github.com/yourusername/beepsat-monitoring-dashboard.git
cd beepsat-monitoring-dashboard
streamlit run fixed_dashboard.py
```

1. Click "🚀 Start Mission" in the sidebar
2. Watch real-time telemetry data flow
3. Monitor live graphs and system metrics

## 📊 Dashboard Components

### Real-Time Metrics
- 🔋 **Battery Voltage** - Power system monitoring with low-battery alerts
- 📡 **Radio Signal Strength** - RSSI tracking and communication status  
- ⚙️ **Task Management** - System task health monitoring
- 🚨 **Error Tracking** - System fault detection and counting
- ⏰ **Uptime Monitoring** - Mission duration tracking

### Live Visualizations
- **Battery Voltage Graph** - Trending power levels over time
- **Radio Signal Chart** - Signal strength variations
- **System Error Plot** - Error accumulation tracking  
- **Uptime Timeline** - Mission duration visualization

## 🛰️ BeepSat Architecture

This project demonstrates a complete satellite software stack:

- **Task-Based System** - Concurrent execution of satellite subsystems
- **Telemetry Collection** - Comprehensive system monitoring
- **Hardware Abstraction** - Emulated PyCubed satellite hardware
- **Ground Station Interface** - Professional mission control dashboard
- **Real-Time Communications** - Live data streaming and visualization

## 📁 Project Structure

```
beepsat-monitoring-dashboard/
├── fixed_dashboard.py           # Main Streamlit dashboard (recommended)
├── integrated_dashboard.py      # Alternative integrated version
├── simple_telemetry_viewer.py   # Command-line telemetry viewer
├── software_example_beepsat/     # BeepSat simulation framework
│   ├── basic/                   # Basic satellite implementation
│   └── advanced/                # Advanced features (logging, commands)
├── requirements.txt             # Python dependencies
├── CLAUDE.md                    # Development guidance
└── README.md                    # This file
```

## 🎮 Usage Examples

### Start Mission Monitoring
1. Launch dashboard: `streamlit run fixed_dashboard.py`
2. Click "🚀 Start Mission" 
3. Monitor real-time telemetry data

### Command-Line Monitoring
```bash
cd software_example_beepsat/basic
python3 main_emulated.py | python3 ../../simple_telemetry_viewer.py
```

### Reset Mission Data
- Use "🔄 Reset Mission" button in dashboard
- Clears all historical data and starts fresh

## 🔧 Technical Details

### Monitoring System
- **Data Rate**: 2Hz telemetry generation
- **Storage**: Rolling 150-point buffer for real-time performance
- **Simulation**: Realistic satellite behavior with hardware emulation
- **Interface**: Professional web-based mission control

### Key Metrics Monitored
- Battery voltage with discharge simulation
- Radio signal strength with realistic variations
- System error counting and fault tracking
- Task execution monitoring
- Mission timing and uptime tracking

## 🎯 Use Cases

- **Educational Demonstrations** - Satellite operations training
- **System Development** - Testing monitoring interfaces
- **Presentation Tool** - Live satellite mission simulation
- **Prototyping Platform** - Developing satellite monitoring systems

## 🤝 Contributing

This project was developed as an educational demonstration of satellite monitoring systems. Feel free to fork and adapt for your own satellite projects!

## 📜 License

This project builds upon the BeepSat demonstration software. See `software_example_beepsat/LICENSES/` for details.

---

**Built with ❤️ for satellite enthusiasts and space mission education**