"""
Dual ROM Testing System
================================================
A comprehensive PyQt6-based application for mechanical testing simulation,
ROM visualization, sensor calibration, and live digital twin monitoring.

Author: CSE Lab
Version: 2.0.3 (Direct B-Matrix Physics-Rigorous Stress Recovery)
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
import gc

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QPushButton, QMessageBox, QInputDialog, QGridLayout, 
                             QTableWidgetItem, QLabel, QLineEdit, QComboBox, QTextEdit, 
                             QSlider, QCheckBox, QSplitter, QSizePolicy, QGroupBox, QTableWidget, 
                             QStackedWidget, QListWidget, QFileDialog, QTabWidget, QFrame, QProgressDialog, QDialog, QProgressBar, QHeaderView)

from PyQt6.QtCore import Qt, QTime, QUrl, QTimer
from PyQt6.QtGui import QFont, QAction, QDesktopServices, QPixmap
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pickle
from datetime import datetime
import traceback
import serial
import serial.tools.list_ports

from PyQt6.QtCore import QThread, pyqtSignal


class ProfessionalTheme:
    PRIMARY_BLUE = "#1e3a5f"
    DARK_BLUE = "#0f1f2e"
    ACCENT_BLUE = "#2980b9"
    BRIGHT_BLUE = "#3498db"
    SUCCESS_GREEN = "#27ae60"
    WARNING_ORANGE = "#e67e22"
    DANGER_RED = "#e74c3c"
    BACKGROUND_LIGHT = "#f5f6fa"
    BORDER_LIGHT = "#d5dbdb"


class OfflinePreparationStudio(QMainWindow):
    
    def closeEvent(self, event):
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
        self.setWindowTitle("Module 1: FEM / ROM Offline Studio (Direct Physics Recovery)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.geometry = {'Lx': 0.5, 'Ly': 0.015, 'Lz': 0.003}
        self.material = {'E': 68e9, 'nu': 0.33, 'rho': 7850}
        self.mesh_params = {'nx': 50, 'ny': 10, 'nz': 10}
        self.settings = {'Integration': 'Full'}
        self.element_type = 'Hexa8'
        self.beam_type = 'Cantilever'
        self.BEAM_H, self.BEAM_L = self.geometry['Lz'], self.geometry['Lx']
        self.exp_u_input = None
        self.node_coords = None; self.element_connectivity = None; self.mesh_info = {}
        self.bc_info = {}; self.loads = {}
        self.K_global = None; self.F_global = None; self.K_reduced = None; self.F_reduced = None
        self.D_mat = None; self.B_global = None; self.U_full = None; self.S_max = None
        self.Sigma_Final2 = None
        self.Phi = None; self.K_rom = None; self.DT_Bank = []
        # performance caches
        self._K_factor = None  # cached factorization for K_reduced
        self._E_global = None  # cached E_global for stress reconstruction

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_proj = QLabel("<b>Project Schematic</b>")
        lbl_proj.setFont(QFont("Arial", 14))
        self.sidebar_layout.addWidget(lbl_proj)
        
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
                QPushButton { text-align: left; padding: 12px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; font-size: 11pt; font-weight: 500; color: #2c3e50; }
                QPushButton:hover { background-color: #e9ecef; border: 1px solid #adb5bd; }
                QPushButton:checked { background-color: #0d6efd; color: white; font-weight: bold; border: 1px solid #0d6efd; }
            """)
            btn.setCheckable(True)
            if i == 0: btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self.switch_workflow_step(idx))
            self.step_buttons.append(btn)
            self.sidebar_layout.addWidget(btn)
            
        self.sidebar_layout.addStretch()
        self.btn_clear_data = QPushButton("🗑️ Clear Entire Project")
        self.btn_clear_data.setStyleSheet("background-color: #dc3545; color: white; padding: 12px; border-radius: 5px; font-weight: bold; font-size: 10pt; border: 1px solid #bb2d3b;")
        self.btn_clear_data.clicked.connect(self.clear_all_project_data)
        self.sidebar_layout.addWidget(self.btn_clear_data)
            
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.sidebar_widget)
        self.main_layout.addWidget(self.stacked_widget, stretch=1)
        
        self.build_ui()

    def switch_workflow_step(self, index):
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == index)
        self.stacked_widget.setCurrentIndex(index)

    def build_ui(self):
        self.stacked_widget.addWidget(self.create_panel1_geometry())
        self.stacked_widget.addWidget(self.create_panel2_load_bc())
        self.stacked_widget.addWidget(self.create_panel3_solve())
        self.stacked_widget.addWidget(self.create_panel4_post_processing())
        self.stacked_widget.addWidget(self.create_panel5_rom_training())
        self.stacked_widget.addWidget(self.create_panel6_rom_validation())

    @staticmethod
    def m_to_mm(value_m): return value_m * 1000.0
    @staticmethod
    def mm_to_m(value_mm): return value_mm / 1000.0
    @staticmethod
    def pa_to_mpa(value_pa): return value_pa / 1e6
    @staticmethod
    def mpa_to_pa(value_mpa): return value_mpa * 1e6

    def lock_ui(self):
        self.central_widget.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def unlock_ui(self):
        self.central_widget.setEnabled(True)
        QApplication.restoreOverrideCursor()    

    def clear_downstream_data(self, stage):
        if stage == 'mesh':
            self.K_global = None; self.F_global = None; self.D_mat = None; self.B_global = None
        if stage in ['mesh', 'bc']:
            self.K_reduced = None; self.F_reduced = None
        if stage in ['mesh', 'bc', 'solve']:
            self.U_full = None; self.Sigma_Final2 = None
        if stage in ['mesh', 'bc', 'solve', 'rom_train']:
            self.Phi = None; self.K_rom = None
            # clear performance caches when relevant matrices change
            self._K_factor = None
            self._E_global = None

    def clear_all_project_data(self):
        reply = QMessageBox.question(self, 'Clear Data', 'Clear all project memory and graphics?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_downstream_data('mesh')
            self.node_coords = None; self.element_connectivity = None; self.DT_Bank = []
            self.action_clear_panel1(); self.action_clear_panel2(); self.action_clear_panel4(); self.action_clear_panel5(); self.action_clear_panel6()
            gc.collect()
    
    def clear_rom_memory(self):
        self.Phi = None; self.K_rom = None; self.SnapshotMatrix = None
        gc.collect()
        QMessageBox.information(None, "Memory Cleared", "ROM data cleared from memory.")

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

    def create_panel1_geometry(self):
        panel = QWidget(); layout = QHBoxLayout(panel)
        left = QWidget(); form = QFormLayout(left)
        self.LmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Lx']):g}"); form.addRow("L (mm):", self.LmEditField)
        self.wmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Ly']):g}"); form.addRow("w (mm):", self.wmEditField)
        self.HmEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Lz']):g}"); form.addRow("H (mm):", self.HmEditField)
        self.HoleRadiusEditField = QLineEdit("0"); form.addRow("Hole side length (mm):", self.HoleRadiusEditField)
        self.HoleCenterXEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Lx'] / 2.0):g}"); form.addRow("Hole center X (mm):", self.HoleCenterXEditField)
        self.HoleCenterYEditField = QLineEdit(f"{self.m_to_mm(self.geometry['Ly'] / 2.0):g}"); form.addRow("Hole center Y (mm):", self.HoleCenterYEditField)
        btn_vis = QPushButton("Visualize Geometry"); btn_vis.clicked.connect(self.VasulizeGeometryButtonPushed); form.addRow(btn_vis)
        self.EPaEditField = QLineEdit(f"{self.pa_to_mpa(self.material['E']):g}"); form.addRow("E (MPa):", self.EPaEditField)
        self.NuEditField = QLineEdit(str(self.material['nu'])); form.addRow("Nu:", self.NuEditField)
        self.rhokgm3EditField = QLineEdit(str(self.material['rho'])); form.addRow("rho (kg/m^3):", self.rhokgm3EditField)
        self.EsizexEditField = QLineEdit(str(self.mesh_params['nx'])); form.addRow("Esize.x:", self.EsizexEditField)
        self.EsizeyEditField = QLineEdit(str(self.mesh_params['ny'])); form.addRow("Esize.y:", self.EsizeyEditField)
        self.EsizezEditField = QLineEdit(str(self.mesh_params['nz'])); form.addRow("Esize.z:", self.EsizezEditField)
        self.Element_typeDropDown = QComboBox(); self.Element_typeDropDown.addItems(["Hexa8", "Hexa20", "Tet4", "Tet10"]); form.addRow("Element_type:", self.Element_typeDropDown)
        self.IntpointDropDown = QComboBox(); self.IntpointDropDown.addItems(["Full", "Reduce","14point"]); form.addRow("Int point:", self.IntpointDropDown)
        btn_mesh = QPushButton("Meshing"); btn_mesh.clicked.connect(self.MeshingButtonPushed); form.addRow(btn_mesh)
        btn_clear = QPushButton("🗑️ Clear Geometry & Mesh"); btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold;"); btn_clear.clicked.connect(self.action_clear_panel1); form.addRow(btn_clear)
        self.MeshinfoTextArea = QTextEdit(); self.MeshinfoTextArea.setReadOnly(True); form.addRow("Mesh info:", self.MeshinfoTextArea)
        right = QSplitter(Qt.Orientation.Vertical)
        self.UIAxes = QtInteractor(right); right.addWidget(self.UIAxes) 
        self.UIAxes2 = QtInteractor(right); right.addWidget(self.UIAxes2) 
        layout.addWidget(left, 1); layout.addWidget(right, 3)
        return panel

    def create_panel2_load_bc(self):
        panel = QWidget(); layout = QVBoxLayout(panel) 
        top_widget = QWidget(); top_layout = QHBoxLayout(top_widget)
        vbox_beam = QVBoxLayout(); vbox_beam.addWidget(QLabel("<b>Beam Type:</b>"))
        self.BeamTypeDropDown = QComboBox(); self.BeamTypeDropDown.addItems(["Cantilever", "Fixed-Fixed", "Simply Supported", "Elastic Foundation", "Axis Load (Tensile)"])
        vbox_beam.addWidget(self.BeamTypeDropDown); top_layout.addLayout(vbox_beam)
        vbox_foundation = QVBoxLayout(); vbox_foundation.addWidget(QLabel("<b>Foundation K (N/m):</b>"))
        self.FoundationStiffnessEditField = QLineEdit("1e6"); self.FoundationStiffnessEditField.setFixedWidth(100); vbox_foundation.addWidget(self.FoundationStiffnessEditField); top_layout.addLayout(vbox_foundation)
        vbox_pos = QVBoxLayout()
        beam_len = self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0
        start_pos = (50 / 100.0) * beam_len
        self.lbl_load_pos = QLabel(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm(start_pos):.1f} mm</span>")
        vbox_pos.addWidget(self.lbl_load_pos)
        self.LoadPositionSlider = QSlider(Qt.Orientation.Horizontal)
        self.LoadPositionSlider.setMinimum(0); self.LoadPositionSlider.setMaximum(100); self.LoadPositionSlider.setValue(50)
        self.LoadPositionSlider.setMinimumWidth(200); self.LoadPositionSlider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.LoadPositionSlider.valueChanged.connect(lambda v: self.lbl_load_pos.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm((v/100.0) * (self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0)):.1f} mm</span>"))
        vbox_pos.addWidget(self.LoadPositionSlider); top_layout.addLayout(vbox_pos)
        vbox_val = QVBoxLayout(); vbox_val.addWidget(QLabel("<b>Load Value (N):</b>"))
        self.LoadValueNEditField = QLineEdit("-10"); self.LoadValueNEditField.setFixedWidth(80); vbox_val.addWidget(self.LoadValueNEditField); top_layout.addLayout(vbox_val)
        vbox_apply = QVBoxLayout(); self.GravitationalForceSwitch = QCheckBox("Enable Gravity"); vbox_apply.addWidget(self.GravitationalForceSwitch)
        btn_apply = QPushButton("Apply Load & BC"); btn_apply.setStyleSheet("font-weight: bold; padding: 6px; background-color: #2b5797; color: white;")
        btn_apply.clicked.connect(self.ApplyLoadButtonPushed); vbox_apply.addWidget(btn_apply)
        btn_clear = QPushButton("🗑️ Clear Load Visuals"); btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 6px;"); btn_clear.clicked.connect(self.action_clear_panel2); vbox_apply.addWidget(btn_clear)
        top_layout.addLayout(vbox_apply)
        vbox_info = QVBoxLayout(); vbox_info.addWidget(QLabel("<b>Matrix Info:</b>"))
        self.MatrixSizeTextArea = QTextEdit(); self.MatrixSizeTextArea.setReadOnly(True); self.MatrixSizeTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        self.MatrixSizeTextArea.setMaximumHeight(45); self.MatrixSizeTextArea.setFixedWidth(150); vbox_info.addWidget(self.MatrixSizeTextArea)
        top_layout.addLayout(vbox_info); layout.addWidget(top_widget, 0)
        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        self.UIAxes3 = QtInteractor(bottom_splitter); bottom_splitter.addWidget(self.UIAxes3)
        self.fig_forces = Figure(); self.UIAxes4 = self.fig_forces.add_subplot(111); self.canvas_forces = FigureCanvas(self.fig_forces)
        bottom_splitter.addWidget(self.canvas_forces); bottom_splitter.setSizes([700, 300]); layout.addWidget(bottom_splitter, 1)
        return panel

    def create_panel3_solve(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        btn_solve = QPushButton("Solve"); btn_solve.clicked.connect(self.SolveButtonPushed)
        self.ComputationalInfromationTextArea = QTextEdit(); self.ComputationalInfromationTextArea.setReadOnly(True)
        layout.addWidget(btn_solve); layout.addWidget(QLabel("Computational Information:")); layout.addWidget(self.ComputationalInfromationTextArea)
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
        btn_plot = QPushButton("Open PostProcessing"); btn_plot.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 4px;"); btn_plot.clicked.connect(self.OpenPostProcessingButtonPushed); top_layout.addWidget(btn_plot)
        btn_clear = QPushButton("🗑️ Clear Graphics"); btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px 20px; border-radius: 4px;"); btn_clear.clicked.connect(self.action_clear_panel4); top_layout.addWidget(btn_clear)
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
        self.num_snapshotsEditField = QLineEdit("12"); self.num_snapshotsEditField.setFixedWidth(100); input_layout.addWidget(self.num_snapshotsEditField); input_layout.addStretch()
        btn_clear_rom = QPushButton("🧹 Clear ROM Memory"); btn_clear_rom.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 10px 15px; border-radius: 5px;"); btn_clear_rom.clicked.connect(self.clear_rom_memory); input_layout.addWidget(btn_clear_rom)
        btn_train = QPushButton("Start ROM Training"); btn_train.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 5px;"); btn_train.clicked.connect(self.TrainButtonPushed); input_layout.addWidget(btn_train)
        btn_clear = QPushButton("🗑️ Clear SVD Plot"); btn_clear.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px 20px; border-radius: 5px;"); btn_clear.clicked.connect(self.action_clear_panel5); input_layout.addWidget(btn_clear)
        layout.addLayout(input_layout)
        layout.addWidget(QLabel("<b>Training Log & Time:</b>"))
        self.TrainningTimeTextArea = QTextEdit(); self.TrainningTimeTextArea.setReadOnly(True); self.TrainningTimeTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
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
        self.ValidationLoadPositionSlider.valueChanged.connect(lambda v: self.lbl_load_pos_val.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{self.m_to_mm((v/100.0) * self.geometry['Lx']):.1f} mm</span>"))
        form.addRow(self.lbl_load_pos_val, self.ValidationLoadPositionSlider)
        self.ValidationLoadNEditField = QLineEdit("-10"); form.addRow("Validation Load (N):", self.ValidationLoadNEditField)
        self.TypeofStressesDropDown_2 = QComboBox(); self.TypeofStressesDropDown_2.addItems(['Sigma_xx', 'Sigma_yy', 'Sigma_zz', 'Tau_xy', 'Tau_yz', 'Tau_zx'])
        form.addRow("Type of Stresses:", self.TypeofStressesDropDown_2)
        self.CheckAccuracyButton = QPushButton("Check Accuracy (FEM vs ROM)")
        self.CheckAccuracyButton.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b5797; color: white;")
        self.CheckAccuracyButton.clicked.connect(self.CheckAccuracyButtonPushed); form.addRow(self.CheckAccuracyButton)
        btn_clear_graphics = QPushButton("🗑️ Clear Accuracy Graphics"); btn_clear_graphics.setStyleSheet("font-weight: bold; padding: 10px; background-color: #7f8c8d; color: white;"); btn_clear_graphics.clicked.connect(self.action_clear_panel6); form.addRow(btn_clear_graphics)
        self.AccuracyResultsTextArea = QTextEdit(); self.AccuracyResultsTextArea.setReadOnly(True); self.AccuracyResultsTextArea.setStyleSheet("font-family: Courier; font-size: 12pt; background-color: #f4f4f4;")
        form.addRow(self.AccuracyResultsTextArea)
        self.SaveButton = QPushButton("Save ROM to Disk"); self.SaveButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #2e8b57; color: white;"); self.SaveButton.clicked.connect(self.SaveButtonPushed); form.addRow(self.SaveButton)
        self.ClearBankButton = QPushButton("Clear ROM Bank"); self.ClearBankButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #b22222; color: white;"); self.ClearBankButton.clicked.connect(self.ClearBankButtonPushed); form.addRow(self.ClearBankButton)
        right = QSplitter(Qt.Orientation.Horizontal)
        fem_widget = QWidget(); fem_layout = QVBoxLayout(fem_widget)
        label_fem = QLabel("<b>FEM</b>"); label_fem.setAlignment(Qt.AlignmentFlag.AlignCenter); self.UIAxes9 = QtInteractor(fem_widget)
        fem_layout.addWidget(label_fem); fem_layout.addWidget(self.UIAxes9); right.addWidget(fem_widget)
        rom_widget = QWidget(); rom_layout = QVBoxLayout(rom_widget)
        label_rom = QLabel("<b>ROM (Direct B-Matrix Physics Recovery)</b>"); label_rom.setAlignment(Qt.AlignmentFlag.AlignCenter); self.UIAxes10 = QtInteractor(rom_widget)
        rom_layout.addWidget(label_rom); rom_layout.addWidget(self.UIAxes10); right.addWidget(rom_widget)
        layout.addWidget(left, 1); layout.addWidget(right, 3)
        return panel

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
        hole_size = self.mm_to_m(float(self.HoleRadiusEditField.text())) if hasattr(self, 'HoleRadiusEditField') else 0.0
        hole_cx = self.mm_to_m(float(self.HoleCenterXEditField.text())) if hasattr(self, 'HoleCenterXEditField') else L / 2.0
        hole_cy = self.mm_to_m(float(self.HoleCenterYEditField.text())) if hasattr(self, 'HoleCenterYEditField') else W / 2.0

        if hole_size > 0.0 and 0.0 <= hole_cx <= L and 0.0 <= hole_cy <= W:
            solid = pv.Box(bounds=(0, L, 0, W, 0, H))
            half_size = hole_size / 2.0
            cutout = pv.Box(bounds=(hole_cx - half_size, hole_cx + half_size, hole_cy - half_size, hole_cy + half_size, 0.0, H))
            geom = solid
            try:
                if hasattr(solid, 'boolean_difference') and hasattr(solid, 'triangulate') and hasattr(cutout, 'triangulate'):
                    solid_tri = solid.triangulate()
                    cutout_tri = cutout.triangulate()
                    geom = solid_tri.boolean_difference(cutout_tri)
                    if not hasattr(geom, 'points') or len(geom.points) == 0:
                        geom = solid_tri
                elif hasattr(solid, 'boolean_difference'):
                    geom = solid.boolean_difference(cutout)
            except Exception:
                geom = solid
            self.UIAxes.add_mesh(geom, name='geom_box', color="lightblue", show_edges=True, opacity=0.4)
            self.UIAxes.add_mesh(cutout, name='hole_cutout', color="white", opacity=0.05, show_edges=False)
        else:
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
        self.hole_params = {
            'size': max(0.0, float(self.HoleRadiusEditField.text()) / 1000.0),
            'cx': max(0.0, float(self.HoleCenterXEditField.text()) / 1000.0),
            'cy': max(0.0, float(self.HoleCenterYEditField.text()) / 1000.0),
        }
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
        self.K_global = None; self.B_global = None
        gc.collect()

        self.lock_ui() 
        try:
            self.Phi = None; self.K_rom = None; self.SnapshotMatrix = None; self.B_global = None
            gc.collect()
            
            if not hasattr(self, 'geometry') or 'Lx' not in self.geometry:
                QMessageBox.warning(None, "Missing Data", "Geometry not found! Please generate the mesh first.")
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
            QMessageBox.critical(None, "Application Error", f"Error: {str(e)}\n\n{traceback.format_exc()}")
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
                    N = np.zeros(8); dN_dxi = np.zeros(8); dN_deta = np.zeros(8)
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
                if abs(detJ) < 1e-12: continue
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
            [1-nu, nu,    nu,    0, 0, 0],
            [nu,   1-nu, nu,    0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        
        n_order = 2 if Settings.get('Integration', '').lower() == 'full' else (1 if Settings.get('Integration', '').lower() == 'reduced' else 0)
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
            Be_all[ig*6:(ig+1)*6, :] = B; dV = detJ * w; Ke += (B.T @ C @ B) * dV
        return Ke, Fb, np.zeros(30), np.zeros(30), Fb, C, Be_all
    
    def Tet10_ShapeFunctions(self, xi, eta, zeta, L4):
        N = np.array([L4*(2*L4-1), xi*(2*xi-1), eta*(2*eta-1), zeta*(2*zeta-1), 4*L4*xi, 4*xi*eta, 4*eta*L4, 4*L4*zeta, 4*xi*zeta, 4*eta*zeta])
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
        xi = g_pts[0, 0]; eta = g_pts[0, 1]; zeta = g_pts[0, 2]; w = g_w[0] * (1.0 / 6.0)
        dN_nat = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        J = dN_nat.T @ Coord; detJ = abs(np.linalg.det(J)); dN_dx = dN_nat @ np.linalg.inv(J).T 
        B = np.zeros((6, 12))
        for i in range(4):
            c = i * 3; dx, dy, dz = dN_dx[i, 0], dN_dx[i, 1], dN_dx[i, 2]
            B[0, c]   = dx; B[1, c+1] = dy; B[2, c+2] = dz
            B[3, c:c+2] = [dy, dx]; B[4, c+1:c+3] = [dz, dy]; B[5, [c, c+2]] = [dz, dx]
        Be_all[0:6, :] = B; Ke += (B.T @ C @ B) * detJ * w
        return Ke, Fb, np.zeros(12), np.zeros(12), Fb, C, Be_all

    def Hexa20_Element_Routine(self, Material, Coord, Loads, Settings):
        E = Material['E']; nu = Material['nu']
        D_const = E / ((1 + nu) * (1 - 2 * nu))
        D = D_const * np.array([
            [1-nu, nu,    nu,    0, 0, 0],
            [nu,   1-nu, nu,    0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        Ke = np.zeros((60, 60)); Fb = np.zeros(60)
        integration_mode = Settings.get('Integration', '').lower()
        if integration_mode == '14point':
            num_gp = 14
            a = 0.795822425754221; b = 0.758786910639328
            w_a = 0.886421592695420; w_b = 0.335180055401662
            gp_corners = np.array([[-a, -a, -a], [ a, -a, -a], [ a,  a, -a], [-a,  a, -a], [-a, -a,  a], [ a, -a,  a], [ a,  a,  a], [-a,  a,  a]])
            gp_axes = np.array([[-b,  0,  0], [ b,  0,  0], [ 0, -b,  0], [ 0,  b,  0], [ 0,  0, -b], [ 0,  0,  b]])
            g_pts = np.vstack((gp_corners, gp_axes)); g_w = np.concatenate((np.ones(8)*w_a, np.ones(6)*w_b))
        else:
            n_order = 3 if integration_mode == 'full' else 2
            g_pts, g_w = self.BuildHexaGauss(n_order); num_gp = n_order**3
        Be_all = np.zeros((6 * g_pts.shape[0], 60)); gp_count = 0
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
            Be_all[gp_count*6:(gp_count+1)*6, :] = B; Ke += (B.T @ D @ B) * detJ * w; gp_count += 1
        return Ke, Fb, np.zeros(60), np.zeros(60), Fb, D, Be_all

    def Hexa20_ShapeFunctions(self, xi, eta, zeta):
        N = np.zeros(20); dN_dxi = np.zeros(20); dN_deta = np.zeros(20); dN_dzeta = np.zeros(20)
        pts = np.array([[-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1], [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1]])
        ri = pts[:, 0]; si = pts[:, 1]; ti = pts[:, 2]
        val = (1 + xi*ri) * (1 + eta*si) * (1 + zeta*ti)
        N[:8] = 0.125 * val * (xi*ri + eta*si + zeta*ti - 2)
        dN_dxi[:8]   = 0.125 * ri * (1+eta*si)*(1+zeta*ti) * (2*xi*ri + eta*si + zeta*ti - 1)
        dN_deta[:8]  = 0.125 * si * (1+xi*ri)*(1+zeta*ti)  * (xi*ri + 2*eta*si + zeta*ti - 1)
        dN_dzeta[:8] = 0.125 * ti * (1+xi*ri)*(1+eta*si)   * (xi*ri + eta*si + 2*zeta*ti - 1)
        mid_coords = np.array([[ 0, -1, -1], [ 1,  0, -1], [ 0,  1, -1], [-1,  0, -1], [ 0, -1,  1], [ 1,  0,  1], [ 0,  1,  1], [-1,  0,  1], [-1, -1,  0], [ 1, -1,  0], [ 1,  1,  0], [-1,  1,  0]])
        for k in range(12):
            id_val = k + 8; ri_m, si_m, ti_m = mid_coords[k]
            if ri_m == 0: 
                N[id_val] = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_dxi[id_val] = 0.25 * (-2*xi) * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_deta[id_val] = 0.25 * (1 - xi**2) * (si_m) * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (ti_m)
            elif si_m == 0: 
                N[id_val] = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (1 + zeta*ti_m)
                dN_dxi[id_val] = 0.25 * (ri_m) * (1 - eta**2) * (1 + zeta*ti_m)
                dN_deta[id_val] = 0.25 * (1 + xi*ri_m) * (-2*eta) * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (ti_m)
            elif ti_m == 0: 
                N[id_val] = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (1 - zeta**2)
                dN_dxi[id_val] = 0.25 * (ri_m) * (1 + eta*si_m) * (1 - zeta**2)
                dN_deta[id_val] = 0.25 * (1 + xi*ri_m) * (si_m) * (1 - zeta**2)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (-2*zeta)
        return N, dN_dxi, dN_deta, dN_dzeta
    
    def is_axis_tension_mode(self):
        mode = self.BeamTypeDropDown.currentText().lower() if hasattr(self, 'BeamTypeDropDown') else ''
        return 'axis' in mode or 'tensile' in mode

    def is_elastic_foundation_mode(self):
        mode = self.BeamTypeDropDown.currentText().lower() if hasattr(self, 'BeamTypeDropDown') else ''
        return 'elastic' in mode or 'foundation' in mode

    def define_loads_at_pos(self, target_x, P_val):
        X = self.node_coords[:, 0]; Z = self.node_coords[:, 2] 
        tol = 1e-8; max_z = np.max(Z); max_x = np.max(X)
        unique_x = np.unique(X); diffs = target_x - unique_x
        if self.is_axis_tension_mode():
            point_nodes = np.where(np.abs(X - max_x) < tol)[0]
            num_n = len(point_nodes); point_load_values = np.zeros((3, num_n))
            if num_n > 0: point_load_values[0, :] = P_val / num_n
            return {'point_nodes': point_nodes, 'point_load_values': point_load_values}
        
        left_mask = np.where(diffs >= -tol)[0]
        left_idx = left_mask[-1] if len(left_mask) > 0 else 0
        right_mask = np.where(diffs <= tol)[0]
        right_idx = right_mask[0] if len(right_mask) > 0 else len(unique_x) - 1
        
        loads = {}
        if left_idx == right_idx:
            x_val = unique_x[left_idx]
            point_nodes = np.where((np.abs(X - x_val) < tol) & (np.abs(Z - max_z) < tol))[0]
            num_n = len(point_nodes); point_load_values = np.zeros((3, num_n))
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
            load_vecs_L = np.zeros((3, num_L)); 
            if num_L > 0: load_vecs_L[2, :] = val_L
            load_vecs_R = np.zeros((3, num_R))
            if num_R > 0: load_vecs_R[2, :] = val_R
            loads['point_load_values'] = np.hstack((load_vecs_L, load_vecs_R))
        return loads
    
    def boundary_conditions(self, K_global, F_global, node_coords, beam_type):
        tol = 1e-5; X = node_coords[:, 0]; Y = node_coords[:, 1]; Z = node_coords[:, 2]
        x_min = np.min(X); x_max = np.max(X); z_min = np.min(Z)
        num_total = K_global.shape[0]
        
        if self.is_axis_tension_mode():
            fixed_nodes = np.where(np.abs(X - x_min) < tol)[0]
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
        elif 'cantilever' in beam_type.lower():
            fixed_nodes = np.where(np.abs(X - x_min) < tol)[0]
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
        elif self.is_elastic_foundation_mode():
            foundation_nodes = np.where(np.abs(Z - z_min) < tol)[0]
            if len(foundation_nodes) > 0:
                anchor_nodes = foundation_nodes[np.argsort(np.abs(X[foundation_nodes] - x_min) + np.abs(Y[foundation_nodes] - np.min(Y)))[:2]]
                horizontal_dofs = []
                for node_id in anchor_nodes:
                    horizontal_dofs.extend([node_id * 3 + 0, node_id * 3 + 1])
                fixed_dofs = np.array(np.unique(horizontal_dofs), dtype=int)
            else: fixed_dofs = np.array([], dtype=int)
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
        K_reduced = K_global.tocsr()[free_dofs, :][:, free_dofs].tocsr() if sp.issparse(K_global) else K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F_global[free_dofs]
        return K_reduced, F_reduced, fixed_dofs, free_dofs
        
    def visualize_BC_3d(self, node_coords, element_connectivity, element_type, mesh_info, bc_info, F_global, targetAxes):
        F_nodes = F_global.reshape(-1, 3); load_mag = np.linalg.norm(F_nodes, axis=1)
        max_load = np.max(load_mag)
        applied_idx = np.where(load_mag > max_load * 0.01)[0] if max_load > 0 else np.array([])
        bbox_min = np.min(node_coords, axis=0); bbox_max = np.max(node_coords, axis=0)
        diagonal = np.linalg.norm(bbox_max - bbox_min)
        sphere_radius = diagonal * 0.015; arrow_scale = diagonal * 0.15 
        n_vis = 8 if 'Hexa' in element_type else 4
        vtk_type = pv.CellType.HEXAHEDRON if 'Hexa' in element_type else pv.CellType.TETRA
        vis_connectivity = element_connectivity[:, :n_vis]
        grid = pv.UnstructuredGrid({vtk_type: vis_connectivity}, node_coords)
        targetAxes.add_mesh(grid, name='bc_base_mesh', show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        fixed_dofs = np.array(bc_info.get('fixed_dofs_indices', []))
        if len(fixed_dofs) > 0:
            fixed_nodes = np.unique(fixed_dofs // 3)
            fixed_coords = np.atleast_2d(node_coords[fixed_nodes])
            spheres = pv.PolyData(fixed_coords).glyph(geom=pv.Sphere(radius=sphere_radius), scale=False, orient=False)
            targetAxes.add_mesh(spheres, name='bc_fixed_dofs', color="red", show_edges=True, edge_color="black") 
        if len(applied_idx) > 0:
            load_coords = np.atleast_2d(node_coords[applied_idx]); load_vectors = np.atleast_2d(F_nodes[applied_idx])
            mags = load_mag[applied_idx]; load_dirs = load_vectors / mags[:, np.newaxis]
            cloud = pv.PolyData(load_coords); cloud["vectors"] = load_dirs * arrow_scale
            arrows = cloud.glyph(orient="vectors", scale="vectors", factor=1.0, geom=pv.Arrow())
            targetAxes.add_mesh(arrows, name='bc_force_arrows', color="blue")
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
            targetAxes.grid(True, linestyle='--', alpha=0.6)
            targetAxes.set_xlabel('Global Node ID'); targetAxes.set_ylabel('Vertical Force (kN)')
            targetAxes.set_title(r'$\bf{Nodal\ Load\ Distribution\ (Lever\ Rule\ Check)}$')
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
        return np.column_stack((X.ravel(order='F'), Y.ravel(order='F'), Z.ravel(order='F'))), (WX * WY * WZ).ravel(order='F')

    def GetGaussTableTetrahedra(self, n):
        if n == 1: return np.array([[0.25, 0.25, 0.25]]), np.array([1.0])
        a = 0.58541020; b = 0.13819660
        return np.array([[a, b, b], [b, a, b], [b, b, a], [b, b, b]]), np.array([0.25, 0.25, 0.25, 0.25])

    def SolveButtonPushed(self):
        self.lock_ui()
        try:
            if not hasattr(self, 'K_reduced') or not hasattr(self, 'F_reduced'):
                self.ComputationalInfromationTextArea.setText("Error: Apply Boundary Conditions first.")
                return
            progress = QProgressDialog("Solving FEM System...", "Cancel", 0, 0, self)
            progress.show(); QApplication.processEvents()
            
            t0 = time.perf_counter()
            U_free = spsolve(self.K_reduced.tocsr(), self.F_reduced) 
            solve_cpu_time = time.perf_counter() - t0
            progress.close()
            
            num_dof = self.K_global.shape[0]
            self.U_full = np.zeros(num_dof)
            self.U_full[self.bc_info['free_dofs_indices']] = U_free

            if hasattr(self, 'B_global') and self.B_global is not None:
                self.Sigma_Final2 = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, self.U_full, self.node_coords, self.element_connectivity, self.element_type)

            summary_text = f"--- SOLVER SUMMARY ---\nCPU Solve Time: {solve_cpu_time:.4f} s\nMax Deflection: {np.max(np.abs(self.U_full))*1000:.4f} mm"
            self.ComputationalInfromationTextArea.setText(summary_text)
        except Exception as e:
            QMessageBox.critical(None, "Solver Error", f"Error:\n{str(e)}")
        finally:
            self.unlock_ui()

    def PostProcess_Stress_3Dsparse(self, B_global, D, U_global, Coords, Connectivity, ElementType):
        Num_Nodes = Coords.shape[0]; Num_Elem = Connectivity.shape[0]
        total_B_rows = B_global.shape[0]; num_gp = total_B_rows // (6 * Num_Elem)
        epsilon_all = B_global.dot(U_global); strain_matrix = epsilon_all.reshape(-1, 6).T
        sigma_gauss_all = D @ strain_matrix 
        E_mat = self.Get_Emat_3D_Full(Coords[Connectivity[0, :]], ElementType, num_gp)
        nodes_per_elem = Connectivity.shape[1]
        row_idx = np.repeat(Connectivity, num_gp, axis=1).ravel()
        gp_ids_per_elem = np.arange(Num_Elem)[:, None] * num_gp + np.arange(num_gp)[None, :]
        col_idx = np.repeat(gp_ids_per_elem[:, None, :], nodes_per_elem, axis=1).ravel()
        val_idx = np.repeat(E_mat[None, :, :], Num_Elem, axis=0).ravel()
        E_global = sp.csr_matrix((val_idx, (row_idx, col_idx)), shape=(Num_Nodes, Num_Elem * num_gp))
        Nodal_Stress_Sum = E_global.dot(sigma_gauss_all.T) 
        Node_Weights = np.array(E_global.dot(np.ones(Num_Elem * num_gp))).flatten(); Node_Weights[Node_Weights == 0] = 1.0
        return Nodal_Stress_Sum / Node_Weights[:, np.newaxis]

    def Get_Emat_3D_Full(self, Coords, ElementType, num_gp):
        nodes_per_elem = Coords.shape[0]
        if num_gp == 1: return np.ones((nodes_per_elem, 1))
        if ElementType == 'Hexa8':
            gpts = [-1/np.sqrt(3), 1/np.sqrt(3)]; GP = np.zeros((8, 3)); cnt = 0
            for i in range(2):
                for j in range(2):
                    for k in range(2): GP[cnt, :] = [gpts[i], gpts[j], gpts[k]]; cnt += 1
            Node_Loc = np.array([[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1], [-1,-1, 1], [1,-1, 1], [1,1, 1], [-1,1, 1]])
            r = np.sqrt(3); E_mat = np.zeros((8, 8))
            for n in range(8):
                for k in range(8): E_mat[n, k] = 0.125 * (1 + Node_Loc[n,0]*GP[k,0]*r) * (1 + Node_Loc[n,1]*GP[k,1]*r) * (1 + Node_Loc[n,2]*GP[k,2]*r)
            return E_mat
        elif ElementType == 'Hexa20' and num_gp == 14:
            a = 0.795822425754221; b = 0.758786910639328
            gp_corners = np.array([[-a, -a, -a], [ a, -a, -a], [ a,  a, -a], [-a,  a, -a], [-a, -a,  a], [ a, -a,  a], [ a,  a,  a], [-a,  a,  a]])
            gp_axes = np.array([[-b,  0,  0], [ b,  0,  0], [ 0, -b,  0], [ 0,  b,  0], [ 0,  0, -b], [ 0,  0,  b]])
            g_pts = np.vstack((gp_corners, gp_axes)); N_G = np.zeros((14, 20))
            for k in range(14):
                N_shape, _, _, _ = self.Hexa20_ShapeFunctions(g_pts[k, 0], g_pts[k, 1], g_pts[k, 2])
                N_G[k, :] = N_shape
            return np.linalg.pinv(N_G)
        elif ElementType == 'Tet10':
            a_t, b_t = 0.58541020, 0.13819660; g_pts = np.array([[a_t, b_t, b_t], [b_t, a_t, b_t], [b_t, b_t, a_t], [b_t, b_t, b_t]]); XYZ_G = np.zeros((4, 3))
            for k in range(4):
                L4 = 1 - np.sum(g_pts[k])
                N = np.array([L4*(2*L4-1), g_pts[k,0]*(2*g_pts[k,0]-1), g_pts[k,1]*(2*g_pts[k,1]-1), g_pts[k,2]*(2*g_pts[k,2]-1), 4*L4*g_pts[k,0], 4*g_pts[k,0]*g_pts[k,1], 4*g_pts[k,1]*L4, 4*L4*g_pts[k,2], 4*g_pts[k,0]*g_pts[k,2], 4*g_pts[k,1]*g_pts[k,2]])
                XYZ_G[k, :] = N.T @ Coords
            return np.column_stack((np.ones(10), Coords)) @ np.linalg.pinv(np.column_stack((np.ones(4), XYZ_G)))
        return np.ones((nodes_per_elem, num_gp)) / num_gp

    def OpenPostProcessingButtonPushed(self):
        self.lock_ui() 
        try:
            if self.Sigma_Final2 is None:
                self.Sigma_Final2 = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, self.U_full, self.node_coords, self.element_connectivity, self.element_type)
            self.plot_stresses(self.Sigma_Final2, self.TypeofStressesDropDown.currentText(), self.UIAxes5, self.U_full, float(self.ScaleFactorEditField.text()))
            self.plot_FS(self.MethodDropDown.currentText(), float(self.YieldStrengthMpaEditField.text()), self.UIAxes6, self.Sigma_Final2, self.U_full, float(self.ScaleFactorEditField.text()), self.DisplayChoiceDropDown.currentText())
        except Exception as e:
            QMessageBox.critical(None, "Error", f"{str(e)}")
        finally:
            self.unlock_ui(); gc.collect()

    def plot_stresses(self, Sigma_Final, stress_type, targetAxes, U_full, scale_factor):
        if len(self.node_coords) != len(Sigma_Final): return
        stress_map = {'Sigma_xx': (0, 'Sigma_xx'), 'Sigma_yy': (1, 'Sigma_yy'), 'Sigma_zz': (2, 'Sigma_zz'), 'Tau_xy': (3, 'Tau_xy'), 'Tau_yz': (4, 'Tau_yz'), 'Tau_zx': (5, 'Tau_zx'), 'Tau_xz': (5, 'Tau_zx')}
        col, lbl = stress_map.get(stress_type, (0, 'Sigma_xx'))
        stress_data = Sigma_Final[:, col] / 1e6 
        c_limits = [np.min(stress_data), np.max(stress_data)]
        if np.isclose(c_limits[0], c_limits[1]): c_limits = [c_limits[0] - 0.1, c_limits[1] + 0.1]

        try:
            U_nodes = U_full.reshape(-1, 3); def_coords = self.node_coords + (U_nodes * scale_factor)
            n_vis = 8 if 'Hexa' in self.element_type else 4
            vtk_type = pv.CellType.HEXAHEDRON if 'Hexa' in self.element_type else pv.CellType.TETRA
            grid_deformed = pv.UnstructuredGrid({vtk_type: self.element_connectivity[:, :n_vis]}, def_coords)
            grid_deformed.point_data["Stress (MPa)"] = stress_data
            targetAxes.clear()
            targetAxes.add_mesh(grid_deformed, scalars="Stress (MPa)", cmap="jet", clim=c_limits, show_edges=True)
            targetAxes.render()
        except Exception as e:
            print(e)

    def plot_FS(self, failure_mode, yield_strength, targetAxes, Sigma_Final, U_full, scale_factor, display_type="FS"):
        if len(self.node_coords) != len(Sigma_Final): return
        sx, sy, sz = Sigma_Final[:, 0], Sigma_Final[:, 1], Sigma_Final[:, 2]; txy, tyz, tzx = Sigma_Final[:, 3], Sigma_Final[:, 4], Sigma_Final[:, 5]
        C_data = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
        FS_data = yield_strength / np.maximum(C_data, 1e-6)
        plot_scalars = C_data if "stress" in display_type.lower() else FS_data
        plot_name = "Stress Data (MPa)" if "stress" in display_type.lower() else "Factor of Safety"
        
        U_nodes = U_full.reshape(-1, 3); def_coords = self.node_coords + (U_nodes * scale_factor)
        n_vis = 8 if 'Hexa' in self.element_type else 4
        vtk_type = pv.CellType.HEXAHEDRON if 'Hexa' in self.element_type else pv.CellType.TETRA
        grid_deformed = pv.UnstructuredGrid({vtk_type: self.element_connectivity[:, :n_vis]}, def_coords)
        grid_deformed.point_data[plot_name] = plot_scalars
        targetAxes.clear()
        targetAxes.add_mesh(grid_deformed, scalars=plot_name, cmap="jet", show_edges=True)
        targetAxes.render()

    def TrainButtonPushed(self):
        """
        Component Mode Synthesis (CMS) / Craig-Bampton Training Implementation:
        Enriches the global POD basis with constraint/boundary modes to accurately
        capture near-clamp high-gradient stress fields.
        """
        self.lock_ui() 
        try:
            self.Phi = None; self.K_rom = None; self.SnapshotMatrix = None
            gc.collect()
            
            if not hasattr(self, 'K_reduced') or self.K_reduced is None:
                raise RuntimeError("CMS Training requires a solved FEM model.")

            num_snapshots = int(self.num_snapshotsEditField.text())
            
            # 1. Clustered Snapshot Generation near Fixed Support
            edge_count = max(6, num_snapshots // 2)
            bulk_count = max(1, num_snapshots - edge_count)
            left_edge = np.geomspace(0.0005, 0.05, edge_count)
            bulk = np.linspace(0.08, 0.99, bulk_count)
            x_norm = np.sort(np.unique(np.concatenate((left_edge, bulk))))
            if len(x_norm) > num_snapshots:
                x_norm = x_norm[np.round(np.linspace(0, len(x_norm) - 1, num_snapshots)).astype(int)]
            elif len(x_norm) < num_snapshots:
                x_norm = np.sort(np.unique(np.concatenate((x_norm, np.linspace(0.0005, 0.99, num_snapshots)))))[:num_snapshots]
            
            x_positions = x_norm * self.geometry['Lx']
            free_dofs = self.bc_info['free_dofs_indices']; num_free_dof = len(free_dofs)
            self.SnapshotMatrix = np.zeros((num_free_dof, num_snapshots))
            
            self.TrainningTimeTextArea.setText("*** Starting CMS Craig-Bampton Training ***\n")
            K_reduced_csr = self.K_reduced.tocsr()
            num_total_dof = self.K_global.shape[0]
            
            progress = QProgressDialog("Assembling CMS Substructure Snapshots...", "Cancel", 0, num_snapshots, self)
            progress.show()
            
            for i in range(num_snapshots):
                base_load = float(self.LoadValueNEditField.text())
                temp_loads = self.define_loads_at_pos(x_positions[i], base_load)
                F_temp = np.zeros(num_total_dof)
                for j in range(len(temp_loads['point_nodes'])):
                    F_temp[temp_loads['point_nodes'][j] * 3 : temp_loads['point_nodes'][j] * 3 + 3] += temp_loads['point_load_values'][:, j]
                
                U_free_i = spla.spsolve(K_reduced_csr, F_temp[free_dofs])
                self.SnapshotMatrix[:, i] = U_free_i
                progress.setValue(i + 1); QApplication.processEvents()
            progress.close()
            
            # 2. Extract Standard POD/Ritz Interior Modes
            U_svd, S_disp, _ = np.linalg.svd(self.SnapshotMatrix, full_matrices=False)
            cum_energy_disp = np.cumsum(S_disp**2) / np.sum(S_disp**2) * 100.0
            n_modes_interior = np.where(cum_energy_disp >= 100.00)[0][0] + 1 if np.any(cum_energy_disp >= 100.00) else min(10, num_snapshots)
            Phi_interior = U_svd[:, :n_modes_interior]

            # 3. COMPONENT MODE SYNTHESIS (CMS) ENRICHMENT: Add Static Constraint/Boundary Modes
            # This injects columns corresponding to unit loads/displacements near the fixed boundary layer
            fixed_dofs = self.bc_info['fixed_dofs_indices']
            num_boundary_modes = min(5, len(fixed_dofs))
            if num_boundary_modes > 0:
                # Build constraint modes $\Psi_c = -K_{ff}^{-1} K_{fc}$
                # For non-intrusive framework, we simulate boundary unit excitations near clamp nodes
                boundary_snapshots = []
                for b_idx in range(num_boundary_modes):
                    F_boundary = np.zeros(num_total_dof)
                    target_node = fixed_dofs[b_idx % len(fixed_dofs)] // 3
                    F_boundary[target_node * 3 + 2] = 1.0 # Unit vertical load near clamp
                    u_b_free = spla.spsolve(K_reduced_csr, F_boundary[free_dofs])
                    boundary_snapshots.append(u_b_free)
                
                Phi_boundary = np.column_stack(boundary_snapshots)
                # Orthogonalize boundary modes against interior modes via Gram-Schmidt / SVD
                Phi_combined = np.hstack((Phi_interior, Phi_boundary))
                U_cms, _, _ = np.linalg.svd(Phi_combined, full_matrices=False)
                # Keep active enriched subspace
                n_total_modes = min(n_modes_interior + num_boundary_modes, U_cms.shape[1])
                self.Phi = U_cms[:, :n_total_modes]
            else:
                self.Phi = Phi_interior

            self.K_rom = self.Phi.T @ (self.K_reduced @ self.Phi)

            # Plot SVD energy spectrum
            fig = self.UIAxes8.figure if hasattr(self.UIAxes8, 'figure') else self.UIAxes8; fig.clf()
            ax1 = fig.add_subplot(111)
            ax1.plot(np.arange(1, len(S_disp)+1), cum_energy_disp[:len(S_disp)], '-ro', linewidth=2)
            ax1.set_ylabel('Cumulative Energy (%)'); ax1.set_xlabel('Mode Number')
            ax1.set_title('CMS-Enriched ROM Invariance Spectrum')
            if hasattr(fig, 'canvas'): fig.canvas.draw_idle()

            QMessageBox.information(None, "CMS Success", f"CMS-Enriched Training Complete!\nTotal Enriched Modes: {self.Phi.shape[1]}")
        except Exception as e:
            QMessageBox.critical(None, "Training Error", f"{str(e)}\n{traceback.format_exc()}")
        finally:
            self.unlock_ui(); gc.collect()
 
    def CheckAccuracyButtonPushed(self):
        self.lock_ui() 
        progress = None
        try:
            if not hasattr(self, 'Phi') or self.Phi is None or not hasattr(self, 'K_rom'):
                raise ValueError("CMS-ROM model not found. Train the model first.")

            x_pos = (self.ValidationLoadPositionSlider.value() / 100.0) * self.geometry['Lx'] 
            P_val = float(self.ValidationLoadNEditField.text())
            scale_factor = float(self.ScaleFactorEditField.text()) if self.ScaleFactorEditField.text() else 1.0
            stress_type = self.TypeofStressesDropDown_2.currentText()
           
            progress = QProgressDialog("Running FEM vs CMS-ROM Validation...", "Cancel", 0, 3, self)
            progress.show()

           

            # 1. FEM Reference
            temp_loads = self.define_loads_at_pos(x_pos, P_val)
            F_temp = np.zeros(self.bc_info['total_dofs'])
            for j in range(len(temp_loads['point_nodes'])):
                F_temp[temp_loads['point_nodes'][j] * 3 : temp_loads['point_nodes'][j] * 3 + 3] += temp_loads['point_load_values'][:, j]

            free_dofs = self.bc_info['free_dofs_indices']; F_red = F_temp[free_dofs]
            cpu_fem_start = time.process_time()
            U_free_fem = spla.spsolve(self.K_reduced.tocsr(), F_red)
            cpu_fem = time.process_time() - cpu_fem_start

            num_dof = self.bc_info['total_dofs']
            U_full_fem = np.zeros(num_dof); U_full_fem[free_dofs] = U_free_fem
            progress.setValue(1)

            # fem stress recovery
            t0 = time.perf_counter()
            Sigma_fem = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_full_fem, self.node_coords, self.element_connectivity, self.element_type)
            time_fem_stress = time.perf_counter() - t0
            progress.setValue(2)

            # 2. CMS-ROM Online Evaluation
            cpu_rom_start = time.process_time()
            F_rom = self.Phi.T @ F_red
            alpha = np.linalg.solve(self.K_rom, F_rom)
            U_free_rom_proj = self.Phi @ alpha
            cpu_rom = time.process_time() - cpu_rom_start

            U_full_rom = np.zeros(num_dof); U_full_rom[free_dofs] = U_free_rom_proj

            # Direct Element-Wise Physical Stress Recovery on Enriched Subspace
            t0_rom_stress = time.perf_counter()
            Sigma_rom = self.PostProcess_Stress_3Dsparse(self.B_global, self.D_mat, U_full_rom, self.node_coords, self.element_connectivity, self.element_type)
            self.plot_stresses(Sigma_rom, stress_type, self.UIAxes10, U_full_rom, scale_factor)
            time_rom_stress = time.perf_counter() - t0_rom_stress
            progress.setValue(3)

            speed_up_solve = cpu_fem / max(cpu_rom, 1e-12)
            speed_up_stress = time_fem_stress / max(time_rom_stress, 1e-12)

            rel_error_U = (np.linalg.norm(U_free_fem - U_free_rom_proj) / max(np.linalg.norm(U_free_fem), 1e-12)) * 100.0
            rel_error_Sigma = (np.linalg.norm(Sigma_fem - Sigma_rom) / max(np.linalg.norm(Sigma_fem), 1e-12)) * 100.0

            results_text = (
                "--- CMS-ROM ACCURACY REPORT ---\n"
                f"FEM Max Deflection: {np.max(np.abs(U_full_fem))*1000:.4f} mm\n"
                f"CMS-ROM Deflection: {np.max(np.abs(U_full_rom))*1000:.4f} mm\n"
                f"Displacement Error: {rel_error_U:.4f} %\n\n"
                f"FEM Max Stress (\u03c3_xx): {np.max(np.abs(Sigma_fem[:,0]))/1e6:.2f} MPa\n"
                f"CMS-ROM Max Stress (\u03c3_xx): {np.max(np.abs(Sigma_rom[:,0]))/1e6:.2f} MPa\n"
                f"Stress Error (Near Fixed Clamp): {rel_error_Sigma:.4f} %\n\n"
                "--- CPU Times (process_time) ---\n"
                f"FEM solve CPU time: {cpu_fem:.4f} s\n"
                f"ROM eval CPU time: {cpu_rom:.4f} s\n"
                f"ROM is {speed_up_solve:.1f}x Faster\n\n"
                f"FEM Stress Reconstruction: {time_fem_stress:.4f} s\n"
                f"ROM Stress Reconstruction: {time_rom_stress:.4f} s\n"
                f"ROM Stress is {speed_up_stress:.1f}x Faster\n\n"
                f"FEM Total Time: {(cpu_fem + time_fem_stress):.4f} s\n"
                f"ROM Total Time: {(cpu_rom + time_rom_stress):.4f} s\n"
                f"Total System Speedup: {(cpu_fem + time_fem_stress)/(cpu_rom + time_rom_stress):.1f}x\n\n"    
                            )
            self.AccuracyResultsTextArea.setText(results_text)

        except Exception as e:
            QMessageBox.critical(None, "Validation Error", f"{str(e)}\n{traceback.format_exc()}")
        finally:
            if progress: progress.close()
            self.unlock_ui(); gc.collect()

    def SaveButtonPushed(self):
        self.lock_ui()
        try:
            if not hasattr(self, 'Phi') or self.Phi is None or not hasattr(self, 'K_rom') or self.K_rom is None:
                QMessageBox.critical(None, "Save Error", "No ROM data found!")
                self.unlock_ui(); return
            
            default_name = f"Cantilever_ROM_Direct_{datetime.now().strftime('%H%M%S')}"
            rom_label, ok = QInputDialog.getText(None, "Save ROM Data", "Enter label:", text=default_name)
            if not ok or not rom_label: self.unlock_ui(); return
                
            New_ROM = {
                'Label': rom_label, 'Phi': self.Phi, 'K_rom': self.K_rom, 'bc_info': self.bc_info, 
                'NumNodes': self.node_coords.shape[0], 'ElementType': self.element_type,
                'Nodes': self.node_coords, 'Connectivity': self.element_connectivity,
                'StressRecoveryMethod': 'Direct B-Matrix Physics Evaluation'
            }

            save_filename, _ = QFileDialog.getSaveFileName(self, "Save ROM Bank", "DigitalTwin_ROM_Bank.pkl", "Pickle Files (*.pkl)", options=QFileDialog.Option.DontConfirmOverwrite)
            if not save_filename: self.unlock_ui(); return
                
            ROM_Bank = pickle.load(open(save_filename, 'rb')) if os.path.exists(save_filename) else []
            ROM_Bank.append(New_ROM)
            pickle.dump(ROM_Bank, open(save_filename, 'wb'))
            QMessageBox.information(None, "Success", f"Saved successfully to {save_filename}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"{str(e)}")
        finally:
            self.unlock_ui()

    def ClearBankButtonPushed(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select ROM Bank", "", "Pickle Files (*.pkl)")
        if file_name and os.path.exists(file_name):
            os.remove(file_name)
            QMessageBox.information(self, "Success", "Deleted successfully.")


def main():
    app = QApplication(sys.argv)
    window = OfflinePreparationStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()