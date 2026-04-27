import serial
import time

# --- Configuration ---
PORT = 'COM5' 
BAUD = 9600
V_REF = 5.0    
GF = 2.0       # BF350 Gauge Factor
V_EXCITE = 5.0 
AMPLIFIER_GAIN = 100.0 # Estimate: Check your LM358 resistor values (Rf/Rin)

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
except:
    print("Error: Port not found.")
    exit()

def get_raw():
    if ser.in_waiting > 0:
        try:
            return float(ser.readline().decode('utf-8').strip())
        except ValueError: return None
    return None

# --- Step 1: Tare ---
print("Taring Quarter-Bridge... Do not touch the bar.")
samples = []
while len(samples) < 20:
    val = get_raw()
    if val is not None: samples.append(val)
tare_offset = sum(samples) / len(samples)

# --- Step 2: Measurement ---
print("\nReading Strain (Quarter-Bridge)...")
try:
    while True:
        raw_val = get_raw()
        if raw_val is not None:
            # 1. Calculate voltage change at Arduino pin
            # (raw_val - tare) converts bits to change in bits
            # bits * (5V / 1023) converts change in bits to change in Volts
            dV_measured = ((raw_val - tare_offset) * V_REF) / 1023.0
            
            # 2. Account for LM358 Gain
            # Vout_bridge = dV_measured / Gain
            dV_bridge = dV_measured / AMPLIFIER_GAIN
            
            # 3. Quarter-Bridge Formula: epsilon = (4 * dV_bridge) / (GF * Vin)
            strain_uE = (4 * dV_bridge) / (GF * V_EXCITE) * 1e6
            
            print(f"Raw: {raw_val:<5} | Strain: {strain_uE:.1f} uE")
            
except KeyboardInterrupt:
    ser.close()