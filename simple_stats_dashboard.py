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

def display_mission_report():
    """Generate and display a comprehensive mission summary report"""
    if len(st.session_state.telemetry_data) < 5:
        st.info("📋 Mission report will be available after collecting sufficient data (minimum 5 data points)")
        st.markdown("### What the Mission Report Will Include:")
        st.write("• **Mission Overview** - Duration, data points collected, system performance")
        st.write("• **Power System Analysis** - Battery health, charging patterns, voltage stability")
        st.write("• **Communication Assessment** - Signal quality, connectivity patterns")
        st.write("• **System Health Report** - Error rates, anomalies, operational issues")
        st.write("• **Performance Summary** - Key metrics and recommendations")
        st.write("• **Trend Analysis** - What happened during the mission")
        return
    
    # Extract data for analysis
    battery_voltages, rssi_values, error_counts, charge_currents = extract_metric_arrays()
    
    # Calculate comprehensive statistics
    calc = SimpleStatCalculator()
    battery_stats = calc.calculate_stats(battery_voltages)
    rssi_stats = calc.calculate_stats(rssi_values)
    error_stats = calc.calculate_stats(error_counts)
    charge_stats = calc.calculate_stats(charge_currents)
    
    # Mission duration
    if st.session_state.mission_start_time:
        mission_duration = time.time() - st.session_state.mission_start_time
        duration_minutes = int(mission_duration // 60)
        duration_seconds = int(mission_duration % 60)
    else:
        mission_duration = 0
        duration_minutes = duration_seconds = 0
    
    # Generate comprehensive report
    st.markdown("## 📋 BEEPSAT MISSION SUMMARY REPORT")
    st.markdown("---")
    
    # Mission Overview
    st.markdown("### 🚀 Mission Overview")
    
    mission_status = "🟢 COMPLETED" if not st.session_state.monitoring else "🟡 IN PROGRESS"
    st.markdown(f"**Mission Status:** {mission_status}")
    st.markdown(f"**Mission Duration:** {duration_minutes}m {duration_seconds}s")
    st.markdown(f"**Data Points Collected:** {len(st.session_state.telemetry_data)}")
    st.markdown(f"**Data Collection Rate:** {len(st.session_state.telemetry_data) / max(mission_duration/60, 1):.1f} points/minute")
    
    # Overall mission health score
    health_score = calculate_mission_health_score(battery_stats, rssi_stats, error_stats)
    health_color = get_health_color(health_score)
    st.markdown(f"**Overall Mission Health:** {health_color} {health_score:.0f}/100")
    
    st.markdown("---")
    
    # Power System Analysis
    st.markdown("### 🔋 Power System Analysis")
    
    if battery_stats:
        battery_health = analyze_battery_performance(battery_stats, charge_stats)
        st.markdown(battery_health)
    
    st.markdown("---")
    
    # Communication Assessment
    st.markdown("### 📡 Communication System Assessment")
    
    if rssi_stats:
        comm_analysis = analyze_communication_performance(rssi_stats)
        st.markdown(comm_analysis)
    
    st.markdown("---")
    
    # System Health Report
    st.markdown("### 🏥 System Health Report")
    
    if error_stats:
        health_analysis = analyze_system_health(error_stats, battery_stats)
        st.markdown(health_analysis)
    
    st.markdown("---")
    
    # Trend Analysis
    st.markdown("### 📈 Trend Analysis")
    
    trend_analysis = analyze_mission_trends(battery_stats, rssi_stats, error_stats)
    st.markdown(trend_analysis)
    
    st.markdown("---")
    
    # Recommendations
    st.markdown("### 💡 Recommendations & Insights")
    
    recommendations = generate_recommendations(battery_stats, rssi_stats, error_stats, mission_duration)
    st.markdown(recommendations)
    
    # Mission Score Summary
    st.markdown("---")
    st.markdown("### 📊 Mission Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        power_score = calculate_power_score(battery_stats)
        st.metric("Power Score", f"{power_score:.0f}/100", f"{get_performance_trend(power_score)}")
    
    with col2:
        comm_score = calculate_comm_score(rssi_stats)
        st.metric("Comm Score", f"{comm_score:.0f}/100", f"{get_performance_trend(comm_score)}")
    
    with col3:
        reliability_score = calculate_reliability_score(error_stats)
        st.metric("Reliability Score", f"{reliability_score:.0f}/100", f"{get_performance_trend(reliability_score)}")
    
    with col4:
        st.metric("Mission Grade", f"{get_mission_grade(health_score)}", f"{health_score:.0f}/100")

def calculate_mission_health_score(battery_stats, rssi_stats, error_stats):
    """Calculate overall mission health score"""
    score = 100
    
    if battery_stats:
        # Battery health impact
        if battery_stats['mean'] < 6.5:
            score -= 20
        if battery_stats['cv'] > 5:  # High variability
            score -= 10
        if len(battery_stats['anomalies']) > 0:
            score -= 5 * len(battery_stats['anomalies'])
    
    if rssi_stats:
        # Communication health impact
        if rssi_stats['mean'] < -70:
            score -= 15
        if rssi_stats['cv'] > 20:  # High signal variability
            score -= 10
    
    if error_stats:
        # Error impact
        if error_stats['slope'] > 0.01:  # Increasing errors
            score -= 25
        if error_stats['max'] > 10:  # High error count
            score -= 15
    
    return max(score, 0)

def get_health_color(score):
    """Get color emoji for health score"""
    if score >= 90:
        return "🟢"
    elif score >= 75:
        return "🟡"
    elif score >= 50:
        return "🟠"
    else:
        return "🔴"

def analyze_battery_performance(battery_stats, charge_stats):
    """Analyze battery performance and generate report text"""
    analysis = []
    
    avg_voltage = battery_stats['mean']
    voltage_stability = battery_stats['cv']
    voltage_trend = battery_stats['slope']
    
    # Overall battery health
    if avg_voltage > 7.2:
        analysis.append("**Battery Health: 🟢 EXCELLENT** - Average voltage of {:.2f}V indicates healthy power system.".format(avg_voltage))
    elif avg_voltage > 6.8:
        analysis.append("**Battery Health: 🟡 GOOD** - Average voltage of {:.2f}V shows adequate power levels.".format(avg_voltage))
    elif avg_voltage > 6.3:
        analysis.append("**Battery Health: 🟠 FAIR** - Average voltage of {:.2f}V suggests monitoring required.".format(avg_voltage))
    else:
        analysis.append("**Battery Health: 🔴 POOR** - Average voltage of {:.2f}V indicates critical power situation.".format(avg_voltage))
    
    # Voltage stability
    if voltage_stability < 2:
        analysis.append("Voltage stability was excellent with only {:.1f}% variation.".format(voltage_stability))
    elif voltage_stability < 5:
        analysis.append("Voltage showed good stability with {:.1f}% variation.".format(voltage_stability))
    else:
        analysis.append("Voltage exhibited high variability ({:.1f}%), indicating potential power system issues.".format(voltage_stability))
    
    # Trend analysis
    if voltage_trend > 0.001:
        analysis.append("📈 Positive trend: Battery voltage increased during mission, possibly due to charging.")
    elif voltage_trend < -0.001:
        analysis.append("📉 Discharge trend: Battery voltage decreased by {:.3f}V per reading, indicating normal discharge.".format(abs(voltage_trend)))
    else:
        analysis.append("➡️ Stable trend: Battery voltage remained consistent throughout mission.")
    
    # Charging analysis
    if charge_stats and charge_stats['mean'] > 0.1:
        analysis.append("⚡ Charging detected: Average charging current of {:.2f}A suggests active power generation.".format(charge_stats['mean']))
    
    # Anomaly detection
    if battery_stats['anomalies']:
        analysis.append("⚠️ {} voltage anomalies detected, requiring investigation.".format(len(battery_stats['anomalies'])))
    
    return " ".join(analysis)

def analyze_communication_performance(rssi_stats):
    """Analyze communication system performance"""
    analysis = []
    
    avg_rssi = rssi_stats['mean']
    signal_stability = rssi_stats['cv']
    
    # Signal quality assessment
    if avg_rssi > -50:
        analysis.append("**Signal Quality: 🟢 EXCELLENT** - Average RSSI of {:.1f} dBm indicates strong communication link.".format(avg_rssi))
    elif avg_rssi > -65:
        analysis.append("**Signal Quality: 🟡 GOOD** - Average RSSI of {:.1f} dBm shows reliable communication.".format(avg_rssi))
    elif avg_rssi > -80:
        analysis.append("**Signal Quality: 🟠 FAIR** - Average RSSI of {:.1f} dBm suggests marginal communication.".format(avg_rssi))
    else:
        analysis.append("**Signal Quality: 🔴 POOR** - Average RSSI of {:.1f} dBm indicates weak communication link.".format(avg_rssi))
    
    # Signal stability
    signal_range = rssi_stats['max'] - rssi_stats['min']
    if signal_range < 20:
        analysis.append("Signal showed excellent stability with only {:.1f} dBm variation.".format(signal_range))
    elif signal_range < 35:
        analysis.append("Signal demonstrated good stability with {:.1f} dBm range.".format(signal_range))
    else:
        analysis.append("Signal exhibited high variability ({:.1f} dBm range), possibly due to orbital mechanics or interference.".format(signal_range))
    
    # Deep fades detection
    if rssi_stats['min'] < -85:
        analysis.append("🚨 Deep signal fades detected (minimum {:.0f} dBm), indicating potential communication blackouts.".format(rssi_stats['min']))
    
    # Signal anomalies
    if rssi_stats['anomalies']:
        analysis.append("📡 {} signal anomalies detected, suggesting environmental or hardware effects.".format(len(rssi_stats['anomalies'])))
    
    return " ".join(analysis)

def analyze_system_health(error_stats, battery_stats):
    """Analyze overall system health"""
    analysis = []
    
    current_errors = error_stats['max']
    error_growth = error_stats['slope']
    
    # Error level assessment
    if current_errors == 0:
        analysis.append("**System Reliability: 🟢 PERFECT** - No errors detected during mission.")
    elif current_errors < 3:
        analysis.append("**System Reliability: 🟢 EXCELLENT** - Only {} errors detected, indicating robust operation.".format(current_errors))
    elif current_errors < 8:
        analysis.append("**System Reliability: 🟡 GOOD** - {} errors detected, within acceptable range.".format(current_errors))
    elif current_errors < 15:
        analysis.append("**System Reliability: 🟠 FAIR** - {} errors detected, monitoring recommended.".format(current_errors))
    else:
        analysis.append("**System Reliability: 🔴 POOR** - {} errors detected, investigation required.".format(current_errors))
    
    # Error trend
    if error_growth > 0.01:
        analysis.append("🔴 Error rate is increasing, indicating potential system degradation.")
    elif error_growth > 0.001:
        analysis.append("🟠 Slight increase in error rate observed.")
    else:
        analysis.append("🟢 Error rate remained stable throughout mission.")
    
    # Correlation with power
    if battery_stats and battery_stats['mean'] < 6.5 and current_errors > 5:
        analysis.append("⚠️ High error count correlates with low battery voltage, suggesting power-related issues.")
    
    return " ".join(analysis)

def analyze_mission_trends(battery_stats, rssi_stats, error_stats):
    """Analyze overall mission trends"""
    trends = []
    
    # Power trends
    if battery_stats:
        if battery_stats['slope'] < -0.001:
            trends.append("🔋 **Power Trend:** Steady discharge observed, consistent with mission operations.")
        elif battery_stats['slope'] > 0.001:
            trends.append("🔋 **Power Trend:** Battery charging detected, indicating active power generation.")
        else:
            trends.append("🔋 **Power Trend:** Stable power levels maintained throughout mission.")
    
    # Communication trends
    if rssi_stats:
        if rssi_stats['cv'] > 15:
            trends.append("📡 **Communication Trend:** High signal variability suggests orbital motion effects or environmental changes.")
        else:
            trends.append("📡 **Communication Trend:** Stable communication link maintained.")
    
    # System trends
    if error_stats:
        if error_stats['slope'] > 0.005:
            trends.append("🚨 **System Trend:** Increasing error rate indicates potential system stress or degradation.")
        else:
            trends.append("🚨 **System Trend:** Stable system performance with consistent error levels.")
    
    return "\n\n".join(trends) if trends else "No significant trends detected in mission data."

def generate_recommendations(battery_stats, rssi_stats, error_stats, mission_duration):
    """Generate mission recommendations"""
    recommendations = []
    
    # Battery recommendations
    if battery_stats:
        if battery_stats['mean'] < 6.5:
            recommendations.append("🔋 **Power Management:** Consider implementing power-saving modes or increasing charging efficiency.")
        if len(battery_stats['anomalies']) > 2:
            recommendations.append("🔋 **Power Monitoring:** Investigate voltage anomalies to identify potential hardware issues.")
    
    # Communication recommendations
    if rssi_stats:
        if rssi_stats['mean'] < -70:
            recommendations.append("📡 **Communication:** Consider antenna optimization or power amplification for improved signal strength.")
        if rssi_stats['min'] < -85:
            recommendations.append("📡 **Link Margin:** Implement communication protocols robust to signal fades.")
    
    # System recommendations
    if error_stats:
        if error_stats['slope'] > 0.01:
            recommendations.append("🚨 **System Health:** Investigate root cause of increasing error rate.")
        if error_stats['max'] > 10:
            recommendations.append("🚨 **Error Management:** Implement enhanced error handling and recovery procedures.")
    
    # Mission duration recommendations
    if mission_duration < 60:
        recommendations.append("⏱️ **Mission Duration:** Consider longer missions to gather more comprehensive performance data.")
    
    # General recommendations
    recommendations.append("📊 **Data Analysis:** Continue monitoring these metrics for long-term trend analysis.")
    recommendations.append("🔄 **Mission Planning:** Use this data to optimize future mission parameters.")
    
    return "\n\n".join(recommendations)

def calculate_power_score(battery_stats):
    """Calculate power system score"""
    if not battery_stats:
        return 50
    
    score = 100
    if battery_stats['mean'] < 6.5:
        score -= 30
    if battery_stats['cv'] > 5:
        score -= 20
    if len(battery_stats['anomalies']) > 0:
        score -= 10 * len(battery_stats['anomalies'])
    
    return max(score, 0)

def calculate_comm_score(rssi_stats):
    """Calculate communication score"""
    if not rssi_stats:
        return 50
    
    score = 100
    if rssi_stats['mean'] < -70:
        score -= 25
    if rssi_stats['cv'] > 20:
        score -= 15
    if rssi_stats['min'] < -85:
        score -= 20
    
    return max(score, 0)

def calculate_reliability_score(error_stats):
    """Calculate system reliability score"""
    if not error_stats:
        return 100
    
    score = 100
    if error_stats['max'] > 5:
        score -= 20
    if error_stats['slope'] > 0.01:
        score -= 30
    
    return max(score, 0)

def get_performance_trend(score):
    """Get performance trend indicator"""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Fair"
    else:
        return "Needs Attention"

def get_mission_grade(score):
    """Get overall mission grade"""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    else:
        return "D"

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
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Live Graphs", "📊 Statistics", "📋 Data Table", "📝 Mission Report"])
    
    with tab1:
        st.markdown("### Real-Time Telemetry Graphs")
        create_simple_plots()
    
    with tab2:
        st.markdown("### Mission Statistics & Analysis")
        display_statistics()
    
    with tab3:
        st.markdown("### Raw Telemetry Data")
        display_data_table()
    
    with tab4:
        st.markdown("### Mission Summary Report")
        display_mission_report()
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()