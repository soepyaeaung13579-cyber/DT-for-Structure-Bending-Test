import serial
import time

# --- 1. Initialization ---
PORT = 'COM5'  # Update if your port changed
BAUD_RATE = 9600
GRAVITY = 9.80665

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for Arduino reset
    print(f"Connected to Arduino on {PORT}")
except Exception as e:
    print(f"Error: Could not connect to {PORT}. {e}")
    exit()

def get_average_raw(samples=10):
    """Reads multiple samples from Serial and returns the average raw count."""
    vals = []
    ser.reset_input_buffer() # Clear old data
    while len(vals) < samples:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            try:
                vals.append(float(line))
            except ValueError:
                continue
    return sum(vals) / len(vals)

# --- 2. Calibration Procedure ---

# A. Tare (Zero Load)
print("\n--- Step 1: TARE ---")
input("Remove all weights from the load cell and press Enter...")
print("Calculating Tare (Zero Offset)...")
tare_offset = get_average_raw(20)
print(f"Tare complete. Offset value: {tare_offset}")

# B. Calibration (Known Weight)
print("\n--- Step 2: CALIBRATION ---")
input("Place a known weight on the load cell and press Enter...")
known_weight_kg = float(input("Enter the weight of the object in KILOGRAMS: "))

print(f"Measuring raw value for {known_weight_kg}kg...")
load_raw_average = get_average_raw(20)

# Factor = (Reading with weight - Tare offset) / Weight in kg
calibration_factor = (load_raw_average - tare_offset) / known_weight_kg

print(f"\nCalibration Successful!")
print(f"Calculated Calibration Factor: {calibration_factor:.4f}")
print("Starting real-time measurements in Newtons...")
print("-" * 40)

# --- 3. Measurement Loop ---
try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            try:
                raw_val = float(line)
                
                # Formula: Weight (kg) = (Raw - Tare) / Factor
                weight_kg = (raw_val - tare_offset) / calibration_factor
                
                # Convert to Newtons
                force_newtons = weight_kg * GRAVITY
                
                # Prevent showing small negative noise when empty
                if abs(force_newtons) < 0.05: force_newtons = 0.00
                
                print(f"Raw: {raw_val:<10} | Weight: {weight_kg:.3f} kg | Force: {force_newtons:.2f} N")
                
            except ValueError:
                pass
except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
finally:
    ser.close()