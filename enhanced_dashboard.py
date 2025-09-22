#!/usr/bin/env python3
"""
Enhanced BeepSat Dashboard with Statistical Analysis
Real-time monitoring with comprehensive statistical insights
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
import pandas as pd
import json
import time
import os
import sys
import random
from collections import deque
from datetime import datetime
import statistics
from scipy import stats

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
    .stat-box {
        background-color: #1e2125;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #31333a;
        margin: 5px 0;
    }
    .anomaly-alert {
        background-color: #3d1a1a;
        border: 2px solid #ff4444;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

class BeepSatSimulator:
    """Enhanced BeepSat simulator with more realistic behavior"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_update = time.time()
        
        # Simulation parameters
        self.battery_base = 7.4
        self.battery_noise = 0.12
        self.battery_trend = 0.0
        
        # Counters
        self.boot_count = random.randint(15, 45)
        self.state_errors = random.randint(1, 8)
        self.gs_responses = random.randint(5, 30)
        self.charge_cycles = random.randint(25, 90)
        
        # Tasks
        self.tasks = ['beacon', 'monitor', 'blink', 'vbatt', 'time', 'imu']
        
        # RSSI simulation with more realistic patterns
        self.rssi_base = -55
        self.rssi_variation = 10
        self.rssi_trend = 0
        
        # Anomaly simulation
        self.anomaly_probability = 0.002  # 0.2% chance per reading
        self.last_anomaly_time = 0
        
    def get_battery_voltage(self, current_time):
        """Calculate realistic battery voltage with occasional anomalies"""
        # Slow discharge over time
        elapsed_hours = (current_time - self.start_time) / 3600
        trend = -0.025 * elapsed_hours
        
        # Normal noise
        noise = random.uniform(-self.battery_noise, self.battery_noise)
        
        # Occasional voltage spikes (solar panel reconnection, etc.)
        if random.random() < self.anomaly_probability:
            noise += random.uniform(0.3, 0.8)  # Positive spike
            self.last_anomaly_time = current_time
        
        # Occasional voltage drops (high current draw)
        elif random.random() < self.anomaly_probability * 0.5:
            noise -= random.uniform(0.2, 0.5)  # Negative spike
            self.last_anomaly_time = current_time
        
        voltage = self.battery_base + trend + noise
        return max(min(voltage, 8.2), 5.5)
    
    def get_rssi(self, current_time):
        """Calculate radio signal strength with realistic fading"""
        # Simulate orbital mechanics affecting signal
        orbital_period = 300  # 5 minute "orbit" for demo
        orbital_phase = (current_time % orbital_period) / orbital_period * 2 * np.pi
        orbital_effect = 8 * np.sin(orbital_phase)  # ±8 dBm variation
        
        # Random fading
        fading = random.uniform(-self.rssi_variation, self.rssi_variation)
        
        # Occasional deep fades or signal boosts
        if random.random() < self.anomaly_probability:
            if random.random() < 0.5:
                fading -= random.uniform(15, 25)  # Deep fade
            else:
                fading += random.uniform(10, 20)  # Signal boost
            self.last_anomaly_time = current_time
        
        rssi = self.rssi_base + orbital_effect + fading
        return max(min(rssi, -20), -100)  # Realistic RSSI bounds
    
    def get_uptime(self, current_time):
        """Get current uptime"""
        return current_time - self.start_time
    
    def generate_telemetry(self):
        """Generate complete telemetry packet"""
        current_time = time.time()
        
        # Occasionally increment error count
        if random.random() < 0.0008:
            self.state_errors += 1
        
        # Occasionally increment GS responses
        if random.random() < 0.003:
            self.gs_responses += 1
        
        battery_v = self.get_battery_voltage(current_time)
        rssi = self.get_rssi(current_time)
        
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
                'gps_on': random.random() < 0.15,
                'low_battery_timeout': battery_v < 5.8,
                'gps_fix': random.random() < 0.4,
                'shutdown': False
            },
            'radio_status': {
                'last_rssi': rssi,
                'frequency': 433.0,
                'available': True
            },
            'power_status': {
                'battery_voltage': battery_v,
                'low_battery_threshold': 6.0,
                'uptime_seconds': self.get_uptime(current_time),
                'charge_current': random.uniform(0.0, 0.9) if random.random() < 0.7 else 0.0
            },
            'system_info': {
                'active_tasks': len(self.tasks),
                'monitoring_frequency': 2,
                'version': 'enhanced_dashboard'
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
        self.last_anomaly_time = 0

class StatisticalAnalyzer:
    """Statistical analysis engine for telemetry data"""
    
    def __init__(self):
        self.anomaly_threshold_multiplier = 2.5  # For anomaly detection
        
    def analyze_metric(self, values, metric_name=""):
        """Comprehensive statistical analysis of a metric"""
        if len(values) < 2:
            return None
            
        values_array = np.array(values)
        
        # Basic statistics
        stats_dict = {
            'count': len(values),
            'mean': np.mean(values_array),
            'median': np.median(values_array),
            'std': np.std(values_array),
            'variance': np.var(values_array),
            'min': np.min(values_array),
            'max': np.max(values_array),
            'range': np.max(values_array) - np.min(values_array),
            'q25': np.percentile(values_array, 25),
            'q75': np.percentile(values_array, 75),
            'iqr': np.percentile(values_array, 75) - np.percentile(values_array, 25)
        }
        
        # Trend analysis
        if len(values) > 3:
            x = np.arange(len(values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, values_array)
            stats_dict.update({
                'trend_slope': slope,
                'trend_r_squared': r_value**2,
                'trend_p_value': p_value
            })
        
        # Anomaly detection using z-score
        if len(values) > 5 and stats_dict['std'] > 0:
            z_scores = np.abs((values_array - stats_dict['mean']) / stats_dict['std'])
            anomalies = z_scores > self.anomaly_threshold_multiplier
            stats_dict.update({
                'anomaly_count': np.sum(anomalies),
                'anomaly_percentage': (np.sum(anomalies) / len(values)) * 100,
                'max_z_score': np.max(z_scores),
                'anomaly_indices': np.where(anomalies)[0].tolist()
            })
        
        # Distribution analysis
        if len(values) > 10:
            # Normality test (Shapiro-Wilk for small samples)
            try:
                shapiro_stat, shapiro_p = stats.shapiro(values_array[:50])  # Limit to 50 for performance
                stats_dict.update({
                    'normality_stat': shapiro_stat,
                    'normality_p_value': shapiro_p,
                    'is_normal': shapiro_p > 0.05
                })
            except:
                pass
        
        # Stability metrics
        if len(values) > 1:
            # Coefficient of variation
            if stats_dict['mean'] != 0:
                stats_dict['cv'] = (stats_dict['std'] / abs(stats_dict['mean'])) * 100
            
            # Rate of change
            diffs = np.diff(values_array)
            stats_dict.update({
                'mean_rate_of_change': np.mean(diffs),
                'max_positive_change': np.max(diffs) if len(diffs) > 0 else 0,
                'max_negative_change': np.min(diffs) if len(diffs) > 0 else 0
            })
        
        return stats_dict
    
    def get_health_status(self, battery_stats, rssi_stats, error_stats):
        """Overall system health assessment"""
        health_score = 100
        alerts = []
        
        if battery_stats:
            # Battery health checks
            if battery_stats['mean'] < 6.5:
                health_score -= 20
                alerts.append("⚠️ Low average battery voltage")
            
            if battery_stats.get('anomaly_percentage', 0) > 10:
                health_score -= 15
                alerts.append("⚠️ High battery voltage anomalies")
            
            if battery_stats.get('trend_slope', 0) < -0.001:
                health_score -= 10
                alerts.append("📉 Battery voltage declining")
        
        if rssi_stats:
            # Radio health checks
            if rssi_stats['mean'] < -70:
                health_score -= 15
                alerts.append("📡 Weak average signal strength")
            
            if rssi_stats.get('anomaly_percentage', 0) > 15:
                health_score -= 10
                alerts.append("📡 Signal instability detected")
        
        if error_stats:
            # Error rate checks
            if error_stats.get('trend_slope', 0) > 0.001:
                health_score -= 25
                alerts.append("🚨 Error rate increasing")
            
            if error_stats.get('max_rate_of_change', 0) > 2:
                health_score -= 15
                alerts.append("🚨 Error spikes detected")
        
        # Determine health level
        if health_score >= 90:
            health_level = "Excellent"
            health_color = "🟢"
        elif health_score >= 75:
            health_level = "Good"
            health_color = "🟡"
        elif health_score >= 50:
            health_level = "Fair"
            health_color = "🟠"
        else:
            health_level = "Poor"
            health_color = "🔴"
        
        return {
            'score': max(health_score, 0),
            'level': health_level,
            'color': health_color,
            'alerts': alerts
        }

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    if 'monitoring' not in st.session_state:
        st.session_state.monitoring = False
    if 'telemetry_data' not in st.session_state:
        st.session_state.telemetry_data = deque(maxlen=200)
    if 'current_data' not in st.session_state:
        st.session_state.current_data = {}
    if 'simulator' not in st.session_state:
        st.session_state.simulator = BeepSatSimulator()
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = StatisticalAnalyzer()
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
        st.session_state.simulator = BeepSatSimulator()
        st.session_state.last_telemetry_time = time.time()
        st.session_state.data_points_generated = 0
        add_log_message("🚀 Mission started - Enhanced monitoring active")

def stop_monitoring():
    """Stop mission monitoring"""
    if st.session_state.monitoring:
        st.session_state.monitoring = False
        add_log_message("🛑 Mission stopped")

def reset_mission():
    """Reset all mission data"""
    if st.session_state.monitoring:
        stop_monitoring()
    
    st.session_state.telemetry_data.clear()
    st.session_state.current_data = {}
    st.session_state.log_messages.clear()
    st.session_state.mission_start_time = None
    st.session_state.last_telemetry_time = 0
    st.session_state.data_points_generated = 0
    st.session_state.simulator.reset()
    
    add_log_message("🔄 Mission data reset complete")

def generate_telemetry_data():
    """Generate telemetry data if monitoring is active"""
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

def extract_metric_data():
    """Extract time series data for analysis"""
    if not st.session_state.telemetry_data:
        return {}, {}, {}, {}
    
    data_list = list(st.session_state.telemetry_data)
    timestamps = []
    battery_voltages = []
    rssi_values = []
    error_counts = []
    uptime_values = []
    
    for data in data_list:
        timestamps.append(data.get('timestamp', time.time()))
        
        power_status = data.get('power_status', {})
        battery_voltages.append(power_status.get('battery_voltage', 0))
        
        radio_status = data.get('radio_status', {})
        rssi_values.append(radio_status.get('last_rssi', -100))
        
        nvm_counters = data.get('nvm_counters', {})
        error_counts.append(nvm_counters.get('state_errors', 0))
        
        uptime_values.append(power_status.get('uptime_seconds', 0))
    
    return {
        'timestamps': timestamps,
        'battery_voltages': battery_voltages,
        'rssi_values': rssi_values,
        'error_counts': error_counts,
        'uptime_values': uptime_values
    }

def create_statistical_summary():
    """Create comprehensive statistical analysis display"""
    if len(st.session_state.telemetry_data) < 5:
        st.info("📊 Statistical analysis will appear after collecting more data points (minimum 5)")
        return
    
    # Extract data
    metrics = extract_metric_data()
    
    # Analyze each metric
    battery_stats = st.session_state.analyzer.analyze_metric(
        metrics['battery_voltages'], "Battery Voltage"
    )
    rssi_stats = st.session_state.analyzer.analyze_metric(
        metrics['rssi_values'], "RSSI"
    )
    error_stats = st.session_state.analyzer.analyze_metric(
        metrics['error_counts'], "Error Count"
    )
    
    # System health assessment
    health = st.session_state.analyzer.get_health_status(battery_stats, rssi_stats, error_stats)
    
    # Display system health
    st.markdown("### 🏥 System Health Assessment")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.metric("Health Score", f"{health['score']:.0f}/100")
    with col2:
        st.markdown(f"**Status:** {health['color']} {health['level']}")
    with col3:
        if health['alerts']:
            for alert in health['alerts']:
                st.markdown(f"<div class='anomaly-alert'>{alert}</div>", unsafe_allow_html=True)
    
    # Detailed statistics for each metric
    st.markdown("### 📊 Detailed Statistical Analysis")
    
    # Create tabs for each metric
    tab1, tab2, tab3 = st.tabs(["🔋 Battery Analysis", "📡 Signal Analysis", "🚨 Error Analysis"])
    
    with tab1:
        if battery_stats:
            display_metric_stats("Battery Voltage", battery_stats, "V", metrics['battery_voltages'])
    
    with tab2:
        if rssi_stats:
            display_metric_stats("RSSI", rssi_stats, "dBm", metrics['rssi_values'])
    
    with tab3:
        if error_stats:
            display_metric_stats("Error Count", error_stats, "errors", metrics['error_counts'])

def display_metric_stats(metric_name, stats, unit, values):
    """Display detailed statistics for a single metric"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### 📈 {metric_name} Statistics")
        
        # Basic statistics
        st.metric("Mean", f"{stats['mean']:.3f} {unit}")
        st.metric("Std Deviation", f"{stats['std']:.3f} {unit}")
        st.metric("Range", f"{stats['range']:.3f} {unit}")
        
        # Percentiles
        st.markdown("**Percentiles:**")
        st.write(f"• 25th: {stats['q25']:.3f} {unit}")
        st.write(f"• 50th (Median): {stats['median']:.3f} {unit}")
        st.write(f"• 75th: {stats['q75']:.3f} {unit}")
        st.write(f"• IQR: {stats['iqr']:.3f} {unit}")
    
    with col2:
        st.markdown(f"#### 🔍 {metric_name} Analysis")
        
        # Trend analysis
        if 'trend_slope' in stats:
            trend_direction = "📈 Increasing" if stats['trend_slope'] > 0 else "📉 Decreasing" if stats['trend_slope'] < 0 else "➡️ Stable"
            st.metric("Trend", trend_direction)
            st.metric("R²", f"{stats['trend_r_squared']:.3f}")
        
        # Anomaly analysis
        if 'anomaly_count' in stats:
            st.metric("Anomalies", f"{stats['anomaly_count']} ({stats['anomaly_percentage']:.1f}%)")
            st.metric("Max Z-Score", f"{stats['max_z_score']:.2f}")
        
        # Stability metrics
        if 'cv' in stats:
            stability = "🟢 Stable" if stats['cv'] < 5 else "🟡 Moderate" if stats['cv'] < 15 else "🔴 Unstable"
            st.metric("Stability", stability)
            st.metric("CV", f"{stats['cv']:.1f}%")
        
        # Rate of change
        if 'mean_rate_of_change' in stats:
            st.metric("Avg Rate of Change", f"{stats['mean_rate_of_change']:.4f} {unit}/reading")
    
    # Distribution visualization
    if len(values) > 10:
        st.markdown(f"#### 📊 {metric_name} Distribution")
        
        # Create histogram
        fig = px.histogram(
            x=values, 
            nbins=20,
            title=f"{metric_name} Distribution",
            labels={'x': f'{metric_name} ({unit})', 'y': 'Frequency'}
        )
        fig.update_layout(
            height=300,
            plot_bgcolor='rgba(14, 17, 23, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Normality test results
        if 'is_normal' in stats:
            normality_status = "✅ Normal" if stats['is_normal'] else "❌ Non-normal"
            st.write(f"**Distribution:** {normality_status} (p={stats['normality_p_value']:.4f})")

def create_telemetry_plots():
    """Create enhanced real-time telemetry plots"""
    if not st.session_state.telemetry_data:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal", "🚨 System Errors", "⏰ Uptime"),
        )
        fig.update_layout(height=600, showlegend=False, plot_bgcolor='rgba(14, 17, 23, 0.8)')
        return fig
    
    metrics = extract_metric_data()
    timestamps = [datetime.fromtimestamp(ts) for ts in metrics['timestamps']]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("🔋 Battery Voltage", "📡 Radio Signal Strength", "🚨 System Errors", "⏰ System Uptime"),
    )
    
    # Battery voltage with anomaly highlighting
    battery_stats = st.session_state.analyzer.analyze_metric(metrics['battery_voltages'])
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=metrics['battery_voltages'],
            mode='lines+markers',
            name='Battery Voltage',
            line=dict(color='cyan', width=3),
            marker=dict(size=4, color='cyan')
        ), row=1, col=1
    )
    
    # Highlight anomalies if detected
    if battery_stats and 'anomaly_indices' in battery_stats and battery_stats['anomaly_indices']:
        anomaly_times = [timestamps[i] for i in battery_stats['anomaly_indices']]
        anomaly_values = [metrics['battery_voltages'][i] for i in battery_stats['anomaly_indices']]
        fig.add_trace(
            go.Scatter(
                x=anomaly_times, y=anomaly_values,
                mode='markers',
                name='Anomalies',
                marker=dict(size=8, color='red', symbol='x')
            ), row=1, col=1
        )
    
    fig.add_hline(y=6.0, line_dash="dash", line_color="red", row=1, col=1)
    
    # RSSI plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=metrics['rssi_values'],
            mode='lines+markers',
            name='RSSI',
            line=dict(color='lime', width=3),
            marker=dict(size=4, color='lime')
        ), row=1, col=2
    )
    
    # Error count plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=metrics['error_counts'],
            mode='lines+markers',
            name='Errors',
            line=dict(color='orange', width=3),
            marker=dict(size=4, color='orange')
        ), row=2, col=1
    )
    
    # Uptime plot
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=metrics['uptime_values'],
            mode='lines+markers',
            name='Uptime',
            line=dict(color='magenta', width=3),
            marker=dict(size=4, color='magenta')
        ), row=2, col=2
    )
    
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
    fig.update_yaxes(title_text="Error Count", row=2, col=1)
    fig.update_yaxes(title_text="Uptime (s)", row=2, col=2)
    
    return fig

def main():
    """Main dashboard function with enhanced statistics"""
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("# 🛰️ BEEPSAT MISSION CONTROL DASHBOARD")
    st.markdown("### Real-Time Monitoring with Statistical Analysis")
    
    # Generate new telemetry data
    new_data_generated = generate_telemetry_data()
    
    # Sidebar - Mission Control
    with st.sidebar:
        st.markdown("## 🎮 Mission Control")
        
        # Status and controls
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
            st.metric("Data Rate", "2.0 Hz")
        else:
            st.metric("Data Rate", "0.0 Hz")
        
        st.markdown("---")
        
        # Mission Log
        st.markdown("## 📝 Mission Log")
        if st.session_state.log_messages:
            log_text = "\n".join(list(st.session_state.log_messages)[-8:])
            st.text_area("Recent Events", log_text, height=180, disabled=True, key="mission_log")
    
    # Main content
    if st.session_state.current_data:
        # Current telemetry display
        st.markdown("## 📡 Current Telemetry Status")
        
        power_status = st.session_state.current_data.get('power_status', {})
        radio_status = st.session_state.current_data.get('radio_status', {})
        nvm_counters = st.session_state.current_data.get('nvm_counters', {})
        system_info = st.session_state.current_data.get('system_info', {})
        
        # Current metrics
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
        
        # Real-time plots
        st.markdown("## 📈 Real-Time Telemetry Graphs")
        fig = create_telemetry_plots()
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistical analysis section
        create_statistical_summary()
        
    else:
        # No data state
        st.markdown("## 🎯 Mission Status")
        st.info("🚀 Click 'Start Mission' to begin enhanced monitoring with statistical analysis")
        
        # Show empty plots
        fig = create_telemetry_plots()
        st.plotly_chart(fig, use_container_width=True)
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()