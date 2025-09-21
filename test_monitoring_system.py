#!/usr/bin/env python3
"""
Test script for the BeepSat monitoring system
Demonstrates both emulation and dashboard capabilities
"""

import subprocess
import time
import sys
import os
import threading

def test_emulation():
    """Test the emulated BeepSat system"""
    print("=" * 60)
    print("TESTING BEEPSAT EMULATION")
    print("=" * 60)
    
    # Change to the basic directory
    basic_dir = "software_example_beepsat/basic"
    if not os.path.exists(basic_dir):
        print(f"Error: Directory {basic_dir} not found")
        return False
    
    print(f"Starting emulated BeepSat from {basic_dir}")
    print("This will run for 30 seconds to generate telemetry data...")
    
    # Run the emulated system
    try:
        process = subprocess.Popen(
            [sys.executable, "main_emulated.py"],
            cwd=basic_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            output = process.stdout.readline()
            if output:
                print(f"[EMULATION] {output.strip()}")
            elif process.poll() is not None:
                break
            time.sleep(0.1)
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=5)
        
        print("\nEmulation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Emulation test failed: {e}")
        return False

def test_dashboard():
    """Test the ground station dashboard"""
    print("\n" + "=" * 60)
    print("TESTING GROUND STATION DASHBOARD")
    print("=" * 60)
    
    print("The dashboard should be started manually with:")
    print("  python3 ground_station_dashboard.py")
    print("\nClick 'Start Console Monitor' to see simulated telemetry")
    print("The dashboard will show:")
    print("  - Battery voltage over time")
    print("  - Radio signal strength (RSSI)")
    print("  - System error counts")
    print("  - Uptime tracking")
    
    response = input("\nWould you like to start the dashboard now? (y/n): ")
    if response.lower().startswith('y'):
        try:
            subprocess.run([sys.executable, "ground_station_dashboard.py"])
            return True
        except KeyboardInterrupt:
            print("\nDashboard closed by user")
            return True
        except Exception as e:
            print(f"Dashboard test failed: {e}")
            return False
    else:
        print("Dashboard test skipped")
        return True

def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    required_modules = [
        'matplotlib',
        'tkinter',
        'json',
        'threading',
        'queue'
    ]
    
    missing = []
    for module in required_modules:
        try:
            if module == 'tkinter':
                import tkinter
            else:
                __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} (missing)")
            missing.append(module)
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install matplotlib")
        return False
    
    print("All dependencies available!")
    return True

def run_integration_test():
    """Run both emulation and dashboard together"""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST")
    print("=" * 60)
    
    print("This test will:")
    print("1. Start the emulated BeepSat in the background")
    print("2. Start the dashboard to visualize the data")
    print("3. Run for 60 seconds with live telemetry")
    
    response = input("\nProceed with integration test? (y/n): ")
    if not response.lower().startswith('y'):
        print("Integration test skipped")
        return True
    
    # Start emulation in background
    basic_dir = "software_example_beepsat/basic"
    emulation_process = None
    
    try:
        print("Starting background emulation...")
        emulation_process = subprocess.Popen(
            [sys.executable, "main_emulated.py"],
            cwd=basic_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        time.sleep(2)  # Let emulation start
        
        print("Starting dashboard...")
        dashboard_process = subprocess.Popen([sys.executable, "ground_station_dashboard.py"])
        
        print("Integration test running...")
        print("In the dashboard, click 'Start Console Monitor' to see live data")
        print("Press Ctrl+C to stop the test")
        
        # Wait for user interrupt
        try:
            dashboard_process.wait()
        except KeyboardInterrupt:
            print("\nStopping integration test...")
        
        # Clean up
        if dashboard_process.poll() is None:
            dashboard_process.terminate()
            dashboard_process.wait(timeout=5)
            
        return True
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        return False
    finally:
        if emulation_process and emulation_process.poll() is None:
            emulation_process.terminate()
            emulation_process.wait(timeout=5)

def main():
    """Main test function"""
    print("BeepSat Monitoring System Test Suite")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\nPlease install missing dependencies before running tests")
        return 1
    
    # Run tests
    tests = [
        ("Emulation Test", test_emulation),
        ("Dashboard Test", test_dashboard),
        ("Integration Test", run_integration_test)
    ]
    
    print(f"\nAvailable tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print(f"  4. Run All Tests")
    print(f"  0. Exit")
    
    while True:
        try:
            choice = input("\nSelect test to run (0-4): ").strip()
            
            if choice == '0':
                print("Exiting test suite")
                break
            elif choice == '4':
                # Run all tests
                for name, test_func in tests:
                    print(f"\n{'='*20} {name} {'='*20}")
                    if not test_func():
                        print(f"{name} failed!")
                        break
                else:
                    print("\nAll tests completed successfully!")
                break
            elif choice in ['1', '2', '3']:
                test_index = int(choice) - 1
                name, test_func = tests[test_index]
                print(f"\n{'='*20} {name} {'='*20}")
                test_func()
            else:
                print("Invalid choice. Please enter 0-4.")
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            break
        except Exception as e:
            print(f"Test error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())