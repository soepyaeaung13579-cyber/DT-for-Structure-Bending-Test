import serial
import time
import math

# --- 1. User Inputs & Physical Parameters ---
# Geometry for your specific test specimen
BEAM_L = 63.5   # mm
BEAM_H = 3.0    # mm
GF = 2.0        # BF350 Gauge Factor
V_IN = 5.0      # Arduino Excitation Voltage

# --- 2. Serial Initialization ---
try:
    # Adjust COM port as needed (Check Arduino IDE -> Tools -> Port)
    ser = serial.Serial('COM4', 115200, timeout=1) 
    time.sleep(2)
    print(f"--- Cyber-Physical Link Established (63.5mm Beam) ---")
except:
    print("Error: Serial port not found. Check cable and close Serial Monitor.")
    exit()

def get_raw_bits(samples=30):
    """Calculates average bits from Arduino A0 with signal smoothing."""
    vals = []
    ser.reset_input_buffer()
    while len(vals) < samples:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            if "Raw_Bits:" in line: # Expecting format from previous Arduino code
                try:
                    parts = line.split('|')
                    raw_val = float(parts[0].split(':')[1])
                    vals.append(raw_val)
                except: continue
    return sum(vals) / len(vals)

# --- 3. Calibration Stage: Physical Dial Gauge Benchmarking ---
print("\n[STEP 1] TARE: Establish Zero Offset")
input("Remove all loads. Ensure Dial Gauge is at 0.00. Press Enter...")
zero_bits = get_raw_bits()
print(f"Zero Baseline established: {zero_bits:.2f} bits")

print("\n[STEP 2] GAIN CALIBRATION: Physical Benchmarking")
input("Apply load until deflection is stable. Press Enter...")
loaded_bits = get_raw_bits()
physical_dial_mm = float(input("Enter reading from Physical Dial Gauge (mm): "))

# --- 3
#  Gain Factor Calculation ---
# A. Calculate Theoretical Strain for this measured deflection by FIXED-FIXED 
# epsilon = (3 * H * delta) / L^2
epsilon_theory = (12.0 * BEAM_H * physical_dial_mm) / (BEAM_L**2)

# B. Calculate Hardware Gain Factor (Electronic slope of LM358)
# dV = V_bits_diff * (5V / 1023)
# Gain = (4 * dV) / (epsilon * GF * Vin)
dV_arduino = ((loaded_bits - zero_bits) * 5.0) / 1023.0
gain_factor = (4.0 * dV_arduino) / (epsilon_theory * GF * V_IN)

print(f"\n--- Calibration Successful ---")
print(f"Theoretical Strain: {epsilon_theory * 1e6:.1f} uE")
print(f"Calculated Gain Factor: {gain_factor:.2f}")
print("-" * 40)



# --- 4. Validation Selection ---
print("\n--- STEP 2: VALIDATION MODE ---")
print("Select Boundary Condition for Validation:")
print("1: Fixed-Fixed (Center Load)")
print("2: Simply Supported (Center Load)")
print("3: Cantilever (Variable Load Position)")
mode = input("Choice (1-3): ")

x_load = 0
if mode == '3':
    x_load = float(input("Enter Distance from Fixed Support to Load/Gauge (mm): "))

# --- 5. Real-Time Execution ---
print("\nMonitoring Started. Compare 'Virtual Dial' with Physical Dial Gauge...")
try:
    while True:
        current_bits = get_raw_bits(samples=5)
        bit_diff = current_bits - zero_bits
        
        # A. Live Strain (Constant Gain Factor)
        v_live = (bit_diff * 5.0) / 1023.0
        live_strain = (4.0 * v_live) / (GF * V_IN * gain_factor)
        
        # B. BC Physics Projection (Validation of Deflection)
        if mode == '1':   # Fixed-Fixed
            virtual_dial = (live_strain * (BEAM_L**2)) / (12.0 * BEAM_H)
        elif mode == '2': # Simply Supported
            virtual_dial = (live_strain * (BEAM_L**2)) / (6.0 * BEAM_H)
        elif mode == '3': # Cantilever (At point of load x)
            # Formula: delta = (epsilon * x^2) / (3 * H)
            virtual_dial = (live_strain * (x_load**2)) / (3.0 * BEAM_H)
            
        print(f"Strain: {live_strain*1e6:<8.1f} uE | Virtual Dial: {virtual_dial:.2f} mm")
        time.sleep(0.1)

except KeyboardInterrupt:
    ser.close()