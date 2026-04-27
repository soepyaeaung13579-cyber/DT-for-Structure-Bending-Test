import serial

ser = serial.Serial('COM5', 9600)

print("Testing Ultrasonic Position... Press Ctrl+C to stop.")

while True:
    if ser.in_waiting > 0:
        raw_val = ser.readline().decode('utf-8').strip()
        try:
            # Distance = (Time / 58) for cm -> / 100 for meters
            position_m = (float(raw_val) / 58.0) / 100.0
            print(f"Load Position: {position_m:.3f} m")
        except ValueError:
            pass