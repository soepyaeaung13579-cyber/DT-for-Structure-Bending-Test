import sys
import serial
import time
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFormLayout, QPushButton, QLabel, 
                             QLineEdit, QTextEdit, QGridLayout, QGroupBox, 
                             QTableWidget, QTableWidgetItem, QComboBox)
from PyQt6.QtCore import QTimer, Qt

class SensorManager:
    """Handles hardware communication and raw-to-physical conversion[cite: 567, 576]."""
    def __init__(self, port='COM4', baud=115200):
        self.port, self.baud, self.ser = port, baud, None
        self.is_connected = False
        # Constants [cite: 608]
        self.GRAVITY, self.V_REF, self.GF, self.V_IN = 9.80665, 5.0, 2.0, 5.0
        self.BEAM_H, self.BEAM_L = 0.02, 0.5 
        # Factors [cite: 609]
        self.load_tare, self.load_calib_factor, self.strain_zero_bits = 0.0, 1.0, 0.0
        self.amp_gain, self.ultra_tare_duration = 100.0, 0.0

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            time.sleep(2)
            self.is_connected = True
            return True
        except: return False

    def get_average_raw(self, samples=10):
        """Averages multiple raw lines for stable benchmarking[cite: 611]."""
        collected = []
        if not self.is_connected: return None
        self.ser.reset_input_buffer()
        while len(collected) < samples:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                try:
                    vals = [float(x) for x in line.split(',')]
                    if len(vals) == 5: collected.append(vals)
                except: continue
        return np.mean(collected, axis=0) if collected else None

class SensorCalibrationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified Calibration & Monitoring Suite")
        self.setGeometry(100, 100, 1450, 900)
        self.sm = SensorManager()
        self.init_ui()
        self.live_timer = QTimer()
        self.live_timer.timeout.connect(self.update_live_dashboard)
        self.live_timer.start(100)

    def init_ui(self):
        cw = QWidget(); self.setCentralWidget(cw); layout = QHBoxLayout(cw)
        left = QVBoxLayout(); mid = QVBoxLayout(); right = QVBoxLayout()

        # 1. Connection & Benchmarking [cite: 616, 617]
        c_grp = QGroupBox("Hardware Controls")
        c_lay = QFormLayout()
        self.btn_conn = QPushButton("Connect Arduino")
        self.btn_conn.clicked.connect(self.handle_connect)
        self.lbl_status = QLabel("Disconnected")
        
        self.btn_load_tare = QPushButton("Tare Load Cell")
        self.btn_load_tare.clicked.connect(self.tare_load)
        self.m_input = QLineEdit("1.0") # Reference mass
        self.btn_load_cal = QPushButton("Set Load Factor")
        self.btn_load_cal.clicked.connect(self.calibrate_load)
        
        self.btn_strain_tare = QPushButton("Tare Strain (Mid)")
        self.btn_strain_tare.clicked.connect(self.tare_strain)
        self.d_input = QLineEdit("1.0") # Reference deflection
        self.btn_strain_cal = QPushButton("Set AMP_GAIN")
        self.btn_strain_cal.clicked.connect(self.calibrate_gain)

        c_lay.addRow(self.btn_conn, self.lbl_status)
        c_lay.addRow(self.btn_load_tare)
        c_lay.addRow("Standard Mass (kg):", self.m_input)
        c_lay.addRow(self.btn_load_cal)
        c_lay.addRow(self.btn_strain_tare)
        c_lay.addRow("Dial Gauge (mm):", self.d_input)
        c_lay.addRow(self.btn_strain_cal)
        c_grp.setLayout(c_lay); left.addWidget(c_grp)

        # Physics Selection [cite: 660]
        v_grp = QGroupBox("Validation Mode")
        v_lay = QFormLayout()
        self.mode = QComboBox(); self.mode.addItems(["Fixed-Fixed", "Simply Supported", "Cantilever"])
        self.pos_x = QLineEdit("250.0")
        v_lay.addRow("Beam Boundary:", self.mode); v_lay.addRow("Gauge X (mm):", self.pos_x)
        v_grp.setLayout(v_lay); left.addWidget(v_grp); left.addStretch()

        # 2. Step Log & Factors [cite: 591, 619]
        self.log_a = QTextEdit(); self.log_a.setReadOnly(True)
        self.log_a.setStyleSheet("background: #1e1e1e; color: #00ff00; font-family: Courier;")
        mid.addWidget(QLabel("<b>Process Log:</b>")); mid.addWidget(self.log_a)
        
        f_grp = QGroupBox("Derived Factors")
        f_lay = QFormLayout()
        self.l_fac = QLabel("1.0"); self.a_fac = QLabel("100.0")
        f_lay.addRow("Load Factor (bits/kg):", self.l_fac); f_lay.addRow("AMP_GAIN:", self.a_fac)
        f_grp.setLayout(f_lay); mid.addWidget(f_grp)

        # 3. Live Readouts [cite: 644]
        d_grp = QGroupBox("Live Readouts")
        d_lay = QGridLayout()
        self.l_load = QLabel("0.00 N"); self.l_s1 = QLabel("0.0 uE"); self.l_s2 = QLabel("0.0 uE")
        self.l_s3 = QLabel("0.0 uE"); self.l_virt = QLabel("0.00 mm"); self.l_pos = QLabel("0.00 mm")
        
        style = "font-size: 12pt; font-weight: bold; color: #00ff00; background: black; padding: 2px;"
        for lbl in [self.l_load, self.l_s1, self.l_s2, self.l_s3, self.l_virt, self.l_pos]: lbl.setStyleSheet(style)
        
        d_lay.addWidget(QLabel("Force:"), 0, 0); d_lay.addWidget(self.l_load, 0, 1)
        d_lay.addWidget(QLabel("Strain Support Left:"), 1, 0); d_lay.addWidget(self.l_s1, 1, 1)
        d_lay.addWidget(QLabel("Strain Mid:"), 2, 0); d_lay.addWidget(self.l_s2, 2, 1)
        d_lay.addWidget(QLabel("Strain Support Right:"), 3, 0); d_lay.addWidget(self.l_s3, 3, 1)
        d_lay.addWidget(QLabel("VIRTUAL DIAL:"), 4, 0); d_lay.addWidget(self.l_virt, 4, 1)
        d_lay.addWidget(QLabel("Position:"), 5, 0); d_lay.addWidget(self.l_pos, 5, 1)
        d_grp.setLayout(d_lay); right.addWidget(d_grp)

        # 4. Tables [cite: 663, 582]
        self.t_def = QTableWidget(5, 4); self.t_def.setHorizontalHeaderLabels(["Pt", "Physical (mm)", "Virtual (mm)", "Error %"])
        self.t_lod = QTableWidget(5, 5); self.t_lod.setHorizontalHeaderLabels(["Pt", "Mass (kg)", "Ref (N)", "Live (N)", "Error %"])
        self.t_pos = QTableWidget(5, 4); self.t_pos.setHorizontalHeaderLabels(["Pt", "Manual (mm)", "Ultra (mm)", "Error %"])

        for t in [self.t_def, self.t_lod, self.t_pos]:
            for i in range(5): 
                t.setItem(i, 0, QTableWidgetItem(f"Pt {i+1}"))
                for col in range(1, t.columnCount()): t.setItem(i, col, QTableWidgetItem("0.0"))

        # Connection of Cell-Changed signals for Auto-Fill [cite: 726, 757, 788]
        self.t_def.itemChanged.connect(self.auto_fill_def)
        self.t_lod.itemChanged.connect(self.auto_fill_lod)
        self.t_pos.itemChanged.connect(self.auto_fill_pos)

        # Refresh Buttons [cite: 1, 2]
        r_def = QPushButton("Refresh Deflection Table"); r_def.clicked.connect(lambda: self.clear_table(self.t_def))
        r_lod = QPushButton("Refresh Load Table"); r_lod.clicked.connect(lambda: self.clear_table(self.t_lod))
        r_pos = QPushButton("Refresh Position Table"); r_pos.clicked.connect(lambda: self.clear_table(self.t_pos))

        right.addWidget(QLabel("<b>Deflection Validation</b>")); right.addWidget(self.t_def); right.addWidget(r_def)
        right.addWidget(QLabel("<b>Load Validation (kg to N auto-convert)</b>")); right.addWidget(self.t_lod); right.addWidget(r_lod)
        right.addWidget(QLabel("<b>Position Validation</b>")); right.addWidget(self.t_pos); right.addWidget(r_pos)

        layout.addLayout(left, 1); layout.addLayout(mid, 2); layout.addLayout(right, 3)

    # --- Logic ---
    def handle_connect(self):
        if self.sm.connect(): self.lbl_status.setText("Connected"); self.log("Serial Ready.")

    def tare_load(self):
        raw = self.sm.get_average_raw(20); self.sm.load_tare = raw[0]; self.log("Load Tared.")

    def calibrate_load(self):
        raw = self.sm.get_average_raw(20); self.sm.load_calib_factor = (raw[0] - self.sm.load_tare) / float(self.m_input.text())
        self.l_fac.setText(f"{self.sm.load_calib_factor:.4f}"); self.log("Load Factor Set.")

    def tare_strain(self):
        raw = self.sm.get_average_raw(30); self.sm.strain_zero_bits = raw[2]; self.log("Strain Tared.")

    def calibrate_gain(self):
        raw = self.sm.get_average_raw(30); dial_m = float(self.d_input.text()) / 1000.0
        eps = (12.0 * self.sm.BEAM_H * dial_m) / (self.sm.BEAM_L**2)
        dV = ((raw[2] - self.sm.strain_zero_bits) * 5.0) / 1023.0
        self.sm.amp_gain = (4.0 * dV) / (eps * self.sm.GF * self.sm.V_IN)
        self.a_fac.setText(f"{self.sm.amp_gain:.2f}"); self.log("Gain Set.")

    def update_live_dashboard(self):
        raw = self.sm.get_average_raw(1)
        if raw is not None:
            force_n = ((raw[0] - self.sm.load_tare) / self.sm.load_calib_factor) * self.sm.GRAVITY

            strains = [((raw[i] - self.sm.strain_zero_bits)*5.0/1023.0)*4e6/(self.sm.GF*self.sm.V_IN*self.sm.amp_gain) for i in range(1,4)]
            # Physics Projection [cite: 656, 659]
            mode = self.mode.currentIndex(); L, H = self.sm.BEAM_L, self.sm.BEAM_H
            e = strains[1]/1e6
            if mode == 0: v = (e*L**2)/(12*H)
            elif mode == 1: v = (e*L**2)/(6*H)
            else: v = (e*(float(self.pos_x.text())/1000.0)**2)/(3*H)
            # Position conversion [cite: 786, 787]
            p_mm = (raw[4] / 58.0) * 10.0
            self.l_load.setText(f"{force_n:.2f} N"); 
            self.l_s2.setText(f"{strains[1]:.1f} uE");self.l_s1.setText(f"{strains[0]:.1f} uE");self.l_s3.setText(f"{strains[2]:.1f} uE")
            self.l_virt.setText(f"{v*1000:.3f} mm"); self.l_pos.setText(f"{p_mm:.2f} mm")

    # --- Auto-Fill Logic [cite: 726, 757, 788] ---
    def auto_fill_def(self, item):
        if item.column() == 1:
            row, val = item.row(), float(self.l_virt.text().replace(" mm",""))
            self.t_def.blockSignals(True)
            self.t_def.setItem(row, 2, QTableWidgetItem(f"{val:.3f}"))
            m = float(item.text())
            if m != 0: self.t_def.setItem(row, 3, QTableWidgetItem(f"{abs((val-m)/m)*100:.2f}%"))
            self.t_def.blockSignals(False)

    def auto_fill_lod(self, item):
        if item.column() == 1: # Mass column
            row = item.row()
            mass_kg = float(item.text())
            ref_n = mass_kg * self.sm.GRAVITY
            live_n = float(self.l_load.text().replace(" N",""))
            self.t_lod.blockSignals(True)
            self.t_lod.setItem(row, 2, QTableWidgetItem(f"{ref_n:.2f}"))
            self.t_lod.setItem(row, 3, QTableWidgetItem(f"{live_n:.2f}"))
            if ref_n != 0: self.t_lod.setItem(row, 4, QTableWidgetItem(f"{abs((live_n-ref_n)/ref_n)*100:.2f}%"))
            self.t_lod.blockSignals(False)

    def auto_fill_pos(self, item):
        if item.column() == 1:
            row, val = item.row(), float(self.l_pos.text().replace(" mm",""))
            self.t_pos.blockSignals(True)
            self.t_pos.setItem(row, 2, QTableWidgetItem(f"{val:.2f}"))
            m = float(item.text())
            if m != 0: self.t_pos.setItem(row, 3, QTableWidgetItem(f"{abs((val-m)/m)*100:.2f}%"))
            self.t_pos.blockSignals(False)

    def clear_table(self, t):
        t.blockSignals(True)
        for i in range(5):
            for j in range(1, t.columnCount()): t.setItem(i, j, QTableWidgetItem("0.0"))
        t.blockSignals(False)

    def log(self, msg): self.log_a.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv); window = SensorCalibrationApp(); window.show(); sys.exit(app.exec())