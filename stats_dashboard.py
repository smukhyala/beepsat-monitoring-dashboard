#!/usr/bin/env python3
"""
BeepSat Dashboard with Prominent Statistical Display
Shows averages, std dev, and other stats immediately and prominently
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
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
    .anomaly-highlight {
        background-color: #3d1a1a;
        border: 2px solid #ff4444;
        padding: 8px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

class SimpleStatCalculator:
    """Simple statistics calculator that works without scipy"""
    
    @staticmethod
    def calculate_stats(values):
        """Calculate comprehensive statistics for a list of values"""
        if not values or len(values) == 0:
            return None
        
        # Convert to numbers
        vals = [float(v) for v in values if v is not None]
        if not vals:
            return None
        
        n = len(vals)
        
        # Basic stats
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
        
        # Percentiles
        def percentile(data, p):
            k = (len(data) - 1) * p / 100
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return data[int(k)]
            return data[int(f)] * (c - k) + data[int(c)] * (k - f)
        
        q25 = percentile(sorted_vals, 25)
        q75 = percentile(sorted_vals, 75)
        
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
        
        # Anomaly detection (simple z-score)
        anomalies = []
        if std_val > 0:
            for i, val in enumerate(vals):
                z_score = abs(val - mean_val) / std_val
                if z_score > 2.5:  # 2.5 sigma threshold
                    anomalies.append(i)
        
        # Coefficient of variation
        cv = (std_val / abs(mean_val)) * 100 if mean_val != 0 else 0
        
        # Rate of change
        if n > 1:
            changes = [vals[i] - vals[i-1] for i in range(1, n)]
            avg_change = sum(changes) / len(changes)
            max_increase = max(changes) if changes else 0
            max_decrease = min(changes) if changes else 0
        else:
            avg_change = max_increase = max_decrease = 0
        
        return {
            'count': n,
            'mean': mean_val,
            'median': median_val,
            'std': std_val,
            'variance': variance,
            'min': min_val,
            'max': max_val,
            'range': range_val,
            'q25': q25,
            'q75': q75,
            'slope': slope,
            'anomalies': anomalies,
            'cv': cv,
            'avg_change': avg_change,
            'max_increase': max_increase,
            'max_decrease': max_decrease
        }

class BeepSatSimulator:
    """BeepSat simulator with realistic variations"""
    
    def __init__(self):
        self.start_time = time.time()
        self.battery_base = 7.4
        self.battery_noise = 0.15
        self.boot_count = random.randint(15, 45)
        self.state_errors = random.randint(1, 8)
        self.gs_responses = random.randint(5, 30)
        self.rssi_base = -55
        
    def get_battery_voltage(self, current_time):
        """Realistic battery voltage with slow discharge"""
        elapsed_hours = (current_time - self.start_time) / 3600
        trend = -0.02 * elapsed_hours  # Slow discharge
        noise = random.uniform(-self.battery_noise, self.battery_noise)
        
        # Occasional spikes (5% chance)
        if random.random() < 0.05:
            noise += random.uniform(0.2, 0.6)
        
        voltage = self.battery_base + trend + noise
        return max(min(voltage, 8.0), 5.8)
    
    def get_rssi(self, current_time):
        """RSSI with orbital effects"""
        # Simulate orbital period effect
        orbital_phase = (current_time % 240) / 240 * 2 * math.pi  # 4-minute "orbit"
        orbital_effect = 6 * math.sin(orbital_phase)
        noise = random.uniform(-8, 8)
        
        # Occasional deep fades (3% chance)
        if random.random() < 0.03:
            noise -= random.uniform(15, 25)
        
        return max(min(self.rssi_base + orbital_effect + noise, -25), -95)
    
    def generate_telemetry(self):
        """Generate telemetry data"""
        current_time = time.time()
        
        # Occasionally increment counters
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
        return {}, {}, {}, {}
    
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

def display_statistics_prominently():
    """Display statistics in the Statistics tab"""
    if len(st.session_state.telemetry_data) < 3:
        st.warning("📊 Statistical analysis will appear after collecting more data")
        st.info(f"Current data points: {len(st.session_state.telemetry_data)} / 3 required")
        
        # Show preview of what will be available
        st.markdown("### Available Statistics (when ready):")
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
    
    # Display prominently
    st.markdown("## 📊 LIVE STATISTICAL ANALYSIS")
    
    # Create columns for each metric
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 🔋 Battery Statistics")
        if battery_stats:
            st.metric("Average", f"{battery_stats['mean']:.3f} V")
            st.metric("Std Dev", f"±{battery_stats['std']:.3f} V")
            st.metric("Range", f"{battery_stats['range']:.3f} V")
            st.metric("Min/Max", f"{battery_stats['min']:.2f} - {battery_stats['max']:.2f} V")
            
            # Trend indicator
            if battery_stats['slope'] > 0.001:
                trend = "📈 Increasing"
            elif battery_stats['slope'] < -0.001:
                trend = "📉 Decreasing"
            else:
                trend = "➡️ Stable"
            st.write(f"**Trend:** {trend}")
            
            # Anomalies
            if battery_stats['anomalies']:
                st.markdown(f"<div class='anomaly-highlight'>⚠️ {len(battery_stats['anomalies'])} anomalies detected</div>", 
                           unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📡 Signal Statistics")
        if rssi_stats:
            st.metric("Average", f"{rssi_stats['mean']:.1f} dBm")
            st.metric("Std Dev", f"±{rssi_stats['std']:.1f} dBm")
            st.metric("Range", f"{rssi_stats['range']:.1f} dBm")
            st.metric("Min/Max", f"{rssi_stats['min']:.0f} - {rssi_stats['max']:.0f} dBm")
            
            # Signal quality
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
                st.markdown(f"<div class='anomaly-highlight'>📡 {len(rssi_stats['anomalies'])} signal anomalies</div>", 
                           unsafe_allow_html=True)
    
    with col3:
        st.markdown("### 🚨 Error Statistics")
        if error_stats:
            st.metric("Current", f"{error_stats['max']}")
            st.metric("Average", f"{error_stats['mean']:.1f}")
            st.metric("Growth Rate", f"{error_stats['avg_change']:.3f}/reading")
            st.metric("Max Jump", f"+{error_stats['max_increase']:.0f}")
            
            # Error trend
            if error_stats['slope'] > 0.01:
                error_trend = "🔴 Increasing"
            elif error_stats['slope'] > 0.001:
                error_trend = "🟠 Slight increase"
            else:
                error_trend = "🟢 Stable"
            st.write(f"**Trend:** {error_trend}")
    
    with col4:
        st.markdown("### ⚡ Power Statistics")
        if charge_stats and battery_stats:
            st.metric("Avg Charge", f"{charge_stats['mean']:.2f} A")
            st.metric("Max Charge", f"{charge_stats['max']:.2f} A")
            st.metric("Stability", f"{battery_stats['cv']:.1f}% CV")
            
            # Power health
            if battery_stats['mean'] > 7.0:
                power_health = "🟢 Healthy"
            elif battery_stats['mean'] > 6.5:
                power_health = "🟡 Moderate"
            else:
                power_health = "🔴 Low"
            st.write(f"**Health:** {power_health}")
    
    # Additional detailed statistics
    with st.expander("📈 Detailed Statistical Analysis", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔋 Battery Detailed Stats")
            if battery_stats:
                st.write(f"• **Median:** {battery_stats['median']:.3f} V")
                st.write(f"• **25th Percentile:** {battery_stats['q25']:.3f} V")
                st.write(f"• **75th Percentile:** {battery_stats['q75']:.3f} V")
                st.write(f"• **Coefficient of Variation:** {battery_stats['cv']:.1f}%")
                st.write(f"• **Average Change:** {battery_stats['avg_change']:.4f} V/reading")
                
                # Histogram
                if len(battery_voltages) > 5:
                    fig = px.histogram(x=battery_voltages, nbins=15, title="Battery Voltage Distribution")
                    fig.update_layout(height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📡 Signal Detailed Stats")
            if rssi_stats:
                st.write(f"• **Median:** {rssi_stats['median']:.1f} dBm")
                st.write(f"• **25th Percentile:** {rssi_stats['q25']:.1f} dBm")
                st.write(f"• **75th Percentile:** {rssi_stats['q75']:.1f} dBm")
                st.write(f"• **Coefficient of Variation:** {rssi_stats['cv']:.1f}%")
                st.write(f"• **Average Change:** {rssi_stats['avg_change']:.2f} dBm/reading")
                
                # Histogram
                if len(rssi_values) > 5:
                    fig = px.histogram(x=rssi_values, nbins=15, title="RSSI Distribution")
                    fig.update_layout(height=250, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

def create_telemetry_plots():
    """Create telemetry plots with statistical overlays"""
    if not st.session_state.telemetry_data:
        fig = make_subplots(rows=2, cols=2, subplot_titles=("Battery", "RSSI", "Errors", "Uptime"))
        fig.update_layout(height=600, showlegend=False)
        return fig
    
    # Extract data
    battery_voltages, rssi_values, error_counts, _ = extract_metric_arrays()
    timestamps = [datetime.fromtimestamp(d['timestamp']) for d in st.session_state.telemetry_data]
    uptime_values = [d['power_status']['uptime_seconds'] for d in st.session_state.telemetry_data]
    
    # Calculate statistics for overlays
    calc = SimpleStatCalculator()
    battery_stats = calc.calculate_stats(battery_voltages)
    
    # Create plots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("🔋 Battery Voltage", "📡 Signal Strength", "🚨 Error Count", "⏰ Uptime")
    )
    
    # Battery plot with statistical overlays
    fig.add_trace(go.Scatter(x=timestamps, y=battery_voltages, mode='lines+markers',
                           name='Battery', line=dict(color='cyan', width=3)), row=1, col=1)
    
    # Add mean line
    if battery_stats:
        fig.add_hline(y=battery_stats['mean'], line_dash="dot", line_color="yellow",
                     annotation_text=f"Avg: {battery_stats['mean']:.2f}V", row=1, col=1)
    
    # RSSI plot
    fig.add_trace(go.Scatter(x=timestamps, y=rssi_values, mode='lines+markers',
                           name='RSSI', line=dict(color='lime', width=3)), row=1, col=2)
    
    # Error plot
    fig.add_trace(go.Scatter(x=timestamps, y=error_counts, mode='lines+markers',
                           name='Errors', line=dict(color='orange', width=3)), row=2, col=1)
    
    # Uptime plot
    fig.add_trace(go.Scatter(x=timestamps, y=uptime_values, mode='lines+markers',
                           name='Uptime', line=dict(color='magenta', width=3)), row=2, col=2)
    
    fig.update_layout(height=600, showlegend=False, plot_bgcolor='rgba(14, 17, 23, 0.8)',
                     font=dict(color='white'))
    
    return fig

def display_data_table():
    """Display raw telemetry data in table format"""
    if not st.session_state.telemetry_data:
        st.info("No telemetry data available yet. Start the mission to see data.")
        return
    
    # Convert telemetry data to a readable table
    data_for_table = []
    for i, data in enumerate(list(st.session_state.telemetry_data)[-20:]):  # Last 20 entries
        power = data.get('power_status', {})
        radio = data.get('radio_status', {})
        counters = data.get('nvm_counters', {})
        
        row = {
            'Time': datetime.fromtimestamp(data.get('timestamp', 0)).strftime("%H:%M:%S"),
            'Battery (V)': f"{power.get('battery_voltage', 0):.3f}",
            'RSSI (dBm)': f"{radio.get('last_rssi', 0):.0f}",
            'Errors': counters.get('state_errors', 0),
            'Charge (A)': f"{power.get('charge_current', 0):.2f}",
            'Uptime (s)': f"{power.get('uptime_seconds', 0):.1f}"
        }
        data_for_table.append(row)
    
    # Display as dataframe
    import pandas as pd
    df = pd.DataFrame(data_for_table)
    st.dataframe(df, use_container_width=True, height=400)
    
    # Summary info
    st.write(f"**Showing last {len(data_for_table)} of {len(st.session_state.telemetry_data)} total data points**")

def main():
    """Main dashboard function"""
    initialize_session_state()
    
    # Header
    st.markdown("# 🛰️ BEEPSAT MISSION CONTROL")
    st.markdown("### Real-Time Monitoring with Live Statistics")
    
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
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Live Graphs", "📊 Statistics", "📋 Data Table"])
    
    with tab1:
        st.markdown("### Real-Time Telemetry Graphs")
        fig = create_telemetry_plots()
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### Mission Statistics & Analysis")
        display_statistics_prominently()
    
    with tab3:
        st.markdown("### Raw Telemetry Data")
        display_data_table()
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()