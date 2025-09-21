#!/usr/bin/env python3
"""
Simple command-line telemetry monitor for BeepSat
No GUI dependencies - works in terminal
"""

import json
import time
import threading
import subprocess
import sys
import os
from collections import deque

class SimpleTelemetryMonitor:
    """Command-line telemetry monitor"""
    
    def __init__(self):
        self.running = False
        self.data_history = deque(maxlen=50)
        self.latest_data = {}
        
    def parse_telemetry_line(self, line):
        """Extract JSON from telemetry output"""
        if 'TELEMETRY_OUTPUT:' in line:
            json_start = line.find('{')
            if json_start != -1:
                try:
                    data = json.loads(line[json_start:])
                    return data
                except json.JSONDecodeError:
                    pass
        elif 'TELEM:' in line:
            json_start = line.find('{')
            if json_start != -1:
                try:
                    data = json.loads(line[json_start:])
                    return data
                except json.JSONDecodeError:
                    pass
        return None
    
    def format_data_summary(self, data):
        """Format telemetry data for display"""
        if not data:
            return "No data"
            
        summary = []
        summary.append(f"⏰ Uptime: {data.get('uptime', 0):.1f}s")
        
        # Power status
        power = data.get('power_status', {})
        battery_v = power.get('battery_voltage', 0)
        summary.append(f"🔋 Battery: {battery_v:.2f}V")
        
        # Radio status
        radio = data.get('radio_status', {})
        rssi = radio.get('last_rssi', 'N/A')
        summary.append(f"📡 RSSI: {rssi} dBm")
        
        # System info
        sys_info = data.get('system_info', {})
        tasks = sys_info.get('active_tasks', 0)
        summary.append(f"⚙️  Tasks: {tasks}")
        
        # Counters
        counters = data.get('nvm_counters', {})
        errors = counters.get('state_errors', 0)
        boots = counters.get('boot_count', 0)
        summary.append(f"🚨 Errors: {errors}")
        summary.append(f"🔄 Boots: {boots}")
        
        return " | ".join(summary)
    
    def display_status(self):
        """Display current status"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("🛰️  BEEPSAT TELEMETRY MONITOR")
        print("=" * 80)
        print()
        
        if self.latest_data:
            print("📊 CURRENT STATUS:")
            print("-" * 40)
            print(self.format_data_summary(self.latest_data))
            print()
            
            # Show detailed power info
            power = self.latest_data.get('power_status', {})
            print("🔋 POWER DETAILS:")
            print(f"   Voltage: {power.get('battery_voltage', 0):.3f}V")
            print(f"   Threshold: {power.get('low_battery_threshold', 0):.1f}V")
            print(f"   Uptime: {power.get('uptime_seconds', 0):.1f}s")
            print()
            
            # Show flags
            flags = self.latest_data.get('nvm_flags', {})
            print("🚩 SYSTEM FLAGS:")
            active_flags = [name for name, value in flags.items() if value]
            if active_flags:
                print(f"   Active: {', '.join(active_flags)}")
            else:
                print("   All flags normal")
            print()
            
            # Show task states
            tasks = self.latest_data.get('task_states', {})
            print("⚙️  TASK STATUS:")
            for task_name, task_info in tasks.items():
                status = "✅ Running" if task_info.get('running', False) else "❌ Stopped"
                print(f"   {task_name:12} {status}")
            print()
            
        else:
            print("⏳ Waiting for telemetry data...")
            print("   Make sure BeepSat emulation is running!")
            print()
        
        # Show recent history
        if len(self.data_history) > 1:
            print("📈 BATTERY VOLTAGE TREND (last 10):")
            recent_voltages = []
            for data in list(self.data_history)[-10:]:
                power = data.get('power_status', {})
                voltage = power.get('battery_voltage', 0)
                recent_voltages.append(f"{voltage:.2f}V")
            print("   " + " → ".join(recent_voltages))
            print()
        
        print("📝 CONTROLS:")
        print("   Press Ctrl+C to exit")
        print("   Data updates automatically every 2 seconds")
        print()
        print(f"📊 Data points collected: {len(self.data_history)}")
        print(f"🕐 Last update: {time.strftime('%H:%M:%S')}")
    
    def monitor_emulation_output(self):
        """Monitor emulated BeepSat output"""
        basic_dir = "software_example_beepsat/basic"
        
        if not os.path.exists(basic_dir):
            print(f"Error: {basic_dir} not found. Run from project root directory.")
            return
        
        try:
            # Start the emulated BeepSat
            process = subprocess.Popen(
                [sys.executable, "main_emulated.py"],
                cwd=basic_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            print("🚀 Started BeepSat emulation...")
            time.sleep(2)  # Let it initialize
            
            # Monitor output
            while self.running:
                line = process.stdout.readline()
                if line:
                    # Try to parse telemetry
                    data = self.parse_telemetry_line(line)
                    if data:
                        self.latest_data = data
                        self.data_history.append(data)
                elif process.poll() is not None:
                    print("❌ BeepSat emulation stopped")
                    break
                    
            # Clean up
            process.terminate()
            process.wait(timeout=5)
            
        except Exception as e:
            print(f"❌ Error monitoring emulation: {e}")
    
    def run(self):
        """Run the monitor"""
        self.running = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_emulation_output, daemon=True)
        monitor_thread.start()
        
        try:
            while self.running:
                self.display_status()
                time.sleep(2)  # Update every 2 seconds
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down monitor...")
            self.running = False
            time.sleep(1)

def main():
    """Main function"""
    print("🛰️  BeepSat Telemetry Monitor")
    print("=" * 40)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists("software_example_beepsat/basic"):
        print("❌ Error: Run this script from the project root directory")
        print("   Expected structure: software_example_beepsat/basic/")
        return 1
    
    print("📡 Starting telemetry monitor...")
    print("   This will automatically start BeepSat emulation")
    print("   Press Ctrl+C to stop")
    print()
    input("Press Enter to continue...")
    
    monitor = SimpleTelemetryMonitor()
    monitor.run()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())