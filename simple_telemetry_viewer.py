#!/usr/bin/env python3
"""
Simple telemetry viewer for BeepSat - just prints formatted data
"""

import json
import sys
import re

def parse_telemetry_line(line):
    """Extract and format telemetry from console output"""
    # Look for telemetry patterns
    if 'TELEMETRY_OUTPUT:' in line or 'TELEM:' in line:
        # Find JSON data
        json_match = re.search(r'\{.*\}', line)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data
            except json.JSONDecodeError:
                pass
    return None

def format_telemetry(data):
    """Format telemetry data nicely"""
    if not data:
        return None
    
    # Extract key metrics
    timestamp = data.get('timestamp', 0)
    uptime = data.get('uptime', 0)
    
    power = data.get('power_status', {})
    battery_v = power.get('battery_voltage', 0)
    
    radio = data.get('radio_status', {})
    rssi = radio.get('last_rssi', 'N/A')
    
    sys_info = data.get('system_info', {})
    tasks = sys_info.get('active_tasks', 0)
    
    counters = data.get('nvm_counters', {})
    errors = counters.get('state_errors', 0)
    boots = counters.get('boot_count', 0)
    
    # Format output
    output = []
    output.append("=" * 80)
    output.append(f"🛰️  BEEPSAT TELEMETRY - Uptime: {uptime:.1f}s")
    output.append("=" * 80)
    output.append(f"🔋 Battery: {battery_v:.3f}V  📡 RSSI: {rssi} dBm  ⚙️  Tasks: {tasks}")
    output.append(f"🚨 Errors: {errors}  🔄 Boots: {boots}")
    
    # Show flags if any are active
    flags = data.get('nvm_flags', {})
    active_flags = [name for name, value in flags.items() if value]
    if active_flags:
        output.append(f"🚩 Active Flags: {', '.join(active_flags)}")
    
    output.append("")
    
    return "\n".join(output)

def main():
    """Main function - read from stdin and format telemetry"""
    print("🛰️  BeepSat Simple Telemetry Viewer")
    print("=" * 50)
    print("Reading telemetry from BeepSat output...")
    print("Pipe the output of main_emulated.py to this script")
    print("Example: python3 main_emulated.py | python3 simple_telemetry_viewer.py")
    print("=" * 50)
    print()
    
    try:
        for line in sys.stdin:
            # Parse telemetry from this line
            data = parse_telemetry_line(line)
            if data:
                formatted = format_telemetry(data)
                if formatted:
                    print(formatted)
            else:
                # Pass through non-telemetry lines (like debug output)
                line = line.strip()
                if line and not line.startswith('[RADIO_TX]') and not line.startswith('[LOG]'):
                    print(f"📝 {line}")
                    
    except KeyboardInterrupt:
        print("\n👋 Telemetry viewer stopped")
    except BrokenPipeError:
        print("\n📡 Input stream ended")

if __name__ == "__main__":
    main()