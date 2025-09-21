#!/usr/bin/env python3
"""
BeepSat Visual Dashboard with tkinter
Real-time satellite monitoring with graphs and status indicators
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import json
import time
import threading
import subprocess
import sys
import os
import queue
from collections import deque
import re

class BeepSatVisualDashboard:
    """Main visual dashboard application"""
    
    def __init__(self):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("BeepSat Visual Monitoring Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')  # Dark theme
        
        # Data management
        self.data_queue = queue.Queue()
        self.telemetry_history = deque(maxlen=200)
        self.is_monitoring = False
        self.monitoring_thread = None
        self.beepsat_process = None
        
        # Data for real-time plotting
        self.max_points = 50
        self.timestamps = deque(maxlen=self.max_points)
        self.battery_voltages = deque(maxlen=self.max_points)
        self.rssi_values = deque(maxlen=self.max_points)
        self.error_counts = deque(maxlen=self.max_points)
        self.uptime_values = deque(maxlen=self.max_points)
        
        # Current values for display
        self.current_data = {}
        
        # Setup UI components
        self.setup_ui()
        self.setup_plots()
        
        # Start data processing
        self.process_telemetry_data()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container with dark theme
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure style for dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='white', background='#1e1e1e')
        style.configure('Status.TLabel', font=('Arial', 12), foreground='#00ff00', background='#1e1e1e')
        style.configure('Value.TLabel', font=('Arial', 11, 'bold'), foreground='#ffffff', background='#2e2e2e')
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="🛰️ BeepSat Real-Time Monitoring Dashboard", 
                               style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = ttk.Label(title_frame, text="● DISCONNECTED", 
                                     style='Status.TLabel', foreground='red')
        self.status_label.pack(side=tk.RIGHT)
        
        # Control Panel
        control_frame = ttk.LabelFrame(main_frame, text="Mission Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Control buttons
        self.start_button = ttk.Button(control_frame, text="🚀 Start Mission", 
                                      command=self.start_monitoring, width=15)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="🛑 Stop Mission", 
                                     command=self.stop_monitoring, width=15, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.reset_button = ttk.Button(control_frame, text="🔄 Reset Data", 
                                      command=self.reset_data, width=15)
        self.reset_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Mission time
        self.mission_time_label = ttk.Label(control_frame, text="Mission Time: 00:00:00", 
                                           style='Value.TLabel')
        self.mission_time_label.pack(side=tk.RIGHT)
        
        # Status Panel - Current Values
        status_frame = ttk.LabelFrame(main_frame, text="Current Telemetry", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create status value displays in a grid
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
        
        # Battery status
        batt_frame = ttk.Frame(status_grid)
        batt_frame.grid(row=0, column=0, padx=10, sticky='w')
        ttk.Label(batt_frame, text="🔋 Battery:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.battery_label = ttk.Label(batt_frame, text="-- V", style='Value.TLabel')
        self.battery_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Radio status
        radio_frame = ttk.Frame(status_grid)
        radio_frame.grid(row=0, column=1, padx=10, sticky='w')
        ttk.Label(radio_frame, text="📡 Signal:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.rssi_label = ttk.Label(radio_frame, text="-- dBm", style='Value.TLabel')
        self.rssi_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Task status
        task_frame = ttk.Frame(status_grid)
        task_frame.grid(row=0, column=2, padx=10, sticky='w')
        ttk.Label(task_frame, text="⚙️ Tasks:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.tasks_label = ttk.Label(task_frame, text="--", style='Value.TLabel')
        self.tasks_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Error status
        error_frame = ttk.Frame(status_grid)
        error_frame.grid(row=0, column=3, padx=10, sticky='w')
        ttk.Label(error_frame, text="🚨 Errors:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.error_label = ttk.Label(error_frame, text="--", style='Value.TLabel')
        self.error_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Uptime
        uptime_frame = ttk.Frame(status_grid)
        uptime_frame.grid(row=0, column=4, padx=10, sticky='w')
        ttk.Label(uptime_frame, text="⏰ Uptime:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.uptime_label = ttk.Label(uptime_frame, text="-- s", style='Value.TLabel')
        self.uptime_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Plots container
        plots_frame = ttk.LabelFrame(main_frame, text="Real-Time Telemetry Graphs", padding=5)
        plots_frame.pack(fill=tk.BOTH, expand=True)
        
        self.plots_container = plots_frame
        
        # System status panel
        system_frame = ttk.LabelFrame(main_frame, text="System Status", padding=10)
        system_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create scrollable text for system messages
        text_frame = ttk.Frame(system_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, height=4, width=80, bg='#2e2e2e', fg='#ffffff',
                               font=('Consolas', 9), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initial log message
        self.log_message("Dashboard initialized. Click 'Start Mission' to begin monitoring.")
    
    def setup_plots(self):
        """Setup matplotlib plots"""
        # Create figure with dark theme
        plt.style.use('dark_background')
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.patch.set_facecolor('#1e1e1e')
        self.fig.suptitle('BeepSat Telemetry Data', fontsize=14, color='white', y=0.95)
        
        # Battery voltage plot
        self.ax1.set_title('Battery Voltage', color='white', fontsize=10)
        self.ax1.set_ylabel('Voltage (V)', color='white')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.set_facecolor('#2e2e2e')
        self.battery_line, = self.ax1.plot([], [], 'cyan', linewidth=2, marker='o', markersize=3)
        self.ax1.axhline(y=6.0, color='red', linestyle='--', alpha=0.7, label='Low Battery')
        self.ax1.legend(fontsize=8)
        self.ax1.tick_params(colors='white')
        
        # RSSI plot
        self.ax2.set_title('Radio Signal Strength', color='white', fontsize=10)
        self.ax2.set_ylabel('RSSI (dBm)', color='white')
        self.ax2.grid(True, alpha=0.3)
        self.ax2.set_facecolor('#2e2e2e')
        self.rssi_line, = self.ax2.plot([], [], 'lime', linewidth=2, marker='s', markersize=3)
        self.ax2.tick_params(colors='white')
        
        # System errors plot
        self.ax3.set_title('System Error Count', color='white', fontsize=10)
        self.ax3.set_ylabel('Errors', color='white')
        self.ax3.set_xlabel('Time (relative)', color='white')
        self.ax3.grid(True, alpha=0.3)
        self.ax3.set_facecolor('#2e2e2e')
        self.error_line, = self.ax3.plot([], [], 'orange', linewidth=2, marker='^', markersize=3)
        self.ax3.tick_params(colors='white')
        
        # Uptime plot
        self.ax4.set_title('System Uptime', color='white', fontsize=10)
        self.ax4.set_ylabel('Uptime (s)', color='white')
        self.ax4.set_xlabel('Time (relative)', color='white')
        self.ax4.grid(True, alpha=0.3)
        self.ax4.set_facecolor('#2e2e2e')
        self.uptime_line, = self.ax4.plot([], [], 'magenta', linewidth=2, marker='d', markersize=3)
        self.ax4.tick_params(colors='white')
        
        # Adjust layout
        plt.tight_layout()
        
        # Embed plots in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.plots_container)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Setup animation
        self.animation = FuncAnimation(self.fig, self.update_plots, interval=1000, blit=False)
    
    def log_message(self, message):
        """Add message to log display"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        # Limit log length
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 100:
            self.log_text.delete("1.0", "10.0")
    
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
        """Monitor BeepSat emulation output"""
        basic_dir = "software_example_beepsat/basic"
        
        if not os.path.exists(basic_dir):
            self.log_message(f"❌ Error: {basic_dir} not found")
            return
        
        try:
            # Start the emulated BeepSat
            self.beepsat_process = subprocess.Popen(
                [sys.executable, "main_emulated.py"],
                cwd=basic_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.log_message("🚀 BeepSat emulation started")
            
            # Monitor output
            while self.is_monitoring and self.beepsat_process.poll() is None:
                try:
                    line = self.beepsat_process.stdout.readline()
                    if line:
                        # Try to parse telemetry
                        data = self.parse_telemetry_line(line)
                        if data:
                            self.data_queue.put(data)
                        # Also log interesting non-telemetry messages
                        elif any(keyword in line for keyword in ['[', 'ERROR', 'WARNING', 'initialized']):
                            # Clean up ANSI codes for display
                            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
                            if clean_line and not clean_line.startswith('[RADIO_TX]') and not clean_line.startswith('[LOG]'):
                                self.log_message(f"📡 {clean_line}")
                except Exception as e:
                    self.log_message(f"❌ Monitoring error: {e}")
                    break
            
            # Clean up
            if self.beepsat_process and self.beepsat_process.poll() is None:
                self.beepsat_process.terminate()
                self.beepsat_process.wait(timeout=5)
                
            self.log_message("🛑 BeepSat monitoring stopped")
            
        except Exception as e:
            self.log_message(f"❌ Failed to start BeepSat: {e}")
    
    def start_monitoring(self):
        """Start monitoring BeepSat"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_label.config(text="● CONNECTED", foreground='lime')
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_beepsat, daemon=True)
        self.monitoring_thread.start()
        
        self.log_message("🎯 Mission started - monitoring telemetry")
    
    def stop_monitoring(self):
        """Stop monitoring BeepSat"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="● DISCONNECTED", foreground='red')
        
        # Stop BeepSat process
        if self.beepsat_process and self.beepsat_process.poll() is None:
            self.beepsat_process.terminate()
        
        self.log_message("🔴 Mission stopped")
    
    def reset_data(self):
        """Reset all data displays"""
        # Clear data structures
        self.timestamps.clear()
        self.battery_voltages.clear()
        self.rssi_values.clear()
        self.error_counts.clear()
        self.uptime_values.clear()
        self.telemetry_history.clear()
        
        # Clear data queue
        while not self.data_queue.empty():
            self.data_queue.get()
        
        # Reset current data
        self.current_data = {}
        
        # Reset display labels
        self.battery_label.config(text="-- V")
        self.rssi_label.config(text="-- dBm")
        self.tasks_label.config(text="--")
        self.error_label.config(text="--")
        self.uptime_label.config(text="-- s")
        self.mission_time_label.config(text="Mission Time: 00:00:00")
        
        self.log_message("🔄 Data reset complete")
    
    def process_telemetry_data(self):
        """Process incoming telemetry data"""
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                self.current_data = data
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
                self.rssi_values.append(rssi if rssi is not None else -100)
                
                # Error count
                nvm_counters = data.get('nvm_counters', {})
                errors = nvm_counters.get('state_errors', 0)
                self.error_counts.append(errors)
                
                # Uptime
                uptime = power_status.get('uptime_seconds', 0)
                self.uptime_values.append(uptime)
                
                # Update display labels
                self.battery_label.config(text=f"{battery_v:.2f} V")
                self.rssi_label.config(text=f"{rssi} dBm")
                
                system_info = data.get('system_info', {})
                active_tasks = system_info.get('active_tasks', 0)
                self.tasks_label.config(text=f"{active_tasks}")
                self.error_label.config(text=f"{errors}")
                self.uptime_label.config(text=f"{uptime:.1f} s")
                
                # Update mission time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                self.mission_time_label.config(text=f"Mission Time: {hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Set battery color based on voltage
                if battery_v < 6.0:
                    self.battery_label.config(foreground='red')
                elif battery_v < 6.5:
                    self.battery_label.config(foreground='orange')
                else:
                    self.battery_label.config(foreground='lime')
                
        except queue.Empty:
            pass
        
        # Schedule next processing
        self.root.after(100, self.process_telemetry_data)
    
    def update_plots(self, frame):
        """Update plot data"""
        if len(self.timestamps) < 2:
            return
        
        # Convert to relative time for better visualization
        current_time = time.time()
        relative_times = [(t - current_time) for t in self.timestamps]
        
        # Update battery voltage plot
        self.battery_line.set_data(relative_times, self.battery_voltages)
        self.ax1.relim()
        self.ax1.autoscale_view()
        self.ax1.set_xlabel('Time (seconds ago)', color='white')
        
        # Update RSSI plot
        self.rssi_line.set_data(relative_times, self.rssi_values)
        self.ax2.relim()
        self.ax2.autoscale_view()
        self.ax2.set_xlabel('Time (seconds ago)', color='white')
        
        # Update error count plot
        self.error_line.set_data(relative_times, self.error_counts)
        self.ax3.relim()
        self.ax3.autoscale_view()
        
        # Update uptime plot
        self.uptime_line.set_data(relative_times, self.uptime_values)
        self.ax4.relim()
        self.ax4.autoscale_view()
        
        return [self.battery_line, self.rssi_line, self.error_line, self.uptime_line]
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_monitoring:
            if messagebox.askokcancel("Quit", "Stop mission and quit dashboard?"):
                self.stop_monitoring()
                time.sleep(1)  # Give time to clean up
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the dashboard"""
        try:
            self.root.mainloop()
        finally:
            if self.is_monitoring:
                self.stop_monitoring()

def main():
    """Main function"""
    print("🛰️ Starting BeepSat Visual Dashboard...")
    
    # Check if we're in the right directory
    if not os.path.exists("software_example_beepsat/basic"):
        print("❌ Error: Run this script from the project root directory")
        print("   Expected structure: software_example_beepsat/basic/")
        return 1
    
    dashboard = BeepSatVisualDashboard()
    dashboard.run()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())