#!/usr/bin/env python3
"""
Simple BeepSat Dashboard with Statistics - No Pandas Conflicts
Shows statistics in tabs without import issues
"""

import streamlit as st
import plotly.graph_objects as go
import json
import time
import os
import sys
import random
import math
from collections import deque
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="BeepSat Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    .stats-box {
        background-color: #1e2125;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #31333a;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class SimpleStatCalculator:
    """Simple statistics calculator"""
    
    @staticmethod
    def calculate_stats(values):
        """Calculate comprehensive statistics for a list of values"""
        if not values or len(values) == 0:
            return None
        
        vals = [float(v) for v in values if v is not None]
        if not vals:
            return None
        
        n = len(vals)
        mean_val = sum(vals) / n
        min_val = min(vals)
        max_val = max(vals)
        range_val = max_val - min_val
        
        # Standard deviation
        variance = sum((x - mean_val) ** 2 for x in vals) / (n - 1) if n > 1 else 0
        std_val = math.sqrt(variance)
        
        # Median
        sorted_vals = sorted(vals)
        if n % 2 == 0:
            median_val = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
        else:
            median_val = sorted_vals[n//2]
        
        # Trend (simple linear regression)
        if n > 2:
            x_vals = list(range(n))
            x_mean = sum(x_vals) / n
            y_mean = mean_val
            
            numerator = sum((x_vals[i] - x_mean) * (vals[i] - y_mean) for i in range(n))
            denominator = sum((x - x_mean) ** 2 for x in x_vals)
            
            slope = numerator / denominator if denominator != 0 else 0
        else:
            slope = 0
        
        # Anomalies (simple z-score)
        anomalies = []
        if std_val > 0:
            for i, val in enumerate(vals):
                z_score = abs(val - mean_val) / std_val
                if z_score > 2.5:
                    anomalies.append(i)
        
        # Coefficient of variation
        cv = (std_val / abs(mean_val)) * 100 if mean_val != 0 else 0
        
        return {
            'count': n,
            'mean': mean_val,
            'median': median_val,
            'std': std_val,
            'min': min_val,
            'max': max_val,
            'range': range_val,
            'slope': slope,
            'anomalies': anomalies,
            'cv': cv
        }

class BeepSatSimulator:
    """BeepSat simulator"""
    
    def __init__(self):
        self.start_time = time.time()
        self.battery_base = 7.4
        self.battery_noise = 0.15
        self.boot_count = random.randint(15, 45)
        self.state_errors = random.randint(1, 8)
        self.gs_responses = random.randint(5, 30)
        self.rssi_base = -55
        
    def get_battery_voltage(self, current_time):
        elapsed_hours = (current_time - self.start_time) / 3600
        trend = -0.02 * elapsed_hours
        noise = random.uniform(-self.battery_noise, self.battery_noise)
        
        if random.random() < 0.05:
            noise += random.uniform(0.2, 0.6)
        
        voltage = self.battery_base + trend + noise
        return max(min(voltage, 8.0), 5.8)
    
    def get_rssi(self, current_time):
        orbital_phase = (current_time % 240) / 240 * 2 * math.pi
        orbital_effect = 6 * math.sin(orbital_phase)
        noise = random.uniform(-8, 8)
        
        if random.random() < 0.03:
            noise -= random.uniform(15, 25)
        
        return max(min(self.rssi_base + orbital_effect + noise, -25), -95)
    
    def generate_telemetry(self):
        current_time = time.time()
        
        if random.random() < 0.001:
            self.state_errors += 1
        if random.random() < 0.005:
            self.gs_responses += 1
        
        battery_v = self.get_battery_voltage(current_time)
        rssi = self.get_rssi(current_time)
        
        return {
            'timestamp': current_time,
            'uptime': current_time - self.start_time,
            'power_status': {
                'battery_voltage': battery_v,
                'uptime_seconds': current_time - self.start_time,
                'charge_current': random.uniform(0.0, 0.8) if random.random() < 0.6 else 0.0
            },
            'radio_status': {
                'last_rssi': rssi,
                'available': True
            },
            'nvm_counters': {
                'boot_count': self.boot_count,
                'state_errors': self.state_errors,
                'gs_responses': self.gs_responses
            },
            'system_info': {
                'active_tasks': 6,
                'monitoring_frequency': 2
            }
        }

# Initialize session state
def initialize_session_state():
    if 'monitoring' not in st.session_state:
        st.session_state.monitoring = False
    if 'telemetry_data' not in st.session_state:
        st.session_state.telemetry_data = deque(maxlen=200)
    if 'current_data' not in st.session_state:
        st.session_state.current_data = {}
    if 'simulator' not in st.session_state:
        st.session_state.simulator = BeepSatSimulator()
    if 'mission_start_time' not in st.session_state:
        st.session_state.mission_start_time = None
    if 'last_telemetry_time' not in st.session_state:
        st.session_state.last_telemetry_time = 0
    if 'data_points_generated' not in st.session_state:
        st.session_state.data_points_generated = 0

def start_monitoring():
    if not st.session_state.monitoring:
        st.session_state.monitoring = True
        st.session_state.mission_start_time = time.time()
        st.session_state.simulator = BeepSatSimulator()
        st.session_state.last_telemetry_time = time.time()
        st.session_state.data_points_generated = 0

def stop_monitoring():
    if st.session_state.monitoring:
        st.session_state.monitoring = False

def reset_mission():
    if st.session_state.monitoring:
        stop_monitoring()
    st.session_state.telemetry_data.clear()
    st.session_state.current_data = {}
    st.session_state.mission_start_time = None
    st.session_state.last_telemetry_time = 0
    st.session_state.data_points_generated = 0

def generate_telemetry_data():
    current_time = time.time()
    if (st.session_state.monitoring and 
        current_time - st.session_state.last_telemetry_time >= 0.5):
        
        telemetry = st.session_state.simulator.generate_telemetry()
        st.session_state.telemetry_data.append(telemetry)
        st.session_state.current_data = telemetry
        st.session_state.last_telemetry_time = current_time
        st.session_state.data_points_generated += 1
        return True
    return False

def extract_metric_arrays():
    """Extract arrays of values for statistical analysis"""
    if not st.session_state.telemetry_data:
        return [], [], [], []
    
    battery_voltages = []
    rssi_values = []
    error_counts = []
    charge_currents = []
    
    for data in st.session_state.telemetry_data:
        power_status = data.get('power_status', {})
        battery_voltages.append(power_status.get('battery_voltage', 0))
        charge_currents.append(power_status.get('charge_current', 0))
        
        radio_status = data.get('radio_status', {})
        rssi_values.append(radio_status.get('last_rssi', -100))
        
        nvm_counters = data.get('nvm_counters', {})
        error_counts.append(nvm_counters.get('state_errors', 0))
    
    return battery_voltages, rssi_values, error_counts, charge_currents

def display_statistics():
    """Display statistics in the Statistics tab"""
    if len(st.session_state.telemetry_data) < 3:
        st.warning("📊 Statistical analysis will appear after collecting more data")
        st.info(f"Current data points: {len(st.session_state.telemetry_data)} / 3 required")
        
        st.markdown("### 📊 Available Statistics (when ready):")
        st.write("🔋 **Battery:** Average, Std Dev, Range, Trend, Anomalies")
        st.write("📡 **Signal:** Average RSSI, Quality, Signal fades")  
        st.write("🚨 **Errors:** Growth rate, Error spikes, Trends")
        st.write("⚡ **Power:** Health score, Stability metrics")
        return
    
    # Extract data
    battery_voltages, rssi_values, error_counts, charge_currents = extract_metric_arrays()
    
    # Calculate statistics
    calc = SimpleStatCalculator()
    battery_stats = calc.calculate_stats(battery_voltages)
    rssi_stats = calc.calculate_stats(rssi_values)
    error_stats = calc.calculate_stats(error_counts)
    charge_stats = calc.calculate_stats(charge_currents)
    
    # Display statistics in columns
    st.markdown("## 📊 MISSION STATISTICS")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 🔋 Battery")
        if battery_stats:
            st.metric("Average", f"{battery_stats['mean']:.3f} V")
            st.metric("Std Dev", f"±{battery_stats['std']:.3f} V")
            st.metric("Range", f"{battery_stats['range']:.3f} V")
            st.write(f"**Min:** {battery_stats['min']:.2f} V")
            st.write(f"**Max:** {battery_stats['max']:.2f} V")
            st.write(f"**Median:** {battery_stats['median']:.3f} V")
            
            if battery_stats['slope'] > 0.001:
                trend = "📈 Increasing"
            elif battery_stats['slope'] < -0.001:
                trend = "📉 Decreasing"
            else:
                trend = "➡️ Stable"
            st.write(f"**Trend:** {trend}")
            
            if battery_stats['anomalies']:
                st.error(f"⚠️ {len(battery_stats['anomalies'])} anomalies detected")
    
    with col2:
        st.markdown("### 📡 Signal")
        if rssi_stats:
            st.metric("Average", f"{rssi_stats['mean']:.1f} dBm")
            st.metric("Std Dev", f"±{rssi_stats['std']:.1f} dBm")
            st.metric("Range", f"{rssi_stats['range']:.1f} dBm")
            st.write(f"**Min:** {rssi_stats['min']:.0f} dBm")
            st.write(f"**Max:** {rssi_stats['max']:.0f} dBm")
            st.write(f"**Median:** {rssi_stats['median']:.1f} dBm")
            
            avg_rssi = rssi_stats['mean']
            if avg_rssi > -50:
                quality = "🟢 Excellent"
            elif avg_rssi > -65:
                quality = "🟡 Good"
            elif avg_rssi > -80:
                quality = "🟠 Fair"
            else:
                quality = "🔴 Poor"
            st.write(f"**Quality:** {quality}")
            
            if rssi_stats['anomalies']:
                st.warning(f"📡 {len(rssi_stats['anomalies'])} signal anomalies")
    
    with col3:
        st.markdown("### 🚨 Errors")
        if error_stats:
            st.metric("Current", f"{error_stats['max']}")
            st.metric("Average", f"{error_stats['mean']:.1f}")
            st.metric("Range", f"{error_stats['range']:.0f}")
            st.write(f"**Min:** {error_stats['min']:.0f}")
            st.write(f"**Max:** {error_stats['max']:.0f}")
            st.write(f"**Median:** {error_stats['median']:.1f}")
            
            if error_stats['slope'] > 0.01:
                error_trend = "🔴 Increasing"
            elif error_stats['slope'] > 0.001:
                error_trend = "🟠 Slight increase"
            else:
                error_trend = "🟢 Stable"
            st.write(f"**Trend:** {error_trend}")
    
    with col4:
        st.markdown("### ⚡ Power")
        if charge_stats and battery_stats:
            st.metric("Avg Charge", f"{charge_stats['mean']:.2f} A")
            st.metric("Max Charge", f"{charge_stats['max']:.2f} A")
            st.metric("Stability", f"{battery_stats['cv']:.1f}% CV")
            st.write(f"**Charge Range:** {charge_stats['range']:.2f} A")
            st.write(f"**Charge Median:** {charge_stats['median']:.2f} A")
            
            if battery_stats['mean'] > 7.0:
                power_health = "🟢 Healthy"
            elif battery_stats['mean'] > 6.5:
                power_health = "🟡 Moderate"
            else:
                power_health = "🔴 Low"
            st.write(f"**Health:** {power_health}")

def create_simple_plots():
    """Create simple plots without subplots to avoid pandas conflict"""
    if not st.session_state.telemetry_data:
        st.info("Start mission to see graphs")
        return
    
    battery_voltages, rssi_values, error_counts, _ = extract_metric_arrays()
    timestamps = [datetime.fromtimestamp(d['timestamp']) for d in st.session_state.telemetry_data]
    uptime_values = [d['power_status']['uptime_seconds'] for d in st.session_state.telemetry_data]
    
    # Create individual plots
    col1, col2 = st.columns(2)
    
    with col1:
        # Battery plot
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=timestamps, y=battery_voltages, mode='lines+markers',
                                name='Battery', line=dict(color='cyan', width=3)))
        fig1.update_layout(title="🔋 Battery Voltage", height=300, 
                          plot_bgcolor='rgba(14, 17, 23, 0.8)', font=dict(color='white'))
        st.plotly_chart(fig1, use_container_width=True)
        
        # Error plot
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=timestamps, y=error_counts, mode='lines+markers',
                                name='Errors', line=dict(color='orange', width=3)))
        fig3.update_layout(title="🚨 Error Count", height=300,
                          plot_bgcolor='rgba(14, 17, 23, 0.8)', font=dict(color='white'))
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        # RSSI plot
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=timestamps, y=rssi_values, mode='lines+markers',
                                name='RSSI', line=dict(color='lime', width=3)))
        fig2.update_layout(title="📡 Signal Strength", height=300,
                          plot_bgcolor='rgba(14, 17, 23, 0.8)', font=dict(color='white'))
        st.plotly_chart(fig2, use_container_width=True)
        
        # Uptime plot
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=timestamps, y=uptime_values, mode='lines+markers',
                                name='Uptime', line=dict(color='magenta', width=3)))
        fig4.update_layout(title="⏰ System Uptime", height=300,
                          plot_bgcolor='rgba(14, 17, 23, 0.8)', font=dict(color='white'))
        st.plotly_chart(fig4, use_container_width=True)

def display_data_table():
    """Display raw telemetry data"""
    if not st.session_state.telemetry_data:
        st.info("No telemetry data available yet. Start the mission to see data.")
        return
    
    st.markdown("### Recent Telemetry Data")
    
    # Show last 15 data points in a simple format
    data_points = list(st.session_state.telemetry_data)[-15:]
    
    for i, data in enumerate(data_points):
        power = data.get('power_status', {})
        radio = data.get('radio_status', {})
        counters = data.get('nvm_counters', {})
        
        timestamp = datetime.fromtimestamp(data.get('timestamp', 0)).strftime("%H:%M:%S")
        battery_v = power.get('battery_voltage', 0)
        rssi = radio.get('last_rssi', 0)
        errors = counters.get('state_errors', 0)
        uptime = power.get('uptime_seconds', 0)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.write(f"**{timestamp}**")
        with col2:
            st.write(f"{battery_v:.3f} V")
        with col3:
            st.write(f"{rssi:.0f} dBm")
        with col4:
            st.write(f"{errors}")
        with col5:
            st.write(f"{uptime:.1f} s")
    
    st.write(f"**Showing last {len(data_points)} of {len(st.session_state.telemetry_data)} total data points**")

def main():
    """Main dashboard function"""
    initialize_session_state()
    
    # Header
    st.markdown("# 🛰️ BEEPSAT MISSION CONTROL")
    st.markdown("### Real-Time Monitoring with Statistics")
    
    # Generate telemetry
    generate_telemetry_data()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎮 Mission Control")
        
        if st.session_state.monitoring:
            st.markdown('<p class="status-connected">● ACTIVE</p>', unsafe_allow_html=True)
            if st.button("🛑 Stop"):
                stop_monitoring()
                st.rerun()
        else:
            st.markdown('<p class="status-disconnected">● INACTIVE</p>', unsafe_allow_html=True)
            if st.button("🚀 Start"):
                start_monitoring()
                st.rerun()
        
        # Mission timer
        if st.session_state.mission_start_time and st.session_state.monitoring:
            elapsed = time.time() - st.session_state.mission_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            st.markdown(f'<p class="mission-time">{minutes:02d}:{seconds:02d}</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="mission-time">00:00</p>', unsafe_allow_html=True)
        
        if st.button("🔄 Reset"):
            reset_mission()
            st.rerun()
        
        st.metric("Data Points", len(st.session_state.telemetry_data))
        st.metric("Generated", st.session_state.data_points_generated)
    
    # Current telemetry
    if st.session_state.current_data:
        st.markdown("## 📡 Current Values")
        power = st.session_state.current_data.get('power_status', {})
        radio = st.session_state.current_data.get('radio_status', {})
        counters = st.session_state.current_data.get('nvm_counters', {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔋 Battery", f"{power.get('battery_voltage', 0):.2f} V")
        with col2:
            st.metric("📡 Signal", f"{radio.get('last_rssi', 0):.0f} dBm")
        with col3:
            st.metric("🚨 Errors", f"{counters.get('state_errors', 0)}")
        with col4:
            st.metric("⏰ Uptime", f"{power.get('uptime_seconds', 0):.0f} s")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📈 Live Graphs", "📊 Statistics", "📋 Data Table"])
    
    with tab1:
        st.markdown("### Real-Time Telemetry Graphs")
        create_simple_plots()
    
    with tab2:
        st.markdown("### Mission Statistics & Analysis")
        display_statistics()
    
    with tab3:
        st.markdown("### Raw Telemetry Data")
        display_data_table()
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()