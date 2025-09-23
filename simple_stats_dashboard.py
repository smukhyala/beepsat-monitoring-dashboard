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

class SignalProcessor:
    """Signal processing utilities for peak detection and fitting"""
    
    @staticmethod
    def find_peaks(values, min_height=None, min_distance=1):
        """
        Find peaks (local maxima) in signal data
        
        Args:
            values: List of signal values
            min_height: Minimum height for peak detection
            min_distance: Minimum distance between peaks (in indices)
        
        Returns:
            dict with peak indices, heights, and properties
        """
        if len(values) < 3:
            return {'peaks': [], 'peak_heights': [], 'peak_properties': []}
        
        peaks = []
        peak_heights = []
        peak_properties = []
        
        # Convert to list if needed
        vals = list(values)
        n = len(vals)
        
        # Find local maxima
        for i in range(1, n - 1):
            # Check if current point is higher than neighbors
            if vals[i] > vals[i-1] and vals[i] > vals[i+1]:
                # Apply minimum height filter
                if min_height is None or vals[i] >= min_height:
                    # Apply minimum distance filter
                    if not peaks or (i - peaks[-1]) >= min_distance:
                        peaks.append(i)
                        peak_heights.append(vals[i])
                        
                        # Calculate peak properties
                        prominence = SignalProcessor._calculate_prominence(vals, i)
                        width = SignalProcessor._calculate_width(vals, i)
                        
                        peak_properties.append({
                            'prominence': prominence,
                            'width': width,
                            'left_base': max(0, i - width//2),
                            'right_base': min(n-1, i + width//2)
                        })
        
        return {
            'peaks': peaks,
            'peak_heights': peak_heights,
            'peak_properties': peak_properties,
            'total_peaks': len(peaks)
        }
    
    @staticmethod
    def find_valleys(values, max_height=None, min_distance=1):
        """
        Find valleys (local minima) in signal data
        """
        if len(values) < 3:
            return {'valleys': [], 'valley_depths': [], 'total_valleys': 0}
        
        # Invert signal and find peaks to get valleys
        inverted = [-v for v in values]
        if max_height is not None:
            min_height_inverted = -max_height
        else:
            min_height_inverted = None
        
        valley_result = SignalProcessor.find_peaks(inverted, min_height_inverted, min_distance)
        
        return {
            'valleys': valley_result['peaks'],
            'valley_depths': [-h for h in valley_result['peak_heights']],
            'total_valleys': valley_result['total_peaks']
        }
    
    @staticmethod
    def _calculate_prominence(values, peak_idx):
        """Calculate peak prominence (height above surrounding minima)"""
        n = len(values)
        peak_height = values[peak_idx]
        
        # Find minimum to the left
        left_min = peak_height
        for i in range(peak_idx - 1, -1, -1):
            if values[i] < left_min:
                left_min = values[i]
        
        # Find minimum to the right
        right_min = peak_height
        for i in range(peak_idx + 1, n):
            if values[i] < right_min:
                right_min = values[i]
        
        # Prominence is height above the higher of the two minima
        reference_min = max(left_min, right_min)
        return peak_height - reference_min
    
    @staticmethod
    def _calculate_width(values, peak_idx, rel_height=0.5):
        """Calculate peak width at relative height"""
        n = len(values)
        peak_height = values[peak_idx]
        
        # Find the base level
        left_min = peak_height
        right_min = peak_height
        
        for i in range(peak_idx - 1, -1, -1):
            if values[i] < left_min:
                left_min = values[i]
        
        for i in range(peak_idx + 1, n):
            if values[i] < right_min:
                right_min = values[i]
        
        base_level = max(left_min, right_min)
        height_threshold = base_level + rel_height * (peak_height - base_level)
        
        # Find width at this height
        left_width = 0
        for i in range(peak_idx - 1, -1, -1):
            if values[i] <= height_threshold:
                break
            left_width += 1
        
        right_width = 0
        for i in range(peak_idx + 1, n):
            if values[i] <= height_threshold:
                break
            right_width += 1
        
        return left_width + right_width + 1
    
    @staticmethod
    def fit_gaussian_peak(x_data, y_data, peak_idx):
        """
        Fit a Gaussian curve to a peak using least-squares minimization
        
        Args:
            x_data: X coordinates (indices or time)
            y_data: Y coordinates (signal values)
            peak_idx: Index of the peak center
        
        Returns:
            dict with fitted parameters and quality metrics
        """
        try:
            # Extract local region around peak
            n = len(y_data)
            window_size = min(10, n // 4)  # Adaptive window size
            start_idx = max(0, peak_idx - window_size)
            end_idx = min(n, peak_idx + window_size + 1)
            
            local_x = x_data[start_idx:end_idx]
            local_y = y_data[start_idx:end_idx]
            
            if len(local_y) < 3:
                return None
            
            # Initial parameter estimates
            peak_height = y_data[peak_idx]
            peak_center = x_data[peak_idx]
            
            # Estimate baseline from edges
            baseline = (local_y[0] + local_y[-1]) / 2
            amplitude = peak_height - baseline
            
            # Estimate width from data spread
            sigma_estimate = len(local_y) / 6  # Rough estimate
            
            # Simple least-squares fitting using normal equations
            # For Gaussian: y = A * exp(-0.5 * ((x - mu) / sigma)^2) + baseline
            # We'll use a simplified linear approximation in log space
            
            # Remove baseline
            y_shifted = [max(y - baseline, 0.001) for y in local_y]  # Avoid log(0)
            
            # Linear least squares for log-transformed Gaussian
            # log(y) ≈ log(A) - 0.5 * ((x - mu) / sigma)^2
            log_y = [math.log(y) for y in y_shifted]
            
            # Use the peak as center and fit width
            x_centered = [(x - peak_center) for x in local_x]
            x_squared = [x * x for x in x_centered]
            
            # Linear regression: log(y) = a + b * x^2
            n_points = len(log_y)
            sum_x2 = sum(x_squared)
            sum_x4 = sum(x * x for x in x_squared)
            sum_y = sum(log_y)
            sum_x2y = sum(x_squared[i] * log_y[i] for i in range(n_points))
            
            # Solve normal equations
            if n_points * sum_x4 - sum_x2 * sum_x2 != 0:
                b = (n_points * sum_x2y - sum_x2 * sum_y) / (n_points * sum_x4 - sum_x2 * sum_x2)
                a = (sum_y - b * sum_x2) / n_points
                
                # Convert back to Gaussian parameters
                fitted_amplitude = math.exp(a)
                fitted_sigma = math.sqrt(-0.5 / b) if b < 0 else sigma_estimate
                fitted_center = peak_center
                fitted_baseline = baseline
                
                # Calculate R-squared
                y_pred = [fitted_amplitude * math.exp(-0.5 * ((x - fitted_center) / fitted_sigma) ** 2) + fitted_baseline 
                         for x in local_x]
                
                ss_res = sum((local_y[i] - y_pred[i]) ** 2 for i in range(len(local_y)))
                y_mean = sum(local_y) / len(local_y)
                ss_tot = sum((y - y_mean) ** 2 for y in local_y)
                
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                return {
                    'amplitude': fitted_amplitude,
                    'center': fitted_center,
                    'sigma': fitted_sigma,
                    'baseline': fitted_baseline,
                    'r_squared': max(0, min(1, r_squared)),
                    'peak_area': fitted_amplitude * fitted_sigma * math.sqrt(2 * math.pi),
                    'fwhm': 2.355 * fitted_sigma,  # Full Width at Half Maximum
                    'quality': 'good' if r_squared > 0.8 else 'fair' if r_squared > 0.5 else 'poor'
                }
            
        except (ValueError, ZeroDivisionError, OverflowError):
            pass
        
        # Fallback simple characterization
        return {
            'amplitude': peak_height - baseline if 'baseline' in locals() else peak_height,
            'center': peak_center if 'peak_center' in locals() else peak_idx,
            'sigma': sigma_estimate if 'sigma_estimate' in locals() else 1.0,
            'baseline': baseline if 'baseline' in locals() else 0,
            'r_squared': 0.0,
            'peak_area': 0.0,
            'fwhm': 0.0,
            'quality': 'poor'
        }
    
    @staticmethod
    def analyze_signal_peaks(values, signal_name="Signal"):
        """
        Comprehensive peak analysis of a signal
        
        Args:
            values: Signal data
            signal_name: Name of the signal for reporting
        
        Returns:
            dict with complete peak analysis
        """
        if len(values) < 5:
            return {
                'signal_name': signal_name,
                'total_peaks': 0,
                'total_valleys': 0,
                'peak_analysis': {},
                'summary': f"Insufficient data for {signal_name} peak analysis"
            }
        
        # Create index array for fitting
        indices = list(range(len(values)))
        
        # Adaptive thresholds based on signal statistics
        mean_val = sum(values) / len(values)
        max_val = max(values)
        min_val = min(values)
        signal_range = max_val - min_val
        
        # Set thresholds as percentages of signal range
        peak_threshold = mean_val + 0.1 * signal_range
        valley_threshold = mean_val - 0.1 * signal_range
        min_distance = max(2, len(values) // 20)  # Adaptive minimum distance
        
        # Find peaks and valleys
        peaks_result = SignalProcessor.find_peaks(values, peak_threshold, min_distance)
        valleys_result = SignalProcessor.find_valleys(values, valley_threshold, min_distance)
        
        # Fit Gaussian to significant peaks
        fitted_peaks = []
        if peaks_result['peaks']:
            for i, peak_idx in enumerate(peaks_result['peaks']):
                if peaks_result['peak_properties'][i]['prominence'] > 0.05 * signal_range:
                    fit_result = SignalProcessor.fit_gaussian_peak(indices, values, peak_idx)
                    if fit_result:
                        fitted_peaks.append({
                            'index': peak_idx,
                            'height': peaks_result['peak_heights'][i],
                            'prominence': peaks_result['peak_properties'][i]['prominence'],
                            'width': peaks_result['peak_properties'][i]['width'],
                            'fit': fit_result
                        })
        
        # Generate summary
        summary_parts = []
        if peaks_result['total_peaks'] > 0:
            avg_peak_height = sum(peaks_result['peak_heights']) / len(peaks_result['peak_heights'])
            summary_parts.append(f"{peaks_result['total_peaks']} peaks detected (avg height: {avg_peak_height:.2f})")
        
        if valleys_result['total_valleys'] > 0:
            avg_valley_depth = sum(valleys_result['valley_depths']) / len(valleys_result['valley_depths'])
            summary_parts.append(f"{valleys_result['total_valleys']} valleys detected (avg depth: {avg_valley_depth:.2f})")
        
        if fitted_peaks:
            good_fits = sum(1 for p in fitted_peaks if p['fit']['r_squared'] > 0.7)
            summary_parts.append(f"{len(fitted_peaks)} peaks fitted ({good_fits} good fits)")
        
        summary = "; ".join(summary_parts) if summary_parts else f"No significant peaks detected in {signal_name}"
        
        return {
            'signal_name': signal_name,
            'total_peaks': peaks_result['total_peaks'],
            'total_valleys': valleys_result['total_valleys'],
            'peak_indices': peaks_result['peaks'],
            'peak_heights': peaks_result['peak_heights'],
            'valley_indices': valleys_result['valleys'],
            'valley_depths': valleys_result['valley_depths'],
            'fitted_peaks': fitted_peaks,
            'peak_analysis': {
                'max_peak_height': max(peaks_result['peak_heights']) if peaks_result['peak_heights'] else 0,
                'avg_peak_prominence': sum(p['prominence'] for p in fitted_peaks) / len(fitted_peaks) if fitted_peaks else 0,
                'avg_peak_width': sum(p['width'] for p in fitted_peaks) / len(fitted_peaks) if fitted_peaks else 0,
                'signal_range': signal_range,
                'peak_density': len(peaks_result['peaks']) / len(values) * 100  # peaks per 100 data points
            },
            'summary': summary
        }

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
        st.write("🔍 **Signal Processing:** Peak detection, Peak fitting, Signal analysis")
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
    
    # Signal Processing Analysis Section
    st.markdown("---")
    st.markdown("## 🔍 SIGNAL PROCESSING ANALYSIS")
    
    # Perform peak analysis on battery and RSSI signals
    if len(battery_voltages) >= 5:
        battery_peak_analysis = SignalProcessor.analyze_signal_peaks(battery_voltages, "Battery Voltage")
        rssi_peak_analysis = SignalProcessor.analyze_signal_peaks(rssi_values, "RSSI Signal")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔋 Battery Voltage Peak Analysis")
            display_peak_analysis(battery_peak_analysis, "V")
        
        with col2:
            st.markdown("### 📡 RSSI Signal Peak Analysis")
            display_peak_analysis(rssi_peak_analysis, "dBm")
        
        # Combined signal analysis summary
        st.markdown("### 📊 Signal Analysis Summary")
        display_signal_summary(battery_peak_analysis, rssi_peak_analysis)
    else:
        st.info("🔍 Signal processing analysis requires at least 5 data points. Currently have: {}".format(len(battery_voltages)))

def display_peak_analysis(peak_analysis, unit):
    """Display peak analysis results for a signal"""
    # Basic peak metrics
    st.metric("Total Peaks", f"{peak_analysis['total_peaks']}")
    st.metric("Total Valleys", f"{peak_analysis['total_valleys']}")
    
    if peak_analysis['total_peaks'] > 0:
        st.metric("Peak Density", f"{peak_analysis['peak_analysis']['peak_density']:.1f}%")
        st.metric("Max Peak Height", f"{peak_analysis['peak_analysis']['max_peak_height']:.2f} {unit}")
        
        if peak_analysis['fitted_peaks']:
            # Show fitted peak information
            st.write("**Fitted Peaks:**")
            good_fits = [p for p in peak_analysis['fitted_peaks'] if p['fit']['r_squared'] > 0.7]
            fair_fits = [p for p in peak_analysis['fitted_peaks'] if 0.5 <= p['fit']['r_squared'] <= 0.7]
            poor_fits = [p for p in peak_analysis['fitted_peaks'] if p['fit']['r_squared'] < 0.5]
            
            st.write(f"• 🟢 Good fits: {len(good_fits)}")
            st.write(f"• 🟡 Fair fits: {len(fair_fits)}")
            st.write(f"• 🔴 Poor fits: {len(poor_fits)}")
            
            # Show best fit details if available
            if good_fits:
                best_fit = max(good_fits, key=lambda x: x['fit']['r_squared'])
                st.write(f"**Best Fit (R² = {best_fit['fit']['r_squared']:.3f}):**")
                st.write(f"• Amplitude: {best_fit['fit']['amplitude']:.3f} {unit}")
                st.write(f"• Width (FWHM): {best_fit['fit']['fwhm']:.1f} data points")
                st.write(f"• Peak Area: {best_fit['fit']['peak_area']:.2f}")
        
        # Display summary
        st.write("**Analysis Summary:**")
        st.info(peak_analysis['summary'])
    else:
        st.info("No significant peaks detected in this signal.")

def display_signal_summary(battery_analysis, rssi_analysis):
    """Display combined signal analysis summary"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_battery_peaks = battery_analysis['total_peaks']
        total_rssi_peaks = rssi_analysis['total_peaks']
        st.metric("Total Signal Features", f"{total_battery_peaks + total_rssi_peaks}")
        
    with col2:
        battery_fitted = len(battery_analysis['fitted_peaks'])
        rssi_fitted = len(rssi_analysis['fitted_peaks'])
        st.metric("Successfully Fitted", f"{battery_fitted + rssi_fitted}")
    
    with col3:
        # Calculate overall signal complexity
        battery_density = battery_analysis['peak_analysis']['peak_density']
        rssi_density = rssi_analysis['peak_analysis']['peak_density']
        avg_complexity = (battery_density + rssi_density) / 2
        
        if avg_complexity > 15:
            complexity = "🔴 High"
        elif avg_complexity > 8:
            complexity = "🟡 Moderate" 
        else:
            complexity = "🟢 Low"
        st.metric("Signal Complexity", complexity)
    
    # Signal analysis insights
    st.markdown("**🧠 Signal Processing Insights:**")
    
    insights = []
    
    # Battery signal insights
    if battery_analysis['total_peaks'] > 3:
        insights.append("🔋 Battery voltage shows significant fluctuations with multiple peaks detected")
    elif battery_analysis['total_peaks'] > 0:
        insights.append("🔋 Battery voltage shows some variability with minor peaks")
    else:
        insights.append("🔋 Battery voltage appears stable with no significant peaks")
    
    # RSSI signal insights
    if rssi_analysis['total_peaks'] > 5:
        insights.append("📡 RSSI signal shows high variability, possibly due to orbital mechanics or interference")
    elif rssi_analysis['total_peaks'] > 2:
        insights.append("📡 RSSI signal shows moderate fluctuations, typical for satellite communications")
    else:
        insights.append("📡 RSSI signal appears relatively stable")
    
    # Peak fitting insights
    total_fitted = len(battery_analysis['fitted_peaks']) + len(rssi_analysis['fitted_peaks'])
    if total_fitted > 0:
        good_fits = sum(1 for p in battery_analysis['fitted_peaks'] + rssi_analysis['fitted_peaks'] 
                       if p['fit']['r_squared'] > 0.7)
        if good_fits / total_fitted > 0.7:
            insights.append("🔍 Peak fitting shows excellent signal characterization quality")
        elif good_fits / total_fitted > 0.4:
            insights.append("🔍 Peak fitting shows good signal characterization with some uncertainty")
        else:
            insights.append("🔍 Peak fitting indicates complex signal patterns requiring further analysis")
    
    # Signal correlation insights
    if battery_analysis['total_peaks'] > 0 and rssi_analysis['total_peaks'] > 0:
        insights.append("🔗 Both signals show peak activity - consider correlation analysis")
    
    for insight in insights:
        st.write(f"• {insight}")
    
    # Peak fitting quality visualization
    if total_fitted > 0:
        with st.expander("📈 Peak Fitting Quality Details", expanded=False):
            st.markdown("**Battery Voltage Peak Fits:**")
            for i, peak in enumerate(battery_analysis['fitted_peaks']):
                quality_color = "🟢" if peak['fit']['r_squared'] > 0.8 else "🟡" if peak['fit']['r_squared'] > 0.5 else "🔴"
                st.write(f"{quality_color} Peak {i+1}: R² = {peak['fit']['r_squared']:.3f}, "
                        f"Height = {peak['height']:.3f} V, Width = {peak['fit']['fwhm']:.1f}")
            
            st.markdown("**RSSI Signal Peak Fits:**")
            for i, peak in enumerate(rssi_analysis['fitted_peaks']):
                quality_color = "🟢" if peak['fit']['r_squared'] > 0.8 else "🟡" if peak['fit']['r_squared'] > 0.5 else "🔴"
                st.write(f"{quality_color} Peak {i+1}: R² = {peak['fit']['r_squared']:.3f}, "
                        f"Height = {peak['height']:.1f} dBm, Width = {peak['fit']['fwhm']:.1f}")

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
        # Battery plot with peak annotations
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=timestamps, y=battery_voltages, mode='lines+markers',
                                name='Battery', line=dict(color='cyan', width=3)))
        
        # Add peak annotations if enough data
        if len(battery_voltages) >= 5:
            battery_peak_analysis = SignalProcessor.analyze_signal_peaks(battery_voltages, "Battery")
            if battery_peak_analysis['peak_indices']:
                peak_timestamps = [timestamps[i] for i in battery_peak_analysis['peak_indices']]
                peak_values = [battery_voltages[i] for i in battery_peak_analysis['peak_indices']]
                fig1.add_trace(go.Scatter(x=peak_timestamps, y=peak_values, mode='markers',
                                        name='Peaks', marker=dict(color='red', size=8, symbol='triangle-up')))
        
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
        # RSSI plot with peak annotations
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=timestamps, y=rssi_values, mode='lines+markers',
                                name='RSSI', line=dict(color='lime', width=3)))
        
        # Add peak annotations if enough data
        if len(rssi_values) >= 5:
            rssi_peak_analysis = SignalProcessor.analyze_signal_peaks(rssi_values, "RSSI")
            if rssi_peak_analysis['peak_indices']:
                peak_timestamps = [timestamps[i] for i in rssi_peak_analysis['peak_indices']]
                peak_values = [rssi_values[i] for i in rssi_peak_analysis['peak_indices']]
                fig2.add_trace(go.Scatter(x=peak_timestamps, y=peak_values, mode='markers',
                                        name='Peaks', marker=dict(color='red', size=8, symbol='triangle-up')))
            if rssi_peak_analysis['valley_indices']:
                valley_timestamps = [timestamps[i] for i in rssi_peak_analysis['valley_indices']]
                valley_values = [rssi_values[i] for i in rssi_peak_analysis['valley_indices']]
                fig2.add_trace(go.Scatter(x=valley_timestamps, y=valley_values, mode='markers',
                                        name='Valleys', marker=dict(color='orange', size=8, symbol='triangle-down')))
        
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