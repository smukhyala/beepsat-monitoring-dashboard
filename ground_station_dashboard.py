#!/usr/bin/env python3
"""
BeepSat Ground Station Dashboard
Real-time visualization of satellite telemetry data
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import json
import time
import threading
import queue
from collections import deque
import sys
import subprocess
import serial
import re

class TelemetryReceiver:
    """Handles receiving telemetry from various sources"""
    
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.running = False
        self.thread = None
        
    def start_console_monitoring(self):
        """Monitor console output for telemetry"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_console, daemon=True)
        self.thread.start()
        
    def start_serial_monitoring(self, port='/dev/ttyUSB0', baudrate=115200):
        """Monitor serial port for telemetry"""
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            self.running = True
            self.thread = threading.Thread(target=self._monitor_serial, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Failed to open serial port {port}: {e}")
            return False
    
    def _monitor_console(self):
        """Monitor stdout for telemetry patterns"""
        # This would be enhanced to read from a subprocess running the satellite
        while self.running:
            # Simulate receiving telemetry for demonstration
            sample_data = {
                'timestamp': time.time(),
                'uptime': time.time() % 1000,
                'power_status': {
                    'battery_voltage': 7.2 + 0.5 * (time.time() % 10) / 10,
                    'uptime_seconds': time.time() % 1000
                },
                'nvm_counters': {
                    'boot_count': 5,
                    'state_errors': int(time.time()) % 3,
                    'gs_responses': int(time.time() / 10) % 20
                },
                'radio_status': {
                    'last_rssi': -50 + 20 * (time.time() % 5) / 5,
                    'available': True
                },
                'system_info': {
                    'active_tasks': 5
                }
            }
            self.data_queue.put(sample_data)
            time.sleep(0.5)  # 2Hz simulation
            
    def _monitor_serial(self):
        """Monitor serial port for telemetry"""
        while self.running:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                if 'TELEMETRY_OUTPUT:' in line or 'TELEM:' in line:
                    # Extract JSON from telemetry line
                    json_start = line.find('{')
                    if json_start != -1:
                        json_data = line[json_start:]
                        try:
                            data = json.loads(json_data)
                            self.data_queue.put(data)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
            except Exception as e:
                print(f"Serial monitoring error: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if hasattr(self, 'serial_port'):
            self.serial_port.close()

class BeepSatDashboard:
    """Main dashboard application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BeepSat Ground Station Dashboard")
        self.root.geometry("1200x800")
        
        # Data storage
        self.data_queue = queue.Queue()
        self.telemetry_history = deque(maxlen=200)
        
        # Telemetry receiver
        self.receiver = TelemetryReceiver(self.data_queue)
        
        # Data for plots
        self.timestamps = deque(maxlen=100)
        self.battery_voltages = deque(maxlen=100)
        self.rssi_values = deque(maxlen=100)
        self.error_counts = deque(maxlen=100)
        self.uptime_values = deque(maxlen=100)
        
        self.setup_ui()
        self.setup_plots()
        
        # Start data processing
        self.process_data()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Control Panel")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Connection controls
        ttk.Button(control_frame, text="Start Console Monitor", 
                  command=self.start_console_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Start Serial Monitor", 
                  command=self.start_serial_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop Monitoring", 
                  command=self.stop_monitoring).pack(side=tk.LEFT, padx=5)
        
        # Status display
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var).pack(side=tk.RIGHT, padx=10)
        
        # Current values frame
        values_frame = ttk.LabelFrame(main_frame, text="Current Values")
        values_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create value display labels
        self.battery_label = ttk.Label(values_frame, text="Battery: -- V")
        self.battery_label.pack(side=tk.LEFT, padx=10)
        
        self.rssi_label = ttk.Label(values_frame, text="RSSI: -- dBm")
        self.rssi_label.pack(side=tk.LEFT, padx=10)
        
        self.uptime_label = ttk.Label(values_frame, text="Uptime: -- s")
        self.uptime_label.pack(side=tk.LEFT, padx=10)
        
        self.tasks_label = ttk.Label(values_frame, text="Tasks: --")
        self.tasks_label.pack(side=tk.LEFT, padx=10)
        
        # Plots container
        self.plots_frame = ttk.Frame(main_frame)
        self.plots_frame.pack(fill=tk.BOTH, expand=True)
        
    def setup_plots(self):
        """Setup matplotlib plots"""
        # Create figure with subplots
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('BeepSat Telemetry Dashboard', fontsize=16)
        
        # Battery voltage plot
        self.ax1.set_title('Battery Voltage')
        self.ax1.set_ylabel('Voltage (V)')
        self.ax1.grid(True, alpha=0.3)
        self.battery_line, = self.ax1.plot([], [], 'b-', linewidth=2)
        self.ax1.axhline(y=6.0, color='r', linestyle='--', alpha=0.7, label='Low Battery')
        self.ax1.legend()
        
        # RSSI plot
        self.ax2.set_title('Radio Signal Strength')
        self.ax2.set_ylabel('RSSI (dBm)')
        self.ax2.grid(True, alpha=0.3)
        self.rssi_line, = self.ax2.plot([], [], 'g-', linewidth=2)
        
        # System errors plot
        self.ax3.set_title('System Error Count')
        self.ax3.set_ylabel('Errors')
        self.ax3.set_xlabel('Time')
        self.ax3.grid(True, alpha=0.3)
        self.error_line, = self.ax3.plot([], [], 'r-', linewidth=2)
        
        # Uptime plot
        self.ax4.set_title('System Uptime')
        self.ax4.set_ylabel('Uptime (s)')
        self.ax4.set_xlabel('Time')
        self.ax4.grid(True, alpha=0.3)
        self.uptime_line, = self.ax4.plot([], [], 'm-', linewidth=2)
        
        # Embed plots in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.plots_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Setup animation
        self.animation = FuncAnimation(self.fig, self.update_plots, interval=500, blit=False)
        
    def start_console_monitoring(self):
        """Start console monitoring"""
        self.receiver.start_console_monitoring()
        self.status_var.set("Monitoring Console")
        
    def start_serial_monitoring(self):
        """Start serial monitoring"""
        if self.receiver.start_serial_monitoring():
            self.status_var.set("Monitoring Serial")
        else:
            self.status_var.set("Serial Failed")
            
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.receiver.stop()
        self.status_var.set("Stopped")
        
    def process_data(self):
        """Process incoming telemetry data"""
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                self.telemetry_history.append(data)
                
                # Extract values for plotting
                timestamp = data.get('timestamp', time.time())
                self.timestamps.append(timestamp)
                
                # Battery voltage
                power_status = data.get('power_status', {})
                battery_v = power_status.get('battery_voltage', 0)
                self.battery_voltages.append(battery_v)
                
                # RSSI
                radio_status = data.get('radio_status', {})
                rssi = radio_status.get('last_rssi', -100)
                if rssi is not None:
                    self.rssi_values.append(rssi)
                else:
                    self.rssi_values.append(-100)
                
                # Error count
                nvm_counters = data.get('nvm_counters', {})
                errors = nvm_counters.get('state_errors', 0)
                self.error_counts.append(errors)
                
                # Uptime
                uptime = power_status.get('uptime_seconds', 0)
                self.uptime_values.append(uptime)
                
                # Update current value labels
                self.battery_label.config(text=f"Battery: {battery_v:.2f} V")
                self.rssi_label.config(text=f"RSSI: {rssi} dBm")
                self.uptime_label.config(text=f"Uptime: {uptime:.1f} s")
                
                system_info = data.get('system_info', {})
                active_tasks = system_info.get('active_tasks', 0)
                self.tasks_label.config(text=f"Tasks: {active_tasks}")
                
        except queue.Empty:
            pass
        
        # Schedule next data processing
        self.root.after(100, self.process_data)
        
    def update_plots(self, frame):
        """Update plot data"""
        if len(self.timestamps) < 2:
            return
            
        # Convert timestamps to relative time for better visualization
        current_time = time.time()
        relative_times = [(t - current_time) for t in self.timestamps]
        
        # Update battery voltage plot
        self.battery_line.set_data(relative_times, self.battery_voltages)
        self.ax1.relim()
        self.ax1.autoscale_view()
        
        # Update RSSI plot
        self.rssi_line.set_data(relative_times, self.rssi_values)
        self.ax2.relim()
        self.ax2.autoscale_view()
        
        # Update error count plot
        self.error_line.set_data(relative_times, self.error_counts)
        self.ax3.relim()
        self.ax3.autoscale_view()
        
        # Update uptime plot
        self.uptime_line.set_data(relative_times, self.uptime_values)
        self.ax4.relim()
        self.ax4.autoscale_view()
        
        # Adjust x-axis labels to show relative time
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.set_xlabel('Time (seconds ago)')
            
    def run(self):
        """Run the dashboard"""
        try:
            self.root.mainloop()
        finally:
            self.receiver.stop()

if __name__ == "__main__":
    dashboard = BeepSatDashboard()
    dashboard.run()