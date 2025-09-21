#!/usr/bin/env python3
"""
Integrated BeepSat Dashboard
Runs both simulation and Streamlit dashboard in one script
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
import threading
import queue
import os
import sys
import re
from collections import deque
from datetime import datetime
import random

# Add the lib directory to Python path for imports
sys.path.insert(0, os.path.join("software_example_beepsat", "basic", "lib"))

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

class IntegratedBeepSatSimulator:
    """Integrated BeepSat simulator that runs directly in the dashboard"""
    
    def __init__(self):
        # Initialize simulation state
        self.start_time = time.time()
        self.running = False
        
        # Simulated hardware state
        self.battery_base = 7.4
        self.battery_noise = 0.2
        self.battery_trend = 0.0
        
        # NVM counters
        self.boot_count = random.randint(10, 50)
        self.state_errors = random.randint(0, 5)
        self.gs_responses = random.randint(0, 25)
        self.charge_cycles = random.randint(20, 100)
        
        # Flags
        self.flags = {
            'low_battery': False,
            'solar_active': True,
            'gps_on': False,
            'low_battery_timeout': False,
            'gps_fix': False,
            'shutdown': False
        }
        
        # Tasks
        self.tasks = ['beacon', 'monitor', 'blink', 'vbatt', 'time', 'imu']
        
        # RSSI simulation
        self.rssi_base = -55
        self.rssi_variation = 15
    
    @property
    def battery_voltage(self):
        """Simulate realistic battery voltage"""
        # Slow discharge over time
        elapsed_hours = (time.time() - self.start_time) / 3600
        self.battery_trend = -0.05 * elapsed_hours
        
        # Add noise
        voltage = self.battery_base + self.battery_trend + random.uniform(-self.battery_noise, self.battery_noise)
        
        # Update low battery flag
        self.flags['low_battery'] = voltage < 6.0
        
        return max(voltage, 5.5)  # Don't go below 5.5V
    
    @property
    def rssi(self):
        """Simulate radio signal strength"""
        return self.rssi_base + random.randint(-self.rssi_variation, self.rssi_variation)
    
    @property
    def uptime(self):
        """Current uptime in seconds"""
        if self.running:
            return time.time() - self.start_time
        return 0
    
    def generate_telemetry(self):
        """Generate a complete telemetry packet"""
        current_time = time.time()
        
        # Occasionally increment error count
        if random.random() < 0.001:  # 0.1% chance per call
            self.state_errors += 1
        
        telemetry = {
            'timestamp': current_time,
            'uptime': self.uptime,
            'task_states': {
                task: {
                    'running': True,
                    'last_seen': current_time
                } for task in self.tasks
            },
            'nvm_counters': {
                'boot_count': self.boot_count,
                'state_errors': self.state_errors,
                'vbus_resets': random.randint(0, 3),
                'gs_responses': self.gs_responses,
                'charge_cycles': self.charge_cycles
            },
            'nvm_flags': self.flags.copy(),
            'radio_status': {
                'last_rssi': self.rssi,
                'frequency': 433.0,
                'available': True
            },
            'power_status': {
                'battery_voltage': self.battery_voltage,
                'low_battery_threshold': 6.0,
                'uptime_seconds': self.uptime,
                'charge_current': random.uniform(0.0, 0.8) if random.random() < 0.7 else 0.0
            },
            'system_info': {
                'active_tasks': len(self.tasks),
                'monitoring_frequency': 2,
                'version': 'integrated'
            }
        }
        
        return telemetry
    
    def start(self):
        """Start the simulation"""
        self.running = True
        self.start_time = time.time()
    
    def stop(self):
        """Stop the simulation"""
        self.running = False
    
    def reset(self):
        """Reset simulation state"""
        self.start_time = time.time()
        self.battery_trend = 0.0
        self.state_errors = random.randint(0, 2)
        self.gs_responses = random.randint(0, 5)

class IntegratedDashboard:
    """Main dashboard with integrated simulation"""
    
    def __init__(self):
        # Initialize session state
        if 'monitoring' not in st.session_state:
            st.session_state.monitoring = False
        if 'telemetry_data' not in st.session_state:
            st.session_state.telemetry_data = deque(maxlen=100)
        if 'current_data' not in st.session_state:
            st.session_state.current_data = {}
        if 'simulator' not in st.session_state:
            st.session_state.simulator = IntegratedBeepSatSimulator()
        if 'mission_start_time' not in st.session_state:
            st.session_state.mission_start_time = None
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = deque(maxlen=50)
        if 'data_generation_thread' not in st.session_state:
            st.session_state.data_generation_thread = None
        if 'telemetry_queue' not in st.session_state:
            st.session_state.telemetry_queue = queue.Queue()
    
    def add_log_message(self, message):
        """Add message to mission log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.log_messages.append(f"[{timestamp}] {message}")
    
    def generate_telemetry_data(self):
        """Background thread to generate telemetry data"""
        while st.session_state.monitoring:
            if st.session_state.simulator.running:
                # Generate telemetry packet
                telemetry = st.session_state.simulator.generate_telemetry()
                st.session_state.telemetry_queue.put(telemetry)
            
            time.sleep(0.5)  # Generate data every 0.5 seconds (2Hz)
    
    def start_monitoring(self):
        """Start the mission monitoring"""
        if not st.session_state.monitoring:
            st.session_state.monitoring = True
            st.session_state.mission_start_time = time.time()
            st.session_state.simulator.start()
            
            # Start data generation thread
            thread = threading.Thread(target=self.generate_telemetry_data, daemon=True)
            thread.start()
            st.session_state.data_generation_thread = thread
            
            self.add_log_message("🚀 Mission started - BeepSat simulation active")
            self.add_log_message("📡 Telemetry generation started at 2Hz")
    
    def stop_monitoring(self):
        """Stop the mission monitoring"""
        if st.session_state.monitoring:
            st.session_state.monitoring = False
            st.session_state.simulator.stop()
            
            self.add_log_message("🛑 Mission stopped")
    
    def reset_mission(self):
        """Reset all mission data"""
        # Stop monitoring if active
        if st.session_state.monitoring:
            self.stop_monitoring()
        
        # Clear data
        st.session_state.telemetry_data.clear()
        st.session_state.current_data = {}
        st.session_state.log_messages.clear()
        
        # Clear queue
        while not st.session_state.telemetry_queue.empty():
            st.session_state.telemetry_queue.get()
        
        # Reset simulator
        st.session_state.simulator.reset()
        st.session_state.mission_start_time = None
        
        self.add_log_message("🔄 Mission data reset")
    
    def process_telemetry_queue(self):
        """Process new telemetry data"""
        processed_count = 0
        while not st.session_state.telemetry_queue.empty():
            try:
                data = st.session_state.telemetry_queue.get_nowait()
                st.session_state.telemetry_data.append(data)
                st.session_state.current_data = data
                processed_count += 1
            except queue.Empty:
                break
        return processed_count
    
    def create_telemetry_plots(self):
        """Create real-time telemetry plots"""
        if not st.session_state.telemetry_data:
            # Empty plot
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal", "🚨 System Errors", "⏰ Uptime"),
            )
            fig.update_layout(height=600, showlegend=False, plot_bgcolor='rgba(14, 17, 23, 0.8)')
            return fig
        
        # Extract data
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
        
        # Create plots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal Strength", "🚨 System Errors", "⏰ System Uptime"),
        )
        
        # Battery voltage
        fig.add_trace(
            go.Scatter(x=timestamps, y=battery_voltages, mode='lines+markers',
                      name='Battery', line=dict(color='cyan', width=2)), row=1, col=1)
        fig.add_hline(y=6.0, line_dash="dash", line_color="red", row=1, col=1)
        
        # RSSI
        fig.add_trace(
            go.Scatter(x=timestamps, y=rssi_values, mode='lines+markers',
                      name='RSSI', line=dict(color='lime', width=2)), row=1, col=2)
        
        # Errors
        fig.add_trace(
            go.Scatter(x=timestamps, y=error_counts, mode='lines+markers',
                      name='Errors', line=dict(color='orange', width=2)), row=2, col=1)
        
        # Uptime
        fig.add_trace(
            go.Scatter(x=timestamps, y=uptime_values, mode='lines+markers',
                      name='Uptime', line=dict(color='magenta', width=2)), row=2, col=2)
        
        # Update layout
        fig.update_layout(
            height=600, showlegend=False,
            plot_bgcolor='rgba(14, 17, 23, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=12)
        )
        
        # Update axes
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        
        # Y-axis labels
        fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
        fig.update_yaxes(title_text="RSSI (dBm)", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_yaxes(title_text="Seconds", row=2, col=2)
        
        return fig
    
    def run(self):
        """Main dashboard interface"""
        # Header
        st.markdown("# 🛰️ BEEPSAT MISSION CONTROL DASHBOARD")
        st.markdown("### Integrated Simulation & Real-Time Monitoring")
        
        # Process telemetry data
        new_data_count = self.process_telemetry_queue()
        
        # Sidebar - Mission Control
        with st.sidebar:
            st.markdown("## 🎮 Mission Control")
            
            # Status and controls
            if st.session_state.monitoring:
                st.markdown('<p class="status-connected">● MISSION ACTIVE</p>', unsafe_allow_html=True)
                if st.button("🛑 Stop Mission", type="secondary"):
                    self.stop_monitoring()
            else:
                st.markdown('<p class="status-disconnected">● MISSION INACTIVE</p>', unsafe_allow_html=True)
                if st.button("🚀 Start Mission", type="primary"):
                    self.start_monitoring()
            
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
                self.reset_mission()
                st.rerun()
            
            # Statistics
            st.markdown("## 📊 Statistics")
            st.metric("Data Points", len(st.session_state.telemetry_data))
            st.metric("Queue Size", st.session_state.telemetry_queue.qsize())
            if new_data_count > 0:
                st.metric("Data Rate", f"{new_data_count * 2:.1f} Hz")
            
            # Mission Log
            st.markdown("## 📝 Mission Log")
            if st.session_state.log_messages:
                log_text = "\n".join(list(st.session_state.log_messages)[-8:])
                st.text_area("Recent Events", log_text, height=180, disabled=True)
        
        # Main content
        if st.session_state.current_data:
            # Current telemetry
            st.markdown("## 📡 Current Telemetry")
            
            power_status = st.session_state.current_data.get('power_status', {})
            radio_status = st.session_state.current_data.get('radio_status', {})
            nvm_counters = st.session_state.current_data.get('nvm_counters', {})
            system_info = st.session_state.current_data.get('system_info', {})
            
            # Metrics row
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                battery_v = power_status.get('battery_voltage', 0)
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
            
            # Plots
            st.markdown("## 📈 Real-Time Telemetry Graphs")
            fig = self.create_telemetry_plots()
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            # No data state
            st.markdown("## 🎯 Mission Status")
            st.info("🚀 Click 'Start Mission' in the sidebar to begin BeepSat simulation and monitoring")
            
            # Empty plots
            fig = self.create_telemetry_plots()
            st.plotly_chart(fig, use_container_width=True)
        
        # Auto-refresh
        time.sleep(1)
        st.rerun()

def main():
    """Main function"""
    dashboard = IntegratedDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()