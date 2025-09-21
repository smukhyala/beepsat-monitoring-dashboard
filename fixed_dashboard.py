#!/usr/bin/env python3
"""
Fixed BeepSat Dashboard - Thread-safe simulation
Runs both simulation and Streamlit dashboard without threading issues
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
import os
import sys
import random
from collections import deque
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="BeepSat Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for space mission theme
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2125;
        border: 1px solid #31333a;
        padding: 10px;
        border-radius: 5px;
    }
    h1 {
        color: #00ff41;
        text-align: center;
        font-family: 'Courier New', monospace;
    }
    .status-connected {
        color: #00ff41;
        font-weight: bold;
    }
    .status-disconnected {
        color: #ff4444;
        font-weight: bold;
    }
    .mission-time {
        font-family: 'Courier New', monospace;
        font-size: 24px;
        color: #00ff41;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class BeepSatSimulator:
    """Thread-safe BeepSat simulator"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_update = time.time()
        
        # Simulation parameters
        self.battery_base = 7.4
        self.battery_noise = 0.15
        self.battery_trend = 0.0
        
        # Counters
        self.boot_count = random.randint(15, 45)
        self.state_errors = random.randint(1, 8)
        self.gs_responses = random.randint(5, 30)
        self.charge_cycles = random.randint(25, 90)
        
        # Tasks
        self.tasks = ['beacon', 'monitor', 'blink', 'vbatt', 'time', 'imu']
        
        # RSSI simulation
        self.rssi_base = -55
        self.rssi_variation = 12
        
    def get_battery_voltage(self, current_time):
        """Calculate realistic battery voltage"""
        # Slow discharge over time
        elapsed_hours = (current_time - self.start_time) / 3600
        trend = -0.03 * elapsed_hours  # Slower discharge
        
        # Add realistic noise
        noise = random.uniform(-self.battery_noise, self.battery_noise)
        
        # Calculate voltage
        voltage = self.battery_base + trend + noise
        
        # Ensure reasonable bounds
        return max(min(voltage, 8.0), 5.8)
    
    def get_rssi(self):
        """Calculate radio signal strength"""
        return self.rssi_base + random.randint(-self.rssi_variation, self.rssi_variation)
    
    def get_uptime(self, current_time):
        """Get current uptime"""
        return current_time - self.start_time
    
    def generate_telemetry(self):
        """Generate complete telemetry packet"""
        current_time = time.time()
        
        # Occasionally increment error count (every ~30 seconds on average)
        if random.random() < 0.001:
            self.state_errors += 1
        
        # Occasionally increment GS responses
        if random.random() < 0.005:
            self.gs_responses += 1
        
        battery_v = self.get_battery_voltage(current_time)
        
        telemetry = {
            'timestamp': current_time,
            'uptime': self.get_uptime(current_time),
            'task_states': {
                task: {
                    'running': True,
                    'last_seen': current_time
                } for task in self.tasks
            },
            'nvm_counters': {
                'boot_count': self.boot_count,
                'state_errors': self.state_errors,
                'vbus_resets': random.randint(0, 4),
                'gs_responses': self.gs_responses,
                'charge_cycles': self.charge_cycles
            },
            'nvm_flags': {
                'low_battery': battery_v < 6.0,
                'solar_active': True,
                'gps_on': random.random() < 0.1,  # Occasionally turn on GPS
                'low_battery_timeout': battery_v < 5.8,
                'gps_fix': random.random() < 0.3,
                'shutdown': False
            },
            'radio_status': {
                'last_rssi': self.get_rssi(),
                'frequency': 433.0,
                'available': True
            },
            'power_status': {
                'battery_voltage': battery_v,
                'low_battery_threshold': 6.0,
                'uptime_seconds': self.get_uptime(current_time),
                'charge_current': random.uniform(0.0, 0.7) if random.random() < 0.6 else 0.0
            },
            'system_info': {
                'active_tasks': len(self.tasks),
                'monitoring_frequency': 2,
                'version': 'fixed_dashboard'
            }
        }
        
        self.last_update = current_time
        return telemetry
    
    def reset(self):
        """Reset simulation state"""
        self.start_time = time.time()
        self.state_errors = random.randint(0, 3)
        self.gs_responses = random.randint(0, 10)
        self.battery_trend = 0.0

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    if 'monitoring' not in st.session_state:
        st.session_state.monitoring = False
    if 'telemetry_data' not in st.session_state:
        st.session_state.telemetry_data = deque(maxlen=150)
    if 'current_data' not in st.session_state:
        st.session_state.current_data = {}
    if 'simulator' not in st.session_state:
        st.session_state.simulator = BeepSatSimulator()
    if 'mission_start_time' not in st.session_state:
        st.session_state.mission_start_time = None
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = deque(maxlen=50)
    if 'last_telemetry_time' not in st.session_state:
        st.session_state.last_telemetry_time = 0
    if 'data_points_generated' not in st.session_state:
        st.session_state.data_points_generated = 0

def add_log_message(message):
    """Add message to mission log"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_messages.append(f"[{timestamp}] {message}")

def start_monitoring():
    """Start mission monitoring"""
    if not st.session_state.monitoring:
        st.session_state.monitoring = True
        st.session_state.mission_start_time = time.time()
        st.session_state.simulator = BeepSatSimulator()  # Fresh simulator
        st.session_state.last_telemetry_time = time.time()
        st.session_state.data_points_generated = 0
        add_log_message("🚀 Mission started - BeepSat simulation active")
        add_log_message("📡 Telemetry generation started")

def stop_monitoring():
    """Stop mission monitoring"""
    if st.session_state.monitoring:
        st.session_state.monitoring = False
        add_log_message("🛑 Mission stopped")

def reset_mission():
    """Reset all mission data"""
    # Stop monitoring if active
    if st.session_state.monitoring:
        stop_monitoring()
    
    # Clear data
    st.session_state.telemetry_data.clear()
    st.session_state.current_data = {}
    st.session_state.log_messages.clear()
    st.session_state.mission_start_time = None
    st.session_state.last_telemetry_time = 0
    st.session_state.data_points_generated = 0
    
    # Reset simulator
    st.session_state.simulator.reset()
    
    add_log_message("🔄 Mission data reset complete")

def generate_telemetry_data():
    """Generate telemetry data if monitoring is active"""
    current_time = time.time()
    
    # Generate data every 0.5 seconds (2Hz)
    if (st.session_state.monitoring and 
        current_time - st.session_state.last_telemetry_time >= 0.5):
        
        # Generate new telemetry
        telemetry = st.session_state.simulator.generate_telemetry()
        
        # Add to data storage
        st.session_state.telemetry_data.append(telemetry)
        st.session_state.current_data = telemetry
        st.session_state.last_telemetry_time = current_time
        st.session_state.data_points_generated += 1
        
        return True
    
    return False

def create_telemetry_plots():
    """Create real-time telemetry plots"""
    if not st.session_state.telemetry_data:
        # Empty plots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal", "🚨 System Errors", "⏰ Uptime"),
        )
        fig.update_layout(
            height=600, 
            showlegend=False, 
            plot_bgcolor='rgba(14, 17, 23, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        return fig
    
    # Extract data for plotting
    data_list = list(st.session_state.telemetry_data)
    timestamps = []
    battery_voltages = []
    rssi_values = []
    error_counts = []
    uptime_values = []
    
    for data in data_list:
        timestamps.append(datetime.fromtimestamp(data.get('timestamp', time.time())))
        
        power_status = data.get('power_status', {})
        battery_voltages.append(power_status.get('battery_voltage', 0))
        
        radio_status = data.get('radio_status', {})
        rssi_values.append(radio_status.get('last_rssi', -100))
        
        nvm_counters = data.get('nvm_counters', {})
        error_counts.append(nvm_counters.get('state_errors', 0))
        
        uptime_values.append(power_status.get('uptime_seconds', 0))
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal Strength", "🚨 System Errors", "⏰ System Uptime"),
    )
    
    # Battery voltage plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=battery_voltages,
            mode='lines+markers',
            name='Battery Voltage',
            line=dict(color='cyan', width=3),
            marker=dict(size=4, color='cyan')
        ), row=1, col=1
    )
    fig.add_hline(y=6.0, line_dash="dash", line_color="red", 
                 annotation_text="Low Battery Threshold", row=1, col=1)
    
    # RSSI plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=rssi_values,
            mode='lines+markers',
            name='RSSI',
            line=dict(color='lime', width=3),
            marker=dict(size=4, color='lime')
        ), row=1, col=2
    )
    
    # Error count plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=error_counts,
            mode='lines+markers',
            name='Errors',
            line=dict(color='orange', width=3),
            marker=dict(size=4, color='orange')
        ), row=2, col=1
    )
    
    # Uptime plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=uptime_values,
            mode='lines+markers',
            name='Uptime',
            line=dict(color='magenta', width=3),
            marker=dict(size=4, color='magenta')
        ), row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=False,
        plot_bgcolor='rgba(14, 17, 23, 0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12)
    )
    
    # Update axes styling
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
    
    # Y-axis labels
    fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
    fig.update_yaxes(title_text="RSSI (dBm)", row=1, col=2)
    fig.update_yaxes(title_text="Error Count", row=2, col=1)
    fig.update_yaxes(title_text="Uptime (s)", row=2, col=2)
    
    return fig

def main():
    """Main dashboard function"""
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("# 🛰️ BEEPSAT MISSION CONTROL DASHBOARD")
    st.markdown("### Real-Time Satellite Monitoring & Simulation")
    
    # Generate new telemetry data
    new_data_generated = generate_telemetry_data()
    
    # Sidebar - Mission Control
    with st.sidebar:
        st.markdown("## 🎮 Mission Control")
        
        # Status display
        if st.session_state.monitoring:
            st.markdown('<p class="status-connected">● MISSION ACTIVE</p>', unsafe_allow_html=True)
            if st.button("🛑 Stop Mission", type="secondary"):
                stop_monitoring()
                st.rerun()
        else:
            st.markdown('<p class="status-disconnected">● MISSION INACTIVE</p>', unsafe_allow_html=True)
            if st.button("🚀 Start Mission", type="primary"):
                start_monitoring()
                st.rerun()
        
        # Mission timer
        if st.session_state.mission_start_time and st.session_state.monitoring:
            elapsed = time.time() - st.session_state.mission_start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            st.markdown(f'<p class="mission-time">{hours:02d}:{minutes:02d}:{seconds:02d}</p>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<p class="mission-time">00:00:00</p>', unsafe_allow_html=True)
        
        # Reset button
        if st.button("🔄 Reset Mission"):
            reset_mission()
            st.rerun()
        
        st.markdown("---")
        
        # Statistics
        st.markdown("## 📊 Mission Statistics")
        st.metric("Data Points", len(st.session_state.telemetry_data))
        st.metric("Total Generated", st.session_state.data_points_generated)
        
        if st.session_state.monitoring:
            data_rate = 2.0  # We generate at 2Hz
            st.metric("Data Rate", f"{data_rate:.1f} Hz")
        else:
            st.metric("Data Rate", "0.0 Hz")
        
        st.markdown("---")
        
        # Mission Log
        st.markdown("## 📝 Mission Log")
        if st.session_state.log_messages:
            log_text = "\n".join(list(st.session_state.log_messages)[-8:])
            st.text_area("Recent Events", log_text, height=200, disabled=True, key="mission_log")
        else:
            st.info("No mission events yet")
    
    # Main content area
    if st.session_state.current_data:
        # Current telemetry display
        st.markdown("## 📡 Current Telemetry Status")
        
        power_status = st.session_state.current_data.get('power_status', {})
        radio_status = st.session_state.current_data.get('radio_status', {})
        nvm_counters = st.session_state.current_data.get('nvm_counters', {})
        system_info = st.session_state.current_data.get('system_info', {})
        
        # Telemetry metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            battery_v = power_status.get('battery_voltage', 0)
            delta_color = "normal"
            if battery_v < 6.0:
                delta_color = "inverse"
            st.metric("🔋 Battery", f"{battery_v:.2f} V")
        
        with col2:
            rssi = radio_status.get('last_rssi', 'N/A')
            st.metric("📡 Signal", f"{rssi} dBm")
        
        with col3:
            tasks = system_info.get('active_tasks', 0)
            st.metric("⚙️ Tasks", f"{tasks}")
        
        with col4:
            errors = nvm_counters.get('state_errors', 0)
            st.metric("🚨 Errors", f"{errors}")
        
        with col5:
            uptime = power_status.get('uptime_seconds', 0)
            st.metric("⏰ Uptime", f"{uptime:.1f} s")
        
        # Real-time plots
        st.markdown("## 📈 Real-Time Telemetry Graphs")
        fig = create_telemetry_plots()
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional system information
        with st.expander("🔧 Detailed System Information", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### System Flags")
                flags = st.session_state.current_data.get('nvm_flags', {})
                for flag_name, flag_value in flags.items():
                    status_icon = "🟢" if flag_value else "⚪"
                    status_text = "Active" if flag_value else "Inactive"
                    st.write(f"{status_icon} {flag_name}: {status_text}")
            
            with col2:
                st.markdown("### Task Status")
                task_states = st.session_state.current_data.get('task_states', {})
                for task_name, task_info in task_states.items():
                    running = task_info.get('running', False)
                    status_icon = "✅" if running else "❌"
                    status_text = "Running" if running else "Stopped"
                    st.write(f"{status_icon} {task_name}: {status_text}")
    
    else:
        # No data state
        st.markdown("## 🎯 Mission Status")
        st.info("🚀 Click 'Start Mission' in the sidebar to begin BeepSat simulation")
        st.markdown("### System Ready")
        st.write("- ✅ Simulator initialized")
        st.write("- ✅ Dashboard ready")
        st.write("- ⏳ Waiting for mission start")
        
        # Show empty plots
        fig = create_telemetry_plots()
        st.plotly_chart(fig, use_container_width=True)
    
    # Auto-refresh every 1 second
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()