#!/usr/bin/env python3
"""
BeepSat Real-Time Dashboard with Streamlit
Professional web-based satellite monitoring interface
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import json
import time
import subprocess
import threading
import queue
import os
import sys
import re
from collections import deque
from datetime import datetime, timedelta

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
    .metric-container {
        background-color: #1e2125;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #31333a;
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

class BeepSatStreamlitDashboard:
    """Streamlit-based BeepSat monitoring dashboard"""
    
    def __init__(self):
        # Initialize session state
        if 'monitoring' not in st.session_state:
            st.session_state.monitoring = False
        if 'telemetry_data' not in st.session_state:
            st.session_state.telemetry_data = deque(maxlen=100)
        if 'current_data' not in st.session_state:
            st.session_state.current_data = {}
        if 'beepsat_process' not in st.session_state:
            st.session_state.beepsat_process = None
        if 'data_queue' not in st.session_state:
            st.session_state.data_queue = queue.Queue()
        if 'monitoring_thread' not in st.session_state:
            st.session_state.monitoring_thread = None
        if 'mission_start_time' not in st.session_state:
            st.session_state.mission_start_time = None
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = deque(maxlen=50)
    
    def parse_telemetry_line(self, line):
        """Extract JSON from telemetry output"""
        if 'TELEMETRY_OUTPUT:' in line or 'TELEM:' in line:
            json_match = re.search(r'\{.*\}', line)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return data
                except json.JSONDecodeError:
                    pass
        return None
    
    def monitor_beepsat(self):
        """Monitor BeepSat emulation in background thread"""
        basic_dir = "software_example_beepsat/basic"
        
        if not os.path.exists(basic_dir):
            return
        
        try:
            # Start BeepSat emulation
            process = subprocess.Popen(
                [sys.executable, "main_emulated.py"],
                cwd=basic_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            st.session_state.beepsat_process = process
            
            # Monitor output
            while st.session_state.monitoring and process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        # Parse telemetry
                        data = self.parse_telemetry_line(line)
                        if data:
                            st.session_state.data_queue.put(data)
                        # Log interesting messages
                        elif any(keyword in line for keyword in ['[', 'ERROR', 'WARNING', 'loaded']):
                            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
                            if clean_line and not any(skip in clean_line for skip in ['[RADIO_TX]', '[LOG]', 'Telemetry']):
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                st.session_state.log_messages.append(f"[{timestamp}] {clean_line}")
                except Exception:
                    break
            
            # Cleanup
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                
        except Exception:
            pass
    
    def start_monitoring(self):
        """Start BeepSat monitoring"""
        if not st.session_state.monitoring:
            st.session_state.monitoring = True
            st.session_state.mission_start_time = time.time()
            
            # Start monitoring thread
            thread = threading.Thread(target=self.monitor_beepsat, daemon=True)
            thread.start()
            st.session_state.monitoring_thread = thread
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.log_messages.append(f"[{timestamp}] 🚀 Mission started - BeepSat monitoring active")
    
    def stop_monitoring(self):
        """Stop BeepSat monitoring"""
        if st.session_state.monitoring:
            st.session_state.monitoring = False
            
            # Stop process
            if st.session_state.beepsat_process:
                try:
                    st.session_state.beepsat_process.terminate()
                except:
                    pass
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.log_messages.append(f"[{timestamp}] 🛑 Mission stopped")
    
    def process_telemetry_queue(self):
        """Process new telemetry data from queue"""
        new_data_count = 0
        while not st.session_state.data_queue.empty():
            try:
                data = st.session_state.data_queue.get_nowait()
                st.session_state.telemetry_data.append(data)
                st.session_state.current_data = data
                new_data_count += 1
            except queue.Empty:
                break
        return new_data_count
    
    def create_telemetry_plots(self):
        """Create real-time telemetry plots"""
        if not st.session_state.telemetry_data:
            # Show placeholder when no data
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Battery Voltage", "Radio Signal Strength", "System Errors", "Uptime"),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            fig.add_trace(go.Scatter(x=[], y=[], name="No Data"), row=1, col=1)
            fig.update_layout(
                height=600,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
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
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Battery voltage plot
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=battery_voltages,
                mode='lines+markers',
                name='Battery Voltage',
                line=dict(color='cyan', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        fig.add_hline(y=6.0, line_dash="dash", line_color="red", 
                     annotation_text="Low Battery", row=1, col=1)
        
        # RSSI plot
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=rssi_values,
                mode='lines+markers',
                name='RSSI',
                line=dict(color='lime', width=2),
                marker=dict(size=4)
            ),
            row=1, col=2
        )
        
        # Error count plot
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=error_counts,
                mode='lines+markers',
                name='Errors',
                line=dict(color='orange', width=2),
                marker=dict(size=4)
            ),
            row=2, col=1
        )
        
        # Uptime plot
        fig.add_trace(
            go.Scatter(
                x=timestamps, y=uptime_values,
                mode='lines+markers',
                name='Uptime',
                line=dict(color='magenta', width=2),
                marker=dict(size=4)
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=600,
            showlegend=False,
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
        fig.update_yaxes(title_text="Error Count", row=2, col=1)
        fig.update_yaxes(title_text="Uptime (s)", row=2, col=2)
        
        return fig
    
    def run(self):
        """Main dashboard interface"""
        # Header
        st.markdown("# 🛰️ BEEPSAT MISSION CONTROL DASHBOARD")
        
        # Process any new telemetry data
        new_data_count = self.process_telemetry_queue()
        
        # Sidebar - Mission Control
        with st.sidebar:
            st.markdown("## 🎮 Mission Control")
            
            # Mission status
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
            
            # Data reset
            if st.button("🔄 Reset Data"):
                st.session_state.telemetry_data.clear()
                st.session_state.current_data = {}
                st.session_state.log_messages.clear()
                st.rerun()
            
            # Statistics
            st.markdown("## 📊 Statistics")
            st.metric("Data Points", len(st.session_state.telemetry_data))
            st.metric("Updates/sec", f"{new_data_count * 2:.1f}")  # Approximate
            
            # System log
            st.markdown("## 📝 Mission Log")
            if st.session_state.log_messages:
                log_text = "\n".join(list(st.session_state.log_messages)[-10:])  # Last 10 messages
                st.text_area("Recent Events", log_text, height=200, disabled=True)
        
        # Main content area
        if st.session_state.current_data:
            # Current telemetry values
            st.markdown("## 📡 Current Telemetry")
            
            # Extract current values
            power_status = st.session_state.current_data.get('power_status', {})
            radio_status = st.session_state.current_data.get('radio_status', {})
            nvm_counters = st.session_state.current_data.get('nvm_counters', {})
            system_info = st.session_state.current_data.get('system_info', {})
            
            # Create metrics display
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                battery_v = power_status.get('battery_voltage', 0)
                battery_color = "normal"
                if battery_v < 6.0:
                    battery_color = "inverse"
                elif battery_v < 6.5:
                    battery_color = "off"
                st.metric("🔋 Battery", f"{battery_v:.2f} V", delta=None)
            
            with col2:
                rssi = radio_status.get('last_rssi', 'N/A')
                st.metric("📡 Signal", f"{rssi} dBm", delta=None)
            
            with col3:
                tasks = system_info.get('active_tasks', 0)
                st.metric("⚙️ Tasks", f"{tasks}", delta=None)
            
            with col4:
                errors = nvm_counters.get('state_errors', 0)
                st.metric("🚨 Errors", f"{errors}", delta=None)
            
            with col5:
                uptime = power_status.get('uptime_seconds', 0)
                st.metric("⏰ Uptime", f"{uptime:.1f} s", delta=None)
            
            # Real-time plots
            st.markdown("## 📈 Real-Time Telemetry Graphs")
            fig = self.create_telemetry_plots()
            st.plotly_chart(fig, use_container_width=True)
            
            # Additional system info
            if st.session_state.current_data:
                with st.expander("🔧 Detailed System Information"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### NVM Flags")
                        flags = st.session_state.current_data.get('nvm_flags', {})
                        for flag_name, flag_value in flags.items():
                            status = "🟢 Active" if flag_value else "⚪ Inactive"
                            st.write(f"{flag_name}: {status}")
                    
                    with col2:
                        st.markdown("### Task States")
                        task_states = st.session_state.current_data.get('task_states', {})
                        for task_name, task_info in task_states.items():
                            running = task_info.get('running', False)
                            status = "✅ Running" if running else "❌ Stopped"
                            st.write(f"{task_name}: {status}")
        
        else:
            # No data state
            st.markdown("## 🎯 Mission Status")
            st.info("Click '🚀 Start Mission' in the sidebar to begin monitoring BeepSat telemetry")
            
            # Show empty plots
            fig = self.create_telemetry_plots()
            st.plotly_chart(fig, use_container_width=True)
        
        # Auto-refresh every 1 second
        time.sleep(1)
        st.rerun()

def main():
    """Main function"""
    # Check directory
    if not os.path.exists("software_example_beepsat/basic"):
        st.error("❌ Error: Run this script from the project root directory")
        st.code("Expected structure: software_example_beepsat/basic/")
        return
    
    # Create and run dashboard
    dashboard = BeepSatStreamlitDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()