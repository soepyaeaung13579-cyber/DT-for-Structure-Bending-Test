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
import gc
import pickle
import traceback
import serial
from datetime import datetime

# Scientific and visualization imports
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import scipy.sparse.linalg as spla
from scipy.integrate import cumulative_trapezoid
import vtk
import pyvista as pv
from pyvistaqt import QtInteractor

# PyQt6 imports - organized by functionality
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QMessageBox, QInputDialog, QGridLayout,
    QTableWidgetItem, QLabel, QLineEdit, QComboBox, QTextEdit,
    QSlider, QCheckBox, QSplitter, QSizePolicy, QGroupBox, QTableWidget,
    QStackedWidget, QListWidget, QFileDialog, QTabWidget, QFrame,
    QProgressDialog, QDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QTime, QUrl, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QDesktopServices, QPixmap


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
    def create_header_widget(title_text, logo_path="CSE IMAGE.png"):
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

        title_label = QLabel(title_text)
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
    def apply_professional_panel_style(widget):
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
    def create_button_style(bg_color, text_color="white", hover_color=None, width=None):
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
    progress = pyqtSignal(int)

    def __init__(self, task_func, *args, **kwargs):
        """
        Initialize hardware worker.
        
        Args:
            task_func: Function to execute in background
            *args: Positional arguments for task_func
            **kwargs: Keyword arguments for task_func
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute the task in background thread."""
        try:
            self.task_func(*self.args, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            traceback.print_exc()


# =========================================================================
# WORKBENCH LAUNCHPAD (Main Application)
# =========================================================================
class WorkbenchLaunchpad(QMainWindow):
    """
    Main application launcher for the Digital Twin Workbench.
    Coordinates module initialization and user interface.
    """

    def __init__(self):
        """Initialize the main workbench launcher window."""
        super().__init__()
        self.setWindowTitle("Digital Twin Mechanical Testing Workbench")
        self.setGeometry(100, 100, 1400, 800)

        # Initialize component managers
        self.offline_studio = None
        self.visualizer_window = None
        self.calib_window = None
        self.live_window = None
        self.sm = None  # Sensor manager

        # Setup main UI
        self._setup_ui()
        self.log_msg("✓ Application initialized successfully")

    def _setup_ui(self):
        """Setup the complete user interface."""
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        main_widget = QWidget()
        main_widget.setLayout(self.main_layout)
        self.setCentralWidget(main_widget)

        # Add header
        header = ProfessionalTheme.create_header_widget("Mechanical Testing Workbench")
        self.main_layout.addWidget(header)

        # Add content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        self._setup_content(content_layout)
        self.main_layout.addWidget(content_widget, 1)

    def _setup_content(self, layout):
        """
        Setup main content area.
        
        Args:
            layout (QVBoxLayout): Parent layout to add content to
        """
        # Top splitter: Sidebar + Schematic
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ====================================================================
        # 1. LEFT SIDEBAR - STATUS & MODULE SELECTION
        # ====================================================================
        sidebar_grp = QGroupBox("System Control Panel")
        ProfessionalTheme.apply_professional_panel_style(sidebar_grp)
        sidebar_lay = QVBoxLayout(sidebar_grp)

        # Status indicators
        self.lbl_active_module = QLabel("🔵 Active Module: None")
        self.lbl_rom_status = QLabel("🔴 ROM Data: Not Loaded")
        self.lbl_hw_status = QLabel("🔴 Hardware: Disconnected")

        for lbl in [self.lbl_active_module, self.lbl_rom_status, self.lbl_hw_status]:
            lbl.setFont(QFont("Segoe UI", 10))
            sidebar_lay.addWidget(lbl)

        sidebar_lay.addSpacing(10)

        # Module buttons
        self.btn_offline = QPushButton("M1: Offline\nStudio")
        self.btn_offline.setMinimumHeight(80)
        self.btn_offline.setStyleSheet(ProfessionalTheme.create_button_style(
            ProfessionalTheme.PRIMARY_BLUE
        ))
        self.btn_offline.clicked.connect(self.launch_offline_studio)
        sidebar_lay.addWidget(self.btn_offline)

        self.btn_calib = QPushButton("M3: Sensor\nCalibration")
        self.btn_calib.setMinimumHeight(80)
        self.btn_calib.setStyleSheet(ProfessionalTheme.create_button_style(
            ProfessionalTheme.WARNING_ORANGE
        ))
        self.btn_calib.clicked.connect(self.launch_calibration)
        sidebar_lay.addWidget(self.btn_calib)

        self.btn_vis = QPushButton("M2: ROM\nVisualizer")
        self.btn_vis.setMinimumHeight(80)
        self.btn_vis.setStyleSheet(ProfessionalTheme.create_button_style(
            ProfessionalTheme.SUCCESS_GREEN
        ))
        self.btn_vis.clicked.connect(self.launch_rom_visualizer)
        sidebar_lay.addWidget(self.btn_vis)

        self.btn_live = QPushButton("M4: Live\nDigital Twin")
        self.btn_live.setMinimumHeight(80)
        self.btn_live.setStyleSheet(ProfessionalTheme.create_button_style(
            ProfessionalTheme.INFO_PURPLE
        ))
        self.btn_live.clicked.connect(self.launch_live_twin)
        sidebar_lay.addWidget(self.btn_live)

        sidebar_lay.addStretch()

        # Help buttons
        btn_student = QPushButton("📘 Student Manual")
        btn_student.setStyleSheet(ProfessionalTheme.create_button_style("#34495e"))
        btn_student.clicked.connect(self.open_student_manual)
        sidebar_lay.addWidget(btn_student)

        btn_instructor = QPushButton("📙 Instructor Manual")
        btn_instructor.setStyleSheet(ProfessionalTheme.create_button_style("#34495e"))
        btn_instructor.clicked.connect(self.open_instructor_manual)
        sidebar_lay.addWidget(btn_instructor)

        self.top_splitter.addWidget(sidebar_grp)

        # ====================================================================
        # 2. CENTER AREA - WORKFLOW SCHEMATIC
        # ====================================================================
        schematic_grp = QGroupBox("Module Workflow Schematic")
        ProfessionalTheme.apply_professional_panel_style(schematic_grp)
        schematic_lay = QVBoxLayout(schematic_grp)
        schematic_grid = QGridLayout()
        schematic_lay.addLayout(schematic_grid)

        def make_connector(text, align):
            """Helper to create connector label."""
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
        schematic_grid.addWidget(
            make_connector("╚", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom),
            3, 0
        )
        schematic_grid.addWidget(
            make_connector("╝", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom),
            3, 2
        )
        schematic_grid.addWidget(self.btn_live, 4, 1)

        # Set equal stretching for columns and rows
        for i in range(3):
            schematic_grid.setColumnStretch(i, 1)
        for i in range(5):
            schematic_grid.setRowStretch(i, 1)

        self.top_splitter.addWidget(schematic_grp)
        self.top_splitter.setSizes([250, 750])  # Sidebar 25%, Schematic 75%

        # ====================================================================
        # 3. BOTTOM TERMINAL CONSOLE
        # ====================================================================
        console_grp = QGroupBox("System Output Console")
        ProfessionalTheme.apply_professional_panel_style(console_grp)
        console_lay = QVBoxLayout(console_grp)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(f"""
            background-color: {ProfessionalTheme.CONSOLE_BG};
            color: {ProfessionalTheme.CONSOLE_TEXT};
            font-family: Consolas, 'Courier New', monospace;
            font-size: 11px;
            border: 1px solid {ProfessionalTheme.BORDER_COLOR};
            border-radius: 4px;
        """)
        console_lay.addWidget(self.console_output)

        # Main Vertical Splitter
        self.main_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_v_splitter.addWidget(self.top_splitter)
        self.main_v_splitter.addWidget(console_grp)
        self.main_v_splitter.setSizes([500, 150])

        layout.addWidget(self.main_v_splitter)
        self.update_system_status()

    # --- SYSTEM UTILITIES ---
    def log_msg(self, msg):
        """
        Log a message to the console output.
        
        Args:
            msg (str): Message to log
        """
        if not hasattr(self, 'console_output'):
            print(msg)
            return

        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.console_output.append(f"[{timestamp}] {msg}")

        # Scroll to bottom
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_system_status(self):
        """Check system components and update status indicators."""
        # Check ROM data
        if hasattr(self, 'offline_studio') and hasattr(self.offline_studio, 'DT_Bank'):
            if len(self.offline_studio.DT_Bank) > 0:
                self.lbl_rom_status.setText("🟢 ROM Data: Loaded in RAM")
                self.lbl_rom_status.setStyleSheet("color: green;")
            else:
                self.lbl_rom_status.setText("🔴 ROM Data: Not Loaded")
                self.lbl_rom_status.setStyleSheet("color: red;")
        else:
            self.lbl_rom_status.setText("🔴 ROM Data: Not Loaded")
            self.lbl_rom_status.setStyleSheet("color: red;")

        # Check hardware connection
        if hasattr(self, 'sm') and self.sm is not None and self.sm.is_connected:
            self.lbl_hw_status.setText(f"🟢 Hardware: Connected ({self.sm.port})")
            self.lbl_hw_status.setStyleSheet("color: green;")
        else:
            self.lbl_hw_status.setText("🔴 Hardware: Disconnected")
            self.lbl_hw_status.setStyleSheet("color: red;")

    def manual_load_rom(self):
        """Allow user to manually load ROM bank from file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open ROM Bank File", "", "Pickle Files (*.pkl)"
        )
        if file_name:
            try:
                with open(file_name, 'rb') as f:
                    self.offline_studio.DT_Bank = pickle.load(f)
                file_basename = os.path.basename(file_name)
                self.log_msg(f"SUCCESS: Loaded ROM Bank from {file_basename}")
                self.update_system_status()
            except Exception as e:
                self.log_msg(f"ERROR: Failed to load ROM - {str(e)}")
                traceback.print_exc()

    # --- MODULE LAUNCHERS ---
    def launch_offline_studio(self):
        """Launch Module 1: Offline Preparation Studio."""
        self.log_msg("Launching Module 1: Offline Preparation Studio...")
        self.lbl_active_module.setText("🔵 Active Module: M1 (Offline Studio)")
        if self.offline_studio is None:
            self.offline_studio = OfflinePreparationStudio()
        self.offline_studio.show()
        self.offline_studio.activateWindow()
        self.update_system_status()

    def launch_rom_visualizer(self):
        """Launch Module 2: ROM Interactive Visualizer."""
        if (not hasattr(self.offline_studio, 'DT_Bank') or
                len(self.offline_studio.DT_Bank) == 0):
            self.log_msg("WARNING: Module 2 requires ROM Data. Prompting load...")
            self.manual_load_rom()
            if (not hasattr(self.offline_studio, 'DT_Bank') or
                    len(self.offline_studio.DT_Bank) == 0):
                self.log_msg("ABORT: No ROM loaded.")
                return

        self.log_msg("Launching Module 2: ROM Interactive Visualizer...")
        self.lbl_active_module.setText("🔵 Active Module: M2 (ROM Visualizer)")
        if self.visualizer_window is None:
            self.visualizer_window = ROMVisualizerWindow(
                dt_bank=self.offline_studio.DT_Bank,
                geometry=self.offline_studio.geometry,
                launcher=self
            )
        self.visualizer_window.show()
        self.visualizer_window.activateWindow()

    def launch_calibration(self):
        """Launch Module 3: Physical Sensor Calibration."""
        self.log_msg("Launching Module 3: Physical Sensor Calibration...")
        self.lbl_active_module.setText("🔵 Active Module: M3 (Sensor Calibration)")
        if self.calib_window is None:
            self.calib_window = CalibrationWindow(
                self.sm,
                self.offline_studio.geometry
            )
        self.calib_window.show()
        self.calib_window.activateWindow()

    def launch_live_twin(self):
        """Launch Module 4: Online Digital Twin Monitor."""
        if (not hasattr(self.offline_studio, 'DT_Bank') or
                len(self.offline_studio.DT_Bank) == 0):
            self.log_msg("WARNING: Module 4 requires ROM Data. Prompting load...")
            self.manual_load_rom()
            if (not hasattr(self.offline_studio, 'DT_Bank') or
                    len(self.offline_studio.DT_Bank) == 0):
                self.log_msg("ABORT: No ROM loaded.")
                return

        self.log_msg("Launching Module 4: Online Digital Twin Monitor...")
        self.lbl_active_module.setText("🔵 Active Module: M4 (Online Digital Twin)")
        if self.live_window is None:
            self.live_window = LiveDigitalTwinWindow(
                sensor_manager=self.sm,
                dt_bank=self.offline_studio.DT_Bank,
                geometry=self.offline_studio.geometry,
                launcher=self
            )
        self.live_window.show()
        self.live_window.activateWindow()

    def open_student_manual(self):
        """Open the student lab manual PDF."""
        pdf_path = os.path.abspath("Student_Manual.pdf")
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            self.log_msg("📘 Opened Student Lab Manual.")
        else:
            error_msg = (f"Could not find the file:\n{pdf_path}\n\n"
                        "Please ensure the PDF is in the same folder as the software.")
            QMessageBox.warning(self, "File Not Found", error_msg)
            self.log_msg("ERROR: Student Manual PDF not found.")

    def open_instructor_manual(self):
        """Open the instructor manual PDF."""
        pdf_path = os.path.abspath("Instructor_Manual.pdf")
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
            self.log_msg("📙 Opened Instructor Manual.")
        else:
            error_msg = (f"Could not find the file:\n{pdf_path}\n\n"
                        "Please ensure the PDF is in the same folder as the software.")
            QMessageBox.warning(self, "File Not Found", error_msg)
            self.log_msg("ERROR: Instructor Manual PDF not found.")


# Placeholder classes for module windows
class OfflinePreparationStudio(QMainWindow):
    """Module 1: Offline Preparation Studio."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Module 1: Offline Preparation Studio")
        self.DT_Bank = []
        self.geometry = None
        self.setGeometry(200, 200, 1000, 700)


class ROMVisualizerWindow(QMainWindow):
    """Module 2: ROM Interactive Visualizer."""
    def __init__(self, dt_bank, geometry, launcher):
        super().__init__()
        self.setWindowTitle("Module 2: ROM Visualizer")
        self.dt_bank = dt_bank
        self.geometry = geometry
        self.launcher = launcher
        self.setGeometry(300, 300, 1000, 700)


class CalibrationWindow(QMainWindow):
    """Module 3: Sensor Calibration."""
    def __init__(self, sensor_manager, geometry):
        super().__init__()
        self.setWindowTitle("Module 3: Sensor Calibration")
        self.sensor_manager = sensor_manager
        self.geometry = geometry
        self.setGeometry(400, 400, 1000, 700)


class LiveDigitalTwinWindow(QMainWindow):
    """Module 4: Live Digital Twin Monitor."""
    def __init__(self, sensor_manager, dt_bank, geometry, launcher):
        super().__init__()
        self.setWindowTitle("Module 4: Live Digital Twin")
        self.sensor_manager = sensor_manager
        self.dt_bank = dt_bank
        self.geometry = geometry
        self.launcher = launcher
        self.setGeometry(500, 500, 1000, 700)


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
