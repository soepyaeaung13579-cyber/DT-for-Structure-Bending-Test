"""
Displacement ROM Testing System
================================================


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
import scipy.linalg as la
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

# ===============================================
# 1. OFFLINE STUDIO (MODULE 1) - ANSYS WORKBENCH STYLE
# =========================================================================
class OfflinePreparationStudio(QMainWindow):
    """The Main Offline Studio, utilizing a Workflow Tree instead of Tabs."""
    
    def closeEvent(self, event):
        """Cleanly shut down all PyVista OpenGL windows to prevent handle errors on exit."""
        pyvista_plotters = ['UIAxes', 'UIAxes2', 'UIAxes3', 'UIAxes_3D_Validation', 'UIAxes5', 'UIAxes6', 'UIAxes9', 'UIAxes10', 'UIAxes11']
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
        self.sigma_gauss_all = None
        self.Phi = None; self.Phi_nodal_stress = None; self.K_rom = None; self.DT_Bank = []
        self.BC={}
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
            "4. Post-Processing",
            "5. ROM Training",
            "6. ROM Validation & Save"
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
        self.stacked_widget.addWidget(self.create_panel4_post_processing())
        self.stacked_widget.addWidget(self.create_panel5_rom_training())
        self.stacked_widget.addWidget(self.create_panel6_rom_validation())

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
            self.Phi = None; self.Phi_nodal_stress = None; self.K_rom = None

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
        self.Phi_full = None
        self.S_disp = None
        self.cum_energy_disp = None
        self.energy_variance = None
        self.Phi_nodal_stress = None
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
        self.UIAxes5.clear(); self.UIAxes5.add_axes(); self.UIAxes5.update()
        self.UIAxes6.clear(); self.UIAxes6.add_axes(); self.UIAxes6.update()

    def action_clear_panel5(self):
        self.fig_svd.clf(); self.UIAxes8.draw_idle()
        self.clear_downstream_data('rom_train')

    def action_clear_panel6(self):
        self.UIAxes9.clear(); self.UIAxes9.add_axes(); self.UIAxes9.update()
        self.UIAxes10.clear(); self.UIAxes10.add_axes(); self.UIAxes10.update()
        self.UIAxes11.clear(); self.UIAxes11.add_axes(); self.UIAxes11.update()

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
        self.IntpointDropDown.addItems(["Full", "Reduce","14point"])
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
        self.BeamTypeDropDown = QComboBox(); self.BeamTypeDropDown.addItems(["Cantilever", "Fixed-Fixed", "Simply Supported", "Elastic Foundation"])
        vbox_beam.addWidget(self.BeamTypeDropDown); top_layout.addLayout(vbox_beam)
        
        vbox_foundation = QVBoxLayout()
        vbox_foundation.addWidget(QLabel("<b>Foundation K (N/m):</b>"))
        self.FoundationStiffnessEditField = QLineEdit("1e6")
        self.FoundationStiffnessEditField.setFixedWidth(100)
        vbox_foundation.addWidget(self.FoundationStiffnessEditField)
        top_layout.addLayout(vbox_foundation)
        
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

    def create_panel4_post_processing(self):
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
        btn_clear.clicked.connect(self.action_clear_panel4)
        top_layout.addWidget(btn_clear)
        
        layout.addWidget(top_widget, 0) 
        
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.UIAxes5 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes5)
        self.UIAxes6 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes6)
        bottom_splitter.setSizes([500, 500]); layout.addWidget(bottom_splitter, 1) 
        return panel

    def create_panel5_rom_training(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("<b>Number of Snapshots:</b>"))
        self.num_snapshotsEditField = QLineEdit("12"); self.num_snapshotsEditField.setFixedWidth(60)
        input_layout.addWidget(self.num_snapshotsEditField)
        
        input_layout.addWidget(QLabel("<b>Disp Modes:</b>"))
        self.disp_modeEditField = QLineEdit("Auto"); self.disp_modeEditField.setFixedWidth(60)
        self.disp_modeEditField.setToolTip("Enter number of displacement modes to retain (e.g. 5, 8) or 'Auto' to use energy threshold recommendation.")
        self.disp_modeEditField.editingFinished.connect(self.update_rom_mode_selection)
        input_layout.addWidget(self.disp_modeEditField)
        
        self.SnapshotMethodDropDown = QComboBox(); self.SnapshotMethodDropDown.addItems(["USS", "BCSS"])
        input_layout.addWidget(QLabel("<b>Snapshot Method:</b>")); input_layout.addWidget(self.SnapshotMethodDropDown)
        
        self.BCSSBoundaryDropDown = QComboBox(); self.BCSSBoundaryDropDown.addItems(["Cantilever", "Fixed-Fixed"])
        input_layout.addWidget(QLabel("<b>BCSS Boundary:</b>")); input_layout.addWidget(self.BCSSBoundaryDropDown)
        self.SnapshotMethodDropDown.currentIndexChanged.connect(self._update_snapshot_controls)
        self._update_snapshot_controls()
        input_layout.addStretch()
        
        # --- MEMORY FIX: Clear ROM data before retraining ---
        btn_clear_rom = QPushButton("🧹 Clear ROM Memory")
        btn_clear_rom.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 10px 15px; border-radius: 5px;")
        btn_clear_rom.clicked.connect(self.clear_rom_memory)
        input_layout.addWidget(btn_clear_rom)
        
        btn_train = QPushButton("Start ROM Training")
        btn_train.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 5px;")
        btn_train.clicked.connect(self.TrainButtonPushed); input_layout.addWidget(btn_train)

        btn_reconstruct = QPushButton("⚡ Reconstruct ROM")
        btn_reconstruct.setStyleSheet("font-weight: bold; padding: 10px 15px; background-color: #27ae60; color: white; border-radius: 5px;")
        btn_reconstruct.setToolTip("Fast update ROM basis parameters, stiffness matrix projection, and stress modes for user-defined Disp Modes without re-solving snapshots.")
        btn_reconstruct.clicked.connect(self.update_rom_mode_selection); input_layout.addWidget(btn_reconstruct)
        
        # --- NEW: Improved Clear Graphics Button ---
        btn_clear = QPushButton("🗑️ Clear SVD Plot")
        btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px 20px; border-radius: 5px;")
        btn_clear.clicked.connect(self.action_clear_panel5)
        input_layout.addWidget(btn_clear)
        
        layout.addLayout(input_layout)
        
        layout.addWidget(QLabel("<b>Training Log & Time:</b>"))
        self.TrainningTimeTextArea = QTextEdit(); self.TrainningTimeTextArea.setReadOnly(True)
        self.TrainningTimeTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        self.TrainningTimeTextArea.setMaximumHeight(150); layout.addWidget(self.TrainningTimeTextArea)
        
        layout.addWidget(QLabel("<b>ROM Invariance (Singular Value Decomposition)</b>"))
        self.fig_svd = Figure(); self.UIAxes8 = FigureCanvas(self.fig_svd); layout.addWidget(self.UIAxes8)
        return panel

    def create_panel6_rom_validation(self):
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
        btn_clear_graphics.clicked.connect(self.action_clear_panel6)
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
        label_fem = QLabel("<b>FEM Stress</b>"); label_fem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.UIAxes9 = QtInteractor(fem_widget)
        fem_layout.addWidget(label_fem); fem_layout.addWidget(self.UIAxes9)
        right.addWidget(fem_widget)
        
        rom_widget = QWidget()
        rom_layout = QVBoxLayout(rom_widget)
        label_rom = QLabel("<b>ROM Stress</b>"); label_rom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.UIAxes10 = QtInteractor(rom_widget)
        rom_layout.addWidget(label_rom); rom_layout.addWidget(self.UIAxes10)
        right.addWidget(rom_widget)

        nmae_widget = QWidget()
        nmae_layout = QVBoxLayout(nmae_widget)
        label_nmae = QLabel("<b>Abs Error / NMAE Contour</b>"); label_nmae.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.UIAxes11 = QtInteractor(nmae_widget)
        nmae_layout.addWidget(label_nmae); nmae_layout.addWidget(self.UIAxes11)
        right.addWidget(nmae_widget)

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
        
        self.UIAxes.clear()
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
        self.foundation_stiffness = float(self.FoundationStiffnessEditField.text()) if hasattr(self, 'FoundationStiffnessEditField') else 1e6
        
        self.generate_mesh_3d()
        
        if 'Hexa' in self.element_type: n_vis, vtk_type = 8, pv.CellType.HEXAHEDRON
        else: n_vis, vtk_type = 4, pv.CellType.TETRA
            
        vis_connectivity = self.element_connectivity[:, :n_vis]
        cells_dict = {vtk_type: vis_connectivity}
        self.grid = pv.UnstructuredGrid(cells_dict, self.node_coords)
        
        self.UIAxes2.clear()
        self.UIAxes2.add_mesh(self.grid, name='mesh_geom', show_edges=True, color="lightblue", opacity=0.8)
        
        if not hasattr(self.UIAxes2, 'axes_widget_added'):
            self.UIAxes2.add_axes()
            self.UIAxes2.axes_widget_added = True
            
        self.UIAxes2.reset_camera()
        self.UIAxes2.update()
        
        self.MeshinfoTextArea.setText(f"Element Type: {self.element_type}\nTotal nodes: {self.mesh_info['num_nodes']}\nTotal elements: {self.mesh_info['num_elements']}")
        
    def _apply_square_hole(self, node_coords, connectivity, Lx, Ly, hole_params):
        if hole_params is None:
            hole_params = {'size': 0.0, 'cx': 0.0, 'cy': 0.0}
        hole_size = hole_params.get('size', 0.0)
        if hole_size <= 0.0:
            return node_coords, connectivity

        cx = hole_params.get('cx', Lx / 2.0)
        cy = hole_params.get('cy', Ly / 2.0)
        if connectivity.size == 0:
            return node_coords, connectivity

        half_size = hole_size / 2.0
        elem_nodes = node_coords[connectivity]
        inside_nodes = (
            (elem_nodes[:, :, 0] >= cx - half_size) &
            (elem_nodes[:, :, 0] <= cx + half_size) &
            (elem_nodes[:, :, 1] >= cy - half_size) &
            (elem_nodes[:, :, 1] <= cy + half_size)
        )
        remove_element = np.all(inside_nodes, axis=1)
        kept_conn = connectivity[~remove_element]
        if kept_conn.size == 0:
            return np.empty((0, 3), dtype=float), np.empty((0, connectivity.shape[1]), dtype=int)

        used_nodes = np.unique(kept_conn)
        node_map = -np.ones(node_coords.shape[0], dtype=int)
        node_map[used_nodes] = np.arange(len(used_nodes))
        new_coords = node_coords[used_nodes]
        new_conn = node_map[kept_conn]
        return new_coords, new_conn

    def generate_hexa8_mesh(self, Lx, Ly, Lz, nx, ny, nz, hole_params=None):
        x = np.linspace(0, Lx, nx + 1)
        y = np.linspace(0, Ly, ny + 1)
        z = np.linspace(0, Lz, nz + 1)
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
        node_coords, connectivity = self._apply_square_hole(node_coords, connectivity, Lx, Ly, hole_params)
        return node_coords, connectivity, {'num_nodes': len(node_coords), 'num_elements': len(connectivity), 'nodes_per_element': 8}

    def generate_hexa20_mesh(self, Lx, Ly, Lz, nx, ny, nz, hole_params=None):
        hex8_nodes, hex8_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
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

    def generate_tet4_mesh(self, Lx, Ly, Lz, nx, ny, nz, hole_params=None):
        hex_nodes, hex_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
        num_hex = len(hex_conn); connectivity = np.zeros((num_hex * 5, 4), dtype=int)
        
        tet_count = 0
        for h in range(num_hex):
            n = hex_conn[h, :]
            tets = [[n[0], n[1], n[3], n[4]], [n[1], n[2], n[3], n[6]], [n[1], n[4], n[5], n[6]], [n[3], n[4], n[6], n[7]], [n[1], n[3], n[4], n[6]]]
            connectivity[tet_count:tet_count+5, :] = tets
            tet_count += 5
            
        return hex_nodes, connectivity, {'num_nodes': len(hex_nodes), 'num_elements': len(connectivity), 'nodes_per_element': 4}

    def generate_tet10_mesh(self, Lx, Ly, Lz, nx, ny, nz, hole_params=None):
        tet4_nodes, tet4_conn, _ = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
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
        hole_params = getattr(self, 'hole_params', None)
        
        if self.element_type == 'Hexa8': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
        elif self.element_type == 'Hexa20': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa20_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
        elif self.element_type == 'Tet4': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
        elif self.element_type == 'Tet10': self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet10_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
            
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
            self.Phi = None; self.Phi_nodal_stress = None; self.K_rom = None; self.SnapshotMatrix = None
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
            elif self.element_type == 'Hexa20': num_gp = 27 if integration_type == 'full' else (8 if integration_type=='reduce' else 14) 
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
            self.Sigma_Final2 = None

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

    def _add_foundation_stiffness_surface(self, Ke, Coord, foundation_stiffness, face_node_indices):
        if foundation_stiffness <= 0.0 or len(face_node_indices) == 0:
            return Ke

        face_nodes_xy = Coord[face_node_indices, :2]
        face_dofs = [int(node_idx) * 3 + 2 for node_idx in face_node_indices]
        if len(face_node_indices) not in (4, 8):
            return Ke

        gauss_points = np.array([-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)])
        weights = np.array([1.0, 1.0])
        num_nodes = len(face_node_indices)

        for xi in gauss_points:
            for eta in gauss_points:
                if num_nodes == 4:
                    N = np.array([
                        0.25 * (1.0 - xi) * (1.0 - eta),
                        0.25 * (1.0 + xi) * (1.0 - eta),
                        0.25 * (1.0 + xi) * (1.0 + eta),
                        0.25 * (1.0 - xi) * (1.0 + eta),
                    ])
                    dN_dxi = np.array([
                        -0.25 * (1.0 - eta),
                        0.25 * (1.0 - eta),
                        0.25 * (1.0 + eta),
                        -0.25 * (1.0 + eta),
                    ])
                    dN_deta = np.array([
                        -0.25 * (1.0 - xi),
                        -0.25 * (1.0 + xi),
                        0.25 * (1.0 + xi),
                        0.25 * (1.0 - xi),
                    ])
                else:
                    corner_coords = np.array([[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]])
                    N = np.zeros(8)
                    dN_dxi = np.zeros(8)
                    dN_deta = np.zeros(8)
                    for n in range(4):
                        xi_i, eta_i = corner_coords[n]
                        N[n] = 0.25 * (1.0 + xi * xi_i) * (1.0 + eta * eta_i) * (xi * xi_i + eta * eta_i - 1.0)
                        dN_dxi[n] = 0.25 * xi_i * (1.0 + eta * eta_i) * (2.0 * xi * xi_i + eta * eta_i)
                        dN_deta[n] = 0.25 * eta_i * (1.0 + xi * xi_i) * (2.0 * eta * eta_i + xi * xi_i)

                    mid_coords = np.array([[0.0, -1.0], [1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
                    for n, (xi_i, eta_i) in enumerate(mid_coords, start=4):
                        if np.isclose(eta_i, -1.0):
                            N[n] = 0.5 * (1.0 - xi * xi) * (1.0 + eta * eta_i)
                            dN_dxi[n] = -xi * (1.0 + eta * eta_i)
                            dN_deta[n] = -0.5 * (1.0 - xi * xi)
                        elif np.isclose(xi_i, 1.0):
                            N[n] = 0.5 * (1.0 - eta * eta) * (1.0 + xi * xi_i)
                            dN_dxi[n] = 0.5 * (1.0 - eta * eta)
                            dN_deta[n] = -eta * (1.0 + xi * xi_i)
                        elif np.isclose(eta_i, 1.0):
                            N[n] = 0.5 * (1.0 - xi * xi) * (1.0 + eta * eta_i)
                            dN_dxi[n] = -xi * (1.0 + eta * eta_i)
                            dN_deta[n] = 0.5 * (1.0 - xi * xi)
                        else:
                            N[n] = 0.5 * (1.0 - eta * eta) * (1.0 + xi * xi_i)
                            dN_dxi[n] = -0.5 * (1.0 - eta * eta)
                            dN_deta[n] = -eta * (1.0 + xi * xi_i)

                J11 = np.dot(dN_dxi, face_nodes_xy[:, 0])
                J12 = np.dot(dN_deta, face_nodes_xy[:, 0])
                J21 = np.dot(dN_dxi, face_nodes_xy[:, 1])
                J22 = np.dot(dN_deta, face_nodes_xy[:, 1])
                detJ = J11 * J22 - J12 * J21
                if abs(detJ) < 1e-12:
                    continue
                w = weights[0] * weights[1] * abs(detJ)
                for i in range(num_nodes):
                    for j in range(num_nodes):
                        Ke[face_dofs[i], face_dofs[j]] += foundation_stiffness * N[i] * N[j] * w
        return Ke

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
        
        n_order = 2 if Settings.get('Integration', '').lower() == 'full' else (1 if Settings.get('Integration', '').lower() == 'reduced' else 0)
        if n_order == 0:
            raise ValueError("Integration order must be 1 or 2 for Hexa8 elements.")
        else:
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
                    
        if self.is_elastic_foundation_mode() and hasattr(self, 'foundation_stiffness') and self.foundation_stiffness > 0.0:
            tol = 1e-8
            z_vals = Coord[:, 2]
            bottom_mask = np.isclose(z_vals, np.min(z_vals), atol=tol)
            face_node_indices = np.where(bottom_mask)[0]
            if len(face_node_indices) > 0:
                Ke = self._add_foundation_stiffness_surface(Ke, Coord, self.foundation_stiffness, face_node_indices)

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
        
        nGauss_vol = 4 if Settings.get('Integration', '').lower() == 'full' else (1 if Settings.get('Integration', '').lower() == 'reduced' else 0)
        Be_all = np.zeros((6 * nGauss_vol, 30))
        if nGauss_vol == 0: raise ValueError("Integration order must be 1 or 4 for Tet10 elements.")
        else:
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
        
        n_order = 2 if Settings.get('Integration', '').lower() == 'full' else (1 if Settings.get('Integration', '').lower() == 'reduced' else 0)
        if n_order==0: raise ValueError("Integration order must be 1 or 2 for Tet4 elements.")
        else:
            g_pts, g_w = self.GetGaussTableTetrahedra(n_order)
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
        integration_mode = Settings.get('Integration', '').lower()
        
        # --- 14-POINT INTEGRATION LOGIC ---
        if integration_mode == '14point':
            num_gp = 14
            
            # 14-point rule constants (Irons' rule coordinates and weights)
            a = 0.795822425754221
            b = 0.758786910639328
            w_a = 0.886421592695420
            w_b = 0.335180055401662
            
            # 8 Corner-aligned points
            gp_corners = np.array([
                [-a, -a, -a], [ a, -a, -a], [ a,  a, -a], [-a,  a, -a],
                [-a, -a,  a], [ a, -a,  a], [ a,  a,  a], [-a,  a,  a]
            ])
            w_corners = np.ones(8) * w_a
            
            # 6 Axis/Face-aligned points
            gp_axes = np.array([
                [-b,  0,  0], [ b,  0,  0],
                [ 0, -b,  0], [ 0,  b,  0],
                [ 0,  0, -b], [ 0,  0,  b]
            ])
            w_axes = np.ones(6) * w_b
            
            # Combine into master tables
            g_pts = np.vstack((gp_corners, gp_axes))
            g_w = np.concatenate((w_corners, w_axes))
            
        else:
            # Fallback to your existing 27-point (full) or 8-point (reduced) product grids
            n_order = 3 if integration_mode == 'full' else 2
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

        if self.is_elastic_foundation_mode() and hasattr(self, 'foundation_stiffness') and self.foundation_stiffness > 0.0:
            tol = 1e-8
            z_vals = Coord[:, 2]
            bottom_mask = np.isclose(z_vals, np.min(z_vals), atol=tol)
            face_node_indices = np.where(bottom_mask)[0]
            if len(face_node_indices) > 0:
                Ke = self._add_foundation_stiffness_surface(Ke, Coord, self.foundation_stiffness, face_node_indices)
            
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
    
    def is_elastic_foundation_mode(self):
        mode = self.BeamTypeDropDown.currentText().lower() if hasattr(self, 'BeamTypeDropDown') else ''
        return 'elastic' in mode or 'foundation' in mode

    def define_loads_at_pos(self, target_x, P_val):
        X = self.node_coords[:, 0]; Z = self.node_coords[:, 2] 
        tol = 1e-8; max_z = np.max(Z); max_x = np.max(X)
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
        tol = 1e-5; X = node_coords[:, 0]; Y = node_coords[:, 1]; Z = node_coords[:, 2]
        x_min = np.min(X); x_max = np.max(X); z_min = np.min(Z)
        num_total = K_global.shape[0]
        
        if 'cantilever' in beam_type.lower():
            fixed_nodes = np.where(np.abs(X - x_min) < tol)[0]
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
        elif self.is_elastic_foundation_mode():
            foundation_nodes = np.where(np.abs(Z - z_min) < tol)[0]
            if len(foundation_nodes) > 0:
                anchor_nodes = foundation_nodes[np.argsort(np.abs(X[foundation_nodes] - x_min) + np.abs(Y[foundation_nodes] - np.min(Y)))[:2]]
                horizontal_dofs = []
                for node_id in anchor_nodes:
                    horizontal_dofs.extend([node_id * 3 + 0, node_id * 3 + 1])
                if len(anchor_nodes) > 1:
                    horizontal_dofs.extend([anchor_nodes[1] * 3 + 0])
                fixed_dofs = np.array(np.unique(horizontal_dofs), dtype=int)
            else:
                fixed_dofs = np.array([], dtype=int)
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
        sphere_radius = max(diagonal * 0.003, 1e-4)
        arrow_scale = max(diagonal * 0.03, 1e-4)
            
        if 'Hexa' in element_type: n_vis = 8; vtk_type = pv.CellType.HEXAHEDRON
        else: n_vis = 4; vtk_type = pv.CellType.TETRA
            
        vis_connectivity = element_connectivity[:, :n_vis]; grid = pv.UnstructuredGrid({vtk_type: vis_connectivity}, node_coords)
        targetAxes.add_mesh(grid, name='bc_base_mesh', show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        targetAxes.add_mesh(grid, show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        
        fixed_dofs = np.array(bc_info.get('fixed_dofs_indices', []))
        if len(fixed_dofs) > 0:
            fixed_nodes = np.unique(fixed_dofs // 3)
            fixed_coords = np.atleast_2d(node_coords[fixed_nodes])
            
            spheres = pv.PolyData(fixed_coords).glyph(
                geom=pv.Sphere(radius=sphere_radius),
                scale=False,
                orient=False
            )
            
            targetAxes.add_mesh(spheres, name='bc_fixed_dofs', color="red", show_edges=True, edge_color="black") 
        else:
            try: targetAxes.remove_actor('bc_fixed_dofs')
            except: pass

        if self.is_elastic_foundation_mode() and hasattr(self, 'foundation_stiffness') and self.foundation_stiffness > 0.0:
            z_vals = node_coords[:, 2]
            bottom_nodes = np.where(np.isclose(z_vals, np.min(z_vals), atol=1e-8))[0]
            if len(bottom_nodes) > 0:
                foundation_coords = np.atleast_2d(node_coords[bottom_nodes])
                foundation_points = pv.PolyData(foundation_coords)
                targetAxes.add_mesh(foundation_points, name='bc_foundation_face', color='gold', point_size=8, render_points_as_spheres=True)
            else:
                try: targetAxes.remove_actor('bc_foundation_face')
                except: pass
        else:
            try: targetAxes.remove_actor('bc_foundation_face')
            except: pass
            
        if len(applied_idx) > 0:
            load_coords = np.atleast_2d(node_coords[applied_idx]); load_vectors = np.atleast_2d(F_nodes[applied_idx])
            mags = load_mag[applied_idx]; load_dirs = load_vectors / mags[:, np.newaxis]
            cloud = pv.PolyData(load_coords); cloud["vectors"] = load_dirs * arrow_scale
            arrows = cloud.glyph(orient="vectors", scale="vectors", factor=1.0, geom=pv.Arrow())
            targetAxes.add_mesh(arrows, name='bc_force_arrows', color="blue")
        else:
            try: targetAxes.remove_actor('bc_force_arrows')
            except: pass

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

            if hasattr(self, 'B_global') and self.B_global is not None and hasattr(self, 'D_mat') and self.D_mat is not None:
                try:
                    self.Sigma_Final2, self.sigma_gauss_all = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, self.U_full, self.node_coords, self.element_connectivity, self.element_type)
                except Exception as stress_err:
                    self.Sigma_Final2 = None
                    print(f"Stress recovery warning: {stress_err}")

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


    def PostProcess_Stress_3Dsparse(self, B_global, D, U_global, Coords, Connectivity, ElementType):
        Num_Nodes = Coords.shape[0]; Num_Elem = Connectivity.shape[0]
        total_B_rows = B_global.shape[0]; num_gp = total_B_rows // (6 * Num_Elem)
        if total_B_rows % (6 * Num_Elem) != 0: 
            raise ValueError(f"B_global rows ({total_B_rows}) is not a multiple of 6 * Num_Elements ({6*Num_Elem}).")
            
        # 1. Compute Gauss Point Stresses
        epsilon_all = B_global.dot(U_global); strain_matrix = epsilon_all.reshape(-1, 6).T
        sigma_gauss_all = D @ strain_matrix 
        
        # 2. Retrieve the Extrapolation Matrix for this scheme
        if hasattr(self, 'Get_Emat_3D_Full'): 
            E_mat = self.Get_Emat_3D_Full(Coords[Connectivity[0, :]], ElementType, num_gp)
        else: 
            E_mat = np.ones((Connectivity.shape[1], num_gp)) / num_gp
            
        nodes_per_elem = Connectivity.shape[1]
        
        # 3. FIX: Build val_idx to align with row_idx and col_idx flattening order
        # Repeat the element connectivity sequence for every Gauss point
        row_idx = np.repeat(Connectivity, num_gp, axis=1).ravel()
        
        # Track the global Gauss point indices cleanly
        gp_ids_per_elem = np.arange(Num_Elem)[:, None] * num_gp + np.arange(num_gp)[None, :]
        col_idx = np.repeat(gp_ids_per_elem[:, None, :], nodes_per_elem, axis=1).ravel()
        
        # Flatten the extrapolation matrix correctly, matching the element mapping sequence
        # This ensures (20, 14) scales accurately across the mesh without unrolling errors
        val_idx = np.repeat(E_mat[None, :, :], Num_Elem, axis=0).ravel()
        
        # 4. Construct the Global Mapping Operator
        E_global = sp.csr_matrix((val_idx, (row_idx, col_idx)), shape=(Num_Nodes, Num_Elem * num_gp))
        
        # 5. Compute the Extrapolated Stress Totals at Nodes
        Nodal_Stress_Sum = E_global.dot(sigma_gauss_all.T) 
        
        # 6. FIX: True Weighted Nodal Normalization
        # Sum the actual weights meeting at each node rather than counting the elements.
        # This accounts for the variable weight profiles of the 14-point scheme.
        Weight_Sum_Operator = sp.csr_matrix((val_idx, (row_idx, col_idx)), shape=(Num_Nodes, Num_Elem * num_gp))
        ones_gauss = np.ones(Num_Elem * num_gp)
        Node_Weights = np.array(Weight_Sum_Operator.dot(ones_gauss)).flatten()
        Node_Weights[Node_Weights == 0] = 1.0  # Prevent division by zero
        
        # 7. Apply the clean normalization scale factor
        Sigma_Final2 = Nodal_Stress_Sum / Node_Weights[:, np.newaxis]
        return Sigma_Final2,sigma_gauss_all
    
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
                
            elif num_gp == 14:
                # Irons' 14-point rule coordinate parameters
                a = 0.795822425754221
                b = 0.758786910639328
                
                # 8 Corner-aligned locations
                gp_corners = np.array([
                    [-a, -a, -a], [ a, -a, -a], [ a,  a, -a], [-a,  a, -a],
                    [-a, -a,  a], [ a, -a,  a], [ a,  a,  a], [-a,  a,  a]
                ])
                
                # 6 Axis/Face-aligned locations
                gp_axes = np.array([
                    [-b,  0,  0], [ b,  0,  0],
                    [ 0, -b,  0], [ 0,  b,  0],
                    [ 0,  0, -b], [ 0,  0,  b]
                ])
                
                # Combine all 14 locations
                g_pts = np.vstack((gp_corners, gp_axes))
                
                # Construct the Shape Function evaluation matrix N_G (14 x 20)
                N_G = np.zeros((14, 20))
                for k in range(14):
                    xi, eta, zeta = g_pts[k, 0], g_pts[k, 1], g_pts[k, 2]
                    N_shape, _, _, _ = self.Hexa20_ShapeFunctions(xi, eta, zeta)
                    N_G[k, :] = N_shape
                    
                # Compute Least-Squares projection matrix back to the 20 nodes
                return np.linalg.pinv(N_G)
                
            elif num_gp == 27:
                g_pts, _ = self.BuildHexaGauss(3); N_G = np.zeros((27, 20))
                for k in range(27):
                    xi, eta, zeta = g_pts[k,0], g_pts[k,1], g_pts[k,2]
                    N_shape, _, _, _ = self.Hexa20_ShapeFunctions(xi, eta, zeta)
                    N_G[k, :] = N_shape
                return np.linalg.pinv(N_G)
                
        elif ElementType == 'Tet10':
            a_t, b_t = 0.58541020, 0.13819660; g_pts = np.array([[a_t, b_t, b_t], [b_t, a_t, b_t], [b_t, b_t, a_t], [b_t, b_t, b_t]]); XYZ_G = np.zeros((4, 3))
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


    def OpenPostProcessingButtonPushed(self):
        self.lock_ui() 
        
        try:
            # 1. DATA VALIDATION
            # Ensure the solver has actually produced results
            if not hasattr(self, 'Sigma_Final2') or self.Sigma_Final2 is None:
                if hasattr(self, 'B_global') and self.B_global is not None and hasattr(self, 'U_full') and self.U_full is not None:
                    try:
                        self.Sigma_Final2, self.sigma_gauss_all = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, self.U_full, self.node_coords, self.element_connectivity, self.element_type)
                    except Exception as retry_error:
                        QMessageBox.warning(self, "Post-Processing", f"Stress recovery failed: {retry_error}")
                        return
                else:
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
                self.plot_stresses(self.sigma_gauss_all, stress_type, self.UIAxes5, self.U_full, self.scalefactor)

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
        

    def plot_stresses(self, stress_data_in, stress_type, targetAxes, U_full, scale_factor, custom_clim=None, title_prefix="Stress", data_label="Stress (MPa)"):
        if stress_data_in is None:
            print("Plot Stress Error: Input stress data is None.")
            targetAxes.clear()
            targetAxes.add_text("Stress data not available.")
            targetAxes.render()
            return
            
        is_nodal = len(self.node_coords) == len(stress_data_in)

        stress_map = {'Sigma_xx': (0, 'Sigma_xx'), 'Sigma_yy': (1, 'Sigma_yy'), 'Sigma_zz': (2, 'Sigma_zz'),
                      'Tau_xy':   (3, 'Tau_xy'),   'Tau_yz':   (4, 'Tau_yz'),   'Tau_zx':   (5, 'Tau_zx'), 'Tau_xz':   (5, 'Tau_zx')}
        col, lbl = stress_map.get(stress_type, (0, 'Sigma_xx'))

        plot_on = 'points'
        if is_nodal:
            stress_data = stress_data_in[:, col] / 1e6 # Nodal stresses in MPa
        else: # Assuming Gauss point stresses
            try:
                num_elements = self.mesh_info['num_elements']
                if stress_data_in.shape[0] != 6:
                     raise ValueError("Gauss stress data has incorrect shape.")
                stress_at_gauss_points = stress_data_in.T # (num_elem * num_gp, 6)
                gauss_stress_component = stress_at_gauss_points[:, col]
                
                num_gp = len(gauss_stress_component) // num_elements
                cell_stress = np.mean(gauss_stress_component.reshape((num_elements, num_gp)), axis=1)
                stress_data = cell_stress / 1e6 # To MPa
                plot_on = 'cells'
            except Exception as e:
                print(f"Could not process Gauss point stresses: {e}")
                targetAxes.clear()
                targetAxes.add_text("Could not process stress data.")
                targetAxes.render()
                return

        is_error_plot = "error" in title_prefix.lower() or "error" in data_label.lower()

        if custom_clim is not None:
            c_limits = custom_clim
        else:
            s_min = float(np.min(stress_data))
            s_max = float(np.max(stress_data))
            
            if is_error_plot:
                # 1. Error plots: strictly non-negative [0, max_error]
                c_limits = [0.0, max(s_max, 1e-6)]
            elif s_min < 0 and s_max > 0:
                # 2. Signed physical stresses (Tension + / Compression -): Symmetric bounds centered at 0 MPa
                max_abs = max(abs(s_min), abs(s_max))
                c_limits = [-max_abs, max_abs]
            elif np.isclose(s_min, s_max):
                c_limits = [s_min - 0.1, s_max + 0.1] if s_max != 0 else [-0.1, 0.1]
            else:
                c_limits = [s_min, s_max]
        
        if U_full.size == 0:
            print("Plot Stress Warning: Empty displacement vector, skipping stress plot.")
            return

        try:
            Max_Disp_mm = np.max(np.abs(U_full)) * 1000.0
            U_nodes = U_full.reshape(-1, 3)
            def_coords = self.node_coords + (U_nodes * scale_factor)
            title_str = f"{title_prefix}: {lbl} ({plot_on})\nMax Deflection: {Max_Disp_mm:.3f} mm (Scale: {scale_factor}x)"

            if 'Hexa' in self.element_type:
                n_vis = 8; vtk_type = pv.CellType.HEXAHEDRON
            else:
                n_vis = 4; vtk_type = pv.CellType.TETRA

            cells_dict = {vtk_type: self.element_connectivity[:, :n_vis]}
            grid_undeformed = pv.UnstructuredGrid(cells_dict, self.node_coords)
            grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)

            if is_nodal:
                grid_deformed.point_data[data_label] = stress_data
            else:
                grid_deformed.cell_data[data_label] = stress_data

            fmt_str = "%.2e" if (is_error_plot and abs(c_limits[1]) < 0.1) else "%.1f"
            sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, fmt=fmt_str, vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)

            targetAxes.clear()
            saved_cam = targetAxes.camera_position if hasattr(targetAxes, 'camera_initialized') and targetAxes.camera_position is not None else None

            targetAxes.add_mesh(grid_undeformed, style='wireframe', color='gray', opacity=0.4, line_width=1.0)
            targetAxes.add_mesh(grid_deformed, scalars=data_label, cmap="jet", clim=c_limits, show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
            targetAxes.add_text(title_str, font_size=10, color='black')

            if not hasattr(targetAxes, 'axes_widget_added'):
                targetAxes.add_axes(); targetAxes.axes_widget_added = True

            if saved_cam:
                targetAxes.camera_position = saved_cam
            else:
                targetAxes.view_isometric()
                targetAxes.reset_camera()
                targetAxes.camera_initialized = True

            targetAxes.render()
        except Exception as e:
            print(f"Plot Stress Error: {e}")
            traceback.print_exc()
            targetAxes.clear()
            targetAxes.add_text("Error during plotting.")
            targetAxes.render()

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

    def _update_snapshot_controls(self):
        is_bcss = self.SnapshotMethodDropDown.currentText().upper() == 'BCSS'
        self.BCSSBoundaryDropDown.setEnabled(is_bcss)

    def _build_snapshot_positions(self, num_snapshots):
        method = self.SnapshotMethodDropDown.currentText().upper() if hasattr(self, 'SnapshotMethodDropDown') else 'USS'
        boundary_class = self.BCSSBoundaryDropDown.currentText().lower() if hasattr(self, 'BCSSBoundaryDropDown') else 'cantilever'
        
        self.BC = boundary_class
        Lx = self.geometry['Lx']
        
        if method == 'BCSS':
            if 'fixed' in boundary_class:
                # Fixed-fixed beams have stress concentrations at BOTH supports (x=0 and x=Lx).
                # Sample both boundaries densely (logarithmically up to 15% of span) plus the interior span.
                edge_count = max(3, num_snapshots // 4)
                bulk_count = max(1, num_snapshots - 2 * edge_count)
                
                left_edge = np.geomspace(0.0005, 0.15, edge_count)
                right_edge = 1.0 - np.geomspace(0.0005, 0.15, edge_count)[::-1]
                bulk = np.linspace(0.18, 0.82, bulk_count)
                
                x_norm = np.sort(np.unique(np.concatenate((left_edge, bulk, right_edge))))
            else:
                # Cantilever/Single boundary: logarithmic clustering over 15% of span near fixed support.
                edge_count = max(6, num_snapshots // 2)
                bulk_count = max(1, num_snapshots - edge_count)
                left_edge = np.geomspace(0.0005, 0.15, edge_count)
                bulk = np.linspace(0.18, 0.99, bulk_count)
                x_norm = np.sort(np.unique(np.concatenate((left_edge, bulk))))
        else:
            x_norm = np.linspace(0.0, 1.0, num_snapshots)

        if len(x_norm) > num_snapshots:
            idx = np.round(np.linspace(0, len(x_norm) - 1, num_snapshots)).astype(int)
            x_norm = x_norm[idx]
        elif len(x_norm) < num_snapshots:
            x_norm = np.sort(np.unique(np.concatenate((x_norm, np.linspace(0.0, 1.0, num_snapshots)))))[:num_snapshots]

        return np.asarray(x_norm) * Lx

    def update_rom_mode_selection(self):
        """Dynamically updates Phi and K_rom when user changes displacement mode selection in disp_modeEditField."""
        if not hasattr(self, 'Phi_full') or self.Phi_full is None or not hasattr(self, 'K_reduced') or self.K_reduced is None:
            return
        
        max_modes = self.Phi_full.shape[1]
        user_disp_mode = self.disp_modeEditField.text().strip() if hasattr(self, 'disp_modeEditField') else "Auto"
        
        if user_disp_mode.isdigit() and int(user_disp_mode) > 0:
            n_modes_disp = min(int(user_disp_mode), max_modes)
            selection_str = f"User Selected Mode: {n_modes_disp}"
        else:
            rec_modes = getattr(self, 'recommended_modes', min(5, max_modes))
            n_modes_disp = min(rec_modes, max_modes)
            selection_str = f"Auto Recommended Mode: {n_modes_disp}"
            if hasattr(self, 'disp_modeEditField'):
                self.disp_modeEditField.setText(str(n_modes_disp))
                
        self.Phi = self.Phi_full[:, :n_modes_disp]
        self.K_rom = self.Phi.T @ (self.K_reduced @ self.Phi)
        
        cum_energy = self.cum_energy_disp[n_modes_disp-1] if hasattr(self, 'cum_energy_disp') and len(self.cum_energy_disp) >= n_modes_disp else 100.0
        msg = (
            f"\n--- Dynamic Mode Update ---\n"
            f"{selection_str}\n"
            f"Phi Retained Shape: {self.Phi.shape}\n"
            f"K_rom Dimension: {self.K_rom.shape[0]} x {self.K_rom.shape[1]}\n"
            f"Retained Displacement Energy: {cum_energy:.4f}%\n"
            f"---------------------------\n"
        )
        print(msg)
        if hasattr(self, 'TrainningTimeTextArea'):
            current_log = self.TrainningTimeTextArea.toPlainText()
            self.TrainningTimeTextArea.setText(msg + current_log)

    def TrainButtonPushed(self):
        self.lock_ui() 
        try:
            # CRITICAL FIX: Purge old ROM data before retraining to prevent mode conflicts
            self.Phi = None; self.Phi_nodal_stress = None; self.K_rom = None
            if hasattr(self, 'SnapshotMatrix'): self.SnapshotMatrix = None
            gc.collect()
            
            if not hasattr(self, 'K_reduced') or self.K_reduced is None:
                raise RuntimeError("ROM training requires a solved FEM model with applied boundary conditions.")
            if not hasattr(self, 'bc_info') or 'free_dofs_indices' not in self.bc_info:
                raise RuntimeError("Boundary condition information is missing. Please apply BC before ROM training.")

            num_snapshots = int(self.num_snapshotsEditField.text())
            x_positions = self._build_snapshot_positions(num_snapshots)

            
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
                base_load = float(self.LoadValueNEditField.text())
                load_val = base_load
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
            self.Phi_full = U_svd
            self.S_disp = S_disp
            energy_disp = S_disp**2 
            cum_energy_disp = np.cumsum(energy_disp) / np.sum(energy_disp) * 100.0
            self.cum_energy_disp = cum_energy_disp
            energy_variance = np.maximum(100.0 - cum_energy_disp, 1e-12)
            self.energy_variance = energy_variance
                                    
            # MEMORY CLEANUP: Delete temporary snapshot matrix and Vt, keep self.Phi_full for fast reconstruction
            del self.SnapshotMatrix, Vt
            gc.collect()  # Force garbage collection for heavy memory usage
                                    
            fig = self.UIAxes8.figure if hasattr(self.UIAxes8, 'figure') else self.UIAxes8; fig.clf()
            ax1 = fig.add_subplot(111); ax2 = ax1.twinx() 
            mode_numbers = np.arange(1, num_snapshots + 1)
            
            ax1.semilogy(mode_numbers, energy_variance, '-ro', linewidth=2, markerfacecolor='r', label='Residual Energy Variance (%)')
            ax1.set_xlabel('Mode Number')
            ax1.set_ylabel('Residual Energy Variance (%)', color='r')
            ax1.tick_params(axis='y', colors='r')
            ax1.grid(True, which='both', linestyle='--', alpha=0.5)

            ax2.semilogy(mode_numbers, cum_energy_disp, '-bo', linewidth=2, markerfacecolor='b', label='Cumulative Energy (%)')
            ax2.set_ylabel('Cumulative Energy (%)', color='b')
            ax2.tick_params(axis='y', colors='b')
            ax2.grid(True, which='both', linestyle=':', alpha=0.3)
            ax1.set_title('ROM Analysis: Residual Energy Variance & Cumulative Energy')
            if hasattr(fig, 'canvas'): fig.canvas.draw_idle()
                                        
            modes_over_threshold = np.where(cum_energy_disp >= 100.00)[0]
            if len(modes_over_threshold) > 0:
                recommended_modes = modes_over_threshold[0] + 1
                threshold_str = f"Threshold (>=100%) reached at mode {recommended_modes}"
            else:
                recommended_modes = num_snapshots
                threshold_str = "Threshold (>=100%) not reached within snapshots"
            
            self.recommended_modes = recommended_modes
                
            # Allow user input GUI control over n_modes_disp
            user_disp_mode = self.disp_modeEditField.text().strip() if hasattr(self, 'disp_modeEditField') else "Auto"
            if user_disp_mode.isdigit() and int(user_disp_mode) > 0:
                n_modes_disp = min(int(user_disp_mode), num_snapshots)
                mode_selection_msg = f"Using User Input Disp Modes: {n_modes_disp} (Auto threshold recommendation: {recommended_modes})"
            else:
                n_modes_disp = min(recommended_modes, num_snapshots)
                mode_selection_msg = f"Using Auto Recommended Disp Modes: {n_modes_disp}"
                if hasattr(self, 'disp_modeEditField'):
                    self.disp_modeEditField.setText(str(n_modes_disp))
                    
            mode_log = (
                f"\n--- Energy Variance & Mode Analysis ---\n"
                f"{threshold_str}\n"
                f"Auto Recommended Modes: {recommended_modes}\n"
                f"{mode_selection_msg}\n"
                f"Retained Displacement Energy: {cum_energy_disp[n_modes_disp-1]:.6f}%\n"
                f"Residual Energy Variance: {energy_variance[n_modes_disp-1]:.6e}%\n"
                f"---------------------------------------\n"
            )
            print(mode_log)
            current_log = self.TrainningTimeTextArea.toPlainText()
            self.TrainningTimeTextArea.setText(mode_log + current_log)
            QApplication.processEvents()
                                        
            self.Phi = self.Phi_full[:, :n_modes_disp]                                                
            print("Projecting Stiffness Matrix...")
            self.K_rom = self.Phi.T @ (self.K_reduced @ self.Phi)                      
            success_msg = f"Training Complete!\nModes retained: {n_modes_disp}\nEnergy: {cum_energy_disp[n_modes_disp-1]:.4f}%\nK_rom Dimension: {self.K_rom.shape[0]} x {self.K_rom.shape[1]}"
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
        Sigma_fem_nodal = None
        Sigma_rom_nodal = None

        try:
            # 1. DATA INTEGRITY CHECKS
            if not all(hasattr(self, attr) and getattr(self, attr) is not None for attr in ['Phi', 'K_rom']):
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
                
            stress_type_plot = self.TypeofStressesDropDown_2.currentText()
           
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

            # 5. FEM REFERENCE SOLVE  (averaged over N_REPEATS for stability)
            K_reduced_csr = self.K_reduced.tocsr() if sp.issparse(self.K_reduced) else sp.csr_matrix(self.K_reduced)

            N_REPEATS = 5
            _fem_times = []
            for _r in range(N_REPEATS):
                _t = time.perf_counter()
                U_free_fem = spla.spsolve(K_reduced_csr, F_red)
                _fem_times.append(time.perf_counter() - _t)
            time_fem_solve = min(_fem_times)  # use min to exclude OS interrupts

            num_dof = self.bc_info['total_dofs']
            U_full_fem = np.zeros(num_dof)
            U_full_fem[free_dofs] = U_free_fem

            progress.setValue(1)

            # 6. FEM STRESS & PLOT
            t0 = time.perf_counter()
            Sigma_fem_nodal, _ = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_full_fem, self.node_coords, self.element_connectivity, self.element_type)
            time_fem_stress = time.perf_counter() - t0
            
            if hasattr(self, 'UIAxes9'):
                self.plot_stresses(Sigma_fem_nodal, stress_type_plot, self.UIAxes9, U_full_fem, scale_factor, title_prefix="FEM Stress", data_label="FEM Stress (MPa)")
            
            progress.setValue(2)

            # 7. ROM PROJECTED SOLVE  (averaged over N_REPEATS)
            _rom_times = []
            for _r in range(N_REPEATS):
                _t = time.perf_counter()
                F_rom = self.Phi.T @ F_red
                alpha = np.linalg.solve(self.K_rom, F_rom) 
                U_free_rom_proj = self.Phi @ alpha
                _rom_times.append(time.perf_counter() - _t)
            time_rom_solve = min(_rom_times)

            F_rom = self.Phi.T @ F_red
            alpha = np.linalg.solve(self.K_rom, F_rom) 
            U_free_rom_proj = self.Phi @ alpha
            
            U_full_rom = np.zeros(num_dof)
            U_full_rom[free_dofs] = U_free_rom_proj
            
            progress.setValue(3)

            # 8. ROM STRESS RECONSTRUCTION & ERROR CONTOUR PLOT
            t0 = time.perf_counter()
            Sigma_rom_nodal, _ = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_full_rom, self.node_coords, self.element_connectivity, self.element_type)
            time_rom_stress = time.perf_counter() - t0
            
            rel_error_Sigma = np.linalg.norm(Sigma_fem_nodal - Sigma_rom_nodal) / max(np.linalg.norm(Sigma_fem_nodal), 1e-12) * 100.0
            fem_max_stress = np.max(np.abs(Sigma_fem_nodal[:, 0])) / 1e6
            rom_max_stress = np.max(np.abs(Sigma_rom_nodal[:, 0])) / 1e6
            
            # Nodal Stress Field Absolute Error Matrix & NMAE Calculation
            abs_err_stress = np.abs(Sigma_fem_nodal - Sigma_rom_nodal)
            max_abs_err_stress = np.max(abs_err_stress)
            fem_peak_val = np.max(np.abs(Sigma_fem_nodal))
            NMAE_stress = (max_abs_err_stress / max(fem_peak_val, 1e-12)) * 100.0

            stress_col_map = {'Sigma_xx': 0, 'Sigma_yy': 1, 'Sigma_zz': 2, 'Tau_xy': 3, 'Tau_yz': 4, 'Tau_zx': 5}
            col_i = stress_col_map.get(stress_type_plot, 0)
            abs_err_comp = np.abs(Sigma_fem_nodal[:, col_i] - Sigma_rom_nodal[:, col_i])
            max_abs_err_comp = np.max(abs_err_comp)
            fem_peak_comp = np.max(np.abs(Sigma_fem_nodal[:, col_i]))
            NMAE_stress_comp = (max_abs_err_comp / max(fem_peak_comp, 1e-12)) * 100.0

            error_plot_data = abs_err_stress

            if hasattr(self, 'UIAxes10'):
                self.plot_stresses(Sigma_rom_nodal, stress_type_plot, self.UIAxes10, U_full_rom, scale_factor, title_prefix="ROM Stress", data_label="ROM Stress (MPa)")

            if hasattr(self, 'UIAxes11'):
                self.plot_stresses(error_plot_data, stress_type_plot, self.UIAxes11, U_full_rom, scale_factor, title_prefix="Abs Error (NMAE)", data_label="Error (MPa)")
            
            progress.setValue(4)

            # 9. ERROR ANALYSIS
            norm_U_fem = np.linalg.norm(U_free_fem)
            rel_error_U = (np.linalg.norm(U_free_fem - U_free_rom_proj) / max(norm_U_fem, 1e-12)) * 100.0
            
            speed_up_solve = time_fem_solve / max(time_rom_solve, 1e-9)
            speed_up_stress = time_fem_stress / max(time_rom_stress, 1e-9)

            # 10. GENERATE REPORT
            results_text = (
                "--- ROM Type: Traditional Displacement ROM ---\n\n"
                "--- DISPLACEMENT COMPARISON ---\n"
                f"FEM Max U: {np.max(np.abs(U_full_fem)):.4e} m\n"
                f"ROM Max U: {np.max(np.abs(U_full_rom)):.4e} m\n"
                f"Relative Error: {rel_error_U:.4f} %\n\n"

                f"--- STRESS CHECK ({stress_type_plot}) ---\n"
                f"FEM Max Stress: {fem_max_stress:.2f} MPa\n"
                f"ROM Max Stress: {rom_max_stress:.2f} MPa\n"
                f"Relative Frobenius Error: {rel_error_Sigma:.4f} %\n"
                f"NMAE Stress (Global Field): {NMAE_stress:.4f} %\n"
                f"NMAE Stress ({stress_type_plot}): {NMAE_stress_comp:.4f} %\n\n"

                f"--- PERFORMANCE  (min of {N_REPEATS} runs) ---\n"
                f"FEM Solve: {time_fem_solve:.6f} s\n"
                f"ROM Solve: {time_rom_solve:.6f} s\n"
                f"ROM is {speed_up_solve:.1f}x Faster\n\n"
                f"FEM Stress Reconstruction: {time_fem_stress:.6f} s\n"
                f"ROM Stress Reconstruction: {time_rom_stress:.6f} s\n"
                f"ROM Stress is {speed_up_stress:.1f}x Faster\n\n"
                f"FEM Total Time: {(time_fem_solve + time_fem_stress):.6f} s\n"
                f"ROM Total Time: {(time_rom_solve + time_rom_stress):.6f} s\n"
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
            Sigma_fem_nodal = None
            Sigma_rom_nodal = None
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
                'Phi_nodal_stress': getattr(self, 'Phi_nodal_stress', None),
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
# APPLICATION ENTRY POINT
# =========================================================================
def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    window = OfflinePreparationStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
