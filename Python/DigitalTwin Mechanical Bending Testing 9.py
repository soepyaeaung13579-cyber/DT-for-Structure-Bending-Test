"""
Digital Twin Mechanical Bending Testing System
================================================
A comprehensive PyQt6-based application for mechanical testing simulation,
ROM visualization, sensor calibration, and live digital twin monitoring.

Author: CSE Lab
Version: 2.0.0
"""

import os
os.environ["QT_API"] = "pyqt6"

import sys
import time
import vtk
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve                       
import scipy.sparse.linalg as spla
from scipy.integrate import cumulative_trapezoid              
import pyvista as pv
from pyvistaqt import QtInteractor                              
import gc  # Added for memory management

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QPushButton, QMessageBox, QInputDialog, QGridLayout, 
                             QTableWidgetItem, QLabel, QLineEdit, QComboBox, QTextEdit, 
                             QSlider, QCheckBox, QSplitter, QSizePolicy, QGroupBox, QTableWidget, 
                             QStackedWidget, QListWidget, QFileDialog, QTabWidget, QFrame, QProgressDialog, QDialog, QProgressBar, QHeaderView) # <--- Added QProgressDialog, QDialog, QProgressBar!

from PyQt6.QtCore import Qt, QTime, QUrl, QTimer
from PyQt6.QtGui import QFont, QAction, QDesktopServices, QPixmap
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pickle
from datetime import datetime
import traceback
import serial
import serial.tools.list_ports  # Auto-detect COM ports

from PyQt6.QtCore import QThread, pyqtSignal


# =========================================================================
# PROFESSIONAL COLOR SCHEME & STYLING CONSTANTS
# =========================================================================
class ProfessionalTheme:
    """Professional color palette for the Digital Twin application."""
    
    # Primary Colors
    PRIMARY_BLUE = "#1e3a5f"
    DARK_BLUE = "#0f1f2e"
    ACCENT_BLUE = "#2980b9"
    BRIGHT_BLUE = "#3498db"

    # Secondary Colors
    SUCCESS_GREEN = "#27ae60"
    HOVER_GREEN = "#229954"
    WARNING_ORANGE = "#e67e22"
    DANGER_RED = "#e74c3c"
    ERROR_RED = "#c0392b"
    INFO_PURPLE = "#8e44ad"

    # Neutral Colors
    BACKGROUND_LIGHT = "#f5f6fa"
    BACKGROUND_MEDIUM = "#ecf0f1"
    BACKGROUND_DARK = "#2c3e50"
    TEXT_DARK = "#1a1a1a"
    TEXT_LIGHT = "#ecf0f1"
    TEXT_GRAY = "#7f8c8d"
    BORDER_COLOR = "#bdc3c7"
    BORDER_LIGHT = "#d5dbdb"

    # Console Styling
    CONSOLE_BG = "#1e1e1e"
    CONSOLE_TEXT = "#00ff00"
    SHADOW_COLOR = "rgba(0, 0, 0, 0.15)"

    @staticmethod
    def create_header_widget(title_text, logo_path="CSE IMAGE.png"): # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        """
        Creates a professional header widget with logo and title.
        
        Args:
            title_text (str): Main title text to display
            logo_path (str): Path to logo image file
            
        Returns:
            QWidget: Styled header widget
        """
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ProfessionalTheme.PRIMARY_BLUE},
                    stop:1 {ProfessionalTheme.ACCENT_BLUE});
                border-bottom: 3px solid {ProfessionalTheme.DARK_BLUE};
            }}
        """)
        header_widget.setFixedHeight(100)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            scaled_pixmap = logo_pixmap.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
        header_layout.addWidget(logo_label)

        # Title Section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        title_label = QLabel(title_text)                                # pyright: ignore[reportUnknownArgumentType]
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {ProfessionalTheme.TEXT_LIGHT};")
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("Digital Twin Monitoring System")
        subtitle_label.setFont(QFont("Segoe UI", 11))
        subtitle_label.setStyleSheet("color: #e8eef7; font-weight: 400;")
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()

        header_layout.addLayout(title_layout, 1)
        header_layout.addStretch()

        return header_widget

    @staticmethod
    def apply_professional_panel_style(widget):                        # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        """
        Applies professional panel styling to a group box.
        
        Args:
            widget (QGroupBox): The widget to style
        """
        if isinstance(widget, QGroupBox):
            widget.setStyleSheet(f"""
                QGroupBox {{
                    font-weight: 600;
                    border: 1px solid {ProfessionalTheme.BORDER_LIGHT};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: #ffffff;
                    padding: 12px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 5px;
                    color: {ProfessionalTheme.PRIMARY_BLUE};
                    font-weight: bold;
                    font-size: 11pt;
                }}
            """)

    @staticmethod
    def create_button_style(bg_color, text_color="white", hover_color=None, width=None): # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        """
        Factory method to create professional button styles.
        
        Args:
            bg_color (str): Background color in hex format
            text_color (str): Text color in hex format
            hover_color (str): Hover state color (auto-darkened if None)
            width (int): Optional minimum button width in pixels
            
        Returns:
            str: CSS stylesheet string
        """
        if hover_color is None:
            # Auto-darken for hover effect
            color_hex = bg_color.replace("#", "")                           
            r = int(color_hex[0:2], 16)                                     
            g = int(color_hex[2:4], 16)                                     
            b = int(color_hex[4:6], 16)                                    
            r, g, b = max(0, r - 20), max(0, g - 20), max(0, b - 20)
            hover_color = f"#{r:02x}{g:02x}{b:02x}"

        width_str = f"min-width: {width}px;" if width else ""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                font-weight: bold;
                padding: 8px 14px;
                border: none;
                border-radius: 5px;
                font-size: 10pt;
                {width_str}
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid {ProfessionalTheme.TEXT_DARK};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                padding: 9px 13px;
            }}
            QPushButton:disabled {{
                background-color: #ccc;
                color: #999;
            }}
        """


# =========================================================================
# BACKGROUND HARDWARE THREAD (Prevents GUI Freezes)
# =========================================================================
class HardwareWorker(QThread):
    """
    Background worker thread for hardware operations.
    Prevents UI freezing during long-running hardware tasks.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress = pyqtSignal(int)
    data_ready = pyqtSignal(object, float, float)

    def __init__(self, task_func, *args, **kwargs): # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        """
        Initialize hardware worker.
        
        Args:
            task_func: Function to execute in background
            *args: Positional arguments for task_func
            **kwargs: Keyword arguments for task_func
        """
        super().__init__()
        self.task_func = task_func
        self.args = args                       # pyright: ignore[reportUnknownMemberType]
        self.kwargs = kwargs                   # pyright: ignore[reportUnknownMemberType]
        self._running = False

    def run(self):
        """Execute the task in background thread."""
        try:
            self._running = True
            if callable(self.task_func):
                self.task_func(*self.args, **self.kwargs) # type: ignore
                self.finished.emit()
                return

            sm = self.task_func
            while self._running:
                raw = sm.get_average_raw(1)
                if raw is not None:
                    if sm.load_calib_factor == 0 or not np.isfinite(sm.load_calib_factor):
                        self.error_occurred.emit("Invalid load calibration factor. Tare with no load, then calibrate with a known mass.")
                        self.msleep(250)
                        continue
                        
                    # 1. Load calculation
                    force_n = ((raw[3] - sm.load_tare) / sm.load_calib_factor) * sm.GRAVITY + sm.load_offset_n
                    
                    # 2. Strain calculations
                    strains = [sm.calc_microstrain(raw[i], sm.strain_tare_bits[i], sm.strain_af[i]) for i in range(3)]
                    
                    # 3.TOF Position calculation using calibrated TOF values from Module 2
                    
                    try:
                        tof_offset = float(sm.TOF_offset_mm)
                    except (AttributeError, ValueError):
                        tof_offset = 0.0
                        
                    p_mm = raw[4] + tof_offset  # Uses calibration output
                    
                    # Send updated data back to live view
                    self.data_ready.emit(strains, float(force_n), float(p_mm))
                    
                self.msleep(50)
        except Exception as e:
            self.error.emit(str(e))
            self.error_occurred.emit(str(e))
            traceback.print_exc()

    def stop(self):
        """Stop the worker loop and wait briefly for the thread to exit."""
        self._running = False
        if self.isRunning():
            self.wait(1000)

# =========================================================================
# . HARDWARE LAYER
# =========================================================================
import serial.tools.list_ports  # Auto-detect COM ports

class SensorManager:
    """Handles hardware communication and physical constants."""
    def __init__(self, port='COM5', baud=115200):  # Removed hardcoded COM3
        self.baud = baud
        self.port = port
        self.ser = None
        self.is_connected = False
        
        # --- HX711 & Bridge Constants ---
        self.GRAVITY = 9.80665
        self.V_REF = 4.85
        self.V_IN = self.V_REF
        self.GF = 2.0
        self.GAIN = 64.0        
        self.ADC_MAX = 16777216.0 
        
        # --- Beam Physical Properties (AL6061) ---
        self.E_GPa = 69.0       
        self.L_m = 0.514          
        self.b_m = 0.015        
        self.h_m = 0.003        
        
        # Compute Structural Stiffness (EI)
        self.I_m4 = (self.b_m * self.h_m**3) / 12.0
        self.EI = (self.E_GPa * 1e9) * self.I_m4
        
        # --- Sensor Tracking Arrays ---
        self.load_tare = 0.0
        self.load_calib_factor = 1.0
        self.load_offset_n = 0.0
        self.ultra_tare = 0.0
        self.ultra_tare_pos = 0.0  # Ultrasonic tare position (mm)
        self.ultra_offset_mm = 0.0
        self.sound_speed_mps = 343.0
        
        # [Ch1 (Left), Ch2 (Mid), Ch3 (Right)]
        self.strain_tare_bits = np.array([0.0, 0.0, 0.0])
        self.strain_af = np.array([2.0, 2.0, 2.0]) 
        self.strain_zero_bits = 0.0
        self.amp_gain = 100.0
        
        self.live_raw = [0, 0, 0, 0, 0]

    def connect(self, port=None):
        """Connects to the dynamically passed COM port."""
        if port is not None:
            self.port = port
        if not self.port:
            print("Connection error: no serial port selected.")
            return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            time.sleep(2)
            self.is_connected = True
            return True
        except Exception as e: 
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Safely disconnect from serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False

    def get_average_raw(self, samples=10, timeout_sec=2.0):
        """Get averaged raw sensor readings."""
        collected = []
        if not self.is_connected: return None
        self.ser.reset_input_buffer()
        start_time = time.time()
        while len(collected) < samples:
            if (time.time() - start_time) > timeout_sec:
                break
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                try:
                    vals = [float(x) for x in line.split(',')]
                    if len(vals) == 5: collected.append(vals)
                except: continue
            else:
                time.sleep(0.01)
        
        if collected:
            self.live_raw = np.mean(collected, axis=0)
            return self.live_raw
        return None

    def compute_af(self, raw_bits):
        """Compute Asymmetric Factor from raw ADC bits."""
        v_offset_ratio = raw_bits / (self.ADC_MAX * self.GAIN)
        return 1.0 / (v_offset_ratio + 0.5)

    def calc_microstrain(self, raw_bits, tare_bits, af):
        """Calculate microstrain from raw ADC with tare reference and AF."""
        delta_bits = raw_bits - tare_bits
        v_ratio = delta_bits / (self.ADC_MAX * self.GAIN)
        return (2.0 * af * v_ratio * 1e6) / self.GF


# =========================================================================
#  WORKBENCH LAUNCHPAD (THE BRAIN)
# =========================================================================
class WorkbenchLaunchpad(QMainWindow):
    """The root entry point. Mimics Ansys Workbench Project Schematic."""
    
    def closeEvent(self, event):
        self.log_msg("Initiating System Shutdown...")
        if hasattr(self, 'offline_studio') and self.offline_studio: self.offline_studio.close()
        if hasattr(self, 'sm'): self.sm.disconnect()
        event.accept()
        if hasattr(self, 'visualizer_window') and self.visualizer_window: self.visualizer_window.close()
        if hasattr(self, 'calib_window') and self.calib_window: self.calib_window.close()
        if hasattr(self, 'live_window') and self.live_window: self.live_window.close()
        if hasattr(self, 'sm'): self.sm.disconnect()
        event.accept()

    def __init__(self):
        super().__init__()
        # 1. NEW TITLE
        self.setWindowTitle("Digital Twin for Smart Structure Lab")
        self.setGeometry(100, 100, 1000, 750) # Expanded to fit the new professional layout
        
        # Show splash screen with loading bar
        self.show_splash_screen()
        
        self.sm = SensorManager(port='COM5', baud=115200)
        self.offline_studio = OfflinePreparationStudio() 
        self.visualizer_window = None 
        self.calib_window = None
        self.live_window = None
        
        self.setup_menu_bar()
        self.build_ui()
        self.statusBar().showMessage("System Ready")
        self.log_msg("Digital Twin Workbench Initialized successfully.")

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        open_rom_act = QAction("📂 Load ROM Bank (.pkl)", self)
        open_rom_act.triggered.connect(self.manual_load_rom)
        file_menu.addAction(open_rom_act)
        file_menu.addSeparator()
        exit_act = QAction("❌ Exit Workbench", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Help Menu (UPDATED)
        help_menu = menubar.addMenu("Help")
        
        student_manual_act = QAction("📘 Open Student Lab Manual (PDF)", self)
        student_manual_act.triggered.connect(self.open_student_manual)
        help_menu.addAction(student_manual_act)
        
        instructor_manual_act = QAction("📙 Open Instructor Manual (PDF)", self)
        instructor_manual_act.triggered.connect(self.open_instructor_manual)
        help_menu.addAction(instructor_manual_act)
        
        help_menu.addSeparator()
        
        about_act = QAction("ℹ️ About System", self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    def show_about(self):
        about_text = (
            "<h2>Digital Twin for Structure Bending Test</h2>"
            "<p><b>Version:</b> Professional 2.0</p>"
            "<p>A comprehensive Cyber-Physical simulation environment integrating "
            "Finite Element Analysis, Reduced Order Modeling (ROM), and Real-Time "
            "Hardware Sensor Fusion.</p>"
        )
        QMessageBox.about(self, "About System", about_text)

    def show_splash_screen(self):
        """Display splash screen with logo and loading bar."""
        splash_dialog = QDialog(None, Qt.WindowType.FramelessWindowHint)
        splash_dialog.setStyleSheet("background-color: #2c3e50; border: 3px solid #3498db; border-radius: 10px;")
        splash_dialog.setFixedSize(550, 400) # Increased height for logo
        
        layout = QVBoxLayout(splash_dialog)
        layout.setContentsMargins(30, 20, 30, 30)
        
        # --- NEW: Logo Image ---
        logo_img=QLabel()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "CSE IMAGE.png")
        logo_pix = QPixmap(logo_path)
        if not logo_pix.isNull():
            logo_img.setPixmap(logo_pix.scaled(400, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo_img.setPixmap(logo_pix.scaled(400, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) # type: ignore
            logo_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_img)
        
        # Title
        title = QLabel("Digital Twin Workbench")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ecf0f1; margin-top: 10px;")
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Structure Bending Test - FEM/ROM Platform")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(subtitle)
        
        # Loading bar
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setStyleSheet("""
            QProgressBar { border: 2px solid #ecf0f1; border-radius: 5px; background-color: #34495e; text-align: center; color: white;}
            QProgressBar::chunk { background-color: #3498db; }
        """)
        layout.addWidget(progress)
        
        # Status text
        status_lbl = QLabel("Initializing System...")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setStyleSheet("color: #2ecc71; font-weight: bold;")
        layout.addWidget(status_lbl)
        
        splash_dialog.move(QApplication.primaryScreen().geometry().center() - splash_dialog.rect().center())
        splash_dialog.show()
        
        # Simulate loading
        for i in range(101):
            progress.setValue(i)
            if i < 30: status_lbl.setText(f"Loading Modules... {i}%")
            elif i < 70: status_lbl.setText(f"Connecting Hardware... {i}%")
            else: status_lbl.setText(f"System Ready! {i}%")
            QApplication.processEvents()
            time.sleep(0.02)
        
        splash_dialog.close()

    def build_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet(f"background-color: {ProfessionalTheme.BACKGROUND_LIGHT};")
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- PROFESSIONAL HEADER WITH LOGO ---
        header = ProfessionalTheme.create_header_widget("Digital Twin Workbench-Smart Structures Lab", "CSE IMAGE.png")
        self.main_layout.addWidget(header)
        
        # --- HORIZONTAL SPLITTER (Sidebar + Schematic) ---
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ====================================================================
        # 1. LEFT SIDEBAR (Logo + Status + Documentation)
        # ====================================================================
        sidebar_widget = QWidget()
        sidebar_widget.setStyleSheet(f"background-color: {ProfessionalTheme.BACKGROUND_LIGHT}; border-right: 1px solid {ProfessionalTheme.BORDER_COLOR};")
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- App Logo at top of Sidebar ---
        side_logo = QLabel()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "CSE IMAGE.png")
        side_pix = QPixmap(logo_path)
        if not side_pix.isNull():
            logo_frame = QFrame()
            logo_frame.setStyleSheet(f"background-color: white; border: 2px solid {ProfessionalTheme.ACCENT_BLUE}; border-radius: 8px; padding: 5px;")
            logo_frame_layout = QVBoxLayout(logo_frame)
            side_logo.setPixmap(side_pix.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            side_logo.setPixmap(side_pix.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) # type: ignore
            side_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_frame_layout.addWidget(side_logo)
            sidebar_layout.addWidget(logo_frame)
        
        sidebar_layout.addSpacing(15)

        # A. System Status Monitor
        status_grp = QGroupBox("System Status Monitor")
        ProfessionalTheme.apply_professional_panel_style(status_grp)
        status_lay = QVBoxLayout(status_grp)
        
        self.lbl_rom_status = QLabel("🔴 ROM Data: Not Loaded")
        self.lbl_hw_status = QLabel("🔴 Hardware: Disconnected")
        self.lbl_active_module = QLabel("🔵 Active Module: None")
        
        # Style status labels
        status_label_style = f"font-weight: bold; color: {ProfessionalTheme.TEXT_DARK}; padding: 4px; border-left: 4px solid {ProfessionalTheme.ACCENT_BLUE}; background-color: {ProfessionalTheme.BACKGROUND_LIGHT};"
        for lbl in [self.lbl_rom_status, self.lbl_hw_status, self.lbl_active_module]:
            lbl.setStyleSheet(status_label_style)
        
        status_lay.addWidget(self.lbl_rom_status)
        status_lay.addWidget(self.lbl_hw_status)
        status_lay.addSpacing(15)
        status_lay.addWidget(self.lbl_active_module)
        
        btn_refresh = QPushButton("↻ Refresh Status")
        btn_refresh.setStyleSheet(f"QPushButton {{ background-color: {ProfessionalTheme.ACCENT_BLUE}; color: white; font-weight: bold; padding: 6px; border-radius: 4px; }}")
        btn_refresh.clicked.connect(self.update_system_status)
        status_lay.addStretch()
        status_lay.addWidget(btn_refresh)

        # B. Quick Documentation Box
        docs_grp = QGroupBox("Lab Documentation")
        ProfessionalTheme.apply_professional_panel_style(docs_grp)
        docs_lay = QVBoxLayout(docs_grp)
        
        btn_student_doc = QPushButton("📘 Student Lab Manual")
        btn_student_doc.setStyleSheet(f"QPushButton {{ background-color: {ProfessionalTheme.INFO_PURPLE}; color: white; font-weight: bold; padding: 8px; border-radius: 4px; text-align: left; }}")
        btn_student_doc.clicked.connect(self.open_student_manual)
        
        btn_instruct_doc = QPushButton("📙 Instructor Manual")
        btn_instruct_doc.setStyleSheet(f"QPushButton {{ background-color: {ProfessionalTheme.PRIMARY_BLUE}; color: white; font-weight: bold; padding: 8px; border-radius: 4px; text-align: left; }}")
        btn_instruct_doc.clicked.connect(self.open_instructor_manual)
        
        docs_lay.addWidget(btn_student_doc)
        docs_lay.addWidget(btn_instruct_doc)
        docs_lay.addStretch()

        # Combine Status and Docs into the Sidebar, then add to Splitter
        sidebar_layout.addWidget(status_grp)
        sidebar_layout.addWidget(docs_grp)
        self.top_splitter.addWidget(sidebar_widget)

        # ====================================================================
        # 2. RIGHT PANEL (The Schematic Flowchart)
        # ====================================================================
        schematic_grp = QGroupBox("Project Schematic: Data Flow & Execution")
        
        # Professional schematic styling with gradient background
        schematic_grp.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold; 
                border: 2px solid {ProfessionalTheme.ACCENT_BLUE}; 
                border-radius: 8px; 
                margin-top: 1.5ex;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 {ProfessionalTheme.BACKGROUND_LIGHT}, 
                    stop:1 #ffffff);
                padding: 5px;
            }} 
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                left: 15px; 
                padding: 0 5px;
                color: {ProfessionalTheme.PRIMARY_BLUE};
                font-weight: bold;
            }}
        """)
        
        schematic_grid = QGridLayout(schematic_grp)
        schematic_grid.setSpacing(15)
        schematic_grid.setContentsMargins(20, 30, 20, 20)
        
        # Professional Button Styles
        base_style = f"""
            QPushButton {{ 
                color: white; 
                font-size: 13px; 
                font-weight: bold; 
                padding: 12px; 
                border-radius: 6px; 
                border: 2px solid {ProfessionalTheme.DARK_BLUE};
                min-height: 80px;
            }}
            QPushButton:hover {{ 
                border: 2px solid {ProfessionalTheme.TEXT_LIGHT};
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34495e, stop:1 #2c3e50);
            }}
            QPushButton:pressed {{
                background-color: {ProfessionalTheme.DARK_BLUE};
                border: 2px solid white;
            }}
        """
        
        # Module Buttons with specific colors
        self.btn_offline = QPushButton("🛠️ Module 1\nOffline Studio")
        self.btn_offline.setStyleSheet(base_style + f"QPushButton {{ background-color: {ProfessionalTheme.PRIMARY_BLUE}; }}")
        self.btn_offline.clicked.connect(self.launch_offline_studio)
        
        self.btn_vis = QPushButton("🔍 Module 2\nROM Visualizer")
        self.btn_vis.setStyleSheet(base_style + f"QPushButton {{ background-color: {ProfessionalTheme.INFO_PURPLE}; }}")
        self.btn_vis.clicked.connect(self.launch_rom_visualizer)
        
        self.btn_calib = QPushButton("📡 Module 3\nSensor Calibration")
        self.btn_calib.setStyleSheet(base_style + f"QPushButton {{ background-color: {ProfessionalTheme.WARNING_ORANGE}; }}")
        self.btn_calib.clicked.connect(self.launch_calibration)
        
        self.btn_live = QPushButton("🚀 Module 4\nOnline Digital Twin")
        self.btn_live.setStyleSheet(base_style + f"QPushButton {{ background-color: {ProfessionalTheme.SUCCESS_GREEN}; border: 2px solid #145a32; }}")
        self.btn_live.setMinimumHeight(100)
        self.btn_live.clicked.connect(self.launch_live_twin)

        # Helper for modern schematic arrows
        def make_connector(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 40px; font-weight: bold; color: #3498db;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl
        
        # Column and Row Stretching for centering
        for i in range(3): schematic_grid.setColumnStretch(i, 1)
        for i in range(5): schematic_grid.setRowStretch(i, 1)

        self.top_splitter.addWidget(schematic_grp)

        def make_connector(text, align):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 56px; font-weight: 900; color: #1e5a96;")
            lbl.setAlignment(align)
            lbl.setMinimumHeight(60)
            return lbl

        # Grid Layout Placement
        schematic_grid.addWidget(self.btn_offline, 0, 0)
        schematic_grid.addWidget(self.btn_calib, 0, 2)
        schematic_grid.addWidget(make_connector("⬇", Qt.AlignmentFlag.AlignCenter), 1, 0)
        schematic_grid.addWidget(make_connector("⬇", Qt.AlignmentFlag.AlignCenter), 1, 2)
        schematic_grid.addWidget(self.btn_vis, 2, 0)
        schematic_grid.addWidget(make_connector("⬇", Qt.AlignmentFlag.AlignCenter), 2, 2)
        schematic_grid.addWidget(make_connector("╚", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom), 3, 0)
        schematic_grid.addWidget(make_connector("╝", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom), 3, 2)
        schematic_grid.addWidget(self.btn_live, 4, 1)
        
        schematic_grid.setColumnStretch(0, 1)
        schematic_grid.setColumnStretch(1, 1)
        schematic_grid.setColumnStretch(2, 1)
        schematic_grid.setRowStretch(0, 1)
        schematic_grid.setRowStretch(1, 1)
        schematic_grid.setRowStretch(2, 1)
        schematic_grid.setRowStretch(3, 1)
        schematic_grid.setRowStretch(4, 1)
        
        self.top_splitter.addWidget(schematic_grp)
        self.top_splitter.setSizes([250, 750]) # Sidebar 25%, Schematic 75%
        
        # ====================================================================
        # 3. BOTTOM TERMINAL CONSOLE
        # ====================================================================
        console_grp = QGroupBox("System Output Console")
        ProfessionalTheme.apply_professional_panel_style(console_grp)
        console_lay = QVBoxLayout(console_grp)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(f"background-color: {ProfessionalTheme.CONSOLE_BG}; color: {ProfessionalTheme.CONSOLE_TEXT}; font-family: Consolas, 'Courier New', monospace; font-size: 11px; border: 1px solid {ProfessionalTheme.BORDER_COLOR}; border-radius: 4px;")
        console_lay.addWidget(self.console_output)

        # Main Vertical Splitter (Top Panels vs Bottom Console)
        self.main_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_v_splitter.addWidget(self.top_splitter)
        self.main_v_splitter.addWidget(console_grp)
        self.main_v_splitter.setSizes([500, 150])               # Console takes up bottom area

        self.main_layout.addWidget(self.main_v_splitter)
        self.update_system_status()
        
    # --- SYSTEM UTILITIES ---
    def log_msg(self, msg):
        """Prints messages to the Ansys-style terminal console."""
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.console_output.append(f"[{timestamp}] {msg}")
        # Scroll to bottom
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_system_status(self):
        """Checks RAM and Hardware to update the Sidebar indicators."""
        # Check ROM
        if hasattr(self.offline_studio, 'DT_Bank') and len(self.offline_studio.DT_Bank) > 0:
            self.lbl_rom_status.setText("🟢 ROM Data: Loaded in RAM")
            self.lbl_rom_status.setStyleSheet("color: green;")
        else:
            self.lbl_rom_status.setText("🔴 ROM Data: Not Loaded")
            self.lbl_rom_status.setStyleSheet("color: red;")
            
        # Check Hardware
        if self.sm.is_connected:
            self.lbl_hw_status.setText(f"🟢 Hardware: Connected ({self.sm.port})")
            self.lbl_hw_status.setStyleSheet("color: green;")
        else:
            self.lbl_hw_status.setText("🔴 Hardware: Disconnected")
            self.lbl_hw_status.setStyleSheet("color: red;")

    def manual_load_rom(self):
        """Allow user to manually load ROM bank from file."""
        from PyQt6.QtWidgets import QFileDialog
        import pickle
        file_name, _ = QFileDialog.getOpenFileName(self, "Open ROM Bank File", "", "Pickle Files (*.pkl)")
        if file_name:
            try:
                with open(file_name, 'rb') as f: 
                    self.offline_studio.DT_Bank = pickle.load(f)
                self.log_msg(f"SUCCESS: Loaded ROM Bank from {file_name.split('/')[-1]}")
                file_basename = os.path.basename(file_name)
                self.log_msg(f"SUCCESS: Loaded ROM Bank from {file_basename}")
                self.update_system_status()
            except Exception as e:
                self.log_msg(f"ERROR: Failed to load ROM - {str(e)}")
                traceback.print_exc()

    # --- MODULE LAUNCHERS ---
    def launch_offline_studio(self):
        self.log_msg("Launching Module 1: Offline Preparation Studio...")
        self.lbl_active_module.setText("🔵 Active Module: M1 (Offline Studio)")
        self.offline_studio.show()
        self.offline_studio.activateWindow()
        self.update_system_status()

    def launch_rom_visualizer(self):
        if not hasattr(self.offline_studio, 'DT_Bank') or len(self.offline_studio.DT_Bank) == 0:
            self.log_msg("WARNING: Module 2 requires ROM Data. Prompting user to load file.")
            self.manual_load_rom()
            if not hasattr(self.offline_studio, 'DT_Bank') or len(self.offline_studio.DT_Bank) == 0:
                self.log_msg("ABORT: No ROM loaded.")
                return 
                
        self.log_msg("Launching Module 2: ROM Interactive Visualizer...")
        self.lbl_active_module.setText("🔵 Active Module: M2 (ROM Visualizer)")
        if self.visualizer_window is None:
            self.visualizer_window = ROMVisualizerWindow(dt_bank=self.offline_studio.DT_Bank, geometry=self.offline_studio.geometry, launcher=self)
        self.visualizer_window.show()
        self.visualizer_window.activateWindow()  

    def launch_calibration(self):
        self.log_msg("Launching Module 3: Physical Sensor Calibration...")
        self.lbl_active_module.setText("🔵 Active Module: M3 (Sensor Calibration)")
        if self.calib_window is None:
            self.calib_window = CalibrationWindow(self.sm, self.offline_studio.geometry)
        self.calib_window.show()
        self.calib_window.activateWindow()

    def launch_live_twin(self):
        if not hasattr(self.offline_studio, 'DT_Bank') or len(self.offline_studio.DT_Bank) == 0:
            self.log_msg("WARNING: Module 4 requires ROM Data. Prompting user to load file.")
            self.manual_load_rom()
            if not hasattr(self.offline_studio, 'DT_Bank') or len(self.offline_studio.DT_Bank) == 0:
                self.log_msg("ABORT: No ROM loaded.")
                return 
                
        self.log_msg("Launching Module 4: Online Digital Twin Monitor...")
        self.lbl_active_module.setText("🔵 Active Module: M4 (Online Digital Twin)")
        if self.live_window is None:
            self.live_window = LiveDigitalTwinWindow(sensor_manager=self.sm, dt_bank=self.offline_studio.DT_Bank, geometry=self.offline_studio.geometry, launcher=self)
        self.live_window.show()
        self.live_window.activateWindow()

    def open_student_manual(self):
        # Change "Student_Manual.pdf" to your actual file name
        pdf_path = os.path.abspath("Student_Manual.pdf") 
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            self.log_msg("📘 Opened Student Lab Manual.")
        else:
            QMessageBox.warning(self, "File Not Found", f"Could not find the file:\n{pdf_path}\n\nPlease ensure the PDF is in the same folder as the software.")
            error_msg = (f"Could not find the file:\n{pdf_path}\n\n"
                        "Please ensure the PDF is in the same folder as the software.")
            QMessageBox.warning(self, "File Not Found", error_msg)
            self.log_msg("ERROR: Student Manual PDF not found.")

    def open_instructor_manual(self):
        # Change "Instructor_Manual.pdf" to your actual file name
        pdf_path = os.path.abspath("Instructor_Manual.pdf")
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            self.log_msg("📙 Opened Instructor Manual.")
        else:
            QMessageBox.warning(self, "File Not Found", f"Could not find the file:\n{pdf_path}\n\nPlease ensure the PDF is in the same folder as the software.")
            error_msg = (f"Could not find the file:\n{pdf_path}\n\n"
                        "Please ensure the PDF is in the same folder as the software.")
            QMessageBox.warning(self, "File Not Found", error_msg)
            self.log_msg("ERROR: Instructor Manual PDF not found.")    


# =========================================================================
# 1. OFFLINE STUDIO (MODULE 1) - ANSYS WORKBENCH STYLE
# =========================================================================
class OfflinePreparationStudio(QMainWindow):
    """The Main Offline Studio, utilizing a Workflow Tree instead of Tabs."""
    
    def closeEvent(self, event):
        """Cleanly shut down all PyVista OpenGL windows to prevent handle errors on exit."""
        pyvista_plotters = ['UIAxes', 'UIAxes2', 'UIAxes3', 'UIAxes_3D_Validation', 'UIAxes5', 'UIAxes6', 'UIAxes9', 'UIAxes10']
        for plotter_name in pyvista_plotters:
            if hasattr(self, plotter_name):
                plotter = getattr(self, plotter_name)
                if plotter is not None:
                    try: plotter.close()
                    except Exception: pass
        event.accept()    

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Module 1: FEM / ROM Offline Studio")
        self.setGeometry(100, 100, 1400, 900)
        
        self.geometry = {'Lx': 0.5, 'Ly': 0.015, 'Lz': 0.003}
        self.material = {'E': 68e9, 'nu': 0.33, 'rho': 7850}
        self.mesh_params = {'nx': 50, 'ny': 10, 'nz': 10}
        self.settings = {'Integration': 'Full'}
        self.element_type = 'Hexa8'
        self.beam_type = 'Cantilever'
        self.BEAM_H, self.BEAM_L = self.geometry['Lz'], self.geometry['Lx']
        self.exp_u_input=None
        self.node_coords = None; self.element_connectivity = None; self.mesh_info = {}
        self.bc_info = {}; self.loads = {}
        self.K_global = None; self.F_global = None; self.K_reduced = None; self.F_reduced = None
        self.D_mat = None; self.B_global = None; self.U_full = None; self.S_max = None
        self.Sigma_Final2 = None
        self.Phi = None; self.Phi_stress = None; self.K_rom = None; self.DT_Bank = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # --- ANSYS WORKBENCH LAYOUT ---
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 1. Left Sidebar: Workflow Tree
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_proj = QLabel("<b>Project Schematic</b>")
        lbl_proj.setFont(QFont("Arial", 14))
        self.sidebar_layout.addWidget(lbl_proj)
        
        # List of workflow buttons
        workflow_steps = [
            "1. Geometry & Meshing",
            "2. Loads & BC",
            "3. Solve Model",
            "4. FEM Validation",
            "5. Post-Processing",
            "6. ROM Training",
            "7. ROM Validation & Save"
        ]
        
        self.step_buttons = []
        for i, step in enumerate(workflow_steps):
            btn = QPushButton(step)
            btn.setStyleSheet("""
                QPushButton { 
                    text-align: left; 
                    padding: 12px; 
                    background-color: #f8f9fa; 
                    border: 1px solid #dee2e6; 
                    border-radius: 5px; 
                    font-size: 11pt;
                    font-weight: 500;
                    color: #2c3e50;
                }
                QPushButton:hover { 
                    background-color: #e9ecef; 
                    border: 1px solid #adb5bd;
                }
                QPushButton:checked { 
                    background-color: #0d6efd; 
                    color: white; 
                    font-weight: bold;
                    border: 1px solid #0d6efd;
                }
            """)
            btn.setCheckable(True)
            if i == 0: btn.setChecked(True)
            
            # Connect the button click to change the stacked widget page
            btn.clicked.connect(lambda checked, idx=i: self.switch_workflow_step(idx))
            self.step_buttons.append(btn)
            self.sidebar_layout.addWidget(btn)
            
        # --- Explicit Clear All Data Button ---
        self.sidebar_layout.addStretch()
        self.btn_clear_data = QPushButton("🗑️ Clear Entire Project")
        self.btn_clear_data.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                padding: 12px; 
                border-radius: 5px; 
                font-weight: bold; 
                font-size: 10pt;
                border: 1px solid #bb2d3b;
            }
            QPushButton:hover { 
                background-color: #bb2d3b; 
            }
        """)
        self.btn_clear_data.clicked.connect(self.clear_all_project_data)
        self.sidebar_layout.addWidget(self.btn_clear_data)
            
        # 2. Right Area: Stacked Widget (The Content)
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.sidebar_widget)
        self.main_layout.addWidget(self.stacked_widget, stretch=1)
        
        self.build_ui()

    def switch_workflow_step(self, index):
        """Changes the active panel and updates button styles."""
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == index)
        self.stacked_widget.setCurrentIndex(index)

    def build_ui(self):
        """Builds all panels and adds them to the Stacked Widget instead of Tabs."""
        self.stacked_widget.addWidget(self.create_panel1_geometry())
        self.stacked_widget.addWidget(self.create_panel2_load_bc())
        self.stacked_widget.addWidget(self.create_panel3_solve())
        self.stacked_widget.addWidget(self.create_panel4_validation())
        self.stacked_widget.addWidget(self.create_panel5_post_processing())
        self.stacked_widget.addWidget(self.create_panel6_rom_training())
        self.stacked_widget.addWidget(self.create_panel7_rom_validation())

    @staticmethod
    def m_to_mm(value_m):
        return value_m * 1000.0

    @staticmethod
    def mm_to_m(value_mm):
        return value_mm / 1000.0

    @staticmethod
    def pa_to_mpa(value_pa):
        return value_pa / 1e6

    @staticmethod
    def mpa_to_pa(value_mpa):
        return value_mpa * 1e6

    def lock_ui(self):
        self.central_widget.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def unlock_ui(self):
        self.central_widget.setEnabled(True)
        QApplication.restoreOverrideCursor()    

    # =========================================================================
    # MEMORY CLEARING LOGIC (CRASH PREVENTION)
    # =========================================================================
    def clear_downstream_data(self, stage):
        """Cascading memory flush. Wipes matrices from RAM based on what you cleared."""
        if stage == 'mesh':
            self.K_global = None; self.F_global = None; self.D_mat = None; self.B_global = None
        if stage in ['mesh', 'bc']:
            self.K_reduced = None; self.F_reduced = None
        if stage in ['mesh', 'bc', 'solve']:
            self.U_full = None; self.Sigma_Final2 = None
        if stage in ['mesh', 'bc', 'solve', 'rom_train']:
            self.Phi = None; self.Phi_stress = None; self.K_rom = None

    def clear_all_project_data(self):
        """Triggered by the red sidebar button to flush absolutely everything."""
        reply = QMessageBox.question(self, 'Clear Data', 'Clear all project memory and graphics?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_downstream_data('mesh')
            self.node_coords = None; self.element_connectivity = None; self.DT_Bank = []
            
            # Wipe all graphics
            self.action_clear_panel1()
            self.action_clear_panel2()
            self.action_clear_panel4()
            self.action_clear_panel5()
            self.action_clear_panel6()
            self.action_clear_panel7()
            
            # Force garbage collection
            gc.collect()
    
    def clear_rom_memory(self):
        """MEMORY FIX: Clears ROM-related data before retraining to prevent crashes on repeated cycles."""
        self.Phi = None
        self.Phi_stress = None
        self.K_rom = None
        self.SnapshotMatrix = None
        gc.collect()  # Force immediate garbage collection
        
        msg = "ROM data cleared from memory.\nSafe to retrain with heavy mesh density."
        QMessageBox.information(None, "Memory Cleared", msg)

    # --- DEDICATED PANEL GRAPHICS CLEAR ACTIONS ---
    def action_clear_panel1(self):
        self.UIAxes.clear(); self.UIAxes.add_axes(); self.UIAxes.update()
        self.UIAxes2.clear(); self.UIAxes2.add_axes(); self.UIAxes2.update()
        self.clear_downstream_data('mesh')

    def action_clear_panel2(self):
        self.UIAxes3.clear(); self.UIAxes3.add_axes(); self.UIAxes3.update()
        self.UIAxes4.clear(); self.canvas_forces.draw_idle()
        self.clear_downstream_data('bc')

    def action_clear_panel4(self):
        self.UIAxes_3D_Validation.clear(); self.UIAxes_3D_Validation.add_axes(); self.UIAxes_3D_Validation.update()
        self.fig_1d_validation.clf(); self.canvas_1d_validation.draw_idle()

    def action_clear_panel5(self):
        self.UIAxes5.clear(); self.UIAxes5.add_axes(); self.UIAxes5.update()
        self.UIAxes6.clear(); self.UIAxes6.add_axes(); self.UIAxes6.update()

    def action_clear_panel6(self):
        self.fig_svd.clf(); self.UIAxes8.draw_idle()
        self.clear_downstream_data('rom_train')

    def action_clear_panel7(self):
        self.UIAxes9.clear(); self.UIAxes9.add_axes(); self.UIAxes9.update()
        self.UIAxes10.clear(); self.UIAxes10.add_axes(); self.UIAxes10.update()

    # =========================================================================
    # UI PANELS 1-7
    # =========================================================================
    def create_panel1_geometry(self):
        panel = QWidget(); layout = QHBoxLayout(panel)
        left = QWidget(); form = QFormLayout(left)
        
        self.LmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Lx']):g}"); form.addRow("L (mm):", self.LmEditField)
        self.wmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Ly']):g}"); form.addRow("w (mm):", self.wmEditField)
        self.HmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Lz']):g}"); form.addRow("H (mm):", self.HmEditField)
        
        btn_vis = QPushButton("Visualize Geometry"); btn_vis.clicked.connect(self.VasulizeGeometryButtonPushed)
        form.addRow(btn_vis)

        self.EPaEditField = QLineEdit(f"{self.pa_to_mpa(self.material['E']):g}"); form.addRow("E (MPa):", self.EPaEditField)
        self.NuEditField = QLineEdit(str(self.material['nu'])); form.addRow("Nu:", self.NuEditField)
        self.rhokgm3EditField = QLineEdit(str(self.material['rho'])); form.addRow("rho (kg/m^3):", self.rhokgm3EditField)

        self.EsizexEditField = QLineEdit(str(self.mesh_params['nx'])); form.addRow("Esize.x:", self.EsizexEditField)
        self.EsizeyEditField = QLineEdit(str(self.mesh_params['ny'])); form.addRow("Esize.y:", self.EsizeyEditField)
        self.EsizezEditField = QLineEdit(str(self.mesh_params['nz'])); form.addRow("Esize.z:", self.EsizezEditField)
        
        self.Element_typeDropDown = QComboBox()
        self.Element_typeDropDown.addItems(["Hexa8", "Hexa20", "Tet4", "Tet10"])
        form.addRow("Element_type:", self.Element_typeDropDown)
        
        self.IntpointDropDown = QComboBox()
        self.IntpointDropDown.addItems(["Full", "Reduce"])
        form.addRow("Int point:", self.IntpointDropDown)
        
        btn_mesh = QPushButton("Meshing"); btn_mesh.clicked.connect(self.MeshingButtonPushed)
        form.addRow(btn_mesh)
        
        # --- NEW: Improved Clear Graphics Button ---
        btn_clear = QPushButton("🗑️ Clear Geometry & Mesh")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold;")
        btn_clear.clicked.connect(self.action_clear_panel1)
        form.addRow(btn_clear)
        
        self.MeshinfoTextArea = QTextEdit(); self.MeshinfoTextArea.setReadOnly(True)
        form.addRow("Mesh info:", self.MeshinfoTextArea)
        
        right = QSplitter(Qt.Orientation.Vertical)
        self.UIAxes = QtInteractor(right); right.addWidget(self.UIAxes) 
        self.UIAxes2 = QtInteractor(right); right.addWidget(self.UIAxes2) 
        
        layout.addWidget(left, 1); layout.addWidget(right, 3)
        return panel

    def create_panel2_load_bc(self):
        panel = QWidget(); layout = QVBoxLayout(panel) 
        top_widget = QWidget(); top_layout = QHBoxLayout(top_widget)
        
        vbox_beam = QVBoxLayout()
        vbox_beam.addWidget(QLabel("<b>Beam Type:</b>"))
        self.BeamTypeDropDown = QComboBox(); self.BeamTypeDropDown.addItems(["Cantilever", "Fixed-Fixed", "Simply Supported"])
        vbox_beam.addWidget(self.BeamTypeDropDown); top_layout.addLayout(vbox_beam)
        
        vbox_pos = QVBoxLayout()
        beam_len = self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0
        start_pos = (50 / 100.0) * beam_len
        self.lbl_load_pos = QLabel(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm(start_pos):.1f} mm</span>")
        vbox_pos.addWidget(self.lbl_load_pos)
        
        self.LoadPositionSlider = QSlider(Qt.Orientation.Horizontal)
        self.LoadPositionSlider.setMinimum(0); self.LoadPositionSlider.setMaximum(100); self.LoadPositionSlider.setValue(50)
        self.LoadPositionSlider.setMinimumWidth(200); self.LoadPositionSlider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.LoadPositionSlider.valueChanged.connect(
            lambda v: self.lbl_load_pos.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm((v/100.0) * (self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0)):.1f} mm</span>")
        )
        vbox_pos.addWidget(self.LoadPositionSlider); top_layout.addLayout(vbox_pos)
        
        vbox_val = QVBoxLayout(); vbox_val.addWidget(QLabel("<b>Load Value (N):</b>"))
        self.LoadValueNEditField = QLineEdit("-10"); self.LoadValueNEditField.setFixedWidth(80)
        vbox_val.addWidget(self.LoadValueNEditField); top_layout.addLayout(vbox_val)
        
        vbox_apply = QVBoxLayout(); self.GravitationalForceSwitch = QCheckBox("Enable Gravity"); vbox_apply.addWidget(self.GravitationalForceSwitch)
        btn_apply = QPushButton("Apply Load & BC"); btn_apply.setStyleSheet("font-weight: bold; padding: 6px; background-color: #2b5797; color: white;")
        btn_apply.clicked.connect(self.ApplyLoadButtonPushed)
        vbox_apply.addWidget(btn_apply)
        
        # --- NEW: Improved Clear Graphics Button ---
        btn_clear = QPushButton("🗑️ Clear Load Visuals")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 6px;")
        btn_clear.clicked.connect(self.action_clear_panel2)
        vbox_apply.addWidget(btn_clear)
        
        top_layout.addLayout(vbox_apply)
        
        vbox_info = QVBoxLayout(); vbox_info.addWidget(QLabel("<b>Matrix Info:</b>"))
        self.MatrixSizeTextArea = QTextEdit(); self.MatrixSizeTextArea.setReadOnly(True); self.MatrixSizeTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        self.MatrixSizeTextArea.setMaximumHeight(45); self.MatrixSizeTextArea.setFixedWidth(150); vbox_info.addWidget(self.MatrixSizeTextArea)
        top_layout.addLayout(vbox_info); layout.addWidget(top_widget, 0)
        
        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        self.UIAxes3 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes3)
        self.fig_forces = Figure(); self.UIAxes4 = self.fig_forces.add_subplot(111); self.canvas_forces = FigureCanvas(self.fig_forces)
        bottom_splitter.addWidget(self.canvas_forces); bottom_splitter.setSizes([700, 300]) 
        layout.addWidget(bottom_splitter, 1)
        return panel

    def create_panel3_solve(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        btn_solve = QPushButton("Solve"); btn_solve.clicked.connect(self.SolveButtonPushed)
        self.ComputationalInfromationTextArea = QTextEdit(); self.ComputationalInfromationTextArea.setReadOnly(True)
        layout.addWidget(btn_solve); layout.addWidget(QLabel("Computational Information:")); layout.addWidget(self.ComputationalInfromationTextArea)
        return panel

    def create_panel4_validation(self):

        panel = QWidget(); layout = QHBoxLayout(panel)
        left = QWidget(); left_layout = QVBoxLayout(left)
        
        # 1. Action Buttons
        btn_val = QPushButton("Validation with Euler-Bernoulli Beam Theory")
        btn_val.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b5797; color: white;")
        btn_val.clicked.connect(self.ValidationwithEulierBernoullisBeamTheoryButtonPushed)
        left_layout.addWidget(btn_val)

        btn_clear = QPushButton("🗑️ Clear Validation Plots")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px;")
        btn_clear.clicked.connect(self.action_clear_panel4)
        left_layout.addWidget(btn_clear)
     
        # 2. Validation Input (Physical Dial Gauge Value)
        self.exp_u_input = QLineEdit("0.00")
        self.exp_u_input.setFixedWidth(80)
        
        input_container = QHBoxLayout()
        input_container.addWidget(QLabel("<b>Exp. Deflection (mm):</b>"))
        input_container.addWidget(self.exp_u_input)
        input_container.addStretch()
        left_layout.addLayout(input_container)

        # 3. 1D Plotting Area
        left_layout.addWidget(QLabel("<b>1D Euler-Bernoulli Beam Theory Results</b>"))
        self.fig_1d_validation = Figure(); self.canvas_1d_validation = FigureCanvas(self.fig_1d_validation)
        left_layout.addWidget(self.canvas_1d_validation, stretch=2) 

        # 4. Summary Text Area
        left_layout.addWidget(QLabel("<b>Validation Summary</b>"))
        self.ValidationSummaryTextArea = QTextEdit(); self.ValidationSummaryTextArea.setReadOnly(True)
        self.ValidationSummaryTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        left_layout.addWidget(self.ValidationSummaryTextArea, stretch=1)

        # 5. 3D Plotting Area
        right = QWidget(); right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("<b>3D Solid Beam Results (Top: Bending, Bottom: Shear)</b>"))
        self.UIAxes_3D_Validation = QtInteractor(right, shape=(2, 1)); right_layout.addWidget(self.UIAxes_3D_Validation)
        
        layout.addWidget(left, 4); layout.addWidget(right, 6)
        return panel

    def create_panel5_post_processing(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        top_widget = QWidget(); top_layout = QHBoxLayout(top_widget)
        
        top_layout.addWidget(QLabel("<b>Stress Type:</b>")); self.TypeofStressesDropDown = QComboBox(); self.TypeofStressesDropDown.addItems(["Sigma_xx", "Sigma_yy", "Sigma_zz", "Tau_xy", "Tau_yz", "Tau_zx"]); top_layout.addWidget(self.TypeofStressesDropDown)
        top_layout.addWidget(QLabel("<b>Failure Method:</b>")); self.MethodDropDown = QComboBox(); self.MethodDropDown.addItems(["Von Mises", "Max Principal", "Max Shear (Tresca)"]); top_layout.addWidget(self.MethodDropDown)
        top_layout.addWidget(QLabel("<b>Display:</b>")); self.DisplayChoiceDropDown = QComboBox(); self.DisplayChoiceDropDown.addItems(["FS", "Stress"]); top_layout.addWidget(self.DisplayChoiceDropDown)
        top_layout.addWidget(QLabel("<b>Yield (MPa):</b>")); self.YieldStrengthMpaEditField = QLineEdit("250"); self.YieldStrengthMpaEditField.setFixedWidth(60); top_layout.addWidget(self.YieldStrengthMpaEditField)
        top_layout.addWidget(QLabel("<b>Scale:</b>")); self.ScaleFactorEditField = QLineEdit("5"); self.ScaleFactorEditField.setFixedWidth(60); top_layout.addWidget(self.ScaleFactorEditField)
        top_layout.addSpacing(20)
        
        btn_plot = QPushButton("Open PostProcessing")
        btn_plot.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 4px;")
        btn_plot.clicked.connect(self.OpenPostProcessingButtonPushed)
        top_layout.addWidget(btn_plot)
        
        # --- NEW: Improved Clear Graphics Button ---
        btn_clear = QPushButton("🗑️ Clear Graphics")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px 20px; border-radius: 4px;")
        btn_clear.clicked.connect(self.action_clear_panel5)
        top_layout.addWidget(btn_clear)
        
        layout.addWidget(top_widget, 0) 
        
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.UIAxes5 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes5)
        self.UIAxes6 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes6)
        bottom_splitter.setSizes([500, 500]); layout.addWidget(bottom_splitter, 1) 
        return panel

    def create_panel6_rom_training(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("<b>Number of Snapshots:</b>"))
        self.num_snapshotsEditField = QLineEdit("12"); self.num_snapshotsEditField.setFixedWidth(100)
        input_layout.addWidget(self.num_snapshotsEditField); input_layout.addStretch()
        
        # --- MEMORY FIX: Clear ROM data before retraining ---
        btn_clear_rom = QPushButton("🧹 Clear ROM Memory")
        btn_clear_rom.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 10px 15px; border-radius: 5px;")
        btn_clear_rom.clicked.connect(self.clear_rom_memory)
        input_layout.addWidget(btn_clear_rom)
        
        btn_train = QPushButton("Start ROM Training")
        btn_train.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 5px;")
        btn_train.clicked.connect(self.TrainButtonPushed); input_layout.addWidget(btn_train)
        
        # --- NEW: Improved Clear Graphics Button ---
        btn_clear = QPushButton("🗑️ Clear SVD Plot")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px 20px; border-radius: 5px;")
        btn_clear.clicked.connect(self.action_clear_panel6)
        input_layout.addWidget(btn_clear)
        
        layout.addLayout(input_layout)
        
        layout.addWidget(QLabel("<b>Training Log & Time:</b>"))
        self.TrainningTimeTextArea = QTextEdit(); self.TrainningTimeTextArea.setReadOnly(True)
        self.TrainningTimeTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        self.TrainningTimeTextArea.setMaximumHeight(150); layout.addWidget(self.TrainningTimeTextArea)
        
        layout.addWidget(QLabel("<b>ROM Invariance (Singular Value Decomposition)</b>"))
        self.fig_svd = Figure(); self.UIAxes8 = FigureCanvas(self.fig_svd); layout.addWidget(self.UIAxes8)
        return panel

    def create_panel7_rom_validation(self):
        panel = QWidget(); layout = QHBoxLayout(panel)
        left = QWidget(); form = QFormLayout(left)

        self.ValidationLoadPositionSlider = QSlider(Qt.Orientation.Horizontal)
        self.ValidationLoadPositionSlider.setMinimum(0); self.ValidationLoadPositionSlider.setMaximum(100); self.ValidationLoadPositionSlider.setValue(50) 
        start_pos = (50 / 100.0) * self.geometry['Lx']
        self.lbl_load_pos_val = QLabel(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm(start_pos):.1f} mm</span>")
        self.ValidationLoadPositionSlider.valueChanged.connect(
            lambda v: self.lbl_load_pos_val.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm((v/100.0) * self.geometry['Lx']):.1f} mm</span>")
        )
        form.addRow(self.lbl_load_pos_val, self.ValidationLoadPositionSlider)

        self.ValidationLoadNEditField = QLineEdit("-10"); form.addRow("Validation Load (N):", self.ValidationLoadNEditField)
        self.TypeofStressesDropDown_2 = QComboBox(); self.TypeofStressesDropDown_2.addItems(['Sigma_xx', 'Sigma_yy', 'Sigma_zz', 'Tau_xy', 'Tau_yz', 'Tau_zx'])
        form.addRow("Type of Stresses:", self.TypeofStressesDropDown_2)

        self.CheckAccuracyButton = QPushButton("Check Accuracy (FEM vs ROM)")
        self.CheckAccuracyButton.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b5797; color: white;")
        self.CheckAccuracyButton.clicked.connect(self.CheckAccuracyButtonPushed)
        form.addRow(self.CheckAccuracyButton)

        # --- NEW: Improved Clear Graphics Button ---
        btn_clear_graphics = QPushButton("🗑️ Clear Accuracy Graphics")
        btn_clear_graphics.setStyleSheet("font-weight: bold; padding: 10px; background-color: #7f8c8d; color: white;")
        btn_clear_graphics.clicked.connect(self.action_clear_panel7)
        form.addRow(btn_clear_graphics)

        self.AccuracyResultsTextArea = QTextEdit(); self.AccuracyResultsTextArea.setReadOnly(True)
        self.AccuracyResultsTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        form.addRow(self.AccuracyResultsTextArea)

        self.SaveButton = QPushButton("Save ROM to Disk")
        self.SaveButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #2e8b57; color: white;")
        self.SaveButton.clicked.connect(self.SaveButtonPushed); form.addRow(self.SaveButton)

        self.ClearBankButton = QPushButton("Clear ROM Bank")
        self.ClearBankButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #b22222; color: white;")
        self.ClearBankButton.clicked.connect(self.ClearBankButtonPushed); form.addRow(self.ClearBankButton)


        right = QSplitter(Qt.Orientation.Horizontal)
        fem_widget = QWidget()
        fem_layout = QVBoxLayout(fem_widget)
        label_fem = QLabel("<b>FEM </b>"); label_fem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.UIAxes9 = QtInteractor(fem_widget)
        fem_layout.addWidget(label_fem); fem_layout.addWidget(self.UIAxes9)
        right.addWidget(fem_widget)
        
        rom_widget = QWidget()
        rom_layout = QVBoxLayout(rom_widget)
        label_rom = QLabel("<b>ROM </b>"); label_rom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.UIAxes10 = QtInteractor(rom_widget)
        rom_layout.addWidget(label_rom); rom_layout.addWidget(self.UIAxes10)
        right.addWidget(rom_widget)
        layout.addWidget(left, 1); layout.addWidget(right, 3)
        return panel


    # =========================================================================
    # CORE MATH & PLOTTING FUNCTIONS
    # =========================================================================
    
    # =========================================================================
    # MATH BACKEND: GEOMETRY, MESHING, ASSEMBLY
    # =========================================================================
    def VasulizeGeometryButtonPushed(self):
        L = self.mm_to_m(float(self.LmEditField.text()))
        W = self.mm_to_m(float(self.wmEditField.text()))
        H = self.mm_to_m(float(self.HmEditField.text()))
        if L <= 0 or W <= 0 or H <= 0: return
        self.geometry = {'Lx': L, 'Ly': W, 'Lz': H}
        if hasattr(self, 'lbl_load_pos'):
            pos_m = (self.LoadPositionSlider.value() / 100.0) * self.geometry['Lx']
            self.lbl_load_pos.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm(pos_m):.1f} mm</span>")
        if hasattr(self, 'lbl_load_pos_val'):
            pos_m = (self.ValidationLoadPositionSlider.value() / 100.0) * self.geometry['Lx']
            self.lbl_load_pos_val.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm(pos_m):.1f} mm</span>")
        
        box = pv.Box(bounds=(0, L, 0, W, 0, H))
        self.UIAxes.add_mesh(box, name='geom_box', color="lightblue", show_edges=True, opacity=0.4)
        
        if not hasattr(self.UIAxes, 'axes_widget_added'):
            self.UIAxes.add_axes()
            self.UIAxes.axes_widget_added = True
            
        self.UIAxes.reset_camera()
        self.UIAxes.update()

    def MeshingButtonPushed(self):
        self.material['E'] = self.mpa_to_pa(float(self.EPaEditField.text()))
        self.material['nu'] = float(self.NuEditField.text())
        self.material['rho'] = float(self.rhokgm3EditField.text())
        self.element_type = self.Element_typeDropDown.currentText()
        self.settings['Integration'] = self.IntpointDropDown.currentText()
        self.mesh_params['nx'] = int(self.EsizexEditField.text())
        self.mesh_params['ny'] = int(self.EsizeyEditField.text())
        self.mesh_params['nz'] = int(self.EsizezEditField.text())
        
        self.generate_mesh_3d()
        
        if 'Hexa' in self.element_type: n_vis, vtk_type = 8, pv.CellType.HEXAHEDRON
        else: n_vis, vtk_type = 4, pv.CellType.TETRA
            
        vis_connectivity = self.element_connectivity[:, :n_vis]
        cells_dict = {vtk_type: vis_connectivity}
        self.grid = pv.UnstructuredGrid(cells_dict, self.node_coords)
        
        self.UIAxes2.add_mesh(self.grid, name='mesh_geom', show_edges=True, color="lightblue", opacity=0.8)
        
        if not hasattr(self.UIAxes2, 'axes_widget_added'):
            self.UIAxes2.add_axes()
            self.UIAxes2.axes_widget_added = True
            
        self.UIAxes2.reset_camera()
        self.UIAxes2.update()
        
        self.MeshinfoTextArea.setText(f"Element Type: {self.element_type}\nTotal nodes: {self.mesh_info['num_nodes']}\nTotal elements: {self.mesh_info['num_elements']}")
        
    def generate_hexa8_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        x = np.linspace(0, Lx, nx + 1); y = np.linspace(0, Ly, ny + 1); z = np.linspace(0, Lz, nz + 1)
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        node_coords = np.column_stack((X.ravel(), Y.ravel(), Z.ravel()))
        
        elems = []
        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    n1 = i*(ny+1)*(nz+1) + j*(nz+1) + k
                    n2 = (i+1)*(ny+1)*(nz+1) + j*(nz+1) + k
                    n3 = (i+1)*(ny+1)*(nz+1) + (j+1)*(nz+1) + k
                    n4 = i*(ny+1)*(nz+1) + (j+1)*(nz+1) + k
                    elems.append([n1, n2, n3, n4, n1+1, n2+1, n3+1, n4+1])
                    
        connectivity = np.array(elems, dtype=int)
        return node_coords, connectivity, {'num_nodes': len(node_coords), 'num_elements': len(connectivity), 'nodes_per_element': 8}

    def generate_hexa20_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        hex8_nodes, hex8_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_hex8 = len(hex8_conn)
        edge_map = {}; mid_node_counter = len(hex8_nodes); mid_nodes_list = []
        connectivity = np.zeros((num_hex8, 20), dtype=int)
        edges = np.array([[0,1], [1,2], [2,3], [3,0], [4,5], [5,6], [6,7], [7,4], [0,4], [1,5], [2,6], [3,7]])
        
        for e in range(num_hex8):
            corners = hex8_conn[e, :]
            mid_nodes = np.zeros(12, dtype=int)
            for edge_idx in range(12):
                n1, n2 = corners[edges[edge_idx, 0]], corners[edges[edge_idx, 1]]
                edge_key = tuple(sorted([n1, n2]))
                if edge_key in edge_map: mid_nodes[edge_idx] = edge_map[edge_key]
                else:
                    mid_nodes_list.append((hex8_nodes[n1] + hex8_nodes[n2]) / 2.0)
                    mid_nodes[edge_idx] = edge_map[edge_key] = mid_node_counter
                    mid_node_counter += 1
            connectivity[e, :8] = corners; connectivity[e, 8:] = mid_nodes
            
        node_coords = np.vstack((hex8_nodes, np.array(mid_nodes_list))) if mid_nodes_list else hex8_nodes
        return node_coords, connectivity, {'num_nodes': len(node_coords), 'num_elements': num_hex8, 'nodes_per_element': 20}

    def generate_tet4_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        hex_nodes, hex_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_hex = len(hex_conn); connectivity = np.zeros((num_hex * 5, 4), dtype=int)
        
        tet_count = 0
        for h in range(num_hex):
            n = hex_conn[h, :]
            tets = [[n[0], n[1], n[3], n[4]], [n[1], n[2], n[3], n[6]], [n[1], n[4], n[5], n[6]], [n[3], n[4], n[6], n[7]], [n[1], n[3], n[4], n[6]]]
            connectivity[tet_count:tet_count+5, :] = tets
            tet_count += 5
            
        return hex_nodes, connectivity, {'num_nodes': len(hex_nodes), 'num_elements': len(connectivity), 'nodes_per_element': 4}

    def generate_tet10_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        tet4_nodes, tet4_conn, _ = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_tet4 = len(tet4_conn)
        edge_map = {}; mid_node_counter = len(tet4_nodes); mid_nodes_list = []
        connectivity = np.zeros((num_tet4, 10), dtype=int)
        edges = np.array([[0,1], [1,2], [0,2], [0,3], [1,3], [2,3]])
        
        for e in range(num_tet4):
            corners = tet4_conn[e, :]
            mid_nodes = np.zeros(6, dtype=int)
            for edge_idx in range(6):
                n1, n2 = corners[edges[edge_idx, 0]], corners[edges[edge_idx, 1]]
                edge_key = tuple(sorted([n1, n2]))
                if edge_key in edge_map: mid_nodes[edge_idx] = edge_map[edge_key]
                else:
                    mid_nodes_list.append((tet4_nodes[n1] + tet4_nodes[n2]) / 2.0)
                    mid_nodes[edge_idx] = edge_map[edge_key] = mid_node_counter
                    mid_node_counter += 1
            connectivity[e, :4] = corners; connectivity[e, 4:] = mid_nodes
            
        node_coords = np.vstack((tet4_nodes, np.array(mid_nodes_list))) if mid_nodes_list else tet4_nodes
        return node_coords, connectivity, {'num_nodes': len(node_coords), 'num_elements': num_tet4, 'nodes_per_element': 10}

    def generate_mesh_3d(self):
        Lx, Ly, Lz = self.geometry['Lx'], self.geometry['Ly'], self.geometry['Lz']
        nx, ny, nz = self.mesh_params['nx'], self.mesh_params['ny'], self.mesh_params['nz']
        
        if self.element_type == 'Hexa8': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Hexa20': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa20_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Tet4': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Tet10': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet10_mesh(Lx, Ly, Lz, nx, ny, nz)
            
        self.mesh_info['element_type'] = self.element_type
   
    def ApplyLoadButtonPushed(self):
      # 1. Explicitly clear old large matrices
        self.K_global = None
        self.B_global = None
        gc.collect() # Manually force Python to free the RAM NOW

        self.lock_ui() 
        try:
            # CRITICAL FIX: Clear OLD ROM data before applying new BC to prevent state contamination
            # This prevents crashes when switching between different boundary conditions repeatedly
            self.Phi = None; self.Phi_stress = None; self.K_rom = None; self.SnapshotMatrix = None
            # Also clear B_global to prevent dense mesh memory bloat during repeated operations
            self.B_global = None
            gc.collect()
            
            if not hasattr(self, 'geometry') or 'Lx' not in self.geometry:
                QMessageBox.warning(None, "Missing Data", "Geometry not found! Please generate the mesh in Tab 1 first.")
                return

            load_pos_meters = (self.LoadPositionSlider.value() / 100.0) * self.geometry['Lx']
            P_val = float(self.LoadValueNEditField.text())
            
            if hasattr(self, 'define_loads_no_bc_3d'): self.loads = self.define_loads_no_bc_3d(self.node_coords)
            else: self.loads = {} 
                 
            if hasattr(self, 'define_loads_at_pos'):
                point_loads = self.define_loads_at_pos(load_pos_meters, P_val)
                self.loads['point_nodes'] = point_loads['point_nodes']
                self.loads['point_load_values'] = point_loads['point_load_values']

            dof_per_node = 3
            num_nodes = self.mesh_info['num_nodes']; num_elements = self.mesh_info['num_elements']
            num_dof = num_nodes * dof_per_node
            
            integration_type = self.settings.get('Integration', 'Full').lower()
            if self.element_type == 'Tet4': num_gp = 1
            elif self.element_type == 'Tet10': num_gp = 4 if integration_type == 'full' else 1
            elif self.element_type == 'Hexa8': num_gp = 8 if integration_type == 'full' else 1
            elif self.element_type == 'Hexa20': num_gp = 27 if integration_type == 'full' else 8
            else: raise ValueError(f"Unknown element type: {self.element_type}")

            nodes_per_elem = self.mesh_info['nodes_per_element']
            entries_per_elem = (nodes_per_elem * dof_per_node)**2
            total_entries = num_elements * entries_per_elem
            entries_per_elemB = 6 * num_gp * (nodes_per_elem * dof_per_node)
            total_entriesB = num_elements * entries_per_elemB
            
            triplet_i = np.zeros(total_entries, dtype=np.int32); triplet_j = np.zeros(total_entries, dtype=np.int32); triplet_val = np.zeros(total_entries)
            self.F_global = np.zeros(num_dof)
            B_triplet_i = np.zeros(total_entriesB, dtype=np.int32); B_triplet_j = np.zeros(total_entriesB, dtype=np.int32); B_triplet_val = np.zeros(total_entriesB)

            curr_idx = 0; curr_idx_B = 0
            self.MatrixSizeTextArea.setText("Assembling...")
            QApplication.processEvents()
            
            for e in range(num_elements):
                element_nodes = self.element_connectivity[e, :]
                elem_coords = self.node_coords[element_nodes, :]
                
                elem_loads = self.prepare_element_loads_3d(self.loads, e, element_nodes, self.element_type) if hasattr(self, 'prepare_element_loads_3d') else {}
                Ke, Fe, self.D_mat, Be_all = self.compute_element_matrices_3d(self.element_type, elem_coords, elem_loads, self.settings)
                
                loc_array = np.repeat(element_nodes, 3) * 3 + np.tile([0, 1, 2], nodes_per_elem)
                rows, cols = np.meshgrid(loc_array, loc_array, indexing='ij')
                
                next_idx = curr_idx + entries_per_elem
                triplet_i[curr_idx:next_idx] = rows.ravel(); triplet_j[curr_idx:next_idx] = cols.ravel(); triplet_val[curr_idx:next_idx] = Ke.ravel()
                curr_idx = next_idx
                
                for g in range(num_gp):
                    row_start = (e * num_gp + g) * 6
                    global_rows = row_start + np.arange(6)
                    Be_gp = Be_all[g*6 : (g+1)*6, :]
                    mesh_R, mesh_C = np.meshgrid(global_rows, loc_array, indexing='ij')
                    num_vals = 6 * len(loc_array)
                    next_idx_B = curr_idx_B + num_vals
                    
                    B_triplet_i[curr_idx_B:next_idx_B] = mesh_R.ravel(); B_triplet_j[curr_idx_B:next_idx_B] = mesh_C.ravel(); B_triplet_val[curr_idx_B:next_idx_B] = Be_gp.ravel()
                    curr_idx_B = next_idx_B
                    
                self.F_global[loc_array] += Fe

            self.K_global = sp.coo_matrix((triplet_val, (triplet_i, triplet_j)), shape=(num_dof, num_dof)).tocsc()
            del triplet_i, triplet_j, triplet_val
            
            total_B_rows = num_elements * num_gp * 6
            self.B_global = sp.coo_matrix((B_triplet_val, (B_triplet_i, B_triplet_j)), shape=(total_B_rows, num_dof)).tocsc()
            del B_triplet_i, B_triplet_j, B_triplet_val

            if 'point_nodes' in self.loads and len(self.loads['point_nodes']) > 0:
                for i, node_id in enumerate(self.loads['point_nodes']):
                    force_vec = self.loads['point_load_values'][:, i]
                    dof_indices = int(node_id) * 3 + np.array([0, 1, 2])
                    self.F_global[dof_indices] += force_vec

            self.MatrixSizeTextArea.setText(f"Total dof: {num_dof} x {num_dof}")

            self.beam_type = self.BeamTypeDropDown.currentText()
            if hasattr(self, 'boundary_conditions'):
                self.K_reduced, self.F_reduced, fixed_dofs, free_dofs = self.boundary_conditions(self.K_global, self.F_global, self.node_coords, self.beam_type)
            else:
                fixed_dofs = np.array([]); free_dofs = np.arange(num_dof)
                self.K_reduced = self.K_global; self.F_reduced = self.F_global

            self.bc_info = {'total_dofs': num_dof, 'fixed_dofs': len(fixed_dofs), 'free_dofs': len(free_dofs),
                            'fixed_dofs_indices': fixed_dofs, 'free_dofs_indices': free_dofs, 'fixed_dofs_values': np.zeros(len(fixed_dofs))}

            if hasattr(self, 'visualize_BC_3d'):
                self.visualize_BC_3d(self.node_coords, self.element_connectivity, self.element_type, self.mesh_info, self.bc_info, self.F_global, self.UIAxes3)
                
            if hasattr(self, 'update_load_bar_chart'):
                self.update_load_bar_chart(self.F_global, self.UIAxes4)
                
        except Exception as e:
            error_msg = f"Crash Prevented!\n\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(None, "Application Error", error_msg)
        finally:
            self.unlock_ui() 
                
    def define_loads_no_bc_3d(self, node_coords):
        loads = {}
        if hasattr(self, 'GravitationalForceSwitch') and self.GravitationalForceSwitch.isChecked(): loads['BodyForceDir'] = np.array([0, 0, -9.81])
        else: loads['BodyForceDir'] = np.array([0, 0, 0])
        loads['traction_nodes'] = []
        loads['surface_traction_value'] = np.array([0, 0, 0])
        return loads

    def prepare_element_loads_3d(self, loads, e, element_nodes, element_type):
        elem_loads = {'BodyForceDir': [], 'SurfaceFaceID': [], 'SurfaceTraction': []}
        if 'BodyForceDir' in loads: elem_loads['BodyForceDir'] = loads['BodyForceDir']
        
        elem_type_lower = element_type.lower()
        if elem_type_lower == 'hexa8': face_defs = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        elif elem_type_lower == 'hexa20': face_defs = [[0, 3, 2, 1, 11, 10, 9, 8], [4, 5, 6, 7, 12, 13, 14, 15], [0, 1, 5, 4, 8, 17, 12, 16], [1, 2, 6, 5, 9, 18, 13, 17], [2, 3, 7, 6, 10, 19, 14, 18], [3, 0, 4, 7, 11, 16, 15, 19]]
        elif elem_type_lower in ['tet4', 'tet10']: face_defs = [[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]]
        else: raise ValueError(f'Element type {element_type} not supported')
            
        if 'traction_nodes' in loads and len(loads['traction_nodes']) > 0:
            for i, local_indices in enumerate(face_defs):
                global_nodes_on_face = element_nodes[local_indices]
                if np.all(np.isin(global_nodes_on_face, loads['traction_nodes'])):
                    elem_loads['SurfaceFaceID'].append(local_indices)
                    elem_loads['SurfaceTraction'].append(loads['surface_traction_value'])
                    
        return elem_loads
    
    def compute_element_matrices_3d(self, element_type, elem_coords, elem_loads, settings):
        type_lower = element_type.lower()
        if type_lower == 'tet4': Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Tet4_Element_Routine(self.material, elem_coords, elem_loads, settings)
        elif type_lower == 'tet10': Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Tet10_Element_Routine(self.material, elem_coords, elem_loads, settings)
        elif type_lower == 'hexa8': Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Hexa8_Element_Routine(self.material, elem_coords, elem_loads, settings)
        elif type_lower == 'hexa20': Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Hexa20_Element_Routine(self.material, elem_coords, elem_loads, settings)
        else: raise ValueError(f'Element type "{element_type}" not recognized.')
        return Ke, F_total, D, Be_all     

    def Hexa8_Element_Routine(self, Material, Coord, Loads, Settings):
        Ke = np.zeros((24, 24)); Fb = np.zeros(24); Fs = np.zeros(24); Fl = np.zeros(24)
        Em = Material['E']; nu = Material['nu']
        D_const = Em / ((1 + nu) * (1 - 2 * nu))
        D = D_const * np.array([
            [1-nu, nu,   nu,   0, 0, 0],
            [nu,   1-nu, nu,   0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        
        n_order = 2 if Settings.get('Integration', '').lower() == 'full' else 1
        gpts, gwts = self.GetGaussTable(n_order) 
        num_gp = n_order**3
        Be_all = np.zeros((6 * num_gp, 24))
        gp_count = 0
        
        for i in range(n_order):
            for j in range(n_order):
                for k in range(n_order):
                    xi, eta, zeta = gpts[i], gpts[j], gpts[k]; w = gwts[i] * gwts[j] * gwts[k]
                    N, dN_dxi, dN_deta, dN_dzeta = self.Hexa8_ShapeFunctions(xi, eta, zeta)
                    nat_derivs = np.vstack([dN_dxi, dN_deta, dN_dzeta])
                    J = nat_derivs @ Coord
                    detJ = max(np.linalg.det(J), 1e-12) 
                    dN_xyz = np.linalg.solve(J, nat_derivs)
                    
                    B = np.zeros((6, 24))
                    for n in range(8):
                        idx = n * 3; dx, dy, dz = dN_xyz[0, n], dN_xyz[1, n], dN_xyz[2, n]
                        B[0, idx]   = dx; B[1, idx+1] = dy; B[2, idx+2] = dz
                        B[3, idx:idx+2] = [dy, dx]; B[4, idx+1:idx+3] = [dz, dy]; B[5, [idx, idx+2]] = [dz, dx]
                        
                    row_idx = gp_count * 6; Be_all[row_idx:row_idx+6, :] = B
                    Ke += (B.T @ D @ B) * detJ * w
                    
                    if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                        b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                        N_mat = np.zeros((3, 24))
                        for n in range(8):
                            col = n * 3
                            N_mat[0, col] = N[n]; N_mat[1, col+1] = N[n]; N_mat[2, col+2] = N[n]
                        Fb += (N_mat.T @ b_vec) * detJ * w
                        
                    gp_count += 1
                    
        F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, D, Be_all
    
    def Hexa8_ShapeFunctions(self, xi, eta, zeta):
        xi_m = np.array([-1, 1, 1, -1, -1, 1, 1, -1]); eta_m = np.array([-1, -1, 1, 1, -1, -1, 1, 1]); zeta_m = np.array([-1, -1, -1, -1, 1, 1, 1, 1])
        N = 0.125 * (1 + xi*xi_m) * (1 + eta*eta_m) * (1 + zeta*zeta_m)
        dN_dxi = 0.125 * xi_m * (1 + eta*eta_m) * (1 + zeta*zeta_m)
        dN_deta = 0.125 * eta_m * (1 + xi*xi_m) * (1 + zeta*zeta_m)
        dN_dzeta = 0.125 * zeta_m * (1 + xi*xi_m) * (1 + eta*eta_m)
        return N, dN_dxi, dN_deta, dN_dzeta

    def Tet10_Element_Routine(self, Material, Coord, Loads, Settings):
        E, nu = Material['E'], Material['nu']
        lambda_val = E*nu/((1+nu)*(1-2*nu)); mu = E/(2*(1+nu))
        C = np.zeros((6, 6)); C[0:3, 0:3] = lambda_val
        for i in range(3): C[i, i] = lambda_val + 2*mu
        C[3, 3] = C[4, 4] = C[5, 5] = mu
        
        nGauss_vol = 4 if Settings.get('Integration', '').lower() == 'full' else 1  
        Be_all = np.zeros((6 * nGauss_vol, 30))
        g_pts, g_w = self.GetGaussTableTetrahedra(nGauss_vol) 
        Ke = np.zeros((30, 30)); Fb = np.zeros(30); Vol_Scale = 1.0 / 6.0 
        
        for ig in range(nGauss_vol):
            xi, eta, zeta = g_pts[ig, 0], g_pts[ig, 1], g_pts[ig, 2]
            L4 = 1 - xi - eta - zeta; w = g_w[ig] * Vol_Scale
            N, dN_nat = self.Tet10_ShapeFunctions(xi, eta, zeta, L4)
            J = dN_nat.T @ Coord
            detJ = abs(np.linalg.det(J)); dN_dx = dN_nat @ np.linalg.inv(J).T 
            
            B = np.zeros((6, 30))
            for i in range(10):
                c = i * 3; dx, dy, dz = dN_dx[i, 0], dN_dx[i, 1], dN_dx[i, 2]
                B[0, c]   = dx; B[1, c+1] = dy; B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]; B[4, c+1:c+3] = [dz, dy]; B[5, [c, c+2]] = [dz, dx]
                
            row_idx = ig * 6; Be_all[row_idx:row_idx+6, :] = B
            dV = detJ * w; Ke += (B.T @ C @ B) * dV
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for i in range(10):
                    idx = i * 3; Fb[idx:idx+3] += N[i] * b_vec * dV
                    
        Fs = np.zeros(30); Fl = np.zeros(30); F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, C, Be_all
    
    def Tet10_ShapeFunctions(self, xi, eta, zeta, L4):
        N = np.array([
            L4*(2*L4-1), xi*(2*xi-1), eta*(2*eta-1), zeta*(2*zeta-1), 
            4*L4*xi, 4*xi*eta, 4*eta*L4, 4*L4*zeta, 4*xi*zeta, 4*eta*zeta 
        ])
        dN_nat = np.zeros((10, 3))
        dN_nat[0, :] = -(4*L4-1); dN_nat[1, 0] = 4*xi-1; dN_nat[2, 1] = 4*eta-1; dN_nat[3, 2] = 4*zeta-1
        dN_nat[4, :] = [4*(L4-xi), -4*xi, -4*xi]
        dN_nat[5, :] = [4*eta, 4*xi, 0]
        dN_nat[6, :] = [-4*eta, 4*(L4-eta), -4*eta]
        dN_nat[7, :] = [-4*zeta, -4*zeta, 4*(L4-zeta)]
        dN_nat[8, :] = [4*zeta, 0, 4*xi]
        dN_nat[9, :] = [0, 4*zeta, 4*eta]
        return N, dN_nat
    
    def Tet4_Element_Routine(self, Material, Coord, Loads, Settings):
        E = Material['E']; nu = Material['nu']
        lambda_val = E * nu / ((1 + nu) * (1 - 2 * nu)); mu = E / (2 * (1 + nu))
        C = np.zeros((6, 6)); C[0:3, 0:3] = lambda_val
        for i in range(3): C[i, i] = lambda_val + 2 * mu
        C[3, 3] = C[4, 4] = C[5, 5] = mu
        
        g_pts, g_w = self.GetGaussTableTetrahedra(1)
        Ke = np.zeros((12, 12)); Fb = np.zeros(12); Be_all = np.zeros((6, 12))
        
        for ig in range(len(g_w)):
            xi = g_pts[ig, 0]; eta = g_pts[ig, 1]; zeta = g_pts[ig, 2]; w = g_w[ig] * (1.0 / 6.0)
            N = np.array([1 - xi - eta - zeta, xi, eta, zeta])
            dN_nat = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
            J = dN_nat.T @ Coord; detJ = abs(np.linalg.det(J)); dN_dx = dN_nat @ np.linalg.inv(J).T 
            
            B = np.zeros((6, 12))
            for i in range(4):
                c = i * 3; dx, dy, dz = dN_dx[i, 0], dN_dx[i, 1], dN_dx[i, 2]
                B[0, c]   = dx; B[1, c+1] = dy; B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]; B[4, c+1:c+3] = [dz, dy]; B[5, [c, c+2]] = [dz, dx]
                
            Be_all[0:6, :] = B; Ke += (B.T @ C @ B) * detJ * w
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for n in range(4):
                    idx = n * 3; Fb[idx:idx+3] += N[n] * b_vec * detJ * w
                    
        Fs = np.zeros(12); Fl = np.zeros(12); F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, C, Be_all

    def Hexa20_Element_Routine(self, Material, Coord, Loads, Settings):
        E = Material['E']; nu = Material['nu']
        D_const = E / ((1 + nu) * (1 - 2 * nu))
        D = D_const * np.array([
            [1-nu, nu,   nu,   0, 0, 0],
            [nu,   1-nu, nu,   0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        
        Ke = np.zeros((60, 60)); Fb = np.zeros(60)
        n_order = 3 if Settings.get('Integration', '').lower() == 'full' else 2
        g_pts, g_w = self.BuildHexaGauss(n_order)
        num_gp = n_order**3
        Be_all = np.zeros((6 * num_gp, 60)); gp_count = 0
        
        for ig in range(g_pts.shape[0]):
            xi, eta, zeta = g_pts[ig, 0], g_pts[ig, 1], g_pts[ig, 2]; w = g_w[ig]
            N, dN_dxi, dN_deta, dN_dzeta = self.Hexa20_ShapeFunctions(xi, eta, zeta)
            nat_derivs = np.column_stack((dN_dxi, dN_deta, dN_dzeta)) 
            J = nat_derivs.T @ Coord
            
            detJ = np.linalg.det(J)
            if abs(detJ) < 1e-12: detJ = 1e-12 if detJ >= 0 else -1e-12
            dN_dx = nat_derivs @ np.linalg.inv(J)
            
            B = np.zeros((6, 60))
            for n in range(20):
                c = n * 3; dx, dy, dz = dN_dx[n, 0], dN_dx[n, 1], dN_dx[n, 2]
                B[0, c]   = dx; B[1, c+1] = dy; B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]; B[4, c+1:c+3] = [dz, dy]; B[5, [c, c+2]] = [dz, dx]
                
            row_idx = gp_count * 6; Be_all[row_idx:row_idx+6, :] = B
            Ke += (B.T @ D @ B) * detJ * w
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for n in range(20):
                    idx = n * 3; Fb[idx:idx+3] += N[n] * b_vec * detJ * w
                    
            gp_count += 1
            
        Fs = np.zeros(60); Fl = np.zeros(60); F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, D, Be_all
    
    def Hexa20_ShapeFunctions(self, xi, eta, zeta):
        N = np.zeros(20); dN_dxi = np.zeros(20); dN_deta = np.zeros(20); dN_dzeta = np.zeros(20)
        pts = np.array([[-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1], [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1]])
        ri = pts[:, 0]; si = pts[:, 1]; ti = pts[:, 2]
        
        val = (1 + xi*ri) * (1 + eta*si) * (1 + zeta*ti)
        N[:8] = 0.125 * val * (xi*ri + eta*si + zeta*ti - 2)
        dN_dxi[:8]   = 0.125 * ri * (1+eta*si)*(1+zeta*ti) * (2*xi*ri + eta*si + zeta*ti - 1)
        dN_deta[:8]  = 0.125 * si * (1+xi*ri)*(1+zeta*ti)  * (xi*ri + 2*eta*si + zeta*ti - 1)
        dN_dzeta[:8] = 0.125 * ti * (1+xi*ri)*(1+eta*si)   * (xi*ri + eta*si + 2*zeta*ti - 1)
        
        mid_coords = np.array([
            [ 0, -1, -1], [ 1,  0, -1], [ 0,  1, -1], [-1,  0, -1],
            [ 0, -1,  1], [ 1,  0,  1], [ 0,  1,  1], [-1,  0,  1],
            [-1, -1,  0], [ 1, -1,  0], [ 1,  1,  0], [-1,  1,  0] 
        ])
        
        for k in range(12):
            id_val = k + 8; ri_m, si_m, ti_m = mid_coords[k]
            if ri_m == 0: 
                N[id_val]        = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_dxi[id_val]   = 0.25 * (-2*xi)     * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_deta[id_val]  = 0.25 * (1 - xi**2) * (si_m)         * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (ti_m)
            elif si_m == 0: 
                N[id_val]        = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (1 + zeta*ti_m)
                dN_dxi[id_val]   = 0.25 * (ri_m)        * (1 - eta**2) * (1 + zeta*ti_m)
                dN_deta[id_val]  = 0.25 * (1 + xi*ri_m) * (-2*eta)     * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (ti_m)
            elif ti_m == 0: 
                N[id_val]        = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (1 - zeta**2)
                dN_dxi[id_val]   = 0.25 * (ri_m)        * (1 + eta*si_m) * (1 - zeta**2)
                dN_deta[id_val]  = 0.25 * (1 + xi*ri_m) * (si_m)         * (1 - zeta**2)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (-2*zeta)
        return N, dN_dxi, dN_deta, dN_dzeta
    
    def define_loads_at_pos(self, target_x, P_val):
        X = self.node_coords[:, 0]; Z = self.node_coords[:, 2] 
        tol = 1e-8; max_z = np.max(Z)
        unique_x = np.unique(X); diffs = target_x - unique_x
        
        left_mask = np.where(diffs >= -tol)[0]
        left_idx = left_mask[-1] if len(left_mask) > 0 else 0
        right_mask = np.where(diffs <= tol)[0]
        right_idx = right_mask[0] if len(right_mask) > 0 else len(unique_x) - 1
        
        loads = {}
        if left_idx == right_idx:
            x_val = unique_x[left_idx]
            point_nodes = np.where((np.abs(X - x_val) < tol) & (np.abs(Z - max_z) < tol))[0]
            num_n = len(point_nodes)
            point_load_values = np.zeros((3, num_n))
            if num_n > 0: point_load_values[2, :] = P_val / num_n 
            loads['point_nodes'] = point_nodes; loads['point_load_values'] = point_load_values
        else:
            x_L = unique_x[left_idx]; x_R = unique_x[right_idx]
            ratio_R = (target_x - x_L) / (x_R - x_L); ratio_L = 1.0 - ratio_R
            nodes_L = np.where((np.abs(X - x_L) < tol) & (np.abs(Z - max_z) < tol))[0]
            nodes_R = np.where((np.abs(X - x_R) < tol) & (np.abs(Z - max_z) < tol))[0]
            loads['point_nodes'] = np.concatenate((nodes_L, nodes_R))
            
            num_L = len(nodes_L); num_R = len(nodes_R)
            val_L = (P_val * ratio_L) / num_L if num_L > 0 else 0
            val_R = (P_val * ratio_R) / num_R if num_R > 0 else 0
            
            load_vecs_L = np.zeros((3, num_L))
            if num_L > 0: load_vecs_L[2, :] = val_L
            load_vecs_R = np.zeros((3, num_R))
            if num_R > 0: load_vecs_R[2, :] = val_R
            loads['point_load_values'] = np.hstack((load_vecs_L, load_vecs_R))
        return loads
    
    def boundary_conditions(self, K_global, F_global, node_coords, beam_type):
        tol = 1e-5; X = node_coords[:, 0]; Z = node_coords[:, 2]
        x_min = np.min(X); x_max = np.max(X); z_min = np.min(Z)
        
        if 'cantilever' in beam_type.lower():
            fixed_nodes = np.where(np.abs(X - x_min) < tol)[0]
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
        elif 'fixed' in beam_type.lower():
            fixed_nodes = np.where((np.abs(X - x_min) < tol) | (np.abs(X - x_max) < tol))[0]
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
        else:
            left_edge_nodes = np.where((np.abs(X - x_min) < tol) & (np.abs(Z - z_min) < tol))[0]
            right_edge_nodes = np.where((np.abs(X - x_max) < tol) & (np.abs(Z - z_min) < tol))[0]
            pin_dofs = np.repeat(left_edge_nodes, 3) * 3 + np.tile([0, 1, 2], len(left_edge_nodes))
            roller_dofs = np.repeat(right_edge_nodes, 2) * 3 + np.tile([1, 2], len(right_edge_nodes))
            fixed_dofs = np.concatenate((pin_dofs, roller_dofs))
            
        fixed_dofs = np.unique(fixed_dofs).astype(int)
        num_total = K_global.shape[0]
        free_dofs = np.setdiff1d(np.arange(num_total), fixed_dofs)
        
        # CRITICAL FIX: Handle sparse matrix extraction correctly
        if sp.issparse(K_global):
            K_global_csr = K_global.tocsr()
            K_reduced = K_global_csr[free_dofs, :][:, free_dofs].tocsr()
        else:
            K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        
        F_reduced = F_global[free_dofs]
        
        print(f"   BC Applied ({beam_type}): {len(fixed_dofs)} DOFs fixed. Reduced system: {K_reduced.shape[0]} x {K_reduced.shape[1]}")
        return K_reduced, F_reduced, fixed_dofs, free_dofs
        
    def visualize_BC_3d(self, node_coords, element_connectivity, element_type, mesh_info, bc_info, F_global, targetAxes):
        F_nodes = F_global.reshape(-1, 3); load_mag = np.linalg.norm(F_nodes, axis=1)
        max_load = np.max(load_mag)
        applied_idx = np.where(load_mag > max_load * 0.01)[0] if max_load > 0 else np.array([])
            
        bbox_min = np.min(node_coords, axis=0); bbox_max = np.max(node_coords, axis=0)
        diagonal = np.linalg.norm(bbox_max - bbox_min)
        sphere_radius = diagonal * 0.015; arrow_scale = diagonal * 0.15 
            
        if 'Hexa' in element_type: n_vis = 8; vtk_type = pv.CellType.HEXAHEDRON
        else: n_vis = 4; vtk_type = pv.CellType.TETRA
            
        vis_connectivity = element_connectivity[:, :n_vis]; grid = pv.UnstructuredGrid({vtk_type: vis_connectivity}, node_coords)
        targetAxes.add_mesh(grid, name='bc_base_mesh', show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        targetAxes.add_mesh(grid, show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        
        fixed_dofs = np.array(bc_info.get('fixed_dofs_indices', []))
        if len(fixed_dofs) > 0:
            fixed_nodes = np.unique(fixed_dofs // 3)
            fixed_coords = np.atleast_2d(node_coords[fixed_nodes])
            
            # --- CRASH FIX: scale=False, orient=False ---
            spheres = pv.PolyData(fixed_coords).glyph(
                geom=pv.Sphere(radius=sphere_radius),
                scale=False,
                orient=False
            )
            
            targetAxes.add_mesh(spheres, name='bc_fixed_dofs', color="red", show_edges=True, edge_color="black") 
        else:
            try: targetAxes.remove_actor('bc_fixed_dofs')
            except: pass
            targetAxes.add_mesh(spheres, color="red", show_edges=True, edge_color="black") 
            
        if len(applied_idx) > 0:
            load_coords = np.atleast_2d(node_coords[applied_idx]); load_vectors = np.atleast_2d(F_nodes[applied_idx])
            mags = load_mag[applied_idx]; load_dirs = load_vectors / mags[:, np.newaxis]
            cloud = pv.PolyData(load_coords); cloud["vectors"] = load_dirs * arrow_scale
            arrows = cloud.glyph(orient="vectors", scale="vectors", factor=1.0, geom=pv.Arrow())
            targetAxes.add_mesh(arrows, name='bc_force_arrows', color="blue")
        else:
            try: targetAxes.remove_actor('bc_force_arrows')
            except: pass
            targetAxes.add_mesh(arrows, color="blue")

        if not hasattr(targetAxes, 'axes_widget_added'):
            targetAxes.add_axes(); targetAxes.axes_widget_added = True
            
        targetAxes.view_isometric(); targetAxes.reset_camera(); targetAxes.update()

    def update_load_bar_chart(self, F_global, targetAxes):
        targetAxes.clear() 
        Fz = F_global[2::3]; load_mag = np.abs(Fz) 
        
        max_load = np.max(load_mag) if len(load_mag) > 0 else 0
        applied_idx = np.where(load_mag > (max_load * 0.01))[0]
        
        if len(applied_idx) > 0:
            forces_kN = load_mag[applied_idx] / 1000.0
            targetAxes.bar(applied_idx, forces_kN, color=[0.2, 0.6, 0.8])
            
            total_kN = np.sum(forces_kN)
            targetAxes.axhline(total_kN, color='red', linestyle='--', linewidth=2)
            
            x_min = np.min(applied_idx)
            targetAxes.text(x_min, total_kN * 1.02, f'Total: {total_kN:.2f} kN', color='red', verticalalignment='bottom')
            
            targetAxes.grid(True, linestyle='--', alpha=0.6)
            targetAxes.set_xlabel('Global Node ID'); targetAxes.set_ylabel('Vertical Force (kN)')
            targetAxes.set_title(r'$\bf{Nodal\ Load\ Distribution\ (Lever\ Rule\ Check)}$')
            targetAxes.set_ylim([0, total_kN * 1.2])
            
            from matplotlib.ticker import MaxNLocator
            targetAxes.xaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            targetAxes.set_title('No Significant Point Loads Applied')
            
        fig = targetAxes.figure; fig.tight_layout()
        if hasattr(fig, 'canvas'): fig.canvas.draw_idle()

    def GetGaussTable(self, N):
        if N == 2: loc = np.array([-0.57735026919, 0.57735026919]); w = np.array([1.0, 1.0])
        elif N == 3: loc = np.array([-0.774596669, 0.0, 0.774596669]); w = np.array([0.555555556, 0.888888889, 0.555555556])
        else: loc = np.array([0.0]); w = np.array([2.0])
        return loc, w

    def BuildHexaGauss(self, N):
        loc1, w1 = self.GetGaussTable(N)
        X, Y, Z = np.meshgrid(loc1, loc1, loc1, indexing='ij'); WX, WY, WZ = np.meshgrid(w1, w1, w1, indexing='ij')
        loc3 = np.column_stack((X.ravel(order='F'), Y.ravel(order='F'), Z.ravel(order='F')))
        w3 = (WX * WY * WZ).ravel(order='F')
        return loc3, w3

    def GetGaussTableTetrahedra(self, n):
        if n == 1: g_pts = np.array([[0.25, 0.25, 0.25]]); g_w = np.array([1.0])
        else:
            a = 0.58541020; b = 0.13819660
            g_pts = np.array([[a, b, b], [b, a, b], [b, b, a], [b, b, b]]); g_w = np.array([0.25, 0.25, 0.25, 0.25])
        return g_pts, g_w

    def SolveButtonPushed(self):

        self.lock_ui()
        try:
            if not hasattr(self, 'K_reduced') or not hasattr(self, 'F_reduced'):
                self.ComputationalInfromationTextArea.setText("Error: Please apply Boundary Conditions first.")
                return

            # Show progress dialog for FEM solving
            progress = QProgressDialog("Solving FEM System...", "Cancel", 0, 0, self)
            progress.setWindowTitle("FEM Solver")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setStyleSheet("QProgressDialog { background-color: white; }")
            progress.show()
            QApplication.processEvents()
            
            solve_start = time.perf_counter()
            U_free = spsolve(self.K_reduced.tocsr(), self.F_reduced) 
            solve_cpu_time = time.perf_counter() - solve_start
            progress.close()
            
            num_dof = self.K_global.shape[0]
            self.U_full = np.zeros(num_dof)
            free_idx = self.bc_info['free_dofs_indices']
            self.U_full[free_idx] = U_free

            reactions_full = self.K_global.dot(self.U_full) - self.F_global
            fixed_idx = self.bc_info['fixed_dofs_indices']
            reaction_forces = reactions_full[fixed_idx]
            
            total_applied = np.sum(self.F_global); total_reaction = np.sum(reaction_forces)
            equilibrium_error = abs(total_applied + total_reaction)
            
            norm_F = np.linalg.norm(self.F_global)
            if norm_F != 0 and (equilibrium_error / norm_F < 1e-5): eq_status = '✓ Equilibrium Satisfied'
            elif norm_F == 0 and equilibrium_error < 1e-6: eq_status = '✓ Equilibrium Satisfied (Zero Load)'
            else: eq_status = '⚠ Equilibrium Error Detected'

            summary_text = (
                "--- SOLVER SUMMARY ---\n"
                f"CPU Solve Time: {solve_cpu_time:.4f} seconds\n"
                f"Max Displacement: {np.max(np.abs(self.U_full)) * 1000.0:.4f} mm\n\n"
                "--- REACTION CHECK ---\n"
                f"Total Applied Force: {total_applied:.3e} N\n"
                f"Total Reaction Force: {total_reaction:.3e} N\n"
                f"Equilibrium Error: {equilibrium_error:.3e} N\n"
                f"{eq_status}"
            )
            self.ComputationalInfromationTextArea.setText(summary_text)
        except Exception as e:
            QMessageBox.critical(None, "Solver Error", f"Error during solve:\n{str(e)}\n\n{traceback.format_exc()}")
        finally:
            self.unlock_ui()

    def get_status_flag(self, error_val):
        if error_val < 5: return '✓ PASS (Excellent Agreement)'
        elif error_val < 15: return '⚠ CAUTION (Convergence Required)'
        else: return '✗ FAIL (Check Mesh/Units)'    

    def ValidationwithEulierBernoullisBeamTheoryButtonPushed(self):
        self.lock_ui() 
        try:
            # 1. PRE-VALIDATION CHECKS & MEMORY CLEANUP
            if not hasattr(self, 'U_full') or self.U_full is None:
                QMessageBox.warning(self, "Solve Required", "Please solve the 3D FEM model first!")
                return
            
            # Prevent Memory Leak: Clear old validation stress before calculating new one
            self.Sigma_Final2 = None 
            import gc
            gc.collect()

            # 2. PHYSICS INPUTS (SI UNITS)
            L = self.geometry['Lx']
            b = self.geometry['Ly']
            h = self.geometry['Lz']
            E = self.material['E']
            
            # Parse Load
            try:
                P = float(self.LoadValueNEditField.text()) 
            except ValueError:
                P = 0.0
                
            a = (self.LoadPositionSlider.value() / 100.0) * L 
            rho = self.material['rho']
            g_vec = self.loads.get('BodyForceDir', [0, 0, 0])
            g = g_vec[2] if len(g_vec) > 2 else 0.0
            
            # Cross-section properties
            I = (b * h**3) / 12.0
            A = b * h
            q = -(A * rho * g) 
            
            # 3. ANALYTICAL SOLVE (1D)
            if hasattr(self, 'compute_1D_Analytical'):
                x_1d, u_1d, s_bending_1d, s_shear_1d, _, _ = self.compute_1D_Analytical(L, a, P, E, I, q, h)
            else:
                raise AttributeError("Method 'compute_1D_Analytical' not found.")
                
            # 4. STRESS RECONSTRUCTION (3D FOM)
            # Use 'name' tags in plotting functions downstream to prevent OOM
            solve_start = time.perf_counter()
            if hasattr(self, 'PostProcess_Stress_3Dsparse'):
                # Ensure B_global exists before calling
                if not hasattr(self, 'B_global') or self.B_global is None:
                    raise ValueError("Stiffness/B-matrix missing. Re-apply loads/BC.")
                    
                self.Sigma_Final2 = self.PostProcess_Stress_3Dsparse(
                    self.B_global, self.D_mat, self.U_full, 
                    self.node_coords, self.element_connectivity, self.element_type
                )
            else:
                raise AttributeError("Method 'PostProcess_Stress_3Dsparse' not found.")
                
            solve_cpu_time1 = time.perf_counter() - solve_start
            
            # 5. DATA EXTRACTION
            if hasattr(self, 'extract_3D_results'):
                _, u_3d_z, s_bending_3d, s_shear_3d = self.extract_3D_results()
            else:
                raise AttributeError("Method 'extract_3D_results' not found.")

            # 6. STABLE RENDERING (Checks for plotters)
            if hasattr(self, 'plot_1D_Validation') and hasattr(self, 'canvas_1d_validation'):
                self.plot_1D_Validation(x_1d, u_1d, s_bending_1d, s_shear_1d, self.canvas_1d_validation)
            
            if hasattr(self, 'plot_3D_Validation') and hasattr(self, 'UIAxes_3D_Validation'):
                # Ensure the plotter isn't closed
                self.plot_3D_Validation(self.UIAxes_3D_Validation)
            
            if hasattr(self, 'update_Validation_Summary'):
                # Pass results to the summary area
                self.update_Validation_Summary(
                    u_1d, u_3d_z, s_bending_1d, s_bending_3d, 
                    s_shear_1d, s_shear_3d, solve_cpu_time1, self.ValidationSummaryTextArea
                )

        except Exception as e:
            error_trace = traceback.format_exc()
            print(error_trace)
            QMessageBox.critical(self, "Validation Error", f"An error occurred:\n{str(e)}")
        finally:
            self.unlock_ui()
            gc.collect() # Final MATLAB-style cleanup

    def compute_1D_Analytical(self, L, a, P, E, I, q, h):
        EI = E * I; A = self.geometry['Ly'] * h; G = E / (2 * (1 + self.material['nu'])); k_shear = 5.0 / 6.0 
        x_vals = np.linspace(0, L, 100); y_vals = np.zeros(100); M_vals = np.zeros(100); V_vals = np.zeros(100)
        b_dist = L - a; current_beam = self.BeamTypeDropDown.currentText().lower()
        
        left_mask = x_vals <= a; right_mask = x_vals > a
        x_L = x_vals[left_mask]; x_R = x_vals[right_mask]
        
        if 'cantilever' in current_beam:
            y_vals[left_mask] = (P * x_L**2) / (6 * EI) * (3*a - x_L); M_vals[left_mask] = P * (a - x_L); V_vals[left_mask] = P
            y_vals[right_mask] = (P * a**2) / (6 * EI) * (3*x_R - a); M_vals[right_mask] = 0.0; V_vals[right_mask] = 0.0
        elif 'fixed' in current_beam:
            R1 = P * b_dist**2 * (3*a + b_dist) / L**3; M1 = -P * a * b_dist**2 / L**2
            y_vals[left_mask] = (P * b_dist**2 * x_L**2) / (6 * EI * L**3) * (3*a*L - (3*a + b_dist)*x_L); M_vals[left_mask] = M1 + R1 * x_L; V_vals[left_mask] = R1
            y_vals[right_mask] = (P * a**2 * (L - x_R)**2) / (6 * EI * L**3) * (3*b_dist*L - (3*b_dist + a)*(L - x_R)); M_vals[right_mask] = M1 + R1 * x_R - P * (x_R - a); V_vals[right_mask] = R1 - P
        else:
            y_vals[left_mask] = (P * b_dist * x_L) / (6 * L * EI) * (L**2 - b_dist**2 - x_L**2); M_vals[left_mask] = (P * b_dist / L) * x_L; V_vals[left_mask] = P * b_dist / L
            y_vals[right_mask] = (P * a * (L - x_R)) / (6 * L * EI) * (L**2 - a**2 - (L - x_R)**2); M_vals[right_mask] = (P * a / L) * (L - x_R); V_vals[right_mask] = -P * a / L
            
        y_shear = cumulative_trapezoid(V_vals, x_vals, initial=0) / (k_shear * G * A)
        if 'fix' in current_beam or 'support' in current_beam: drift = np.linspace(0, y_shear[-1], len(x_vals)); y_shear = y_shear - drift
            
        y_vals = y_vals + y_shear
        S_bend_vals = (np.abs(M_vals) * (h / 2.0)) / I; S_shear_vals = (3.0 * np.abs(V_vals)) / (2.0 * A)
        S_bend_max = (np.max(np.abs(M_vals)) * (h / 2.0)) / I; S_shear_max = (3.0 * np.max(np.abs(V_vals))) / (2.0 * A)
        return x_vals, y_vals, S_bend_vals, S_shear_vals, S_bend_max, S_shear_max

    def PostProcess_Stress_3Dsparse(self, B_global, D, U_global, Coords, Connectivity, ElementType):
        Num_Nodes = Coords.shape[0]; Num_Elem = Connectivity.shape[0]
        total_B_rows = B_global.shape[0]; num_gp = total_B_rows // (6 * Num_Elem)
        if total_B_rows % (6 * Num_Elem) != 0: raise ValueError(f"B_global rows ({total_B_rows}) is not a multiple of 6 * Num_Elements ({6*Num_Elem}).")
            
        epsilon_all = B_global.dot(U_global); strain_matrix = epsilon_all.reshape(-1, 6).T
        sigma_gauss_all = D @ strain_matrix 
        
        if hasattr(self, 'Get_Emat_3D_Full'): E_mat = self.Get_Emat_3D_Full(Coords[Connectivity[0, :]], ElementType, num_gp)
        else: E_mat = np.ones((Connectivity.shape[1], num_gp)) / num_gp
            
        nodes_per_elem = Connectivity.shape[1]
        row_idx = np.repeat(Connectivity, num_gp, axis=1).ravel()
        gp_ids_per_elem = np.arange(Num_Elem)[:, None] * num_gp + np.arange(num_gp)[None, :]
        col_idx = np.repeat(gp_ids_per_elem[:, None, :], nodes_per_elem, axis=1).ravel()
        val_idx = np.tile(E_mat, (Num_Elem, 1)).ravel()
        
        E_global = sp.csr_matrix((val_idx, (row_idx, col_idx)), shape=(Num_Nodes, Num_Elem * num_gp))
        
        adj_row = Connectivity.ravel(); adj_col = np.repeat(np.arange(Num_Elem), nodes_per_elem); adj_val = np.ones(len(adj_row))
        Adj = sp.csr_matrix((adj_val, (adj_row, adj_col)), shape=(Num_Nodes, Num_Elem))
        Node_Counts = np.array(Adj.sum(axis=1)).flatten(); Node_Counts[Node_Counts == 0] = 1 
        
        Nodal_Stress_Sum = E_global.dot(sigma_gauss_all.T) 
        Sigma_Final2 = Nodal_Stress_Sum / Node_Counts[:, np.newaxis]
        return Sigma_Final2
    
    def extract_3D_results(self):
        z_coords = self.node_coords[:, 2]; y_coords = self.node_coords[:, 1]
        z_max_actual = np.max(z_coords); z_min_actual = np.min(z_coords)
        z_mid_actual = (z_max_actual + z_min_actual) / 2.0; y_mid_actual = (np.max(y_coords) + np.min(y_coords)) / 2.0
        tol = (z_max_actual - z_min_actual) * 0.01 
    
        top_idx = np.where((np.abs(z_coords - z_max_actual) < tol) & (np.abs(y_coords - y_mid_actual) < tol))[0]
        mid_idx = np.where((np.abs(z_coords - z_mid_actual) < tol) & (np.abs(y_coords - y_mid_actual) < tol))[0]
    
        x_3d = self.node_coords[top_idx, 0]; u_3d_z = self.U_full[top_idx * 3 + 2] 
        s_bending_3d = self.Sigma_Final2[top_idx, 0]; s_shear_3d = self.Sigma_Final2[mid_idx, 5] 
        
        s_idx = np.argsort(x_3d)
        return x_3d[s_idx], u_3d_z[s_idx], s_bending_3d[s_idx], s_shear_3d[s_idx]

    def Get_Emat_3D_Full(self, Coords, ElementType, num_gp):
        nodes_per_elem = Coords.shape[0]
        if num_gp == 1: return np.ones((nodes_per_elem, 1))
            
        if ElementType == 'Hexa8':
            gpts = [-1/np.sqrt(3), 1/np.sqrt(3)]; GP = np.zeros((8, 3)); cnt = 0
            for i in range(2):
                for j in range(2):
                    for k in range(2):
                        GP[cnt, :] = [gpts[i], gpts[j], gpts[k]]; cnt += 1
                        
            Node_Loc = np.array([[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1], [-1,-1, 1], [1,-1, 1], [1,1, 1], [-1,1, 1]])
            r = np.sqrt(3); E_mat = np.zeros((8, 8))
            for n in range(8):
                for k in range(8):
                    E_mat[n, k] = 0.125 * (1 + Node_Loc[n,0]*GP[k,0]*r) * (1 + Node_Loc[n,1]*GP[k,1]*r) * (1 + Node_Loc[n,2]*GP[k,2]*r)
            return E_mat
            
        elif ElementType == 'Hexa20':
            if num_gp == 8:
                g_pts, _ = self.BuildHexaGauss(2)
                Node_Loc = np.array([
                    [-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1], [-1,-1, 1], [1,-1, 1], [1,1, 1], [-1,1, 1],
                    [0,-1,-1], [1,0,-1], [0,1,-1], [-1,0,-1], [0,-1,1], [1,0,1], [0,1,1], [-1,0,1],
                    [-1,-1,0], [1,-1,0], [1,1,0], [-1,1,0]
                ])
                r = np.sqrt(3); E_mat = np.zeros((20, 8))
                for n in range(20):
                    for k in range(8):
                        E_mat[n, k] = 0.125 * (1 + Node_Loc[n,0]*g_pts[k,0]*r) * (1 + Node_Loc[n,1]*g_pts[k,1]*r) * (1 + Node_Loc[n,2]*g_pts[k,2]*r)
                return E_mat
                
            elif num_gp == 27:
                g_pts, _ = self.BuildHexaGauss(3); N_G = np.zeros((27, 20))
                for k in range(27):
                    xi, eta, zeta = g_pts[k,0], g_pts[k,1], g_pts[k,2]
                    N_shape, _, _, _ = self.Hexa20_ShapeFunctions(xi, eta, zeta)
                    N_G[k, :] = N_shape
                return np.linalg.pinv(N_G)
                
        elif ElementType == 'Tet10':
            a, b = 0.58541020, 0.13819660; g_pts = np.array([[a, b, b], [b, a, b], [b, b, a], [b, b, b]]); XYZ_G = np.zeros((4, 3))
            for k in range(4):
                xi, eta, zeta = g_pts[k,0], g_pts[k,1], g_pts[k,2]; L4 = 1 - xi - eta - zeta
                N = np.array([
                    L4*(2*L4-1), xi*(2*xi-1), eta*(2*eta-1), zeta*(2*zeta-1),
                    4*L4*xi, 4*xi*eta, 4*eta*L4, 4*L4*zeta, 4*xi*zeta, 4*eta*zeta
                ])
                XYZ_G[k, :] = N.T @ Coords
            M_nodes = np.column_stack((np.ones(10), Coords)); M_gauss = np.column_stack((np.ones(4), XYZ_G))
            return M_nodes @ np.linalg.pinv(M_gauss)
            
        elif ElementType == 'Tet4': return np.ones((4, 1))
        else: return np.ones((nodes_per_elem, num_gp)) / num_gp
        
    def plot_1D_Validation(self, x_1d, u_1d, s_bending_1d, s_shear_1d, targetPanel):
        fig = targetPanel.figure if hasattr(targetPanel, 'figure') else targetPanel
        fig.clf() 
        axes = fig.subplots(3, 1); ax1, ax2, ax3 = axes[0], axes[1], axes[2]
        
        x_1d_mm = x_1d * 1000.0
        ax1.plot(x_1d_mm, u_1d * 1000, 'b-', linewidth=2.5); ax1.grid(True, linestyle='--'); ax1.set_ylabel('Deflection [mm]'); ax1.set_title(r'$\bf{1D\ Euler-Bernoulli\ Analytical\ Results}$')
        ax2.plot(x_1d_mm, s_bending_1d / 1e6, 'r-', linewidth=2.5); ax2.grid(True, linestyle='--'); ax2.set_ylabel(r'Bending $\sigma_{xx}$ [MPa]')
        ax3.plot(x_1d_mm, s_shear_1d / 1e6, 'g-', linewidth=2.5); ax3.grid(True, linestyle='--'); ax3.set_xlabel('Beam Length [mm]'); ax3.set_ylabel(r'Shear $\tau_{xz}$ [MPa]')
        
        load_pos = (self.LoadPositionSlider.value() / 100.0) * self.geometry['Lx'] * 1000.0
        ax1.axvline(load_pos, color='k', linestyle='--', label='P'); ax2.axvline(load_pos, color='k', linestyle='--', label='P'); ax3.axvline(load_pos, color='k', linestyle='--', label='P')
        
        fig.tight_layout(pad=1.5)
        if hasattr(fig, 'canvas'): fig.canvas.draw_idle()

    def plot_3D_Validation(self, targetAxes):
        try:
            try:
                targetAxes.clear()
            except Exception:
                pass

            if not hasattr(self, 'U_full') or not hasattr(self, 'Sigma_Final2'):
                print("Validation data not found. Run 3D FEM solve first.")
                return
                
            if len(self.node_coords) != len(self.Sigma_Final2):
                print("CRITICAL ERROR: Mesh size and Validation Stress arrays do not match!")
                return
            
            U_nodes = self.U_full.reshape(-1, 3)
            max_u = np.max(np.abs(self.U_full))
            
            scale = (self.geometry['Lx'] * 0.15) / max(max_u, 1e-9) 
            warped_coords = self.node_coords + (U_nodes * scale)
            
            if 'Hexa' in self.element_type:
                n_vis = 8
                vtk_type = pv.CellType.HEXAHEDRON
            else:
                n_vis = 4
                vtk_type = pv.CellType.TETRA
                
            vis_connectivity = self.element_connectivity[:, :n_vis]
            cells_dict = {vtk_type: vis_connectivity}
            
            grid = pv.UnstructuredGrid(cells_dict, warped_coords)
            
            stress_bending_mpa = self.Sigma_Final2[:, 0] / 1e6
            stress_shear_mpa = self.Sigma_Final2[:, 5] / 1e6
            
            sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, 
                         fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)

            targetAxes.subplot(0, 0)
            
            grid_top = grid.copy()
            grid_top.point_data["Bending Stress (MPa)"] = stress_bending_mpa
            
            targetAxes.add_mesh(grid_top, name='val_bending', scalars="Bending Stress (MPa)", 
                                cmap="jet", show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
            targetAxes.add_text("3D FEA: Bending Stress XX [MPa]", name='val_bend_txt', font_size=10, color='black')
            targetAxes.view_isometric(); targetAxes.add_axes(); targetAxes.reset_camera()
            
            targetAxes.subplot(1, 0)
            
            grid_bot = grid.copy()
            grid_bot.point_data["Shear Stress XZ (MPa)"] = stress_shear_mpa
            
            targetAxes.add_mesh(grid_bot, name='val_shear', scalars="Shear Stress XZ (MPa)", 
                                cmap="jet", show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
            targetAxes.add_text("3D FEA: Shear Stress XZ [MPa]", name='val_shear_txt', font_size=10, color='black')
            targetAxes.view_isometric(); targetAxes.add_axes(); targetAxes.reset_camera()
            
            targetAxes.update()
        except Exception as e:
            print(f"Validation Plot Error: {e}")
            traceback.print_exc()
            try:
                targetAxes.clear()
            except Exception:
                pass
            return

    def update_Validation_Summary(self, u_1d, u_3d, s_1d, s_3d, ss_1d, ss_3d, cpu_time, targetTextArea):
        # 1. Numerical Extraction (SI to mm/MPa)
        max_u_fom = np.max(np.abs(u_3d)) * 1000 if len(u_3d) > 0 else np.max(np.abs(self.U_full)) * 1000
        max_s_fom = np.max(np.abs(s_3d)) / 1e6 if len(s_3d) > 0 else np.max(np.abs(self.Sigma_Final2[:, 0])) / 1e6
        max_ss_fom = np.max(np.abs(ss_3d)) / 1e6 if len(ss_3d) > 0 else np.max(np.abs(self.Sigma_Final2[:, 5])) / 1e6
        
        max_u_1d = np.max(np.abs(u_1d)) * 1000
        max_s_1d = np.max(np.abs(s_1d)) / 1e6
        max_ss_1d = np.max(np.abs(ss_1d)) / 1e6

        # 2. DISCRETIZATION ERROR ANALYSIS (A)
        u_error_1d = (abs(max_u_1d - max_u_fom) / max_u_1d * 100) if max_u_1d > 1e-12 else 0.0
       
        

        # 3. EXPERIMENTAL VALIDATION (B)
        try:
            # FIX: Use .text() and float() instead of .value()
            u_max_exp = float(self.exp_u_input.text()) if hasattr(self, 'exp_u_input') else 0.0
        except:
            u_max_exp = 0.0

        u_error_exp = (abs(u_max_exp - max_u_fom) / u_max_exp * 100) if u_max_exp > 1e-12 else 0.0

        # 4. Generate Summary Text
        summary_text = (
            "========================================\n"
            "        VALIDATION SUMMARY             \n"
            "========================================\n"
            f"Computation Time (FOM) : {cpu_time:.4f} s\n\n"
            
            "--- (A) DISCRETIZATION ERROR ANALYSIS ---\n"
            "MAX DISPLACEMENT (z-axis):\n"
            f"  Analytical (1D) : {max_u_1d:.4f} mm\n"
            f"  Numerical (FOM) : {max_u_fom:.4f} mm\n"
            f"  Error ε_u(1D)   : {u_error_1d:.2f} %\n\n"
            
            "PEAK BENDING STRESS (σ_xx):\n"
            f"  Analytical (1D) : {max_s_1d:.2f} MPa\n"
            f"  Numerical (FOM) : {max_s_fom:.2f} MPa\n"
           

            "PEAK SHEAR STRESS (τ_xz):\n"
            f"  Analytical (1D) : {max_ss_1d:.2f} MPa\n"
            f"  Numerical (FOM) : {max_ss_fom:.2f} MPa\n"
          
            
            "--- (B) EXPERIMENTAL VALIDATION ---\n"
            "DEFLECTION BENCHMARK (Dial Gauge):\n"
            f"  Physical (Exp)  : {u_max_exp:.4f} mm\n"
            f"  Numerical (FOM) : {max_u_fom:.4f} mm\n"
            f"  Error ε_u(exp)  : {u_error_exp:.2f} %\n"
            
            "----------------------------------------\n"
            f"STATUS: {self.get_status_flag(u_error_1d)}\n"
            "========================================"
        )
        
        targetTextArea.setText(summary_text)

    def OpenPostProcessingButtonPushed(self):
        self.lock_ui() 
        
        try:
            # 1. DATA VALIDATION
            # Ensure the solver has actually produced results
            if not hasattr(self, 'Sigma_Final2') or self.Sigma_Final2 is None:
                QMessageBox.warning(self, "Post-Processing", "Results not found! Please run the 3D solver in Tab 3 first.")
                return
            
            if not hasattr(self, 'U_full') or self.U_full is None:
                QMessageBox.warning(self, "Post-Processing", "Displacement data missing.")
                return

            # 2. INPUT PARSING (With Error Handling)
            try:
                yield_strength = float(self.YieldStrengthMpaEditField.text()) if self.YieldStrengthMpaEditField.text() else 250.0
                self.scalefactor = float(self.ScaleFactorEditField.text()) if self.ScaleFactorEditField.text() else 1.0
            except ValueError:
                QMessageBox.critical(self, "Input Error", "Yield strength and Scale must be numeric values.")
                return

            stress_type = self.TypeofStressesDropDown.currentText()
            fail_mode = self.MethodDropDown.currentText()
            display_choice = self.DisplayChoiceDropDown.currentText()

            # 3. MEMORY CLEANUP
            # Flush existing graphics buffers before drawing new ones
            gc.collect()

            # 4. PROTECTED RENDERING
            # Render Stress Plot (Left)
            if hasattr(self, 'plot_stresses') and hasattr(self, 'UIAxes5'):
                # Ensure the plotter is active before adding mesh
                self.plot_stresses(self.Sigma_Final2, stress_type, self.UIAxes5, self.U_full, self.scalefactor)

            # Render Safety/Intensity Plot (Right)
            if hasattr(self, 'plot_FS') and hasattr(self, 'UIAxes6'):
                self.plot_FS(fail_mode, yield_strength, self.UIAxes6, self.Sigma_Final2, self.U_full, self.scalefactor, display_type=display_choice)
                
        except Exception as e:
            # Catch unexpected crashes and report them without closing the app
            err_msg = f"Post-Processing Error:\n{str(e)}\n\n{traceback.format_exc()}"
            print(err_msg)
            QMessageBox.critical(None, "Application Error", "Graphics engine encountered an error. Try resetting the camera.")
        
        finally:
            # Always unlock the UI and do a final memory sweep
            self.unlock_ui()
            gc.collect()
        

    def plot_stresses(self, Sigma_Final, stress_type, targetAxes, U_full, scale_factor, custom_clim=None):
        if len(self.node_coords) != len(Sigma_Final):
            print("Plot Stress Warning: Node count mismatch, skipping stress plot.")
            return
            
        stress_map = {'Sigma_xx': (0, 'Sigma_xx'), 'Sigma_yy': (1, 'Sigma_yy'), 'Sigma_zz': (2, 'Sigma_zz'),
                      'Tau_xy':   (3, 'Tau_xy'),   'Tau_yz':   (4, 'Tau_yz'),   'Tau_zx':   (5, 'Tau_zx'), 'Tau_xz':   (5, 'Tau_zx')}
        col, lbl = stress_map.get(stress_type, (0, 'Sigma_xx'))
        stress_data = Sigma_Final[:, col] / 1e6 
        
        if custom_clim is not None:
            c_limits = custom_clim
        else:
            s_min = np.min(stress_data)
            s_max = np.max(stress_data)
            if np.isclose(s_min, s_max):
                c_limits = [s_min - 0.1, s_max + 0.1]
            else:
                c_limits = [s_min, s_max]
        
        if U_full.size == 0:
            print("Plot Stress Warning: Empty displacement vector, skipping stress plot.")
            return

        try:
            Max_Disp_mm = np.max(np.abs(U_full)) * 1000.0
            U_nodes = U_full.reshape(-1, 3)
            def_coords = self.node_coords + (U_nodes * scale_factor)
            title_str = f"Stress Component: {lbl}\nMax Deflection: {Max_Disp_mm:.3f} mm (Visual Scale: {scale_factor}x)"

            if 'Hexa' in self.element_type:
                n_vis = 8; vtk_type = pv.CellType.HEXAHEDRON
            else:
                n_vis = 4; vtk_type = pv.CellType.TETRA

            cells_dict = {vtk_type: self.element_connectivity[:, :n_vis]}
            grid_undeformed = pv.UnstructuredGrid(cells_dict, self.node_coords)
            grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)
            grid_deformed.point_data["Stress (MPa)"] = stress_data

            sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)

            try:
                targetAxes.clear()
            except Exception:
                pass

            saved_cam = None
            try:
                if hasattr(targetAxes, 'camera_initialized'):
                    saved_cam = targetAxes.camera_position
            except Exception:
                saved_cam = None

            try:
                targetAxes.clear_scalar_bars()
            except Exception:
                try:
                    for key in list(targetAxes.scalar_bars.keys()):
                        targetAxes.remove_scalar_bar(key)
                except Exception:
                    pass

            targetAxes.add_mesh(grid_undeformed, name='base_wireframe', style='wireframe', color='gray', opacity=0.4, line_width=1.0, reset_camera=False)
            targetAxes.add_mesh(grid_deformed, name='active_solid', scalars="Stress (MPa)", cmap="jet", clim=c_limits, show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs, reset_camera=False)
            targetAxes.add_text(title_str, name='active_text', font_size=10, color='black')
            targetAxes.add_mesh(grid_undeformed, style='wireframe', color='gray', opacity=0.4, line_width=1.0, reset_camera=False)
            targetAxes.add_mesh(grid_deformed, scalars="Stress (MPa)", cmap="jet", clim=c_limits, show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs, reset_camera=False)
            targetAxes.add_text(title_str, font_size=10, color='black')

            if not hasattr(targetAxes, 'axes_widget_added'):
                targetAxes.add_axes(); targetAxes.axes_widget_added = True

            if not hasattr(targetAxes, 'camera_initialized'):
                min_c = np.min(self.node_coords, axis=0); max_c = np.max(self.node_coords, axis=0); span_x = max_c[0] - min_c[0]; buf = span_x * 0.2
                fixed_bounds = [min_c[0]-buf, max_c[0]+buf, min_c[1]-buf, max_c[1]+buf, min_c[2]-(buf*2), max_c[2]+(buf*2)]
                targetAxes.view_isometric()
                targetAxes.reset_camera(bounds=fixed_bounds)
                targetAxes.camera_initialized = True
            elif saved_cam is not None:
                try:
                    targetAxes.camera_position = saved_cam
                except Exception:
                    pass

            targetAxes.render()
        except Exception as e:
            print(f"Plot Stress Error: {e}")
            traceback.print_exc()
            try:
                targetAxes.clear()
            except Exception:
                pass
            return

    def plot_FS(self, failure_mode, yield_strength, targetAxes, Sigma_Final, U_full, scale_factor, display_type="FS", custom_clim=None):
        if len(self.node_coords) != len(Sigma_Final): return
            
        sx, sy, sz = Sigma_Final[:, 0], Sigma_Final[:, 1], Sigma_Final[:, 2]; txy, tyz, tzx = Sigma_Final[:, 3], Sigma_Final[:, 4], Sigma_Final[:, 5]; num_nodes = len(sx)
        
        if "von mises" in failure_mode.lower():
            C_data = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
        elif "principal" in failure_mode.lower() or "tresca" in failure_mode.lower() or "shear" in failure_mode.lower():
            stress_tensors = np.zeros((num_nodes, 3, 3))
            stress_tensors[:, 0, 0] = sx; stress_tensors[:, 0, 1] = txy; stress_tensors[:, 0, 2] = tzx
            stress_tensors[:, 1, 0] = txy; stress_tensors[:, 1, 1] = sy;  stress_tensors[:, 1, 2] = tyz
            stress_tensors[:, 2, 0] = tzx; stress_tensors[:, 2, 1] = tyz; stress_tensors[:, 2, 2] = sz
            eigenvalues = np.linalg.eigvalsh(stress_tensors)
            if "principal" in failure_mode.lower(): C_data = eigenvalues[:, 2] / 1e6
            else: C_data = (eigenvalues[:, 2] - eigenvalues[:, 0]) / 2.0 / 1e6
        else:
            C_data = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6

        FS_data = yield_strength / np.maximum(C_data, 1e-6)
        
        # --- Custom Limit Override ---
        if "stress" in display_type.lower():
            plot_scalars = C_data; plot_name = "Stress Data (MPa)"; cmap_choice = "jet"
            if custom_clim is not None:
                c_limits = custom_clim
            else:
                s_min=min(C_data); 
                s_max = max(C_data)
                c_limits = [s_min, s_max]
    
            title_str = f"{failure_mode} (MPa)\nMax Deflection: {(np.max(np.abs(U_full)) * 1000.0):.3f} mm"
        else:
            plot_scalars = FS_data; plot_name = "Factor of Safety"; cmap_choice = "jet_r"
            c_limits = custom_clim if custom_clim is not None else [0, 5] 
            title_str = f"Factor of Safety (FS < 1 is Failure)\nMax Deflection: {(np.max(np.abs(U_full)) * 1000.0):.3f} mm"
        # -----------------------------

        Max_Disp_mm = np.max(np.abs(U_full)) * 1000.0; U_nodes = U_full.reshape(-1, 3); def_coords = self.node_coords + (U_nodes * scale_factor)
        
        if 'Hexa' in self.element_type: n_vis = 8; vtk_type = pv.CellType.HEXAHEDRON
        else: n_vis = 4; vtk_type = pv.CellType.TETRA
            
        cells_dict = {vtk_type: self.element_connectivity[:, :n_vis]}
        grid_undeformed = pv.UnstructuredGrid(cells_dict, self.node_coords)
        grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)
        grid_deformed.point_data[plot_name] = plot_scalars
        
        sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)
        
        # --- THE ZOOM FIX: Save the camera exactly where your mouse left it ---
        saved_cam = None
        try:
            if hasattr(targetAxes, 'camera_initialized'):
                saved_cam = targetAxes.camera_position
        except Exception:
            saved_cam = None

        try:
            targetAxes.clear()
        except Exception:
            pass

        try:
            targetAxes.clear_scalar_bars()
        except Exception:
            try:
                for key in list(targetAxes.scalar_bars.keys()):
                    targetAxes.remove_scalar_bar(key)
            except Exception:
                pass

        try:
            targetAxes.add_mesh(grid_undeformed, name='base_wireframe', style='wireframe', color='gray', opacity=0.4, line_width=1.0, reset_camera=False)
            targetAxes.add_mesh(grid_deformed, name='active_solid', scalars=plot_name, cmap=cmap_choice, clim=c_limits, show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs, reset_camera=False)
            targetAxes.add_text(title_str, name='active_text', font_size=10, color='black')
            targetAxes.add_mesh(grid_undeformed, style='wireframe', color='gray', opacity=0.4, line_width=1.0, reset_camera=False)
            targetAxes.add_mesh(grid_deformed, scalars=plot_name, cmap=cmap_choice, clim=c_limits, show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs, reset_camera=False)
            targetAxes.add_text(title_str, font_size=10, color='black')

            if not hasattr(targetAxes, 'axes_widget_added'):
                targetAxes.add_axes(); targetAxes.axes_widget_added = True

            if not hasattr(targetAxes, 'camera_initialized'):
                min_c = np.min(self.node_coords, axis=0); max_c = np.max(self.node_coords, axis=0); span_x = max_c[0] - min_c[0]; buf = span_x * 0.2
                fixed_bounds = [min_c[0]-buf, max_c[0]+buf, min_c[1]-buf, max_c[1]+buf, min_c[2]-(buf*2), max_c[2]+(buf*2)]
                targetAxes.view_isometric()
                targetAxes.reset_camera(bounds=fixed_bounds)
                targetAxes.camera_initialized = True
            elif saved_cam is not None:
                try:
                    targetAxes.camera_position = saved_cam
                except Exception:
                    pass

            targetAxes.render()
        except Exception as e:
            print(f"Plot FS Error: {e}")
            traceback.print_exc()
            try:
                targetAxes.clear()
            except Exception:
                pass
            return

    def TrainButtonPushed(self):
        self.lock_ui() 
        try:
            # CRITICAL FIX: Purge old ROM data before retraining to prevent mode conflicts
            self.Phi = None; self.Phi_stress = None; self.K_rom = None
            if hasattr(self, 'SnapshotMatrix'): self.SnapshotMatrix = None
            gc.collect()
            
            if not hasattr(self, 'K_reduced') or self.K_reduced is None:
                raise RuntimeError("ROM training requires a solved FEM model with applied boundary conditions.")
            if not hasattr(self, 'bc_info') or 'free_dofs_indices' not in self.bc_info:
                raise RuntimeError("Boundary condition information is missing. Please apply BC before ROM training.")

            num_snapshots = int(self.num_snapshotsEditField.text())
            x_positions = np.linspace(0.01 * self.geometry['Lx'], 0.99 * self.geometry['Lx'], num_snapshots)
            
            free_dofs = self.bc_info['free_dofs_indices']; num_free_dof = len(free_dofs)
            self.SnapshotMatrix = np.zeros((num_free_dof, num_snapshots))
            
            self.TrainningTimeTextArea.setText("*** Starting ROM Training ***\n"); print("Starting ROM Training...")
            K_reduced_csr = self.K_reduced.tocsr()
            num_total_dof = self.K_global.shape[0]
            num_nodes = self.node_coords.shape[0]
            
            # Show progress dialog for snapshot collection
            progress = QProgressDialog("Collecting Snapshots...", "Cancel", 0, num_snapshots, self)
            progress.setWindowTitle("ROM Training - Snapshot Stage")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setStyleSheet("QProgressDialog { background-color: white; }")
            progress.show()
            
            for i in range(num_snapshots):
                load_val = float(self.LoadValueNEditField.text())
                temp_loads = self.define_loads_at_pos(x_positions[i], load_val); F_temp = np.zeros(num_total_dof)
                for j in range(len(temp_loads['point_nodes'])):
                    node_id = temp_loads['point_nodes'][j]; force_vec = temp_loads['point_load_values'][:, j]
                    dof_indices = node_id * 3 + np.array([0, 1, 2]); F_temp[dof_indices] += force_vec
                    
                F_red_i = F_temp[free_dofs]
                start_time = time.perf_counter()
                U_free_i = spla.spsolve(K_reduced_csr, F_red_i)
                elapsedTime = time.perf_counter() - start_time
                
                new_entry = f"Snap {i+1}: {elapsedTime:.4f}s at {x_positions[i] * 1000.0:.1f} mm\n"
                current_text = self.TrainningTimeTextArea.toPlainText()
                self.TrainningTimeTextArea.setText(new_entry + current_text)
                progress.setValue(i + 1)
                QApplication.processEvents() 
                self.SnapshotMatrix[:, i] = U_free_i
                
            progress.close()
            
            print("Performing Singular Value Decomposition (SVD)...")
            U_svd, S_disp, Vt = np.linalg.svd(self.SnapshotMatrix, full_matrices=False)
            self.Phi = U_svd; energy_disp = S_disp**2 
            cum_energy_disp = np.cumsum(energy_disp) / np.sum(energy_disp) * 100.0
            
            # MEMORY CLEANUP: Delete temporary large matrices
            del self.SnapshotMatrix, U_svd, Vt
            gc.collect()  # Force garbage collection for heavy memory usage
            
            fig = self.UIAxes8.figure if hasattr(self.UIAxes8, 'figure') else self.UIAxes8; fig.clf()
            ax1 = fig.add_subplot(111); ax2 = ax1.twinx() 
            mode_numbers = np.arange(1, num_snapshots + 1)
            
            ax1.bar(mode_numbers, S_disp / max(np.max(S_disp), 1e-12), color='#3399CC', alpha=0.8); ax1.set_xlabel('Mode Number'); ax1.set_ylabel('Relative Singular Values', color='black'); ax1.tick_params(axis='y', colors='black'); ax1.grid(True, linestyle='--', alpha=0.5)
            ax2.plot(mode_numbers, cum_energy_disp, '-bo', linewidth=2, markerfacecolor='b'); ax2.set_ylabel('Cumulative Energy (%)', color='black'); ax2.set_ylim([np.min(cum_energy_disp) , 100]); ax2.tick_params(axis='y', colors='black')
            ax1.set_title('ROM Invariance: Displacement Modes')
            if hasattr(fig, 'canvas'): fig.canvas.draw_idle()
                
            modes_over_threshold = np.where(cum_energy_disp > 99.999)[0]
            if len(modes_over_threshold) > 0: n_modes_disp = modes_over_threshold[0] + 1 
            else: n_modes_disp = min(15, num_snapshots)
                
            self.Phi = self.Phi[:, :n_modes_disp]
            print("Projecting Stiffness Matrix...")
            self.K_rom = self.Phi.T @ (self.K_reduced @ self.Phi)
            
            num_modes = self.Phi.shape[1]; self.Phi_stress = np.zeros((num_nodes * 6, num_modes)) 
            msg = "Generating Exact Stress Modes...\n"; current_text = self.TrainningTimeTextArea.toPlainText()
            self.TrainningTimeTextArea.setText(msg + current_text); QApplication.processEvents()
            
            # Show progress dialog for stress mode generation
            stress_progress = QProgressDialog("Computing Stress Modes...", "Cancel", 0, num_modes, self)
            stress_progress.setWindowTitle("ROM Training - Stress Stage")
            stress_progress.setWindowModality(Qt.WindowModality.WindowModal)
            stress_progress.setStyleSheet("QProgressDialog { background-color: white; }")
            stress_progress.show()
            
            for m in range(num_modes):
                U_mode_full = np.zeros(num_total_dof); U_mode_full[free_dofs] = self.Phi[:, m]
                Sigma_mode = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_mode_full, self.node_coords, self.element_connectivity, self.element_type)
                self.Phi_stress[:, m] = Sigma_mode.flatten()
                stress_progress.setValue(m + 1)
                QApplication.processEvents()
            
            stress_progress.close()
                
            success_msg = f"Training Complete!\nModes retained: {n_modes_disp}\nEnergy: {cum_energy_disp[n_modes_disp-1]:.4f}%"
            QMessageBox.information(None, "ROM Success", success_msg)
            
            # MEMORY CLEANUP: Force garbage collection after heavy computations
            gc.collect()
        except Exception as e:
            QMessageBox.critical(None, "Training Error", f"Error:\n{str(e)}\n\n{traceback.format_exc()}")
            gc.collect()  # Clean up even on error
        finally:
            self.unlock_ui() 
 
    def CheckAccuracyButtonPushed(self):
        self.lock_ui() 
        progress = None
        Sigma_fem = None
        Sigma_rom = None
        try:
            # 1. DATA INTEGRITY CHECKS
            if not hasattr(self, 'Phi') or self.Phi is None or not hasattr(self, 'K_rom'):
                raise ValueError("ROM data is missing. Train the ROM first.")
            if not hasattr(self, 'K_reduced') or self.K_reduced is None:
                raise ValueError("FEM System not solved. Apply BCs and Solve first.")
            if not hasattr(self, 'B_global') or self.B_global is None:
                raise ValueError("Stress recovery matrices missing. Re-assemble model.")

            # 2. INPUT PARSING
            try:
                x_pos = (self.ValidationLoadPositionSlider.value() / 100.0) * self.geometry['Lx'] 
                P_val = float(self.ValidationLoadNEditField.text())
                scale_factor = float(self.ScaleFactorEditField.text()) if self.ScaleFactorEditField.text() else 1.0
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Load value and scale factor must be numeric.")
                return
                
            stress_type = self.TypeofStressesDropDown_2.currentText()
           
            # 3. INITIALIZE PROGRESS
            progress = QProgressDialog("Validating FEM vs ROM...", "Cancel", 0, 4, self)
            progress.setWindowTitle("ROM Validation Engine")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            self.AccuracyResultsTextArea.setText("*** Initializing Accuracy Check ***\n")
            QApplication.processEvents()

            # 4. LOAD VECTOR ASSEMBLY
            temp_loads = self.define_loads_at_pos(x_pos, P_val)
            F_temp = np.zeros(self.bc_info['total_dofs'])
            for j in range(len(temp_loads['point_nodes'])):
                node_id = temp_loads['point_nodes'][j]
                force_vec = temp_loads['point_load_values'][:, j]
                F_temp[node_id * 3 : node_id * 3 + 3] += force_vec
            
            free_dofs = self.bc_info['free_dofs_indices']
            F_red = F_temp[free_dofs]

            # 5. FEM REFERENCE SOLVE
            t0 = time.perf_counter()
            K_reduced_csr = self.K_reduced.tocsr() if sp.issparse(self.K_reduced) else sp.csr_matrix(self.K_reduced)
            U_free_fem = spla.spsolve(K_reduced_csr, F_red)
            time_fem_solve = time.perf_counter() - t0
            
            num_dof = self.bc_info['total_dofs']
            U_full_fem = np.zeros(num_dof)
            U_full_fem[free_dofs] = U_free_fem
            
            progress.setValue(1)

            # 6. FEM STRESS & PLOT
            t0 = time.perf_counter()
            Sigma_fem = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_full_fem, self.node_coords, self.element_connectivity, self.element_type)
            time_fem_stress = time.perf_counter() - t0
            
            if hasattr(self, 'UIAxes9'):
                self.plot_stresses(Sigma_fem, stress_type, self.UIAxes9, U_full_fem, scale_factor)
            
            progress.setValue(2)
            gc.collect() # Clear temporary FEM arrays from RAM

            # 7. ROM PROJECTED SOLVE
            t0 = time.perf_counter()
            F_rom = self.Phi.T @ F_red
            alpha = np.linalg.solve(self.K_rom, F_rom) 
            U_free_rom_proj = self.Phi @ alpha
            time_rom_solve = time.perf_counter() - t0
            
            U_full_rom = np.zeros(num_dof)
            U_full_rom[free_dofs] = U_free_rom_proj
            
            progress.setValue(3)

            # 8. ROM STRESS RECONSTRUCTION & PLOT
            t0 = time.perf_counter()
            Sigma_rom = (self.Phi_stress @ alpha).reshape((-1, 6))
            time_rom_stress = time.perf_counter() - t0
            
            if hasattr(self, 'UIAxes10'):
                self.plot_stresses(Sigma_rom, stress_type, self.UIAxes10, U_full_rom, scale_factor)
            
            progress.setValue(4)

            # 9. ERROR ANALYSIS
            norm_U_fem = np.linalg.norm(U_free_fem)
            rel_error_U = (np.linalg.norm(U_free_fem - U_free_rom_proj) / max(norm_U_fem, 1e-12)) * 100.0
            rel_error_Sigma = np.linalg.norm(Sigma_fem - Sigma_rom) / max(np.linalg.norm(Sigma_fem), 1e-12) * 100.0
            
            speed_up_solve = time_fem_solve / max(time_rom_solve, 1e-9)
            speed_up_stress = time_fem_stress / max(time_rom_stress, 1e-9)

            # 10. GENERATE REPORT
            results_text = (
                "--- DISPLACEMENT COMPARISON ---\n"
                f"FEM Max U: {np.max(np.abs(U_full_fem)):.4e} m\n"
                f"ROM Max U: {np.max(np.abs(U_full_rom)):.4e} m\n"
                f"Relative Error: {rel_error_U:.4f} %\n\n"

                "--- STRESS CHECK (\u03c3_xx) ---\n"
                f"FEM Max Stress: {np.max(np.abs(Sigma_fem[:,0]))/1e6:.2f} MPa\n"
                f"ROM Max Stress: {np.max(np.abs(Sigma_rom[:,0]))/1e6:.2f} MPa\n"
                f"Relative Error: {rel_error_Sigma:.4f} %\n\n"

                "--- PERFORMANCE ---\n"
                f"FEM Solve: {time_fem_solve:.4f} s\n"
                f"ROM Solve: {time_rom_solve:.4f} s\n"
                f"ROM is {speed_up_solve:.1f}x Faster\n\n"
                f"FEM Stress Reconstruction: {time_fem_stress:.4f} s\n"
                f"ROM Stress Reconstruction: {time_rom_stress:.4f} s\n"
                f"ROM Stress is {speed_up_stress:.1f}x Faster\n\n"
                f"FEM Total Time: {(time_fem_solve + time_fem_stress):.4f} s\n"
                f"ROM Total Time: {(time_rom_solve + time_rom_stress):.4f} s\n"
                f"Total System Speedup: {(time_fem_solve + time_fem_stress)/(time_rom_solve + time_rom_stress):.1f}x\n\n"    
            )
            self.AccuracyResultsTextArea.setText(results_text)

        except Exception as e:
            QMessageBox.critical(None, "Accuracy Check Error", f"Calculations failed:\n{str(e)}")
            print(traceback.format_exc())
        finally:
            if progress: progress.close()
            self.unlock_ui()
            # Final RAM Cleanup
            Sigma_fem = None
            Sigma_rom = None
            gc.collect()

    def SaveButtonPushed(self):
        self.lock_ui()
        try:
            if not hasattr(self, 'Phi') or self.Phi is None or not hasattr(self, 'K_rom') or self.K_rom is None:
                QMessageBox.critical(None, "Save Error", "No ROM data found! Please train the ROM first.")
                self.unlock_ui()
                return
            
            default_name = f"Cantilever_ROM_{datetime.now().strftime('%H%M%S')}"
            instruction_text = (
                "CRITICAL FOR LIVE TWIN:\n"
                "The name MUST contain one of these keywords based on your current setup:\n"
                "- 'Simply' (for Simply Supported)\n"
                "- 'Cant' (for Cantilever)\n"
                "- 'Fix' (for Fixed-Fixed)\n\n"
                "Enter a label for this ROM state:"
            )
            rom_label, ok = QInputDialog.getText(None, "Save ROM Data for Digital Twin", instruction_text, text=default_name)
            if not ok or not rom_label: 
                self.unlock_ui()
                return
                
            # --- UPDATE THIS DICTIONARY ---
            New_ROM = {
                'Label': rom_label, 
                'Phi': self.Phi, 
                'Phi_stress': self.Phi_stress, 
                'K_rom': self.K_rom, 
                'bc_info': self.bc_info, 
                'NumNodes': self.node_coords.shape[0], 
                'ElementType': self.element_type,
                'Nodes': self.node_coords,
                'Connectivity': self.element_connectivity # <--- CRITICAL NEW ADDITION
            }

            # --- THE FIX: Disable the scary "Overwrite/Replace" warning ---
            options = QFileDialog.Option.DontConfirmOverwrite
            save_filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Select ROM Bank to Update (or create new)", 
                "DigitalTwin_ROM_Bank.pkl", 
                "Pickle Files (*.pkl);;All Files (*)",
                options=options
            )
            
            if not save_filename:
                self.unlock_ui()
                return # User canceled
                
            # Safely Load existing, Append the new ROM, and Save
            if os.path.exists(save_filename):
                try:
                    with open(save_filename, 'rb') as f: 
                        ROM_Bank = pickle.load(f)
                    ROM_Bank.append(New_ROM)
                except Exception as e:
                    QMessageBox.critical(None, "File Error", f"Could not read existing Bank. Is it corrupted?\n{e}")
                    self.unlock_ui()
                    return
            else: 
                ROM_Bank = [New_ROM]
            
            # Write with error handling
            try:
                with open(save_filename, 'wb') as f: 
                    pickle.dump(ROM_Bank, f)
            except Exception as e:
                QMessageBox.critical(None, "Write Error", f"Failed to save ROM bank. Disk full or permission issue?\n{e}")
                self.unlock_ui()
                return
                
            if hasattr(self, 'DT_Bank'): self.DT_Bank = ROM_Bank
            msg = f"ROM '{rom_label}' successfully added to:\n{save_filename}\n\nTotal Models in Bank: {len(ROM_Bank)}"
            QMessageBox.information(None, "Save Successful", msg)
            
            # MEMORY CLEANUP: Force garbage collection after large pickle operations
            ROM_Bank = None
            New_ROM = None
            gc.collect()
            
        except Exception as e:
            QMessageBox.critical(None, "Critical Error", f"Unexpected error during save:\n{str(e)}\n\n{traceback.format_exc()}")
            gc.collect()
        finally:
            self.unlock_ui()


    def ClearBankButtonPushed(self):
        # --- THE FIX: Let the user browse for the exact bank they want to clear ---
        file_name, _ = QFileDialog.getOpenFileName(self, "Select ROM Bank to Clear", "", "Pickle Files (*.pkl)")
        
        if not file_name: 
            return # User canceled
            
        reply = QMessageBox.question(self, 'Clear ROM Bank', f"Are you sure you want to permanently delete all ROMs inside:\n{file_name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(file_name):
                os.remove(file_name)
                # Clear active RAM if it's the same bank
                if hasattr(self, 'DT_Bank'): self.DT_Bank = []
                QMessageBox.information(self, "Success", "ROM Bank has been deleted from disk.") 


# =========================================================================
# 2. CALIBRATION BAY (MODULE 2)
# =========================================================================
class CalibrationWindow(QMainWindow):
    def __init__(self, sensor_manager, parent_geometry):
        super().__init__()
        self.setWindowTitle("Module 2: Hardware Calibration Bay")
        self.setGeometry(200, 200, 1200, 700)
        self.sm = sensor_manager
        self.beam_geometry = parent_geometry
        self._updating_table = False
        self.sm.L_m = float(parent_geometry.get('Lx', self.sm.L_m))
        self.sm.b_m = float(parent_geometry.get('Ly', self.sm.b_m))
        self.sm.h_m = float(parent_geometry.get('Lz', self.sm.h_m))
        self.sm.I_m4 = (self.sm.b_m * self.sm.h_m**3) / 12.0
        self.sm.EI = (self.sm.E_GPa * 1e9) * self.sm.I_m4

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.build_ui()
        self.refresh_ports()
        self.live_timer = QTimer()
        self.live_timer.timeout.connect(self.update_live_dashboard)

    def build_ui(self):
        left = QVBoxLayout(); mid = QVBoxLayout(); right = QVBoxLayout()

        c_grp = QGroupBox("Hardware Controls"); c_lay = QFormLayout()
        ProfessionalTheme.apply_professional_panel_style(c_grp)
        self.combo_ports = QComboBox()
        self.btn_refresh_ports = QPushButton("Scan Ports")
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        port_h = QHBoxLayout(); port_h.addWidget(self.combo_ports); port_h.addWidget(self.btn_refresh_ports)
        self.btn_conn = QPushButton("Connect Arduino")
        self.btn_conn.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.ACCENT_BLUE, width=140))
        self.btn_conn.clicked.connect(self.handle_connect)
        self.lbl_status = QLabel("Disconnected")
        self.lbl_status.setStyleSheet(f"color: {ProfessionalTheme.TEXT_GRAY}; font-weight: 500;")
        c_lay.addRow("Select Device:", port_h)
        c_lay.addRow(self.btn_conn, self.lbl_status)
        c_grp.setLayout(c_lay); left.addWidget(c_grp)

        load_grp = QGroupBox("Load Cell")
        ProfessionalTheme.apply_professional_panel_style(load_grp)
        load_lay = QFormLayout()
        self.btn_load_tare = QPushButton("Tare Load Cell")
        self.btn_load_tare.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.INFO_PURPLE, width=140))
        self.btn_load_tare.clicked.connect(self.tare_load)
        self.m_input = QLineEdit("1.0"); self.inp_mass = self.m_input
        self.m_input.setStyleSheet(f"border: 1px solid {ProfessionalTheme.BORDER_LIGHT}; border-radius: 4px; padding: 6px; font-size: 10pt;")
        self.btn_load_cal = QPushButton("Set Load Factor")
        self.btn_load_cal.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.ACCENT_BLUE, width=140))
        self.btn_load_cal.clicked.connect(self.calibrate_load)
        self.inp_offset_n = QLineEdit("0.0")
        self.inp_offset_n.setStyleSheet(f"border: 1px solid {ProfessionalTheme.BORDER_LIGHT}; border-radius: 4px; padding: 6px; font-size: 10pt;")
        load_lay.addRow(self.btn_load_tare)
        load_lay.addRow("Standard Mass (kg):", self.m_input)
        load_lay.addRow(self.btn_load_cal)
        load_lay.addRow("Load Offset (N):", self.inp_offset_n)
        load_grp.setLayout(load_lay); left.addWidget(load_grp)

        TOF_grp = QGroupBox("TOF Sensor")
        ProfessionalTheme.apply_professional_panel_style(TOF_grp)
        TOF_lay = QFormLayout()
        self.btn_tare_TOF = QPushButton("Tare TOF")
        self.btn_tare_TOF.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.INFO_PURPLE, width=140))
        self.btn_tare_TOF.clicked.connect(self.tare_TOF)
        self.inp_TOF_offset = QLineEdit("0.0")
        TOF_lay.addRow(self.btn_tare_TOF)
        TOF_lay.addRow("TOF Offset (mm):", self.inp_TOF_offset)
        TOF_grp.setLayout(TOF_lay); left.addWidget(TOF_grp)

        strain_grp = QGroupBox("Strain Gauge")
        ProfessionalTheme.apply_professional_panel_style(strain_grp)
        strain_lay = QFormLayout()
        self.btn_compute_af = QPushButton("Compute AF")
        self.btn_compute_af.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.ACCENT_BLUE, width=140))
        self.btn_compute_af.clicked.connect(self.find_af)
        self.btn_strain_tare = QPushButton("Tare Strain")
        self.btn_strain_tare.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.INFO_PURPLE, width=140))
        self.btn_strain_tare.clicked.connect(self.tare_strain)
        self.btn_calc_strain_pos = QPushButton("Calculate Strain Positions")
        self.btn_calc_strain_pos.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.ACCENT_BLUE, width=180))
        self.btn_calc_strain_pos.clicked.connect(self.calculate_strain_positions)
        self.mode = QComboBox(); self.mode.addItems(["Fixed-Fixed", "Simply Supported", "Cantilever"]); self.mode_combo = self.mode
        self.inp_x1 = QLineEdit("125")
        self.pos_x = QLineEdit("250.0")
        self.inp_x3 = QLineEdit("375")
        self.fiber_combo = QComboBox(); self.fiber_combo.addItems(["Top Surface (+h/2)", "Bottom Surface (-h/2)", "Custom Y (mm)"])
        self.fiber_combo.currentIndexChanged.connect(self.toggle_custom_y)
        self.inp_y_custom = QLineEdit("1.5"); self.inp_y_custom.setEnabled(False)
        self.d_input = QLineEdit("1.0"); self.inp_dial = self.d_input
        strain_lay.addRow(self.btn_compute_af)
        strain_lay.addRow(self.btn_strain_tare)
        strain_lay.addRow(self.btn_calc_strain_pos)
        strain_lay.addRow("Beam Boundary:", self.mode)
        strain_lay.addRow("Left Gauge X (mm):", self.inp_x1)
        strain_lay.addRow("Mid Gauge X (mm):", self.pos_x)
        strain_lay.addRow("Right Gauge X (mm):", self.inp_x3)
        strain_lay.addRow("Gauge Y-Fiber:", self.fiber_combo)
        strain_lay.addRow("Custom Y offset (mm):", self.inp_y_custom)
        strain_lay.addRow("Dial Gauge (mm):", self.d_input)
        strain_grp.setLayout(strain_lay); left.addWidget(strain_grp); left.addStretch()

        self.log_a = QTextEdit(); self.log_a.setReadOnly(True); self.log_box = self.log_a
        self.log_a.setStyleSheet(f"background: {ProfessionalTheme.CONSOLE_BG}; color: {ProfessionalTheme.CONSOLE_TEXT}; font-family: Courier; border: 1px solid {ProfessionalTheme.BORDER_COLOR}; border-radius: 4px;")
        mid.addWidget(QLabel(f"<b style='color: {ProfessionalTheme.PRIMARY_BLUE};'>Process Log:</b>")); mid.addWidget(self.log_a)

        f_grp = QGroupBox("Derived Factors"); f_lay = QFormLayout()
        ProfessionalTheme.apply_professional_panel_style(f_grp)
        self.l_tare = QLabel("0.0"); self.l_fac = QLabel("1.0"); self.l_af = QLabel("2.0")
        f_lay.addRow("Load Tare Raw (bits):", self.l_tare)
        f_lay.addRow("Load Factor (bits/kg):", self.l_fac)
        f_lay.addRow("Asymmetric Factor (AF):", self.l_af)
        f_grp.setLayout(f_lay); mid.addWidget(f_grp)

        d_grp = QGroupBox("Live Readouts"); d_lay = QGridLayout()
        ProfessionalTheme.apply_professional_panel_style(d_grp)
        self.l_load = QLabel("0.00 N"); self.l_s1 = QLabel("0.0 uE"); self.l_s2 = QLabel("0.0 uE")
        self.l_s3 = QLabel("0.0 uE"); self.l_pos = QLabel("0.00 mm")
        style = f"font-size: 14pt; font-weight: bold; color: {ProfessionalTheme.SUCCESS_GREEN}; background: {ProfessionalTheme.CONSOLE_BG}; padding: 8px; border-radius: 4px; border: 1px solid {ProfessionalTheme.PRIMARY_BLUE};"
        for lbl in [self.l_load, self.l_s1, self.l_s2, self.l_s3,  self.l_pos]: lbl.setStyleSheet(style);
        d_lay.addWidget(QLabel("Force:"), 0, 0); d_lay.addWidget(self.l_load, 0, 1)
        d_lay.addWidget(QLabel("Strain Support Left:"), 1, 0); d_lay.addWidget(self.l_s1, 1, 1)
        d_lay.addWidget(QLabel("Strain Mid:"), 2, 0); d_lay.addWidget(self.l_s2, 2, 1)
        d_lay.addWidget(QLabel("Strain Support Right:"), 3, 0); d_lay.addWidget(self.l_s3, 3, 1)
      
        d_lay.addWidget(QLabel("Position:"), 5, 0); d_lay.addWidget(self.l_pos, 5, 1)
        d_grp.setLayout(d_lay); right.addWidget(d_grp)

        self.t_def = self.create_strain_table()
        self.t_lod = QTableWidget(5, 6); self.t_lod.setHorizontalHeaderLabels(["Pt", "Mass (kg)", "Ref (N)", "Raw ADC", "Live Load (N)", "Error %"])
        self.t_pos = QTableWidget(5, 4); self.t_pos.setHorizontalHeaderLabels(["Pt", "Manual (mm)", "TOF(mm)", "Error %"])
        for t in [self.t_def, self.t_lod, self.t_pos]:
            try: t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            except Exception: pass
            for i in range(5):
                t.setItem(i, 0, QTableWidgetItem(f"Pt {i+1}"))
                for col in range(1, t.columnCount()): t.setItem(i, col, QTableWidgetItem("0.0"))
        self.t_def.itemChanged.connect(self.t_strain_item_changed)
        self.t_lod.itemChanged.connect(self.auto_fill_lod)
        self.t_pos.itemChanged.connect(self.auto_fill_pos)
        r_def = QPushButton("Refresh Strain Table"); r_def.clicked.connect(lambda: self.clear_table(self.t_def))
        r_lod = QPushButton("Refresh Load Table"); r_lod.clicked.connect(lambda: self.clear_table(self.t_lod))
        r_pos = QPushButton("Refresh Position Table"); r_pos.clicked.connect(lambda: self.clear_table(self.t_pos))
        right.addWidget(QLabel("<b>Strain Validation</b>")); right.addWidget(self.t_def); right.addWidget(r_def)
        right.addWidget(QLabel("<b>Load Validation</b>")); right.addWidget(self.t_lod); right.addWidget(r_lod)
        right.addWidget(QLabel("<b>Position Validation</b>")); right.addWidget(self.t_pos); right.addWidget(r_pos)
        self.layout.addLayout(left, 1); self.layout.addLayout(mid, 2); self.layout.addLayout(right, 3)

    def create_strain_table(self):
        t = QTableWidget(5, 11)
        t.setHorizontalHeaderLabels(["Pt", "Dial (mm)", "S1_Th", "S2_Th", "S3_Th", "S1_Measure", "S2_Measure", "S3_Measure", "S1_Err %", "S2_Err %", "S3_Err %"])
        return t

    def showEvent(self, event):
        self.live_timer.start(100); super().showEvent(event)

    def closeEvent(self, event):
        self.live_timer.stop(); event.accept()

    def toggle_custom_y(self, idx):
        self.inp_y_custom.setEnabled(idx == 2)

    def refresh_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(f"{port.device} - {port.description}", port.device)
        if not ports:
            self.combo_ports.addItem("No COM Ports Detected", None)
            self.log("Scanned: No active COM ports found. Check USB cable.")
        else:
            self.log(f"Scanned: Found {len(ports)} available device(s).")

    def handle_connect(self):
        selected_port = self.combo_ports.currentData() or self.sm.port
        if not selected_port:
            self.log("Error: Please select a valid COM port from the dropdown.")
            return
        if self.sm.connect(selected_port):
            self.lbl_status.setText(f"Connected ({selected_port})")
            self.lbl_status.setStyleSheet("color: #00aa00; font-weight: bold;")
            self.log(f"Hardware synchronized successfully on {selected_port}.")
        else:
            self.lbl_status.setText("Connection Failed")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            self.log(f"Failed to open {selected_port}. Is the serial monitor open in Arduino IDE?")

    def find_af(self):
        raw = self.sm.get_average_raw(20)
        if raw is None:
            self.log("Error: No strain data for AF computation.")
            return
        for i in range(3):
            self.sm.strain_af[i] = self.sm.compute_af(raw[i])
        avg_af = np.mean(self.sm.strain_af)
        self.l_af.setText(f"{avg_af:.3f}")
        self.log(f"AF computed: S1={self.sm.strain_af[0]:.3f}, S2={self.sm.strain_af[1]:.3f}, S3={self.sm.strain_af[2]:.3f}")

    def tare_load(self):
        raw = self.sm.get_average_raw(15)
        if raw is None:
            self.log("Error: Cannot tare load; no data.")
            return
        self.sm.load_tare = raw[3]
        self.l_tare.setText(f"{self.sm.load_tare:.1f}")
        self.log("Load cell tared from raw channel 4.")

    def calibrate_load(self):
        raw = self.sm.get_average_raw(20)
        if raw is None:
            self.log("Error: No raw data for load calibration.")
            return
        try:
            mass = float(self.inp_mass.text())
            offset = float(self.inp_offset_n.text())
        except ValueError:
            self.log("Error: Invalid mass or load offset.")
            return
        self.sm.load_offset_n = offset
        ref_n = mass * self.sm.GRAVITY
        raw_delta = raw[3] - self.sm.load_tare
        if ref_n - offset == 0 or raw_delta == 0:
            self.log("Error: Invalid load calibration values; divide by zero.")
            return
        self.sm.load_calib_factor = (raw_delta * self.sm.GRAVITY) / (ref_n - offset)
        self.l_fac.setText(f"{self.sm.load_calib_factor:.3f}")
        self.log(f"Load calibration factor computed: {self.sm.load_calib_factor:.3f}")

    def tare_strain(self):
        raw = self.sm.get_average_raw(20)
        if raw is None:
            self.log("Error: Cannot tare strain; no data.")
            return
        for i in range(3):
            self.sm.strain_tare_bits[i] = raw[i]
        self.sm.strain_zero_bits = raw[1]
        self.log("All strain gauges tared from raw channels 1-3.")

    def calibrate_gain(self):
        self.find_af()

    def tare_TOF(self):
        raw = self.sm.get_average_raw(15)
        if raw is None:
            self.log("Error: Cannot tare TOF; no data.")
            return
        try: TOF_offset = float(self.inp_TOF_offset.text())
        except ValueError: TOF_offset = 0.0
        
        self.sm.TOF_offset_mm = TOF_offset
        TOF_pos_tare = raw[4] + TOF_offset
        self.sm.TOF_tare = raw[4]
        self.sm.TOF_tare_pos = TOF_pos_tare
        self.log(f"TOF tared: position={TOF_pos_tare:.2f} mm, offset={TOF_offset:.1f} mm.")

    def _theory_strains(self, dial_mm, mode_idx=None):
        dial_m = dial_mm / 1000.0
        L = self.sm.L_m
        EI = self.sm.EI
        H = self.sm.h_m
        
        if mode_idx is None:
            mode_idx = self.mode.currentIndex()
            
        if self.fiber_combo.currentIndex() == 0:
            y_fiber = H / 2.0
        elif self.fiber_combo.currentIndex() == 1:
            y_fiber = -H / 2.0
        else:
            try: y_fiber = float(self.inp_y_custom.text()) / 1000.0
            except ValueError: y_fiber = H / 2.0
            
        try:
            x1_m = float(self.inp_x1.text()) / 1000.0
            x2_m = float(self.pos_x.text()) / 1000.0
            x3_m = float(self.inp_x3.text()) / 1000.0
        except ValueError:
            x1_m, x2_m, x3_m = L * 0.25, L * 0.5, L * 0.75

        # Dial gauge is assumed positioned at the center (x = L/2) for calculating equivalent force P
        x_dial = L / 2.0

        if mode_idx == 0:  # --- FIXED-FIXED BEAM ---
            # Deflection at center (x = L/2) for symmetric load P at center: delta = (P * L^3) / (192 * EI)
            P_equiv = (dial_m * 192.0 * EI) / (L**3)
            
            def get_theory_uE(x):
                # Exact symmetric Fixed-Fixed bending moment profile: M(x) = P/2 * x - P*L/8 (for left half)
                xx = x if x <= L / 2.0 else L - x
                M = (P_equiv * xx / 2.0) - (P_equiv * L / 8.0)
                return (-y_fiber * (M / EI)) * 1e6

        elif mode_idx == 1:  # --- SIMPLY SUPPORTED BEAM ---
            # Deflection at center (x = L/2) for symmetric load P at center: delta = (P * L^3) / (48 * EI)
            P_equiv = (dial_m * 48.0 * EI) / (L**3)
            
            def get_theory_uE(x):
                # Exact symmetric Simply Supported bending moment profile: M(x) = P/2 * x (for left half)
                xx = x if x <= L / 2.0 else L - x
                M = (P_equiv * xx) / 2.0
                return (-y_fiber * (M / EI)) * 1e6

        else:  # --- CANTILEVER BEAM ---
            # Deflection at free end (x = L) for a point load P at the free end: delta = (P * L^3) / (3 * EI)
            # Alternatively, if your physical dial gauge measures at the free end (L), use 3.0. 
            P_equiv = (dial_m * 3.0 * EI) / (L**3)
            
            def get_theory_uE(x):
                # Exact Cantilever bending moment profile from fixed end (x=0) to free end (x=L):
                # M(x) = -P * (L - x)
                M = -P_equiv * (L - x)
                return (-y_fiber * (M / EI)) * 1e6

        return [get_theory_uE(x1_m), get_theory_uE(x2_m), get_theory_uE(x3_m)]

    def update_live_dashboard(self):
        if not self.sm.is_connected:
            return
        raw = self.sm.get_average_raw(1)
        if raw is None:
            return
        if self.sm.load_calib_factor == 0 or not np.isfinite(self.sm.load_calib_factor):
            self.l_load.setText("-- N")
            self.log("Invalid load factor. Recalibrate load cell with a known mass.")
            return
        try: offset = float(self.inp_offset_n.text())
        except ValueError: offset = 0.0
        self.sm.load_offset_n = offset
        force_n = ((raw[3] - self.sm.load_tare) / self.sm.load_calib_factor) * self.sm.GRAVITY + offset
    
        try: TOF_offset = float(self.inp_TOF_offset.text())
        except ValueError: TOF_offset = 0.0
        self.sm.TOF_offset_mm = TOF_offset
        p_mm = raw[4] + TOF_offset
        strains = [self.sm.calc_microstrain(raw[i], self.sm.strain_tare_bits[i], self.sm.strain_af[i]) for i in range(3)]
        
        self.l_load.setText(f"{force_n:.2f} N")
        self.l_s1.setText(f"{strains[0]:.1f} uE"); self.l_s2.setText(f"{strains[1]:.1f} uE"); self.l_s3.setText(f"{strains[2]:.1f} uE")
        self.l_pos.setText(f"{p_mm:.2f} mm")
        self.l_tare.setText(f"{self.sm.load_tare:.1f}"); self.l_fac.setText(f"{self.sm.load_calib_factor:.3f}")

    def t_strain_item_changed(self, item):
        if self._updating_table or item.column() != 1:
            return
        try:
            dial_mm = float(item.text())
            raw = self.sm.get_average_raw(20)
            if raw is None: return
            th = self._theory_strains(dial_mm)
            meas_signed = [self.sm.calc_microstrain(raw[i], self.sm.strain_tare_bits[i], self.sm.strain_af[i]) for i in range(3)]
            meas = [abs(v) for v in meas_signed]
            errs = [abs((abs(th[i]) - meas[i]) / abs(th[i])) * 100.0 if th[i] != 0 else 0.0 for i in range(3)]
            self._updating_table = True
            for col, val in enumerate(th + meas_signed + errs, start=2):
                suffix = "%" if col >= 8 else ""
                item.tableWidget().setItem(item.row(), col, QTableWidgetItem(f"{val:.1f}{suffix}"))
            self._updating_table = False
        except Exception as e:
            self._updating_table = False
            self.log(f"Strain table update error: {e}")

    def auto_fill_def(self, item):
        self.t_strain_item_changed(item)

    def auto_fill_lod(self, item):
        if self._updating_table or item.column() != 1:
            return
        try:
            mass = float(item.text())
            raw = self.sm.get_average_raw(10)
            if raw is None: return
            ref_n = mass * self.sm.GRAVITY
            raw_adc = raw[3]
            try: offset = float(self.inp_offset_n.text())
            except ValueError: offset = 0.0
            live_n = ((raw_adc - self.sm.load_tare) / self.sm.load_calib_factor) * self.sm.GRAVITY + offset
            error = abs((live_n - ref_n) / ref_n) * 100.0 if ref_n != 0 else 0.0
            self._updating_table = True
            self.t_lod.setItem(item.row(), 2, QTableWidgetItem(f"{ref_n:.3f}"))
            self.t_lod.setItem(item.row(), 3, QTableWidgetItem(f"{raw_adc:.1f}"))
            self.t_lod.setItem(item.row(), 4, QTableWidgetItem(f"{live_n:.3f}"))
            self.t_lod.setItem(item.row(), 5, QTableWidgetItem(f"{error:.2f}%"))
            self._updating_table = False
        except Exception as e:
            self._updating_table = False
            self.log(f"Load table update error: {e}")

    def auto_fill_pos(self, item):
        if self._updating_table or item.column() != 1:
            return
        try:
            man_pos = float(item.text())
            try: TOF_offset =  float(self.inp_TOF_offset.text())
            except ValueError: TOF_offset = 0.0
            raw= self.sm.get_average_raw(10)
            TOF_pos =  raw[4]  + TOF_offset
            error = abs((TOF_pos - man_pos) / man_pos) * 100.0 if man_pos != 0 else 0.0
            self._updating_table = True
            self.t_pos.setItem(item.row(), 2, QTableWidgetItem(f"{TOF_pos:.2f}"))
            self.t_pos.setItem(item.row(), 3, QTableWidgetItem(f"{error:.2f}%"))
            self._updating_table = False
        except Exception as e:
            self._updating_table = False
            self.log(f"Position table update error: {e}")

    def calculate_strain_positions(self):
        raw = self.sm.get_average_raw(20)
        if raw is None:
            self.log("Error: cannot compute positions; no raw data.")
            return
        try: dial_mm = float(self.inp_dial.text())
        except ValueError:
            self.log("Error: invalid dial input for position calculation.")
            return
        L = self.sm.L_m
        meas = [abs(self.sm.calc_microstrain(raw[i], self.sm.strain_tare_bits[i], self.sm.strain_af[i])) for i in range(3)]
        best = []
        for ch, ref_text in [(0, self.inp_x1.text()), (2, self.inp_x3.text())]:
            try: ref = float(ref_text) / 1000.0
            except ValueError: ref = L * (0.25 if ch == 0 else 0.75)
            xs = np.linspace(max(0.0, ref - 0.0025), min(L, ref + 0.0025), 20)
            best_x, best_err = ref, float("inf")
            for x in xs:
                old = self.inp_x1.text() if ch == 0 else self.inp_x3.text()
                if ch == 0: self.inp_x1.setText(f"{x * 1000.0:.3f}")
                else: self.inp_x3.setText(f"{x * 1000.0:.3f}")
                th = abs(self._theory_strains(dial_mm)[ch])
                err = abs(th - meas[ch])
                if err < best_err:
                    best_x, best_err = x, err
                if ch == 0: self.inp_x1.setText(old)
                else: self.inp_x3.setText(old)
            best.append((best_x, best_err))
        self.inp_x1.setText(f"{best[0][0] * 1000.0:.1f}")
        self.inp_x3.setText(f"{best[1][0] * 1000.0:.1f}")
        self.log(f"Estimated sensor X positions: Left={best[0][0] * 1000.0:.1f} mm, Right={best[1][0] * 1000.0:.1f} mm")

    def clear_table(self, t):
        t.blockSignals(True)
        for i in range(t.rowCount()):
            for j in range(1, t.columnCount()): t.setItem(i, j, QTableWidgetItem("0.0"))
        t.blockSignals(False)

    def log(self, msg):
        self.log_a.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


#=========================================================================
# MODULE 3: ROM INTERACTIVE VISUALIZER (OFFLINE SIMULATION)
# =====================================================================
class ROMVisualizerWindow(QMainWindow):
    """Standalone window to manually simulate and visualize ROMs using sliders."""

    def __init__(self, dt_bank, geometry, launcher):
        super().__init__()
        self.setWindowTitle("Module 3: ROM Interactive Visualizer")
        self.setGeometry(150, 150, 1350, 900)
        
        self.DT_Bank = dt_bank
        self.geometry = geometry
        self.launcher = launcher 
        self.isSimulating = False
        self._is_rendering = False

        # Current Calculation State
        self.current_U = None
        self.current_Sigma = None
        self.Active_ROM = None
        self.active_beam_target = None
        self.auto_tare_on_beam_change = True
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.build_ui()

    def build_ui(self):
        # --- 1. Top Control Panel (Physics Inputs) ---
        input_group = QGroupBox("Physics Controls")
        input_layout = QGridLayout(input_group)
        
        self.StartLiveTwinButton = QPushButton("Start Simulation")
        self.StartLiveTwinButton.setMinimumHeight(40)
        self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #e0e0e0; color: black;")
        self.StartLiveTwinButton.clicked.connect(self.toggle_simulation)
        
        self.StainGauge1Switch = QCheckBox("Clamp 1 (Left)")
        self.StainGauge2Switch = QCheckBox("Clamp 2 (Right)")
        
        input_layout.addWidget(self.StartLiveTwinButton, 0, 0, 1, 2)
        input_layout.addWidget(self.StainGauge1Switch, 0, 2)
        input_layout.addWidget(self.StainGauge2Switch, 0, 3)
        
        beam_len = self.geometry.get('Lx', 1.0)
        self.lbl_pos = QLabel(f"Load Position: {(50/100.0)*beam_len*1000.0:.1f} mm")
        input_layout.addWidget(self.lbl_pos, 1, 0)
        
        self.LoadPositionSlider_2 = QSlider(Qt.Orientation.Horizontal)
        self.LoadPositionSlider_2.setRange(0, 100); self.LoadPositionSlider_2.setValue(50)
        input_layout.addWidget(self.LoadPositionSlider_2, 1, 1, 1, 3)
        
        input_layout.addWidget(QLabel("Load Value (N):"), 2, 0)
        self.LoadValueNSlider = QSlider(Qt.Orientation.Horizontal)
        self.LoadValueNSlider.setRange(1, 15000); self.LoadValueNSlider.setValue(1000)
        self.LoadNEditField = QLineEdit("1000"); self.LoadNEditField.setFixedWidth(60)
        input_layout.addWidget(self.LoadValueNSlider, 2, 1, 1, 2)
        input_layout.addWidget(self.LoadNEditField, 2, 3)
        self.main_layout.addWidget(input_group, 0)

        # --- 2. Middle Control Panel (Rendering Options) ---
        render_group = QGroupBox("Rendering Options")
        render_layout = QHBoxLayout(render_group)
        
        render_layout.addWidget(QLabel("<b>Primary Mode:</b>"))
        self.PrimaryModeCombo = QComboBox()
        self.PrimaryModeCombo.addItems(["Failure", "Stress"])
        render_layout.addWidget(self.PrimaryModeCombo)
        
        self.options_stack = QStackedWidget()
        
        fail_widget = QWidget(); fail_lay = QHBoxLayout(fail_widget); fail_lay.setContentsMargins(0,0,0,0)
        fail_lay.addWidget(QLabel("Output:"))
        self.FailDisplayCombo = QComboBox(); self.FailDisplayCombo.addItems(["FS", "Stress Intensity"])
        fail_lay.addWidget(self.FailDisplayCombo)
        fail_lay.addWidget(QLabel("Criteria:"))
        self.FailMethodCombo = QComboBox(); self.FailMethodCombo.addItems(["Von Mises", "Max Principal", "Max Shear (Tresca)"])
        fail_lay.addWidget(self.FailMethodCombo)
        self.options_stack.addWidget(fail_widget)
        
        stress_widget = QWidget(); stress_lay = QHBoxLayout(stress_widget); stress_lay.setContentsMargins(0,0,0,0)
        stress_lay.addWidget(QLabel("Component:"))
        self.StressTypeCombo = QComboBox(); self.StressTypeCombo.addItems(["Sigma_xx", "Sigma_yy", "Sigma_zz", "Tau_xy", "Tau_yz", "Tau_zx"])
        stress_lay.addWidget(self.StressTypeCombo)
        self.options_stack.addWidget(stress_widget)
        
        render_layout.addWidget(self.options_stack)
        
        render_layout.addWidget(QLabel("<b>Scale:</b>"))
        self.ScaleFactorEditField_2 = QLineEdit("500"); self.ScaleFactorEditField_2.setFixedWidth(50)
        render_layout.addWidget(self.ScaleFactorEditField_2)
        
        self.AutoColorLimitSwitch = QCheckBox("Auto Color")
        self.AutoColorLimitSwitch.setChecked(True)
        self.AutoColorLimitSwitch.stateChanged.connect(self.toggle_color_limits)
        render_layout.addWidget(self.AutoColorLimitSwitch)
        
        self.CMinEdit = QLineEdit("-250"); self.CMinEdit.setFixedWidth(50); self.CMinEdit.setEnabled(False)
        self.CMaxEdit = QLineEdit("250"); self.CMaxEdit.setFixedWidth(50); self.CMaxEdit.setEnabled(False)
        render_layout.addWidget(QLabel("Min:"))
        render_layout.addWidget(self.CMinEdit)
        render_layout.addWidget(QLabel("Max:"))
        render_layout.addWidget(self.CMaxEdit)
        
        self.btn_apply_color = QPushButton("Apply Limit")
        self.btn_apply_color.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_apply_color.setEnabled(False)
        self.btn_apply_color.clicked.connect(self.update_visuals_only)
        render_layout.addWidget(self.btn_apply_color)
        
        self.btn_reset_cam = QPushButton("🎥 Default Views")
        self.btn_reset_cam.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
        self.btn_reset_cam.clicked.connect(self.reset_camera_view)
        render_layout.addWidget(self.btn_reset_cam)
        
        render_layout.addStretch()
        self.main_layout.addWidget(render_group, 0)

        # --- 3. Main Graphics Tab Area (Separated into Individual Parallel View Tabs) ---#
        self.graphics_tabs = QTabWidget()
        
        # Tab A: 3D Isometric
        self.tab_3d = QWidget(); layout_3d = QVBoxLayout(self.tab_3d)
        self.UIAxes_3D = QtInteractor(); layout_3d.addWidget(self.UIAxes_3D)
        self.graphics_tabs.addTab(self.tab_3d, "3D Isometric View")
        
        # Tab B: Front View (YZ)
        self.tab_front = QWidget(); layout_front = QVBoxLayout(self.tab_front)
        self.UIAxes_2D_Front = QtInteractor(); layout_front.addWidget(self.UIAxes_2D_Front)
        self.graphics_tabs.addTab(self.tab_front, "Front View (YZ)")
        
        # Tab C: Top View (XY)
        self.tab_top = QWidget(); layout_top = QVBoxLayout(self.tab_top)
        self.TopSliceCombo = QComboBox(); self.TopSliceCombo.addItems(["Top Layer", "Axis", "Bottom Layer"])
        self.TopSliceCombo.currentTextChanged.connect(self.on_top_slice_changed)
        layout_top.addWidget(self.TopSliceCombo)
        self.UIAxes_2D_Top = QtInteractor(); layout_top.addWidget(self.UIAxes_2D_Top)
        self.graphics_tabs.addTab(self.tab_top, "Top View (XY)")
        
        # Tab D: Section Cut (XZ)
        self.tab_sec = QWidget(); layout_sec = QVBoxLayout(self.tab_sec)
        self.SectionSlider = QSlider(Qt.Orientation.Horizontal); self.SectionSlider.setRange(0, 100); self.SectionSlider.setValue(50)
        self.SectionSlider.valueChanged.connect(self.on_section_change)
        self.lbl_sec = QLabel(f"Section Cut (Y): 0.0 mm")
        layout_sec.addWidget(self.lbl_sec); layout_sec.addWidget(self.SectionSlider)
        self.UIAxes_2D_Sec = QtInteractor(); layout_sec.addWidget(self.UIAxes_2D_Sec)
        self.graphics_tabs.addTab(self.tab_sec, "Section Cut (XZ)")

        # Assemble Splitting Panes (Graphics Tabs Left vs Matplotlib Lines Right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.graphics_tabs)
        
        right_panel = QWidget(); right_lay = QVBoxLayout(right_panel)
        right_lay.addWidget(QLabel("<b>Engineering Line Plots</b>"))
        self.line_figure = Figure(figsize=(4, 8), tight_layout=True)
        self.line_canvas = FigureCanvas(self.line_figure)
        right_lay.addWidget(self.line_canvas)
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([950, 350])
        self.main_layout.addWidget(main_splitter, 1)

        # Connect structural signals
        self.PrimaryModeCombo.currentIndexChanged.connect(self.switch_render_options)
        self.LoadPositionSlider_2.valueChanged.connect(self.on_slider_change)
        self.LoadValueNSlider.valueChanged.connect(self.on_force_change)
        self.LoadNEditField.textChanged.connect(self.on_text_force_change)
        self.AutoColorLimitSwitch.stateChanged.connect(self.toggle_color_limits)
        
        for w in [self.PrimaryModeCombo, self.FailDisplayCombo, self.FailMethodCombo, self.StressTypeCombo]:
            w.currentTextChanged.connect(self.update_visuals_only)
        self.graphics_tabs.currentChanged.connect(self.update_visuals_only)

    def reset_camera_view(self):
        """Forces all PyVista cameras into their unique engineered alignments."""
        if hasattr(self, 'UIAxes_3D'):
            self.UIAxes_3D.view_isometric()
            self.UIAxes_3D.reset_camera()
            self.UIAxes_3D.render()

        if hasattr(self, 'UIAxes_2D_Top'):
            self.UIAxes_2D_Top.view_xy()
            self.UIAxes_2D_Top.camera.parallel_projection = True
            # Apply a 90-degree twist around the viewing axis
            self.UIAxes_2D_Top.camera.roll=-90
            self.UIAxes_2D_Top.reset_camera(); self.UIAxes_2D_Top.render()

        if hasattr(self, 'UIAxes_2D_Front'):
            self.UIAxes_2D_Front.view_yz()
            self.UIAxes_2D_Front.camera.parallel_projection = True
            # Flip the front view upside down (90 degree rotation)
            self.UIAxes_2D_Front.camera.roll= 270
            self.UIAxes_2D_Front.reset_camera(); self.UIAxes_2D_Front.render()

        if hasattr(self, 'UIAxes_2D_Sec'):
            self.UIAxes_2D_Sec.view_xz()
            self.UIAxes_2D_Sec.camera.parallel_projection = True
            self.UIAxes_2D_Sec.reset_camera(); self.UIAxes_2D_Sec.render()

    def switch_render_options(self, index):
        self.options_stack.setCurrentIndex(index)
        self.update_visuals_only()

    def on_top_slice_changed(self):
        if hasattr(self, 'UIAxes_2D_Top'):
            self.UIAxes_2D_Top.view_xy(negative=("Bottom" in self.TopSliceCombo.currentText()))
            self.UIAxes_2D_Top.reset_camera(); self.UIAxes_2D_Top.render()
        self.update_visuals_only()  

    def toggle_simulation(self):
        self.isSimulating = not self.isSimulating
        if self.isSimulating:
            self.StartLiveTwinButton.setText('Simulation: ACTIVE')
            self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #3498db; color: white;") 
            self.run_DigitalTwin_Update()
        else:
            self.StartLiveTwinButton.setText('Start Simulation')
            self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #e0e0e0; color: black;")

    def on_slider_change(self, val):
        pos_m = (val / 100.0) * self.geometry.get('Lx', 1.0)
        self.lbl_pos.setText(f"Load Position: {pos_m * 1000.0:.1f} mm")
        if self.isSimulating: self.run_DigitalTwin_Update()

    def on_force_change(self, val):
        self.LoadNEditField.blockSignals(True)
        self.LoadNEditField.setText(str(val))
        self.LoadNEditField.blockSignals(False)
        if self.isSimulating: self.run_DigitalTwin_Update()

    def on_text_force_change(self):
        try:
            val = int(float(self.LoadNEditField.text()))
            self.LoadValueNSlider.blockSignals(True)
            self.LoadValueNSlider.setValue(val)
            self.LoadValueNSlider.blockSignals(False)
            if self.isSimulating: self.run_DigitalTwin_Update()
        except ValueError: pass

    def on_section_change(self, val):
        pos_m = (val / 100.0) * self.geometry.get('Lx', 1.0)
        self.lbl_sec.setText(f"<b>Section Cut (Y-Axis):</b> {pos_m * 1000.0:.1f} mm")
        if self.isSimulating and self.graphics_tabs.currentIndex() == 3:
            self.update_visuals_only()
    
    def toggle_color_limits(self):
        is_auto = self.AutoColorLimitSwitch.isChecked()
        self.CMinEdit.setEnabled(not is_auto); self.CMaxEdit.setEnabled(not is_auto)
        self.btn_apply_color.setEnabled(not is_auto)
        self.update_visuals_only()

    def run_DigitalTwin_Update(self, *args):
        if not self.isSimulating: return
        if self._is_rendering: return 
        self._is_rendering = True
        
        try:
            sg1 = self.StainGauge1Switch.isChecked()
            sg2 = self.StainGauge2Switch.isChecked()
            target_keyword = 'Fix' if (sg1 and sg2) else ('Cant' if (sg1 or sg2) else 'Simply')
                
            self.Active_ROM = next((r for r in self.DT_Bank if target_keyword.lower() in r['Label'].lower()), None)
            if self.Active_ROM is None: return

            self.launcher.offline_studio.node_coords = self.Active_ROM['Nodes']
            self.launcher.offline_studio.element_type = self.Active_ROM['ElementType']
            if 'Connectivity' in self.Active_ROM:
                self.launcher.offline_studio.element_connectivity = self.Active_ROM['Connectivity']

            load_pos_m = (self.LoadPositionSlider_2.value() / 100.0) * self.geometry['Lx']
            load_val = -abs(float(self.LoadValueNSlider.value())) 
            
            temp_loads = self.launcher.offline_studio.define_loads_at_pos(load_pos_m, load_val) 
            num_nodes = self.Active_ROM['NumNodes']; F_temp = np.zeros(num_nodes * 3)
            for j in range(len(temp_loads['point_nodes'])):
                node_id = temp_loads['point_nodes'][j]; force_vec = temp_loads['point_load_values'][:, j]
                F_temp[node_id*3 : node_id*3+3] += force_vec
                
            active_free_dofs = self.Active_ROM['bc_info']['free_dofs_indices']
            F_red = F_temp[active_free_dofs]
            
            alpha = np.linalg.solve(self.Active_ROM['K_rom'], self.Active_ROM['Phi'].T @ F_red) 
            self.current_U = np.zeros(num_nodes * 3); self.current_U[active_free_dofs] = self.Active_ROM['Phi'] @ alpha
            self.current_Sigma = (self.Active_ROM['Phi_stress'] @ alpha).reshape((num_nodes, 6))

            self._update_graphics()
            
        except Exception as e:
            print(traceback.format_exc())
            self.isSimulating = False
            self.StartLiveTwinButton.setText('Start Simulation')
        finally:
            self._is_rendering = False
            
       

    def update_visuals_only(self, *args):
        if not self.isSimulating or self.current_U is None: return
        if self._is_rendering: return
        self._is_rendering = True
        try: self._update_graphics()
        finally: self._is_rendering = False

    def _update_graphics(self):
        # Prevent rendering on uninitialized states
        if self.Active_ROM is None or self.current_U is None or self.current_Sigma is None:
            return
            
        mode = self.PrimaryModeCombo.currentText()
        try: sf = float(self.ScaleFactorEditField_2.text())
        except: sf = 500.0 
        try: yield_strength = float(self.launcher.offline_studio.YieldStrengthMpaEditField.text())
        except: yield_strength = 250.0 

        # --- COORDINATE MAPPING (New_X = -Old_Y, New_Y = Old_X, New_Z = -Old_Z) ---
        nodes = self.Active_ROM['Nodes']
        nodes_mapped = np.zeros_like(nodes)
        nodes_mapped[:, 0] = nodes[:, 1]  
        nodes_mapped[:, 1] = nodes[:, 0]   
        nodes_mapped[:, 2] = nodes[:, 2]  
        
        U_nodes = self.current_U.reshape(-1, 3)
        U_mapped = np.zeros_like(U_nodes)
        U_mapped[:, 0] =  U_nodes[:, 1]
        U_mapped[:, 1] =  U_nodes[:, 0]
        U_mapped[:, 2] =  U_nodes[:, 2]
        
        U_mapped_1d = U_mapped.flatten()
        def_coords = nodes_mapped + (U_mapped * sf)
        
        # Setup modern PyVista safe replacement grid
        if 'Hexa' in self.launcher.offline_studio.element_type: n_vis, vtk_type = 8, pv.CellType.HEXAHEDRON
        else: n_vis, vtk_type = 4, pv.CellType.TETRA
        cells_dict = {vtk_type: self.launcher.offline_studio.element_connectivity[:, :n_vis]}
        grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)

        
        # Color Bounds Scaling
        if self.AutoColorLimitSwitch.isChecked(): custom_clim = None
        else:
            try:
                c_min, c_max = float(self.CMinEdit.text()), float(self.CMaxEdit.text())
                custom_clim = [c_min, c_max] if c_min != c_max else [c_min, c_min + 1e-6]
            except: custom_clim = None

        current_tab_idx = self.graphics_tabs.currentIndex()
        # --- TAB 0: 3D VOLUME ISOMETRIC VIEW ---
        if current_tab_idx == 0:
            # Safely re-route mapped arrays through offline plotter definitions
            original_coords = self.launcher.offline_studio.node_coords
            self.launcher.offline_studio.node_coords = nodes_mapped
            
            if mode == "Stress":
                self.launcher.offline_studio.plot_stresses(self.current_Sigma, self.StressTypeCombo.currentText(), self.UIAxes_3D, U_mapped_1d, sf, custom_clim=custom_clim)
            else:
                self.launcher.offline_studio.plot_FS(self.FailMethodCombo.currentText(), yield_strength, self.UIAxes_3D, self.current_Sigma, U_mapped_1d, sf, self.FailDisplayCombo.currentText(), custom_clim=custom_clim)
            self.UIAxes_3D.update()
            self.launcher.offline_studio.node_coords = original_coords

        # --- TAB 1, 2, 3: HIGH-SPEED PARALLEL 2D EXTRACTIONS (Removes direct _actors references) ---
        elif current_tab_idx in [1,2,3]:
            
            scalars, cmap, plot_name = self.get_plot_scalars()
            if current_tab_idx == 1:
              grid_deformed.point_data[plot_name] = scalars

            else:
                # --- Generate the UN-DEFORMED static unstructured grid for Orthographic assessment ---
             grid_undeformed = pv.UnstructuredGrid(cells_dict, nodes_mapped)
             grid_undeformed.point_data[plot_name] = scalars

            c_limits = custom_clim if custom_clim is not None else [np.min(scalars), np.max(scalars) + 1e-6]
            sargs_horiz = dict(title_font_size=10, label_font_size=8, vertical=False, position_x=0.05, position_y=0.02, width=0.9, height=0.08)
            sargs_vert = dict(title_font_size=10, label_font_size=8, vertical=True, position_x=0.88, position_y=0.05, width=0.08, height=0.85)

            # TAB 1: FRONT VIEW (YZ Plane)
            if current_tab_idx == 1:
                self.UIAxes_2D_Front.clear() # Safe alternative to remove_actor()
                x_cut = (grid_deformed.bounds[0] + grid_deformed.bounds[1]) / 2.0
                try:
                    slice_front = grid_deformed.slice(normal='x', origin=(x_cut, 0, 0))
                    self.UIAxes_2D_Front.add_mesh(slice_front, name='front', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_vert, reset_camera=False)
                except: pass
                
                self.UIAxes_2D_Front.render()
                

           
            # ====================================================================
            # TAB 2: TOP VIEW (XY Plane Layer Cut - UNDEFORMED SHAPE)
            # ====================================================================
            elif current_tab_idx == 2:
                self.UIAxes_2D_Top.clear()
                z_max, z_min = np.max(nodes_mapped[:, 2]), np.min(nodes_mapped[:, 2])
                top_choice = self.TopSliceCombo.currentText()
                
                # Apply an epsilon offset inward from the boundary surfaces to prevent numerical clipping crashes
                if "Top" in top_choice:
                    target_z = z_max - 1e-4
                elif "Bottom" in top_choice:
                    target_z = z_min + 1e-4
                else:
                    target_z = (z_max + z_min) / 2.0
                    
                try:
                    slice_top = grid_undeformed.slice(normal='z', origin=(0, 0, target_z))
                    self.UIAxes_2D_Top.add_mesh(slice_top, name='top', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_horiz, reset_camera=False)
                except: pass
                
                # Keep camera standard rotation alignment updated
               
                self.UIAxes_2D_Top.render()

            # ====================================================================
            # TAB 3: SECTION CUT (XZ Plane Length Cross-Section - UNDEFORMED SHAPE)
            # ====================================================================
            elif current_tab_idx == 3:
                self.UIAxes_2D_Sec.clear()
                cut_y = (self.SectionSlider.value() / 100.0) * self.geometry['Lx']
                try:
                    # Slice the un-deformed grid so cross-sectional boundaries remain constant
                    slice_sec = grid_undeformed.slice(normal='y', origin=(0, cut_y, 0))
                    self.UIAxes_2D_Sec.add_mesh(slice_sec, name='section', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_horiz, reset_camera=False)
                except: pass
                
                self.UIAxes_2D_Sec.render()

        self.render_line_plots()

    def get_plot_scalars(self):
        mode = self.PrimaryModeCombo.currentText()
        if mode == "Stress":
            s_map = {'Sigma_xx': 0, 'Sigma_yy': 1, 'Sigma_zz': 2, 'Tau_xy': 3, 'Tau_yz': 4, 'Tau_zx': 5}
            col = s_map.get(self.StressTypeCombo.currentText(), 0)
            return self.current_Sigma[:, col] / 1e6, "jet", "Stress (MPa)"
        else:
            sx, sy, sz = self.current_Sigma[:, 0], self.current_Sigma[:, 1], self.current_Sigma[:, 2]
            txy, tyz, tzx = self.current_Sigma[:, 3], self.current_Sigma[:, 4], self.current_Sigma[:, 5]
            fail_mode = self.FailMethodCombo.currentText()
            num_nodes = len(sx)
            if "von mises" in fail_mode.lower():
                val = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
            elif "principal" in fail_mode.lower() or "tresca" in fail_mode.lower() or "shear" in fail_mode.lower():
                stress_tensors = np.zeros((num_nodes, 3, 3))
                stress_tensors[:, 0, 0] = sx; stress_tensors[:, 0, 1] = txy; stress_tensors[:, 0, 2] = tzx
                stress_tensors[:, 1, 0] = txy; stress_tensors[:, 1, 1] = sy;  stress_tensors[:, 1, 2] = tyz
                stress_tensors[:, 2, 0] = tzx; stress_tensors[:, 2, 1] = tyz; stress_tensors[:, 2, 2] = sz
                eigenvalues = np.linalg.eigvalsh(stress_tensors)
                val = eigenvalues[:, 2] / 1e6 if "principal" in fail_mode.lower() else (eigenvalues[:, 2] - eigenvalues[:, 0]) / 2.0 / 1e6
            else:
                val = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
                
            if self.FailDisplayCombo.currentText() == "Stress": return val, "jet", "Stress (MPa)"
            else:
                try: yield_strength = float(self.launcher.offline_studio.YieldStrengthMpaEditField.text())
                except: yield_strength = 250.0 
                return yield_strength / np.maximum(val, 1e-6), "jet_r", "Factor of Safety"

    def render_line_plots(self):
        nodes = self.Active_ROM['Nodes']
        y_top, y_bot = np.max(nodes[:, 1]), np.min(nodes[:, 1])
        y_mid = (y_top + y_bot) / 2.0  
        x_line = np.linspace(0, self.geometry['Lx'], 50)
        x_line_mm = x_line * 1000.0
        
        defl, s_top, s_bot, s_shear = [], [], [], []
        for x in x_line:
            idx_t = np.argmin(np.sqrt((nodes[:, 0]-x)**2 + (nodes[:, 1]-y_top)**2))
            idx_b = np.argmin(np.sqrt((nodes[:, 0]-x)**2 + (nodes[:, 1]-y_bot)**2))
            idx_m = np.argmin(np.sqrt((nodes[:, 0]-x)**2 + (nodes[:, 1]-y_mid)**2))
            defl.append(self.current_U[idx_t * 3 + 1] * 1000) 
            s_top.append(self.current_Sigma[idx_t, 0] / 1e6)              
            s_bot.append(self.current_Sigma[idx_b, 0] / 1e6) 
            s_shear.append(self.current_Sigma[idx_m, 3] / 1e6) 
            
        if not hasattr(self, '_line_initialized'):
            self.line_figure.clear()
            self.axL1 = self.line_figure.add_subplot(311)
            self.l_defl, = self.axL1.plot(x_line_mm, defl, 'b', linewidth=2)
            self.axL1.set_title("Deflection (mm)")
            
            self.axL2 = self.line_figure.add_subplot(312)
            self.l_top, = self.axL2.plot(x_line_mm, s_top, 'r', label='Tension Fiber')
            self.l_bot, = self.axL2.plot(x_line_mm, s_bot, 'g', label='Compression Fiber')
            self.axL2.set_title("Bending Stress (MPa)")
            
            self.axL3 = self.line_figure.add_subplot(313)
            self.l_shear, = self.axL3.plot(x_line_mm, s_shear, 'k', label='Neutral Axis')
            self.axL3.set_title("Shear Stress (MPa)")
            
            for ax in [self.axL1, self.axL2, self.axL3]:
                ax.grid(True, which='both', linestyle=':', alpha=0.5)
                ax.minorticks_on()
                
            self.line_figure.tight_layout()
            self._line_initialized = True
        else:
            self.l_defl.set_ydata(defl)
            self.l_top.set_ydata(s_top)
            self.l_bot.set_ydata(s_bot)
            self.l_shear.set_ydata(s_shear)
            for ax in [self.axL1, self.axL2, self.axL3]: 
                ax.relim(); ax.autoscale_view()

        if np.max(np.abs(s_top)) >= np.max(np.abs(s_bot)):
            self.l_top.set_label('Dominant: Tension')
            self.axL2.legend(handles=[self.l_top], loc='upper right', fontsize='small')
        else:
            self.l_bot.set_label('Dominant: Compression')
            self.axL2.legend(handles=[self.l_bot], loc='upper right', fontsize='small')
                
        self.line_canvas.draw_idle()

    def closeEvent(self, event):
        self.isSimulating = False
        try: 
            self.UIAxes_3D.close()
            self.UIAxes_2D_Top.close()
            self.UIAxes_2D_Front.close()
            self.UIAxes_2D_Sec.close()
        except: pass
        if hasattr(self, 'launcher') and self.launcher: self.launcher.visualizer_window = None 
        event.accept()


# =========================================================================
# MODULE 4: LIVE DIGITAL TWIN WINDOW (REAL-TIME SENSOR FUSION)
# =========================================================================
class LiveDigitalTwinWindow(QMainWindow):
    """Visualizes real-time sensor data mapped onto the ROM model with Ansys-style layouts."""
    def __init__(self, sensor_manager, dt_bank, geometry, launcher):
        super().__init__()
        self.setWindowTitle("Module 4: Online Digital Twin Monitor")
        self.setGeometry(100, 100, 1450, 950) 
        
        self.sm = sensor_manager
        self.DT_Bank = dt_bank
        self.geometry = geometry
        self.launcher = launcher 
        
        self._is_rendering = False 
        self.current_U = None
        self.current_Sigma = None
        self.Active_ROM = None
        self.active_beam_target = None
        self.auto_tare_on_removeLoad = True

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.build_ui()
        
        # --- BACKGROUND THREAD SETUP ---
        # Assuming HardwareWorker is defined elsewhere in your code
        self.hw_worker = HardwareWorker(self.sm)
        self.hw_worker.data_ready.connect(self.process_live_data)
        self.hw_worker.error_occurred.connect(self.handle_thread_error)
        
    def build_ui(self):

        # =================================================================
        # 1. TOP DASHBOARD (3-Column Professional Layout)
        # =================================================================
        top_container = QWidget()
        top_grid = QGridLayout(top_container)
        top_grid.setContentsMargins(5, 5, 5, 5)
        top_grid.setSpacing(10)

        # --- COLUMN 0: Header with Logo (Spans both rows) ---
        self.header = ProfessionalTheme.create_header_widget("Monitor")
        self.header.setFixedWidth(240)
        top_grid.addWidget(self.header, 0, 0, 2, 1)

        # --- COLUMN 1, ROW 0: Visualization Control ---
        view_grp = QGroupBox("Visualization Control")
        ProfessionalTheme.apply_professional_panel_style(view_grp)
        view_lay = QHBoxLayout(view_grp)
        view_lay.setContentsMargins(10, 2, 10, 2)
        
        self.PrimaryModeCombo = QComboBox(); self.PrimaryModeCombo.addItems(["Failure", "Stress"])
        self.options_stack = QStackedWidget()
        
        fail_c = QWidget(); fail_l = QHBoxLayout(fail_c); fail_l.setContentsMargins(0,0,0,0)
        self.FailDisplayCombo = QComboBox(); self.FailDisplayCombo.addItems(["FS", "Stress Intensity"])
        self.FailMethodCombo = QComboBox(); self.FailMethodCombo.addItems(["Von Mises", "Max Principal", "Max Shear (Tresca)"])
        fail_l.addWidget(self.FailDisplayCombo); fail_l.addWidget(self.FailMethodCombo)
        self.options_stack.addWidget(fail_c)
        
        stress_c = QWidget(); stress_l = QHBoxLayout(stress_c); stress_l.setContentsMargins(0,0,0,0)
        self.StressTypeCombo = QComboBox(); self.StressTypeCombo.addItems(["Sigma_xx", "Sigma_yy", "Sigma_zz", "Tau_xy", "Tau_yz", "Tau_zx"])
        stress_l.addWidget(self.StressTypeCombo); self.options_stack.addWidget(stress_c)
        self.PrimaryModeCombo.currentIndexChanged.connect(self.options_stack.setCurrentIndex)

        view_lay.addWidget(QLabel("Mode:")); view_lay.addWidget(self.PrimaryModeCombo); view_lay.addWidget(self.options_stack)
        
        view_lay.addWidget(QLabel("Scale:")); self.ScaleFactorEditField_2 = QLineEdit("500"); self.ScaleFactorEditField_2.setFixedWidth(40)
        view_lay.addWidget(self.ScaleFactorEditField_2)
        
        self.AutoColorLimitSwitch = QCheckBox("Auto Color"); self.AutoColorLimitSwitch.setChecked(True)
        view_lay.addWidget(self.AutoColorLimitSwitch)
        self.CMinEdit = QLineEdit("-250"); self.CMinEdit.setFixedWidth(40); self.CMinEdit.setEnabled(False)
        self.CMaxEdit = QLineEdit("250"); self.CMaxEdit.setFixedWidth(40); self.CMaxEdit.setEnabled(False)
        self.btn_apply_color = QPushButton("Apply"); self.btn_apply_color.setEnabled(False)
        view_lay.addWidget(QLabel("Min:")); view_lay.addWidget(self.CMinEdit); view_lay.addWidget(QLabel("Max:")); view_lay.addWidget(self.CMaxEdit); view_lay.addWidget(self.btn_apply_color)

        self.btn_reset_cam = QPushButton("🎥 View"); self.btn_reset_cam.setFixedWidth(50)
        view_lay.addWidget(self.btn_reset_cam)
        top_grid.addWidget(view_grp, 0, 1)

        # --- COLUMN 1, ROW 1: Cyber-Physics Interface ---
        in_grp = QGroupBox("Cyber-Physics Interface")
        ProfessionalTheme.apply_professional_panel_style(in_grp)
        in_lay = QHBoxLayout(in_grp)
        in_lay.setContentsMargins(10, 2, 10, 2)
        
        self.btn_connect_hw = QPushButton("Connect Hardware")
        self.btn_go_live = QPushButton("GO LIVE"); self.btn_go_live.setCheckable(True)
        in_lay.addWidget(self.btn_connect_hw); in_lay.addWidget(self.btn_go_live)
        
        self.in_Load = QLineEdit("0.0"); self.load_pos_m = QLineEdit("0.0")
        self.in_S1 = QLineEdit("0"); self.in_S2 = QLineEdit("0"); self.in_S3 = QLineEdit("0")
        
        for w in [self.in_Load, self.load_pos_m, self.in_S1, self.in_S2, self.in_S3]:
            w.setReadOnly(True); w.setFixedWidth(45); w.setStyleSheet(f"background: {ProfessionalTheme.CONSOLE_BG}; color: yellow;")
        
        in_lay.addWidget(QLabel("Load(N):")); in_lay.addWidget(self.in_Load)
        in_lay.addWidget(QLabel("Pos(mm):")); in_lay.addWidget(self.load_pos_m)
        in_lay.addWidget(QLabel("SG1(uE):")); in_lay.addWidget(self.in_S1)
        in_lay.addWidget(QLabel("SG2(uE):")); in_lay.addWidget(self.in_S2)
        in_lay.addWidget(QLabel("SG3(uE):")); in_lay.addWidget(self.in_S3)
        in_lay.addStretch()
        top_grid.addWidget(in_grp, 1, 1)

        # --- COLUMN 2: Live Predictions ---
        pred_grp = QGroupBox("Live Predictions")
        ProfessionalTheme.apply_professional_panel_style(pred_grp)
        pred_grid = QGridLayout(pred_grp)
        pred_grid.setContentsMargins(8, 4, 8, 4)
        pred_grid.setSpacing(6)

        self.predict_s1 = QLabel("P1: --")
        self.predict_s2 = QLabel("P2: --")
        self.predict_s3 = QLabel("P3: --")
        
        p_style = f"font-weight: bold; color: {ProfessionalTheme.SUCCESS_GREEN}; background: {ProfessionalTheme.CONSOLE_BG}; padding: 4px; border-radius: 3px; border: 1px solid #34495e;"
        for lbl in [self.predict_s1, self.predict_s2, self.predict_s3]:
            lbl.setStyleSheet(p_style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pre_s1_loc = QLineEdit("11")
        self.pre_s2_loc = QLineEdit("257")
        self.pre_s3_loc = QLineEdit("497")
        
        l_style = "border: 1px solid gray; border-radius: 2px; padding: 2px; background: white; font-weight: bold;"
        for le in [self.pre_s1_loc, self.pre_s2_loc, self.pre_s3_loc]:
            le.setFixedWidth(40); le.setFixedHeight(22); le.setStyleSheet(l_style)

        self.lbl_fs_status = QLabel("FS: --")
        self.lbl_fs_status.setStyleSheet("font-weight: bold; color: white; background: #2b5797; padding: 2px; border-radius: 4px;")
        self.lbl_fs_status.setFixedWidth(100) 
        self.lbl_fs_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fs_status.setWordWrap(True) 

        pred_grid.addWidget(self.predict_s1, 0, 0); pred_grid.addWidget(self.predict_s2, 1, 0); pred_grid.addWidget(self.predict_s3, 2, 0)

        style_label = "font-size: 8pt; font-weight: bold;"
        l1 = QLabel("L1:mm"); l1.setStyleSheet(style_label)
        l2 = QLabel("L2:mm"); l2.setStyleSheet(style_label)
        l3 = QLabel("L3:mm"); l3.setStyleSheet(style_label)

        pred_grid.addWidget(l1, 0, 1); pred_grid.addWidget(self.pre_s1_loc, 0, 2)
        pred_grid.addWidget(l2, 1, 1); pred_grid.addWidget(self.pre_s2_loc, 1, 2)
        pred_grid.addWidget(l3, 2, 1); pred_grid.addWidget(self.pre_s3_loc, 2, 2)
        pred_grid.addWidget(self.lbl_fs_status, 0, 3, 3, 1)

        pred_grid.setColumnStretch(0, 0); pred_grid.setColumnStretch(1, 0); pred_grid.setColumnStretch(2, 0); pred_grid.setColumnStretch(3, 0)
        top_grid.addWidget(pred_grp, 0, 2, 2, 1)
        top_grid.setColumnStretch(1, 1); top_grid.setColumnStretch(2, 1) 
        self.main_layout.addWidget(top_container)

        # =================================================================
        # 2. MAIN CONTENT AREA (Graphics + Plots)
        # =================================================================
        self.graphics_tabs = QTabWidget()
        
        # Tab A: 3D Isometric
        self.tab_3d = QWidget(); layout_3d = QVBoxLayout(self.tab_3d)
        self.UIAxes_3D = QtInteractor(); layout_3d.addWidget(self.UIAxes_3D)
        self.graphics_tabs.addTab(self.tab_3d, "3D Isometric View")
        
        # Tab B: Front View (YZ)
        self.tab_front = QWidget(); layout_front = QVBoxLayout(self.tab_front)
        self.UIAxes_2D_Front = QtInteractor(); layout_front.addWidget(self.UIAxes_2D_Front)
        self.graphics_tabs.addTab(self.tab_front, "Front View (YZ)")
        
        # Tab C: Top View (XY)
        self.tab_top = QWidget(); layout_top = QVBoxLayout(self.tab_top)
        self.TopSliceCombo = QComboBox(); self.TopSliceCombo.addItems(["Top Layer", "Axis", "Bottom Layer"])
        self.TopSliceCombo.currentTextChanged.connect(self.on_top_slice_changed)
        layout_top.addWidget(self.TopSliceCombo)
        self.UIAxes_2D_Top = QtInteractor(); layout_top.addWidget(self.UIAxes_2D_Top)
        self.graphics_tabs.addTab(self.tab_top, "Top View (XY)")
        
        # Tab D: Section Cut (XZ)
        self.tab_sec = QWidget(); layout_sec = QVBoxLayout(self.tab_sec)
        self.SectionSlider = QSlider(Qt.Orientation.Horizontal); self.SectionSlider.setRange(0, 100); self.SectionSlider.setValue(50)
        self.SectionSlider.valueChanged.connect(self.on_section_change)
        self.lbl_sec = QLabel(f"Section Cut (Y): 0.0 mm")
        layout_sec.addWidget(self.lbl_sec); layout_sec.addWidget(self.SectionSlider)
        self.UIAxes_2D_Sec = QtInteractor(); layout_sec.addWidget(self.UIAxes_2D_Sec)
        self.graphics_tabs.addTab(self.tab_sec, "Section Cut (XZ)")

        # Assemble Splitting Panes (Graphics Tabs Left vs Matplotlib Lines Right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.graphics_tabs)
        
        right_panel = QWidget(); right_lay = QVBoxLayout(right_panel)
        right_lay.addWidget(QLabel("<b>Engineering Line Plots</b>"))
        self.line_figure = Figure(figsize=(4, 8), tight_layout=True)
        self.line_canvas = FigureCanvas(self.line_figure)
        right_lay.addWidget(self.line_canvas)
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([950, 350])
        self.main_layout.addWidget(main_splitter, 1)

        # --- CORRECTED SIGNAL CONNECTIONS ---
        self.btn_connect_hw.clicked.connect(self.attempt_connect)
        self.btn_go_live.clicked.connect(self.toggle_live_feed)
        self.PrimaryModeCombo.currentIndexChanged.connect(self.update_visuals_only)
        self.SectionSlider.valueChanged.connect(self.on_section_change)
        self.AutoColorLimitSwitch.stateChanged.connect(self.toggle_color_limits)
        self.btn_apply_color.clicked.connect(self.update_visuals_only)
        self.btn_reset_cam.clicked.connect(self.reset_camera_view)
        
        for w in [self.PrimaryModeCombo, self.FailDisplayCombo, self.FailMethodCombo, self.StressTypeCombo]:
            w.currentTextChanged.connect(self.update_visuals_only)
        self.graphics_tabs.currentChanged.connect(self.update_visuals_only)

    # =================================================================
    # UI LOGIC & HARDWARE THREADING
    # =================================================================
    def attempt_connect(self):
        if hasattr(self.launcher, 'calib_window') and self.launcher.calib_window: 
            self.launcher.calib_window.handle_connect()
        else:
            if self.sm.connect(): QMessageBox.information(self, "Hardware", "Direct Connection Successful")
            else: QMessageBox.warning(self, "Hardware Error", "Could not connect to Arduino.")

    def toggle_live_feed(self, checked):
        if checked:
            self.btn_go_live.setText("⏹ STOP")
            self.btn_go_live.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.ERROR_RED, width=95))
            self.hw_worker.start()
        else:
            self.btn_go_live.setText("▶ LIVE")
            self.btn_go_live.setStyleSheet(ProfessionalTheme.create_button_style(ProfessionalTheme.SUCCESS_GREEN, width=95))
            self.hw_worker.stop()

    def handle_thread_error(self, err_msg):
        print(f"Hardware Thread Error:\n{err_msg}")
        self.btn_go_live.setChecked(False)

    def toggle_color_limits(self):
        is_auto = self.AutoColorLimitSwitch.isChecked()
        self.CMinEdit.setEnabled(not is_auto); self.CMaxEdit.setEnabled(not is_auto)
        self.btn_apply_color.setEnabled(not is_auto)
        self.update_visuals_only()

    def on_section_change(self, val):
        pos_m = (val / 100.0) * self.geometry['Lx']
        self.lbl_sec.setText(f"Section Cut (Y): {pos_m * 1000.0:.1f} mm")
        if self.graphics_tabs.currentIndex() == 3: self.update_visuals_only()

    def reset_camera_view(self):
        """Forces all PyVista cameras into their unique engineered alignments."""
        if hasattr(self, 'UIAxes_3D'):
            self.UIAxes_3D.view_isometric()
            self.UIAxes_3D.reset_camera()
            self.UIAxes_3D.render()

        if hasattr(self, 'UIAxes_2D_Top'):
            self.UIAxes_2D_Top.view_xy()
            self.UIAxes_2D_Top.camera.parallel_projection = True
            # Apply a 90-degree twist around the viewing axis
            self.UIAxes_2D_Top.camera.roll=90
            self.UIAxes_2D_Top.reset_camera(); self.UIAxes_2D_Top.render()

        if hasattr(self, 'UIAxes_2D_Front'):
            self.UIAxes_2D_Front.view_yz()
            self.UIAxes_2D_Front.camera.parallel_projection = True
            # Flip the front view upside down (90 degree rotation)
            self.UIAxes_2D_Front.camera.roll= 270
            self.UIAxes_2D_Front.reset_camera(); self.UIAxes_2D_Front.render()

        if hasattr(self, 'UIAxes_2D_Sec'):
            self.UIAxes_2D_Sec.view_xz()
            self.UIAxes_2D_Sec.camera.parallel_projection = True
            self.UIAxes_2D_Sec.reset_camera(); self.UIAxes_2D_Sec.render()


    def on_top_slice_changed(self):
        self.update_visuals_only()      

    def safe_add_mesh(self, interactor, mesh, name, **kwargs):
        """Safely add a mesh without triggering internal PyVista _actors crashes."""
        try:
            if name in interactor.renderer.actors:
                interactor.renderer.remove_actor(interactor.renderer.actors[name])
        except Exception: pass
        interactor.add_mesh(mesh, name=name, **kwargs)
        

    # =================================================================
    # REAL-TIME MATH (Triggered by Hardware Thread)
    # =================================================================
    def ensure_live_calibration_state(self):
        if not hasattr(self, 'active_beam_target'): self.active_beam_target = None
        if not hasattr(self, 'auto_tare_on_removeLoad'): self.auto_tare_on_removeLoad = True

    def process_live_data(self, strains, force_n, p_mm):
        if self._is_rendering: return  
        self._is_rendering = True
        
        try:
            self.ensure_live_calibration_state()
            
            # Update Hardware Readout Strings
            self.in_Load.setText(f"{force_n:.1f}")
            self.in_S1.setText(f"{strains[0]:.1f}")
            self.in_S2.setText(f"{strains[1]:.1f}")
            self.in_S3.setText(f"{strains[2]:.1f}")
            self.load_pos_m.setText(f"{p_mm:.1f}")

            # Ensure we always have an Active_ROM reference
            if self.Active_ROM is None:
                self.Active_ROM = self.DT_Bank[0]
            num_nodes = self.Active_ROM['NumNodes']

            # --- CHECK IF LOAD IS OFF (Triggers Auto-Tare) ---
            if abs(force_n) < 0.5:  
                raw = np.asarray(getattr(self.sm, 'live_raw', []), dtype=float)
                if raw.size >= 5:
                    self.sm.strain_tare_bits[:3] = raw[:3]
                    self.sm.strain_zero_bits = raw[1]
                    self.sm.load_tare = raw[3]
                
                self.predict_s1.setText("P1: 0.0 uE")
                self.predict_s2.setText("P2: 0.0 uE")
                self.predict_s3.setText("P3: 0.0 uE")
                self.lbl_fs_status.setText("Unladen: System & Load Cell Zeroed")
                self.lbl_fs_status.setStyleSheet("font-size: 11pt; font-weight: bold; background: #34495e; color: white; padding: 10px; border-radius: 6px;")
                
                # FIX: Do NOT clear the axes. Push a 0-stress state to the renderer instead!
                self.current_U = np.zeros(num_nodes * 3)
                self.current_Sigma = np.zeros((num_nodes, 6))
                self._update_graphics()
                
                self._is_rendering = False
                return  

            # --- BEAM CLASSIFICATION STRICTLY BY ACTIVE SENSOR DATA ---
            strains_array = np.array(strains, dtype=float)
            strain_signs = np.sign(strains_array)
            s1_opposes_s2 = strain_signs[0] != 0 and strain_signs[1] != 0 and strain_signs[0] != strain_signs[1]
            s3_opposes_s2 = strain_signs[2] != 0 and strain_signs[1] != 0 and strain_signs[2] != strain_signs[1]
            all_same_sign = np.all(strain_signs != 0) and np.all(strain_signs == strain_signs[0])

            if s1_opposes_s2 and s3_opposes_s2: target = 'Fix'
            elif all_same_sign and np.argmax(np.abs(strains_array)) == 1: target = 'Simply'
            else: target = 'Cant'

            self.active_beam_target = target
            self.Active_ROM = next((r for r in self.DT_Bank if target.lower() in r['Label'].lower()), self.DT_Bank[0])

            self.launcher.offline_studio.node_coords = self.Active_ROM['Nodes']
            self.launcher.offline_studio.element_type = self.Active_ROM['ElementType']
            if 'Connectivity' in self.Active_ROM: self.launcher.offline_studio.element_connectivity = self.Active_ROM['Connectivity']

            # --- Physics Projection Engine ---
            Lx = self.geometry['Lx']
            load_pos_m = max(0, min(p_mm / 1000.0, Lx))
            temp_loads = self.launcher.offline_studio.define_loads_at_pos(load_pos_m, force_n)
            
            F_temp = np.zeros(num_nodes * 3)
            for j in range(len(temp_loads['point_nodes'])):
                node_id = temp_loads['point_nodes'][j]
                force_vec = temp_loads['point_load_values'][:, j]
                F_temp[node_id*3 : node_id*3+3] += force_vec
            
            active_free_dofs = self.Active_ROM['bc_info']['free_dofs_indices']
            F_red = F_temp[active_free_dofs]
            alpha = np.linalg.solve(self.Active_ROM['K_rom'], self.Active_ROM['Phi'].T @ F_red)
            
            self.current_U = np.zeros(num_nodes * 3)
            self.current_U[active_free_dofs] = self.Active_ROM['Phi'] @ alpha
            self.current_Sigma = (self.Active_ROM['Phi_stress'] @ alpha).reshape((num_nodes, 6))

            # --- Validation Metrics Generation ---
            nodes = self.Active_ROM['Nodes']
            tol_x = Lx * 0.02  
            
            try: x_loc_1 = float(self.pre_s1_loc.text().strip()) / 1000.0
            except: x_loc_1 = Lx * 0.25
            try: x_loc_2 = float(self.pre_s2_loc.text().strip()) / 1000.0
            except: x_loc_2 = Lx * 0.50
            try: x_loc_3 = float(self.pre_s3_loc.text().strip()) / 1000.0
            except: x_loc_3 = Lx * 0.75
            
            mask_s1 = np.abs(nodes[:,0] - x_loc_1) < tol_x
            idx_s1 = np.where(mask_s1)[0][np.argmin(nodes[mask_s1, 2])] if np.any(mask_s1) else np.argmin(np.abs(nodes[:,0] - x_loc_1))
            mask_s2 = np.abs(nodes[:,0] - x_loc_2) < tol_x
            idx_s2 = np.where(mask_s2)[0][np.argmin(nodes[mask_s2, 2])] if np.any(mask_s2) else np.argmin(np.abs(nodes[:,0] - x_loc_2))
            mask_s3 = np.abs(nodes[:,0] - x_loc_3) < tol_x
            idx_s3 = np.where(mask_s3)[0][np.argmin(nodes[mask_s3, 2])] if np.any(mask_s3) else np.argmin(np.abs(nodes[:,0] - x_loc_3))
            
            E_mod = self.launcher.offline_studio.material['E']
            p1 = (self.current_Sigma[idx_s1, 0] / E_mod) * 1e6
            p2 = (self.current_Sigma[idx_s2, 0] / E_mod) * 1e6
            p3 = (self.current_Sigma[idx_s3, 0] / E_mod) * 1e6
            
            e1 = (abs(p1 - strains[0]) / max(abs(strains[0]), 1e-5)) * 100
            e2 = (abs(p2 - strains[1]) / max(abs(strains[1]), 1e-5)) * 100
            e3 = (abs(p3 - strains[2]) / max(abs(strains[2]), 1e-5)) * 100
            
            self.predict_s1.setText(f"{p1:.1f} uE (Err:{e1:.1f}%)")
            self.predict_s2.setText(f"{p2:.1f} uE (Err:{e2:.1f}%)")
            self.predict_s3.setText(f"{p3:.1f} uE (Err:{e3:.1f}%)")
            
            try: yield_strength = float(self.launcher.offline_studio.YieldStrengthMpaEditField.text())
            except: yield_strength = 250.0
            
            vm = np.sqrt(self.current_Sigma[:,0]**2 - self.current_Sigma[:,0]*self.current_Sigma[:,1] + self.current_Sigma[:,1]**2 + 3*self.current_Sigma[:,3]**2)
            fs = yield_strength / max(np.max(vm)/1e6, 1e-9) 
            
            if fs < 1.0:
                self.lbl_fs_status.setText("⚠️ FAILURE RISK ⚠️")
                self.lbl_fs_status.setStyleSheet(f"font-size: 11pt; font-weight: bold; background: {ProfessionalTheme.ERROR_RED}; color: white; padding: 10px; border-radius: 6px;")
            else:
                self.lbl_fs_status.setText(f"✓ FS: {fs:.2f} | SAFE")
                self.lbl_fs_status.setStyleSheet(f"font-size: 11pt; font-weight: bold; background: {ProfessionalTheme.SUCCESS_GREEN}; color: white; padding: 10px; border-radius: 6px;")

            # Finally, push data to the screens
            self._update_graphics()

        except Exception as e:
            print(traceback.format_exc())
            self.btn_go_live.setChecked(False)
        finally:
            self._is_rendering = False

    # =================================================================
    # GRAPHICS RENDERING ENGINE
    # =================================================================
    def update_visuals_only(self, *args):
        if self.current_U is None or self.current_Sigma is None: return
        if self._is_rendering: return
        self._is_rendering = True
        try: self._update_graphics()
        finally: self._is_rendering = False

    def get_plot_scalars(self):
        mode = self.PrimaryModeCombo.currentText()
        if mode == "Stress":
            s_map = {'Sigma_xx': 0, 'Sigma_yy': 1, 'Sigma_zz': 2, 'Tau_xy': 3, 'Tau_yz': 4, 'Tau_zx': 5}
            col = s_map.get(self.StressTypeCombo.currentText(), 0)
            return self.current_Sigma[:, col] / 1e6, "jet", "Stress (MPa)"
        else:
            sx, sy, sz = self.current_Sigma[:, 0], self.current_Sigma[:, 1], self.current_Sigma[:, 2]
            txy, tyz, tzx = self.current_Sigma[:, 3], self.current_Sigma[:, 4], self.current_Sigma[:, 5]
            fail_mode = self.FailMethodCombo.currentText()
            num_nodes = len(sx)
            
            if "von mises" in fail_mode.lower():
                val = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
            elif "principal" in fail_mode.lower() or "tresca" in fail_mode.lower() or "shear" in fail_mode.lower():
                stress_tensors = np.zeros((num_nodes, 3, 3))
                stress_tensors[:, 0, 0] = sx; stress_tensors[:, 0, 1] = txy; stress_tensors[:, 0, 2] = tzx
                stress_tensors[:, 1, 0] = txy; stress_tensors[:, 1, 1] = sy;  stress_tensors[:, 1, 2] = tyz
                stress_tensors[:, 2, 0] = tzx; stress_tensors[:, 2, 1] = tyz; stress_tensors[:, 2, 2] = sz
                eigenvalues = np.linalg.eigvalsh(stress_tensors)
                if "principal" in fail_mode.lower(): val = eigenvalues[:, 2] / 1e6
                else: val = (eigenvalues[:, 2] - eigenvalues[:, 0]) / 2.0 / 1e6
            else: val = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
                
            if self.FailDisplayCombo.currentText() == "Stress": return val, "jet", "Stress (MPa)"
            else:
                try: yield_strength = float(self.launcher.offline_studio.YieldStrengthMpaEditField.text())
                except: yield_strength = 250.0 
                return yield_strength / np.maximum(val, 1e-6), "jet_r", "Factor of Safety"

    def _update_graphics(self):
        if self.Active_ROM is None or self.current_U is None or self.current_Sigma is None:
            return
            
        mode = self.PrimaryModeCombo.currentText()
        try: sf = float(self.ScaleFactorEditField_2.text())
        except: sf = 500.0 
        try: yield_strength = float(self.launcher.offline_studio.YieldStrengthMpaEditField.text())
        except: yield_strength = 250.0 

        # --- COORDINATE MAPPING (New_X = -Old_Y, New_Y = Old_X, New_Z = -Old_Z) ---
        nodes = self.Active_ROM['Nodes']
        nodes_mapped = np.zeros_like(nodes)
        nodes_mapped[:, 0] = -nodes[:, 1]  
        nodes_mapped[:, 1] = nodes[:, 0]   
        nodes_mapped[:, 2] = -nodes[:, 2]  
        
        U_nodes = self.current_U.reshape(-1, 3)
        U_mapped = np.zeros_like(U_nodes)
        U_mapped[:, 0] = -U_nodes[:, 1]
        U_mapped[:, 1] = U_nodes[:, 0]
        U_mapped[:, 2] = -U_nodes[:, 2]
        
        U_mapped_1d = U_mapped.flatten()
        def_coords = nodes_mapped + (U_mapped * sf)
        
        if 'Hexa' in self.launcher.offline_studio.element_type: n_vis, vtk_type = 8, pv.CellType.HEXAHEDRON
        else: n_vis, vtk_type = 4, pv.CellType.TETRA
        cells_dict = {vtk_type: self.launcher.offline_studio.element_connectivity[:, :n_vis]}
        
        grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)

        # Color Bounds Scaling
        if self.AutoColorLimitSwitch.isChecked(): custom_clim = None
        else:
            try:
                c_min, c_max = float(self.CMinEdit.text()), float(self.CMaxEdit.text())
                custom_clim = [c_min, c_max] if c_min != c_max else [c_min, c_min + 1e-6]
            except: custom_clim = None

        current_tab_idx = self.graphics_tabs.currentIndex()

        # --- TAB 0: 3D VOLUME ISOMETRIC VIEW ---
        if current_tab_idx == 0:
            original_coords = self.launcher.offline_studio.node_coords
            self.launcher.offline_studio.node_coords = nodes_mapped
            
            if mode == "Stress":
                self.launcher.offline_studio.plot_stresses(self.current_Sigma, self.StressTypeCombo.currentText(), self.UIAxes_3D, U_mapped_1d, sf, custom_clim=custom_clim)
            else:
                self.launcher.offline_studio.plot_FS(self.FailMethodCombo.currentText(), yield_strength, self.UIAxes_3D, self.current_Sigma, U_mapped_1d, sf, self.FailDisplayCombo.currentText(), custom_clim=custom_clim)
            
            try: self.UIAxes_3D.add_text(f"Live Twin Active: {self.Active_ROM['Label']}", name="live_lbl", position='upper_right', color='red')
            except: pass
            
            self.UIAxes_3D.update()
            self.launcher.offline_studio.node_coords = original_coords

        # --- TAB 1, 2, 3: HIGH-SPEED PARALLEL 2D EXTRACTIONS ---
        elif current_tab_idx in [1, 2, 3]:
            scalars, cmap, plot_name = self.get_plot_scalars()
            c_limits = custom_clim if custom_clim is not None else [np.min(scalars), np.max(scalars) + 1e-6]
            sargs_horiz = dict(title_font_size=10, label_font_size=8, vertical=False, position_x=0.05, position_y=0.02, width=0.9, height=0.08)
            sargs_vert = dict(title_font_size=10, label_font_size=8, vertical=True, position_x=0.88, position_y=0.05, width=0.08, height=0.85)

            # TAB 1: FRONT VIEW (YZ Plane) - DEFORMED
            if current_tab_idx == 1:
                grid_deformed.point_data[plot_name] = scalars
                self.UIAxes_2D_Front.clear() 
                x_cut = (grid_deformed.bounds[0] + grid_deformed.bounds[1]) / 2.0
                try:
                    slice_front = grid_deformed.slice(normal='x', origin=(x_cut, 0, 0))
                    self.safe_add_mesh(self.UIAxes_2D_Front, slice_front, name='front', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_vert, reset_camera=False)
                except: pass
                
                if not hasattr(self, '_2d_cams_initialized'): 
                    self.UIAxes_2D_Front.view_yz()
                    self.UIAxes_2D_Front.camera.up = (0, 0, -1)
                self.UIAxes_2D_Front.render()

            # For Tabs 2 and 3: Create UNDEFORMED static grid
            if current_tab_idx in [2, 3]:
                grid_undeformed = pv.UnstructuredGrid(cells_dict, nodes_mapped)
                grid_undeformed.point_data[plot_name] = scalars

                # TAB 2: TOP VIEW (XY Plane Layer Cut) - STATIC
                if current_tab_idx == 2:
                    self.UIAxes_2D_Top.clear()
                    z_max, z_min = np.max(nodes_mapped[:, 2]), np.min(nodes_mapped[:, 2])
                    top_choice = self.TopSliceCombo.currentText()
                    
                    if "Top" in top_choice: target_z = z_max - 1e-4
                    elif "Bottom" in top_choice: target_z = z_min + 1e-4
                    else: target_z = (z_max + z_min) / 2.0
                        
                    try:
                        slice_top = grid_undeformed.slice(normal='z', origin=(0, 0, target_z))
                        self.safe_add_mesh(self.UIAxes_2D_Top, slice_top, name='top', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_horiz, reset_camera=False)
                    except: pass
                    
                    self.UIAxes_2D_Top.view_xy()
                    self.UIAxes_2D_Top.camera.roll = 90
                    self.UIAxes_2D_Top.render()

                # TAB 3: SECTION CUT (XZ Plane Length Cross-Section) - STATIC
                elif current_tab_idx == 3:
                    self.UIAxes_2D_Sec.clear()
                    cut_y = (self.SectionSlider.value() / 100.0) * self.geometry['Lx']
                    try:
                        slice_sec = grid_undeformed.slice(normal='y', origin=(0, cut_y, 0))
                        self.safe_add_mesh(self.UIAxes_2D_Sec, slice_sec, name='section', scalars=plot_name, cmap=cmap, clim=c_limits, show_edges=False, scalar_bar_args=sargs_horiz, reset_camera=False)
                    except: pass
                    
                    if not hasattr(self, '_2d_cams_initialized'):
                        self.UIAxes_2D_Sec.view_xz()
                        self.UIAxes_2D_Sec.camera.up = (0, 0, 1) # Prevent Warning
                    self.UIAxes_2D_Sec.render()

            if not hasattr(self, '_2d_cams_initialized'):
                self.UIAxes_2D_Top.enable_2d_style()
                self.UIAxes_2D_Front.enable_2d_style()
                self.UIAxes_2D_Sec.enable_2d_style()
                self.reset_camera_view()
                self._2d_cams_initialized = True

        self.render_line_plots()

    def render_line_plots(self):
        nodes = self.Active_ROM['Nodes']
        nodes_mapped = np.zeros_like(nodes)
        nodes_mapped[:, 0] = -nodes[:, 1]  
        nodes_mapped[:, 1] = nodes[:, 0]   
        nodes_mapped[:, 2] = -nodes[:, 2]  

        y_top, y_bot = np.max(nodes_mapped[:, 2]), np.min(nodes_mapped[:, 2])
        y_mid = (y_top + y_bot) / 2.0  
        x_center = (np.max(nodes_mapped[:, 0]) + np.min(nodes_mapped[:, 0])) / 2.0 
        
        y_line = np.linspace(0, self.geometry['Lx'], 50)
        y_line_mm = y_line * 1000.0
        
        U_mapped = np.zeros_like(self.current_U.reshape(-1, 3))
        U_mapped[:, 2] = -self.current_U.reshape(-1, 3)[:, 2]
        U_mapped_1d = U_mapped.flatten()

        defl, s_top, s_bot, s_shear = [], [], [], []
        for y_val in y_line:
            idx_t = np.argmin(np.sqrt((nodes_mapped[:, 1]-y_val)**2 + (nodes_mapped[:, 2]-y_top)**2 + (nodes_mapped[:, 0]-x_center)**2))
            idx_b = np.argmin(np.sqrt((nodes_mapped[:, 1]-y_val)**2 + (nodes_mapped[:, 2]-y_bot)**2 + (nodes_mapped[:, 0]-x_center)**2))
            idx_m = np.argmin(np.sqrt((nodes_mapped[:, 1]-y_val)**2 + (nodes_mapped[:, 2]-y_mid)**2 + (nodes_mapped[:, 0]-x_center)**2))
            
            defl.append(U_mapped_1d[idx_t * 3 + 2] * 1000) 
            s_top.append(self.current_Sigma[idx_t, 0] / 1e6)              
            s_bot.append(self.current_Sigma[idx_b, 0] / 1e6) 
            s_shear.append(self.current_Sigma[idx_m, 3] / 1e6) 
            
        if not hasattr(self, '_line_initialized'):
            self.line_figure.clear()
            self.axL1 = self.line_figure.add_subplot(311)
            self.l_defl, = self.axL1.plot(y_line_mm, defl, 'b', linewidth=2)
            self.axL1.set_title("Deflection (mm)")
            
            self.axL2 = self.line_figure.add_subplot(312)
            self.l_top, = self.axL2.plot(y_line_mm, s_top, 'r', label='Tension Fiber')
            self.l_bot, = self.axL2.plot(y_line_mm, s_bot, 'g', label='Compression Fiber')
            self.axL2.set_title("Bending Stress (MPa)")
            
            self.axL3 = self.line_figure.add_subplot(313)
            self.l_shear, = self.axL3.plot(y_line_mm, s_shear, 'k', label='Neutral Axis')
            self.axL3.set_title("Shear Stress (MPa)")
            
            for ax in [self.axL1, self.axL2, self.axL3]:
                ax.grid(True, which='both', linestyle=':', alpha=0.5)
                ax.minorticks_on()
                
            self.line_figure.tight_layout()
            self._line_initialized = True
        else:
            self.l_defl.set_ydata(defl)
            self.l_top.set_ydata(s_top)
            self.l_bot.set_ydata(s_bot)
            self.l_shear.set_ydata(s_shear)
            for ax in [self.axL1, self.axL2, self.axL3]: 
                ax.relim(); ax.autoscale_view()

        if np.max(np.abs(s_top)) >= np.max(np.abs(s_bot)):
            self.l_top.set_label('Dominant: Tension')
            self.axL2.legend(handles=[self.l_top], loc='upper right', fontsize='small')
        else:
            self.l_bot.set_label('Dominant: Compression')
            self.axL2.legend(handles=[self.l_bot], loc='upper right', fontsize='small')
                
        self.line_canvas.draw_idle()

    def closeEvent(self, event):
        if hasattr(self, 'hw_worker'): self.hw_worker.stop()
        try: 
            self.UIAxes_3D.close()
            self.UIAxes_2D_Top.close()
            self.UIAxes_2D_Front.close()
            self.UIAxes_2D_Sec.close()
        except: pass
        if hasattr(self, 'launcher') and self.launcher: self.launcher.live_window = None 
        event.accept()

# =========================================================================
# APPLICATION ENTRY POINT
# =========================================================================
def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    window = WorkbenchLaunchpad()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
