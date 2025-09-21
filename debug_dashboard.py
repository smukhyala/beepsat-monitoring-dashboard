#!/usr/bin/env python3
"""
Debug version of BeepSat Streamlit Dashboard
Shows connection status and data flow
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
import subprocess
import threading
import queue
import os
import sys
import re
from collections import deque
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="BeepSat Debug Dashboard",
    page_icon="🛰️",
    layout="wide"
)

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
if 'debug_messages' not in st.session_state:
    st.session_state.debug_messages = deque(maxlen=20)
if 'raw_lines' not in st.session_state:
    st.session_state.raw_lines = deque(maxlen=10)

def add_debug_message(msg):
    """Add debug message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    st.session_state.debug_messages.append(f"[{timestamp}] {msg}")

def parse_telemetry_line(line):
    """Extract JSON from telemetry output"""
    if 'TELEMETRY_OUTPUT:' in line or 'TELEM:' in line:
        json_start = line.find('{')
        if json_start != -1:
            json_data = line[json_start:]
            try:
                data = json.loads(json_data)
                return data
            except json.JSONDecodeError as e:
                add_debug_message(f"JSON decode error: {e}")
    return None

def monitor_beepsat():
    """Monitor BeepSat with detailed debugging"""
    basic_dir = "software_example_beepsat/basic"
    
    add_debug_message("Starting BeepSat monitoring thread")
    
    if not os.path.exists(basic_dir):
        add_debug_message(f"ERROR: Directory {basic_dir} not found")
        return
    
    try:
        add_debug_message("Starting BeepSat process...")
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
        add_debug_message("BeepSat process started successfully")
        
        line_count = 0
        telemetry_count = 0
        
        while st.session_state.monitoring and process.poll() is None:
            try:
                line = process.stdout.readline()
                if line:
                    line_count += 1
                    clean_line = line.strip()
                    
                    # Store raw lines for debugging
                    st.session_state.raw_lines.append(clean_line)
                    
                    # Try to parse telemetry
                    data = parse_telemetry_line(line)
                    if data:
                        telemetry_count += 1
                        st.session_state.data_queue.put(data)
                        add_debug_message(f"Telemetry parsed #{telemetry_count}")
                    
                    # Log interesting lines
                    if any(keyword in clean_line for keyword in ['tasks loaded', 'Running', 'Battery:', 'IMU']):
                        add_debug_message(f"BeepSat: {clean_line}")
                        
                elif process.poll() is not None:
                    add_debug_message("BeepSat process ended")
                    break
                    
            except Exception as e:
                add_debug_message(f"Monitoring error: {e}")
                break
        
        add_debug_message(f"Monitoring stopped. Lines: {line_count}, Telemetry: {telemetry_count}")
        
        # Cleanup
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
            add_debug_message("BeepSat process terminated")
            
    except Exception as e:
        add_debug_message(f"Failed to start BeepSat: {e}")

def start_monitoring():
    """Start monitoring with debug output"""
    if not st.session_state.monitoring:
        st.session_state.monitoring = True
        add_debug_message("🚀 Starting mission monitoring")
        
        # Clear old data
        while not st.session_state.data_queue.empty():
            st.session_state.data_queue.get()
        
        # Start monitoring thread
        thread = threading.Thread(target=monitor_beepsat, daemon=True)
        thread.start()

def stop_monitoring():
    """Stop monitoring"""
    if st.session_state.monitoring:
        st.session_state.monitoring = False
        add_debug_message("🛑 Stopping mission monitoring")
        
        if st.session_state.beepsat_process:
            try:
                st.session_state.beepsat_process.terminate()
                add_debug_message("BeepSat process terminated")
            except:
                pass

def process_data_queue():
    """Process telemetry data from queue"""
    processed_count = 0
    while not st.session_state.data_queue.empty():
        try:
            data = st.session_state.data_queue.get_nowait()
            st.session_state.telemetry_data.append(data)
            st.session_state.current_data = data
            processed_count += 1
        except queue.Empty:
            break
    
    if processed_count > 0:
        add_debug_message(f"Processed {processed_count} telemetry packets")
    
    return processed_count

# Main dashboard
st.title("🛰️ BeepSat Debug Dashboard")

# Process any new data
new_data_count = process_data_queue()

# Control panel
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.monitoring:
        if st.button("🛑 Stop Mission"):
            stop_monitoring()
    else:
        if st.button("🚀 Start Mission"):
            start_monitoring()

with col2:
    if st.button("🔄 Clear Debug Log"):
        st.session_state.debug_messages.clear()
        st.session_state.raw_lines.clear()
        st.rerun()

with col3:
    status = "🟢 ACTIVE" if st.session_state.monitoring else "🔴 INACTIVE"
    st.write(f"Status: {status}")

# Statistics
st.write("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Telemetry Points", len(st.session_state.telemetry_data))
with col2:
    st.metric("Queue Size", st.session_state.data_queue.qsize())
with col3:
    st.metric("Debug Messages", len(st.session_state.debug_messages))
with col4:
    st.metric("Monitoring", "Yes" if st.session_state.monitoring else "No")

# Current telemetry
if st.session_state.current_data:
    st.write("---")
    st.subheader("📡 Current Telemetry")
    
    power_status = st.session_state.current_data.get('power_status', {})
    radio_status = st.session_state.current_data.get('radio_status', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        battery_v = power_status.get('battery_voltage', 0)
        st.metric("🔋 Battery", f"{battery_v:.2f} V")
    with col2:
        rssi = radio_status.get('last_rssi', 'N/A')
        st.metric("📡 RSSI", f"{rssi} dBm")
    with col3:
        uptime = power_status.get('uptime_seconds', 0)
        st.metric("⏰ Uptime", f"{uptime:.1f} s")
    with col4:
        timestamp = st.session_state.current_data.get('timestamp', 0)
        age = time.time() - timestamp
        st.metric("🕐 Data Age", f"{age:.1f} s")

# Debug information
st.write("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🐛 Debug Messages")
    if st.session_state.debug_messages:
        debug_text = "\n".join(list(st.session_state.debug_messages))
        st.text_area("Debug Log", debug_text, height=300, disabled=True)
    else:
        st.info("No debug messages yet")

with col2:
    st.subheader("📜 Raw BeepSat Output")
    if st.session_state.raw_lines:
        raw_text = "\n".join(list(st.session_state.raw_lines))
        st.text_area("Raw Output", raw_text, height=300, disabled=True)
    else:
        st.info("No raw output yet")

# Simple plot if we have data
if len(st.session_state.telemetry_data) > 1:
    st.write("---")
    st.subheader("📈 Battery Voltage Trend")
    
    data_list = list(st.session_state.telemetry_data)
    timestamps = []
    voltages = []
    
    for data in data_list:
        timestamps.append(datetime.fromtimestamp(data.get('timestamp', time.time())))
        power_status = data.get('power_status', {})
        voltages.append(power_status.get('battery_voltage', 0))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, 
        y=voltages,
        mode='lines+markers',
        name='Battery Voltage',
        line=dict(color='cyan', width=2)
    ))
    fig.update_layout(
        height=300,
        xaxis_title="Time",
        yaxis_title="Voltage (V)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# Auto-refresh
time.sleep(2)
st.rerun()