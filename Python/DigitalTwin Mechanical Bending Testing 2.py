import os
os.environ["QT_API"] = "pyqt6" # Forces PyVista to use PyQt6

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
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, 
                             QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,QMessageBox,QInputDialog,QGridLayout,
                             QLabel, QLineEdit, QComboBox, QTextEdit, QSlider, QCheckBox, QSplitter,QGroupBox)
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pickle
from datetime import datetime
import scipy.sparse.linalg as spla
import traceback

class DigitalTwin_Mechanical_Testing(QMainWindow):

    def closeEvent(self, event):
        """Cleanly shut down VTK/PyVista OpenGL windows to prevent handle errors on exit."""
        # List of all PyVista 3D canvases we created in the app
        pyvista_plotters = [
            'UIAxes', 'UIAxes2', 'UIAxes3', 
            'UIAxes_3D_Validation', 
            'UIAxes5', 'UIAxes6', 
            'UIAxes9', 'UIAxes10',
            'UIAxes5_2', 'UIAxes6_2', 'UIAxes7_2'
        ]
        
        # Safely tell each 3D canvas to power down its graphics memory
        for plotter_name in pyvista_plotters:
            if hasattr(self, plotter_name):
                plotter = getattr(self, plotter_name)
                if plotter is not None:
                    try:
                        plotter.close()
                    except Exception:
                        pass # Ignore if it's already closed
                        
        # Now it is safe to let PyQt close the main window
        event.accept()    


    def __init__(self):
        super().__init__()
        self.setWindowTitle("FEM / ROM / Digital Twin")
        self.setGeometry(100, 100, 1400, 900)

        # --- 1. MATLAB Private Properties Equivalent ---
        self.geometry = {'Lx': 6.0, 'Ly': 0.5, 'Lz': 1.0}
        self.material = {'E': 200e9, 'nu': 0.3, 'rho': 7850}
        self.mesh_params = {'nx': 10, 'ny': 3, 'nz': 3}
        self.settings = {'Integration': 'Full'}
        self.element_type = 'Hexa8'
        self.beam_type = 'Cantilever'
        
        self.node_coords = None
        self.element_connectivity = None
        self.mesh_info = {}
        self.bc_info = {}
        self.loads = {}
        
        self.K_global = None
        self.F_global = None
        self.K_reduced = None
        self.F_reduced = None
        self.D_mat = None
        self.B_global = None
        self.U_full = None
        
        self.Phi = None
        self.Phi_stress = None
        self.K_rom = None
        self.DT_Bank = []
        self.isLive = False

        # --- 2. Main UI Setup ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.build_ui()

    # =========================================================================
    # UI BUILDERS (1:1 App Designer Translation)
    # =========================================================================
    def build_ui(self):
        self.create_tab1_geometry()
        self.create_tab2_load_bc()
        self.create_tab3_solve()
        self.create_tab4_validation()
        self.create_tab5_post_processing()
        self.create_tab6_rom_training()
        self.create_tab7_rom_validation()
        self.create_tab8_classify_dt()

    def create_tab1_geometry(self):
        tab = QWidget(); layout = QHBoxLayout(tab)
        left = QWidget(); form = QFormLayout(left)
        
        self.LmEditField = QLineEdit(str(self.geometry['Lx'])); form.addRow("L(m):", self.LmEditField)
        self.wmEditField = QLineEdit(str(self.geometry['Ly'])); form.addRow("w(m):", self.wmEditField)
        self.HmEditField = QLineEdit(str(self.geometry['Lz'])); form.addRow("H(m):", self.HmEditField)
        
        btn_vis = QPushButton("Visualize Geometry"); btn_vis.clicked.connect(self.VasulizeGeometryButtonPushed)
        form.addRow(btn_vis)

        self.EPaEditField = QLineEdit(str(self.material['E'])); form.addRow("E (Pa):", self.EPaEditField)
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
        
        self.MeshinfoTextArea = QTextEdit(); self.MeshinfoTextArea.setReadOnly(True)
        form.addRow("Mesh info:", self.MeshinfoTextArea)
        
        right = QSplitter(Qt.Orientation.Vertical)
        self.UIAxes = QtInteractor(right); right.addWidget(self.UIAxes) # Geometry
        self.UIAxes2 = QtInteractor(right); right.addWidget(self.UIAxes2) # Meshing
        
        layout.addWidget(left, 1); layout.addWidget(right, 3)
        self.tabs.addTab(tab, "1. Geometry & Meshing")

    def create_tab2_load_bc(self):
        from PyQt6.QtWidgets import QSizePolicy # Required to prevent crushing
        
        tab = QWidget()
        layout = QVBoxLayout(tab) 
        
        # ==========================================
        # TOP DASHBOARD: Controls
        # ==========================================
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # 1. Beam Type
        vbox_beam = QVBoxLayout()
        vbox_beam.addWidget(QLabel("<b>Beam Type:</b>"))
        self.BeamTypeDropDown = QComboBox()
        self.BeamTypeDropDown.addItems(["Cantilever", "Fixed-Fixed", "Simply Supported"])
        vbox_beam.addWidget(self.BeamTypeDropDown)
        top_layout.addLayout(vbox_beam)
        
        # 2. THE ANTI-CRUSH SLIDER & DYNAMIC LABEL
        vbox_pos = QVBoxLayout()
        
        # Safe fallback: If geometry isn't generated yet, pretend the beam is 1.0m long
        beam_len = self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0
        start_pos = (50 / 100.0) * beam_len
        
        self.lbl_load_pos = QLabel(f"<b>Load Position:</b><br><span style='color:blue;'>{start_pos:.2f} m</span>")
        vbox_pos.addWidget(self.lbl_load_pos)
        
        self.LoadPositionSlider = QSlider(Qt.Orientation.Horizontal)
        self.LoadPositionSlider.setMinimum(0)
        self.LoadPositionSlider.setMaximum(100)
        self.LoadPositionSlider.setValue(50) # Set default to middle
        
        # THIS PREVENTS THE SLIDER FROM DISAPPEARING:
        self.LoadPositionSlider.setMinimumWidth(200) 
        self.LoadPositionSlider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Link the slider to update the label text instantly in real-time safely
        self.LoadPositionSlider.valueChanged.connect(
            lambda v: self.lbl_load_pos.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{(v/100.0) * (self.geometry.get('Lx', 1.0) if hasattr(self, 'geometry') else 1.0):.2f} m</span>")
        )
        
        vbox_pos.addWidget(self.LoadPositionSlider)
        top_layout.addLayout(vbox_pos)
        
        # 3. Load Value
        vbox_val = QVBoxLayout()
        vbox_val.addWidget(QLabel("<b>Load Value (N):</b>"))
        self.LoadValueNEditField = QLineEdit("-10000")
        self.LoadValueNEditField.setFixedWidth(80)
        vbox_val.addWidget(self.LoadValueNEditField)
        top_layout.addLayout(vbox_val)
        
        # 4. Gravity & Apply Button
        vbox_apply = QVBoxLayout()
        self.GravitationalForceSwitch = QCheckBox("Enable Gravity")
        vbox_apply.addWidget(self.GravitationalForceSwitch)
        
        btn_apply = QPushButton("Apply Load & BC")
        btn_apply.setStyleSheet("font-weight: bold; padding: 6px; background-color: #2b5797; color: white;")
        btn_apply.clicked.connect(self.ApplyLoadButtonPushed)
        vbox_apply.addWidget(btn_apply)
        top_layout.addLayout(vbox_apply)
        
        # 5. Matrix Info
        vbox_info = QVBoxLayout()
        vbox_info.addWidget(QLabel("<b>Matrix Info:</b>"))
        self.MatrixSizeTextArea = QTextEdit()
        self.MatrixSizeTextArea.setReadOnly(True)
        self.MatrixSizeTextArea.setStyleSheet("font-family: Courier; background-color: #f4f4f4;")
        self.MatrixSizeTextArea.setMaximumHeight(45)
        self.MatrixSizeTextArea.setFixedWidth(150)
        vbox_info.addWidget(self.MatrixSizeTextArea)
        top_layout.addLayout(vbox_info)
        
        layout.addWidget(top_widget, 0)
        
        # ==========================================
        # BOTTOM PANEL: Visualizations
        # ==========================================
        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.UIAxes3 = QtInteractor(bottom_splitter)
        bottom_splitter.addWidget(self.UIAxes3)
        
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        self.fig_forces = Figure()
        self.UIAxes4 = self.fig_forces.add_subplot(111)
        self.canvas_forces = FigureCanvas(self.fig_forces)
        bottom_splitter.addWidget(self.canvas_forces)
        
        bottom_splitter.setSizes([700, 300]) 
        layout.addWidget(bottom_splitter, 1)
        self.tabs.addTab(tab, "2. Load & BC")


    def create_tab3_solve(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        btn_solve = QPushButton("Solve"); btn_solve.clicked.connect(self.SolveButtonPushed)
        self.ComputationalInfromationTextArea = QTextEdit(); self.ComputationalInfromationTextArea.setReadOnly(True)
        layout.addWidget(btn_solve); layout.addWidget(QLabel("Computational Information:")); layout.addWidget(self.ComputationalInfromationTextArea)
        self.tabs.addTab(tab, "3. Solve")

    def create_tab4_validation(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # ==========================================
        # LEFT PANEL: Button, 1D Graphs, and Summary
        # ==========================================
        left = QWidget()
        left_layout = QVBoxLayout(left)

        # 1. Validation Button
        btn_val = QPushButton("Validation with Euler-Bernoulli Beam Theory")
        # Optional: Make the button pop out so the user knows to click it
        btn_val.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b5797; color: white;")
        btn_val.clicked.connect(self.ValidationwithEulierBernoullisBeamTheoryButtonPushed)
        left_layout.addWidget(btn_val)

        # 2. 1D Matplotlib Canvas
        left_layout.addWidget(QLabel("<b>1D Euler-Bernoulli Beam Theory Results</b>"))
        self.fig_1d_validation = Figure()
        self.canvas_1d_validation = FigureCanvas(self.fig_1d_validation)
        # stretch=2 gives the graph twice as much vertical space as the text box
        left_layout.addWidget(self.canvas_1d_validation, stretch=2) 

        # 3. Summary Text Area
        left_layout.addWidget(QLabel("<b>Validation Summary</b>"))
        self.ValidationSummaryTextArea = QTextEdit()
        self.ValidationSummaryTextArea.setReadOnly(True)
        self.ValidationSummaryTextArea.setStyleSheet("font-family: Courier; font-size: 10pt; background-color: #f4f4f4;")
        left_layout.addWidget(self.ValidationSummaryTextArea, stretch=1)


        # ==========================================
        # RIGHT PANEL: 3D PyVista Split View
        # ==========================================
        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(QLabel("<b>3D Solid Beam Results (Top: Bending, Bottom: Shear)</b>"))
        
        # 4. Create the 3D PyVista Interactor (Split into 2 rows natively!)
        self.UIAxes_3D_Validation = QtInteractor(right, shape=(2, 1))
        right_layout.addWidget(self.UIAxes_3D_Validation)


        # ==========================================
        # ASSEMBLE MAIN TAB
        # ==========================================
        # Add left and right panels to the main layout (ratio 40% left, 60% right)
        layout.addWidget(left, 4)
        layout.addWidget(right, 6)

        self.tabs.addTab(tab, "4. Validation")

    def create_tab5_post_processing(self):
        tab = QWidget()
        layout = QVBoxLayout(tab) # Changed to Top/Bottom layout
        
        # ==========================================
        # TOP PANEL: Dashboard Controls
        # ==========================================
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # 1. Stress Type Dropdown
        top_layout.addWidget(QLabel("<b>Stress Type:</b>"))
        self.TypeofStressesDropDown = QComboBox()
        self.TypeofStressesDropDown.addItems(["Sigma_xx", "Sigma_yy", "Sigma_zz", "Tau_xy", "Tau_yz", "Tau_zx"])
        top_layout.addWidget(self.TypeofStressesDropDown)
        
        # 2. Failure Method Dropdown
        top_layout.addWidget(QLabel("<b>Failure Method:</b>"))
        self.MethodDropDown = QComboBox()
        self.MethodDropDown.addItems(["Von Mises", "Max Principal", "Max Shear (Tresca)"])
        top_layout.addWidget(self.MethodDropDown)

        # 3. Select Safety or Stress (Fixed the label text here!)
        top_layout.addWidget(QLabel("<b>Display:</b>"))
        self.DisplayChoiceDropDown = QComboBox()
        self.DisplayChoiceDropDown.addItems(["FS", "Stress"])
        top_layout.addWidget(self.DisplayChoiceDropDown)

        # 4. Yield Strength Input
        top_layout.addWidget(QLabel("<b>Yield (MPa):</b>"))
        self.YieldStrengthMpaEditField = QLineEdit("250")
        self.YieldStrengthMpaEditField.setFixedWidth(60) # Keep it compact
        top_layout.addWidget(self.YieldStrengthMpaEditField)
        
        # 5. Deformation Scale Input
        top_layout.addWidget(QLabel("<b>Scale:</b>"))
        self.ScaleFactorEditField = QLineEdit("500")
        self.ScaleFactorEditField.setFixedWidth(60) # Keep it compact
        top_layout.addWidget(self.ScaleFactorEditField)
        
        # Spacer to push the button to the right side
        top_layout.addSpacing(20)
        
        # 6. Process Button
        btn_plot = QPushButton("Open PostProcessing")
        btn_plot.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 4px;")
        btn_plot.clicked.connect(self.OpenPostProcessingButtonPushed)
        top_layout.addWidget(btn_plot)
        
        # Add the top dashboard to the main layout
        layout.addWidget(top_widget, 0) 
        
        # ==========================================
        # BOTTOM PANEL: 3D Visualizations
        # ==========================================
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Canvas 1: Component Stress
        self.UIAxes5 = QtInteractor(bottom_splitter)
        bottom_splitter.addWidget(self.UIAxes5)
        
        # Canvas 2: Failure Stress OR Factor of Safety (Toggled by Dropdown)
        self.UIAxes6 = QtInteractor(bottom_splitter)
        bottom_splitter.addWidget(self.UIAxes6)
        
        # Set them to take exactly 50% of the screen each
        bottom_splitter.setSizes([500, 500])
        
        # Add the 3D canvases to the main layout
        layout.addWidget(bottom_splitter, 1) 
        
        self.tabs.addTab(tab, "5. Post Processing")

        
    def create_tab6_rom_training(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ==========================================
        # TOP CONTROLS: Inputs & Buttons
        # ==========================================
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("<b>Number of Snapshots:</b>"))
        
        # FIXED: Mapped to self.num_snapshotsEditField
        self.num_snapshotsEditField = QLineEdit("12")
        self.num_snapshotsEditField.setFixedWidth(100)
        input_layout.addWidget(self.num_snapshotsEditField)
        
        # Push button to the left
        input_layout.addStretch()
        
        # FIXED: Mapped callback to self.TrainButtonPushed
        btn_train = QPushButton("Start ROM Training")
        btn_train.setStyleSheet("font-weight: bold; padding: 10px 20px; background-color: #2b5797; color: white; border-radius: 5px;")
        btn_train.clicked.connect(self.TrainButtonPushed)
        input_layout.addWidget(btn_train)
        
        layout.addLayout(input_layout)
        
        # ==========================================
        # MIDDLE: Real-time Training Log
        # ==========================================
        layout.addWidget(QLabel("<b>Training Log & Time:</b>"))
        
        # FIXED: Mapped to self.TrainningTimeTextArea
        self.TrainningTimeTextArea = QTextEdit()
        self.TrainningTimeTextArea.setReadOnly(True)
        self.TrainningTimeTextArea.setStyleSheet("font-family: Courier; font-size: 10pt; background-color: #f4f4f4;")
        self.TrainningTimeTextArea.setMaximumHeight(150)
        layout.addWidget(self.TrainningTimeTextArea)
        
        # ==========================================
        # BOTTOM: SVD Energy Plot (UIAxes8)
        # ==========================================
        layout.addWidget(QLabel("<b>ROM Invariance (Singular Value Decomposition)</b>"))
        
        # FIXED: Mapped the canvas to self.UIAxes8
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        
        self.fig_svd = Figure()
        self.UIAxes8 = FigureCanvas(self.fig_svd)
        layout.addWidget(self.UIAxes8)
        
        self.tabs.addTab(tab, "6. ROM Training")

    def create_tab7_rom_validation(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # ==========================================
        # LEFT PANEL: Controls & Outputs
        # ==========================================
        left = QWidget()
        form = QFormLayout(left)

        # 1. Load Position Slider
        self.ValidationLoadPositionSlider = QSlider(Qt.Orientation.Horizontal)
        self.ValidationLoadPositionSlider.setMinimum(0)
        self.ValidationLoadPositionSlider.setMaximum(100)
        self.ValidationLoadPositionSlider.setValue(50) # Set default to middle
        # Create a dynamic label that shows the starting position in meters
        start_pos = (50 / 100.0) * self.geometry['Lx']
        self.lbl_load_pos = QLabel(f"<b>Load Position:</b><br><span style='color:blue;'>{start_pos:.2f} m</span>")
        
        # Link the slider to update the label text instantly in real-time
        self.ValidationLoadPositionSlider.valueChanged.connect(
            lambda v: self.lbl_load_pos.setText(f"<b>Load Position:</b><br><span style='color:blue;'>{(v/100.0) * self.geometry['Lx']:.2f} m</span>")
        )
        form.addRow(self.lbl_load_pos, self.ValidationLoadPositionSlider)

        # 2. Validation Load Input
        self.ValidationLoadNEditField = QLineEdit("-10000")
        form.addRow("Validation Load (N):", self.ValidationLoadNEditField)

        # 3. Stress Type Dropdown
        self.TypeofStressesDropDown_2 = QComboBox()
        self.TypeofStressesDropDown_2.addItems(['Sigma_xx', 'Sigma_yy', 'Sigma_zz', 'Tau_xy', 'Tau_yz', 'Tau_zx'])
        form.addRow("Type of Stresses:", self.TypeofStressesDropDown_2)

        # 4. Check Accuracy Button
        self.CheckAccuracyButton = QPushButton("Check Accuracy (FEM vs ROM)")
        self.CheckAccuracyButton.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2b5797; color: white;")
        self.CheckAccuracyButton.clicked.connect(self.CheckAccuracyButtonPushed) # UNCOMMENTED
        form.addRow(self.CheckAccuracyButton)

        # 5. Results Text Area
        self.AccuracyResultsTextArea = QTextEdit()
        self.AccuracyResultsTextArea.setReadOnly(True)
        self.AccuracyResultsTextArea.setStyleSheet("font-family: Courier; font-size: 10pt; background-color: #f4f4f4;")
        form.addRow(self.AccuracyResultsTextArea)

        # 6. Save ROM Button
        self.SaveButton = QPushButton("Save ROM to Central Bank")
        self.SaveButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #2e8b57; color: white;")
        self.SaveButton.clicked.connect(self.SaveButtonPushed) # UNCOMMENTED
        form.addRow(self.SaveButton)

        # 7. Clear Bank Button
        self.ClearBankButton = QPushButton("Clear ROM Bank")
        self.ClearBankButton.setStyleSheet("font-weight: bold; padding: 8px; background-color: #b22222; color: white;")
        self.ClearBankButton.clicked.connect(self.ClearBankButtonPushed) # UNCOMMENTED
        form.addRow(self.ClearBankButton)

        # ==========================================
        # RIGHT PANEL: Dual 3D View (FEM vs ROM)
        # ==========================================
        right = QSplitter(Qt.Orientation.Horizontal)
        
        # FIXED: Variable names matched to backend math
        self.UIAxes9 = QtInteractor(right)
        right.addWidget(self.UIAxes9) 
        
        self.UIAxes10 = QtInteractor(right)
        right.addWidget(self.UIAxes10)
        
        layout.addWidget(left, 1)
        layout.addWidget(right, 3)
        self.tabs.addTab(tab, "7. ROM Validation")

    def create_tab8_classify_dt(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # --- 1. Top Control Panel ---
        ctrl_group = QGroupBox("Digital Twin Controls")
        ctrl_layout = QGridLayout(ctrl_group)
        
        self.StartLiveTwinButton = QPushButton("Start Live Twin")
        self.StartLiveTwinButton.setMinimumHeight(40)
        self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #e0e0e0; color: black;")
        self.StartLiveTwinButton.clicked.connect(self.StartLiveTwinButtonValueChanged)
        
        self.StainGauge1Switch = QCheckBox("Strain Gauge 1 (Left)")
        self.StainGauge2Switch = QCheckBox("Strain Gauge 2 (Right)")
        
        # Load Controls
        ctrl_layout.addWidget(self.StartLiveTwinButton, 0, 0, 1, 2)
        ctrl_layout.addWidget(self.StainGauge1Switch, 0, 2)
        ctrl_layout.addWidget(self.StainGauge2Switch, 0, 3)
        
        ctrl_layout.addWidget(QLabel("Load Position (%):"), 1, 0)
        self.LoadPositionSlider_2 = QSlider(Qt.Orientation.Horizontal)
        self.LoadPositionSlider_2.setRange(0, 100); self.LoadPositionSlider_2.setValue(50)
        ctrl_layout.addWidget(self.LoadPositionSlider_2, 1, 1, 1, 3)
        
        ctrl_layout.addWidget(QLabel("Load Value (kN):"), 2, 0)
        self.LoadValueNSlider = QSlider(Qt.Orientation.Horizontal)
        self.LoadValueNSlider.setRange(1, 13); self.LoadValueNSlider.setValue(10)
        self.LoadNEditField = QLineEdit("10"); self.LoadNEditField.setFixedWidth(50)
        ctrl_layout.addWidget(self.LoadValueNSlider, 2, 1, 1, 2)
        ctrl_layout.addWidget(self.LoadNEditField, 2, 3)

        # Visualization Selectors
        vis_box = QHBoxLayout()
        self.TypeofStressesDropDown_3 = QComboBox()
        self.TypeofStressesDropDown_3.addItems(["Sigma_xx", "Sigma_yy", "Sigma_zz", "Tau_xy", "Tau_yz", "Tau_zx"])
        self.MethodDropDown_2 = QComboBox()
        self.MethodDropDown_2.addItems(["Von Mises", "Max Principal", "Max Shear (Tresca)"])
        self.DisplayChoiceDropDown_2 = QComboBox()
        self.DisplayChoiceDropDown_2.addItems(["FS", "Stress"])
        self.ScaleFactorEditField_2 = QLineEdit("500"); self.ScaleFactorEditField_2.setFixedWidth(50)

        vis_box.addWidget(QLabel("Stress:")); vis_box.addWidget(self.TypeofStressesDropDown_3)
        vis_box.addWidget(QLabel("Failure:")); vis_box.addWidget(self.MethodDropDown_2)
        vis_box.addWidget(QLabel("View:")); vis_box.addWidget(self.DisplayChoiceDropDown_2)
        vis_box.addWidget(QLabel("Scale:")); vis_box.addWidget(self.ScaleFactorEditField_2)
        ctrl_layout.addLayout(vis_box, 3, 0, 1, 4)

        main_layout.addWidget(ctrl_group, 0)

        # --- 2. Main Visual Splitter ---
        self.dt_main_splitter = QSplitter(Qt.Orientation.Vertical)

        # A. Top Sub-Pane: Dual 3D PyVista Views
        top_3d_widget = QWidget()
        top_3d_layout = QHBoxLayout(top_3d_widget)
        self.UIAxes5_2 = QtInteractor(); top_3d_layout.addWidget(self.UIAxes5_2)
        self.UIAxes6_2 = QtInteractor(); top_3d_layout.addWidget(self.UIAxes6_2)
        self.dt_main_splitter.addWidget(top_3d_widget)

        # B. Bottom Sub-Pane: 2D Engineering Analysis (Matplotlib)
        self.dt_figure = Figure(figsize=(12, 4), tight_layout=True)
        self.dt_canvas = FigureCanvas(self.dt_figure)
        self.dt_main_splitter.addWidget(self.dt_canvas)

        # Set initial proportions (60% 3D, 40% 2D)
        self.dt_main_splitter.setSizes([600, 400])
        main_layout.addWidget(self.dt_main_splitter, 1)

        # Connect all signals
        self.LoadPositionSlider_2.valueChanged.connect(self.LoadPositionSlider_2ValueChanged)
        self.LoadValueNSlider.valueChanged.connect(self.LoadValueNSliderValueChanged)
        self.LoadNEditField.textChanged.connect(self.LoadNEditFieldValueChanged)
        self.StainGauge1Switch.stateChanged.connect(self.StainGauge1SwitchValueChanged)
        self.StainGauge2Switch.stateChanged.connect(self.StainGauge2SwitchValueChanged)
        self.TypeofStressesDropDown_3.currentTextChanged.connect(lambda: getattr(self, 'isLive', False) and self.run_DigitalTwin_Update())
        self.MethodDropDown_2.currentTextChanged.connect(lambda: getattr(self, 'isLive', False) and self.run_DigitalTwin_Update())
        self.DisplayChoiceDropDown_2.currentTextChanged.connect(lambda: getattr(self, 'isLive', False) and self.run_DigitalTwin_Update())

        self.tabs.addTab(tab, "8. Live Digital Twin")


    # =========================================================================
    # TAB 1 & 2 MATH BACKEND: GEOMETRY, MESHING, ASSEMBLY
    # =========================================================================
    def VasulizeGeometryButtonPushed(self):
        L, W, H = float(self.LmEditField.text()), float(self.wmEditField.text()), float(self.HmEditField.text())
        if L <= 0 or W <= 0 or H <= 0: return
        self.geometry = {'Lx': L, 'Ly': W, 'Lz': H}
        
        self.UIAxes.clear()
        box = pv.Box(bounds=(0, L, 0, W, 0, H))
        self.UIAxes.add_mesh(box, color="lightblue", show_edges=True, opacity=0.4)
        self.UIAxes.add_axes()
        self.UIAxes.reset_camera()

    def MeshingButtonPushed(self):
        # 1. Update properties
        self.material['E'] = float(self.EPaEditField.text())
        self.material['nu'] = float(self.NuEditField.text())
        self.material['rho'] = float(self.rhokgm3EditField.text())
        
        self.element_type = self.Element_typeDropDown.currentText()
        self.settings['Integration'] = self.IntpointDropDown.currentText()
        
        self.mesh_params['nx'] = int(self.EsizexEditField.text())
        self.mesh_params['ny'] = int(self.EsizeyEditField.text())
        self.mesh_params['nz'] = int(self.EsizezEditField.text())
        
        # 2. Generate the Mesh Data
        self.generate_mesh_3d()
        
        # 3. Clean Visualization
        self.UIAxes2.clear()
        
        if 'Hexa' in self.element_type:
            n_vis = 8
            vtk_type = pv.CellType.HEXAHEDRON
        else:
            n_vis = 4
            vtk_type = pv.CellType.TETRA
            
        # CRITICAL: Extract only the corner nodes so it looks structured
        vis_connectivity = self.element_connectivity[:, :n_vis]
        
        # Pass the dictionary safely
        cells_dict = {vtk_type: vis_connectivity}
        self.grid = pv.UnstructuredGrid(cells_dict, self.node_coords)
        
        self.UIAxes2.add_mesh(self.grid, show_edges=True, color="lightblue", opacity=0.8)
        self.UIAxes2.add_axes()
        self.UIAxes2.reset_camera()
        self.UIAxes2.update()
        
        # 4. Update UI Text
        self.MeshinfoTextArea.setText(f"Element Type: {self.element_type}\n"
                                      f"Total nodes: {self.mesh_info['num_nodes']}\n"
                                      f"Total elements: {self.mesh_info['num_elements']}")
        
    def generate_hexa8_mesh(self, Lx, Ly, Lz, nx, ny, nz):
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
                    n5, n6, n7, n8 = n1+1, n2+1, n3+1, n4+1
                    # CRITICAL FIX: Removed the -1. It is already 0-indexed!
                    elems.append([n1, n2, n3, n4, n5, n6, n7, n8])
                    
        connectivity = np.array(elems, dtype=int)
        info = {'num_nodes': len(node_coords), 'num_elements': len(connectivity), 'nodes_per_element': 8}
        return node_coords, connectivity, info

    def generate_hexa20_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        hex8_nodes, hex8_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_hex8 = len(hex8_conn)
        edge_map = {}
        mid_node_counter = len(hex8_nodes)
        mid_nodes_list = []
        
        connectivity = np.zeros((num_hex8, 20), dtype=int)
        edges = np.array([[0,1], [1,2], [2,3], [3,0], [4,5], [5,6], [6,7], [7,4], [0,4], [1,5], [2,6], [3,7]])
        
        for e in range(num_hex8):
            corners = hex8_conn[e, :]
            mid_nodes = np.zeros(12, dtype=int)
            for edge_idx in range(12):
                n1, n2 = corners[edges[edge_idx, 0]], corners[edges[edge_idx, 1]]
                edge_key = tuple(sorted([n1, n2]))
                if edge_key in edge_map:
                    mid_nodes[edge_idx] = edge_map[edge_key]
                else:
                    new_coord = (hex8_nodes[n1] + hex8_nodes[n2]) / 2.0
                    mid_nodes_list.append(new_coord)
                    mid_nodes[edge_idx] = mid_node_counter
                    edge_map[edge_key] = mid_node_counter
                    mid_node_counter += 1
                    
            connectivity[e, :8] = corners
            connectivity[e, 8:] = mid_nodes
            
        node_coords = np.vstack((hex8_nodes, np.array(mid_nodes_list))) if mid_nodes_list else hex8_nodes
        info = {'num_nodes': len(node_coords), 'num_elements': num_hex8, 'nodes_per_element': 20}
        return node_coords, connectivity, info

    def generate_tet4_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        hex_nodes, hex_conn, _ = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_hex = len(hex_conn)
        connectivity = np.zeros((num_hex * 5, 4), dtype=int)
        
        tet_count = 0
        for h in range(num_hex):
            n = hex_conn[h, :]
            tets = [
                [n[0], n[1], n[3], n[4]],
                [n[1], n[2], n[3], n[6]],
                [n[1], n[4], n[5], n[6]],
                [n[3], n[4], n[6], n[7]],
                [n[1], n[3], n[4], n[6]]
            ]
            connectivity[tet_count:tet_count+5, :] = tets
            tet_count += 5
            
        info = {'num_nodes': len(hex_nodes), 'num_elements': len(connectivity), 'nodes_per_element': 4}
        return hex_nodes, connectivity, info

    def generate_tet10_mesh(self, Lx, Ly, Lz, nx, ny, nz):
        tet4_nodes, tet4_conn, _ = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz)
        num_tet4 = len(tet4_conn)
        edge_map = {}
        mid_node_counter = len(tet4_nodes)
        mid_nodes_list = []
        
        connectivity = np.zeros((num_tet4, 10), dtype=int)
        edges = np.array([[0,1], [1,2], [0,2], [0,3], [1,3], [2,3]])
        
        for e in range(num_tet4):
            corners = tet4_conn[e, :]
            mid_nodes = np.zeros(6, dtype=int)
            for edge_idx in range(6):
                n1, n2 = corners[edges[edge_idx, 0]], corners[edges[edge_idx, 1]]
                edge_key = tuple(sorted([n1, n2]))
                if edge_key in edge_map:
                    mid_nodes[edge_idx] = edge_map[edge_key]
                else:
                    new_coord = (tet4_nodes[n1] + tet4_nodes[n2]) / 2.0
                    mid_nodes_list.append(new_coord)
                    mid_nodes[edge_idx] = mid_node_counter
                    edge_map[edge_key] = mid_node_counter
                    mid_node_counter += 1
                    
            connectivity[e, :4] = corners
            connectivity[e, 4:] = mid_nodes
            
        node_coords = np.vstack((tet4_nodes, np.array(mid_nodes_list))) if mid_nodes_list else tet4_nodes
        info = {'num_nodes': len(node_coords), 'num_elements': num_tet4, 'nodes_per_element': 10}
        return node_coords, connectivity, info

    def generate_mesh_3d(self):
        Lx, Ly, Lz = self.geometry['Lx'], self.geometry['Ly'], self.geometry['Lz']
        nx, ny, nz = self.mesh_params['nx'], self.mesh_params['ny'], self.mesh_params['nz']
        
        if self.element_type == 'Hexa8':
            self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Hexa20':
            self.node_coords, self.element_connectivity, self.mesh_info = self.generate_hexa20_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Tet4':
            self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz)
        elif self.element_type == 'Tet10':
           self.node_coords, self.element_connectivity, self.mesh_info = self.generate_tet10_mesh(Lx, Ly, Lz, nx, ny, nz)
            
        self.mesh_info['element_type'] = self.element_type
   
    ######################################################################
    # Tab 2Apply Load 
    # ##############################################################        
    def ApplyLoadButtonPushed(self):
        
        try:
            # 0. Safety Check
            if not hasattr(self, 'geometry') or 'Lx' not in self.geometry:
                QMessageBox.warning(None, "Missing Data", "Geometry not found! Please generate the mesh in Tab 1 first.")
                return

            # 1. Sync Slider and Load Data
            load_pos_meters = (self.LoadPositionSlider.value() / 100.0) * self.geometry['Lx']
            P_val = float(self.LoadValueNEditField.text())
            
            # A. Get distributed loads (Gravity)
            if hasattr(self, 'define_loads_no_bc_3d'):
                self.loads = self.define_loads_no_bc_3d(self.node_coords)
            else:
                self.loads = {} 
                 
            # B. Get Point Loads (Lever Rule)
            if hasattr(self, 'define_loads_at_pos'):
                point_loads = self.define_loads_at_pos(load_pos_meters, P_val)
                self.loads['point_nodes'] = point_loads['point_nodes']
                self.loads['point_load_values'] = point_loads['point_load_values']

            # 2. Setup Assembly Parameters
            dof_per_node = 3
            num_nodes = self.mesh_info['num_nodes']
            num_elements = self.mesh_info['num_elements']
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
            
            triplet_i = np.zeros(total_entries, dtype=np.int32)
            triplet_j = np.zeros(total_entries, dtype=np.int32)
            triplet_val = np.zeros(total_entries)
            self.F_global = np.zeros(num_dof)
            
            B_triplet_i = np.zeros(total_entriesB, dtype=np.int32)
            B_triplet_j = np.zeros(total_entriesB, dtype=np.int32)
            B_triplet_val = np.zeros(total_entriesB)

            # 3. Global Assembly Loop
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
                triplet_i[curr_idx:next_idx] = rows.ravel()
                triplet_j[curr_idx:next_idx] = cols.ravel()
                triplet_val[curr_idx:next_idx] = Ke.ravel()
                curr_idx = next_idx
                
                for g in range(num_gp):
                    row_start = (e * num_gp + g) * 6
                    global_rows = row_start + np.arange(6)
                    Be_gp = Be_all[g*6 : (g+1)*6, :]
                    mesh_R, mesh_C = np.meshgrid(global_rows, loc_array, indexing='ij')
                    num_vals = 6 * len(loc_array)
                    next_idx_B = curr_idx_B + num_vals
                    
                    B_triplet_i[curr_idx_B:next_idx_B] = mesh_R.ravel()
                    B_triplet_j[curr_idx_B:next_idx_B] = mesh_C.ravel()
                    B_triplet_val[curr_idx_B:next_idx_B] = Be_gp.ravel()
                    curr_idx_B = next_idx_B
                    
                self.F_global[loc_array] += Fe

            # 4. Finalize Sparse Matrix
            self.K_global = sp.coo_matrix((triplet_val, (triplet_i, triplet_j)), shape=(num_dof, num_dof)).tocsc()
            del triplet_i, triplet_j, triplet_val
            
            total_B_rows = num_elements * num_gp * 6
            self.B_global = sp.coo_matrix((B_triplet_val, (B_triplet_i, B_triplet_j)), shape=(total_B_rows, num_dof)).tocsc()
            del B_triplet_i, B_triplet_j, B_triplet_val

            # 5. Apply Point Loads
            if 'point_nodes' in self.loads and len(self.loads['point_nodes']) > 0:
                for i, node_id in enumerate(self.loads['point_nodes']):
                    force_vec = self.loads['point_load_values'][:, i]
                    dof_indices = int(node_id) * 3 + np.array([0, 1, 2])
                    self.F_global[dof_indices] += force_vec

            self.MatrixSizeTextArea.setText(f"Total dof: {num_dof} x {num_dof}")

            # --- Apply Boundary Conditions ---
            self.beam_type = self.BeamTypeDropDown.currentText()
            
            if hasattr(self, 'boundary_conditions'):
                self.K_reduced, self.F_reduced, fixed_dofs, free_dofs = self.boundary_conditions(
                    self.K_global, self.F_global, self.node_coords, self.beam_type)
            else:
                fixed_dofs = np.array([]); free_dofs = np.arange(num_dof)

            self.bc_info = {
                'total_dofs': num_dof, 'fixed_dofs': len(fixed_dofs), 'free_dofs': len(free_dofs),
                'fixed_dofs_indices': fixed_dofs, 'free_dofs_indices': free_dofs,
                'fixed_dofs_values': np.zeros(len(fixed_dofs))
            }

            if hasattr(self, 'visualize_BC_3d'):
                self.visualize_BC_3d(self.node_coords, self.element_connectivity, self.element_type,
                                     self.mesh_info, self.bc_info, self.F_global, self.UIAxes3)
                
            if hasattr(self, 'update_load_bar_chart'):
                self.update_load_bar_chart(self.F_global, self.UIAxes4)
                
        except Exception as e:
            error_msg = f"Crash Prevented!\n\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(None, "Application Error", error_msg)
                
        
                
    def define_loads_no_bc_3d(self, node_coords):
        """Calculates global distributed loads (like gravity). Point loads are handled separately by the Lever Rule."""
        import numpy as np
        loads = {}
        
        # --- 1. GRAVITY SWITCH ---
        if hasattr(self, 'GravitationalForceSwitch') and self.GravitationalForceSwitch.isChecked():
            loads['BodyForceDir'] = np.array([0, 0, -9.81])
        else:
            loads['BodyForceDir'] = np.array([0, 0, 0])
            
        # --- 2. SURFACE TRACTION (Placeholder for future features) ---
        loads['traction_nodes'] = []
        loads['surface_traction_value'] = np.array([0, 0, 0])
        
        return loads

    def prepare_element_loads_3d(self, loads, e, element_nodes, element_type):
        """Maps Global Distributed Loads to Local Element Definitions"""
        import numpy as np
        elem_loads = {
            'BodyForceDir': [],
            'SurfaceFaceID': [],
            'SurfaceTraction': []
            # Point loads removed to prevent double-counting during global assembly
        }
        
        # 1. Body Forces (Gravity)
        if 'BodyForceDir' in loads:
            elem_loads['BodyForceDir'] = loads['BodyForceDir']
            
        # 2. Define Local Face Topology (0-Indexed for Python)
        elem_type_lower = element_type.lower()
        if elem_type_lower == 'hexa8':
            face_defs = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        elif elem_type_lower == 'hexa20':
            face_defs = [[0, 3, 2, 1, 11, 10, 9, 8], [4, 5, 6, 7, 12, 13, 14, 15], 
                         [0, 1, 5, 4, 8, 17, 12, 16], [1, 2, 6, 5, 9, 18, 13, 17], 
                         [2, 3, 7, 6, 10, 19, 14, 18], [3, 0, 4, 7, 11, 16, 15, 19]]
        elif elem_type_lower in ['tet4', 'tet10']:
            face_defs = [[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]]
        else:
            raise ValueError(f'Element type {element_type} not supported')
            
        # 3. Surface Traction Mapping
        if 'traction_nodes' in loads and len(loads['traction_nodes']) > 0:
            for i, local_indices in enumerate(face_defs):
                global_nodes_on_face = element_nodes[local_indices]
                if np.all(np.isin(global_nodes_on_face, loads['traction_nodes'])):
                    elem_loads['SurfaceFaceID'].append(local_indices)
                    elem_loads['SurfaceTraction'].append(loads['surface_traction_value'])
                    
        return elem_loads
    

    def compute_element_matrices_3d(self, element_type, elem_coords, elem_loads, settings):
        """Wrapper to route to the correct 3D element numerical routine"""
        type_lower = element_type.lower()
        
        # Route to the newly translated '_Numerical' methods, passing self.material
        if type_lower == 'tet4':
            Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Tet4_Element_Routine(
                self.material, elem_coords, elem_loads, settings)
                
        elif type_lower == 'tet10':
            Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Tet10_Element_Routine(
                self.material, elem_coords, elem_loads, settings)
                
        elif type_lower == 'hexa8':
            Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Hexa8_Element_Routine(
                self.material, elem_coords, elem_loads, settings)
                
        elif type_lower == 'hexa20':
            Ke, Fb, Fs, Fl, F_total, D, Be_all = self.Hexa20_Element_Routine(
                self.material, elem_coords, elem_loads, settings)
                
        else:
            raise ValueError(f'Element type "{element_type}" not recognized.')
            
        # The Global Assembly loop expects exactly 4 outputs: Ke, Fe (which is F_total), D, Be_all
        return Ke, F_total, D, Be_all     

    

    def Hexa8_Element_Routine(self, Material, Coord, Loads, Settings):
        # 1. Initialization
        Ke = np.zeros((24, 24))
        Fb = np.zeros(24)
        Fs = np.zeros(24)
        Fl = np.zeros(24)
        
        # Material Properties
        Em = Material['E']
        nu = Material['nu']
        
        # Constitutive Matrix (3D Isotropic)
        D_const = Em / ((1 + nu) * (1 - 2 * nu))
        D = D_const * np.array([
            [1-nu, nu,   nu,   0, 0, 0],
            [nu,   1-nu, nu,   0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        
        # 2. Integration Rule Selection
        if Settings.get('Integration', '').lower() == 'full':
            n_order = 2 # 2x2x2 = 8 points
        else:
            n_order = 1 # 1x1x1 = 1 point (Reduced)
            
        gpts, gwts = self.GetGaussTable(n_order) # Assuming you have this helper
        num_gp = n_order**3
        
        # Pre-allocate stacked B-Matrix
        Be_all = np.zeros((6 * num_gp, 24))
        
        # Volume Integration
        gp_count = 0
        for i in range(n_order):
            for j in range(n_order):
                for k in range(n_order):
                    xi, eta, zeta = gpts[i], gpts[j], gpts[k]
                    w = gwts[i] * gwts[j] * gwts[k]
                    
                    N, dN_dxi, dN_deta, dN_dzeta = self.Hexa8_ShapeFunctions(xi, eta, zeta)
                    
                    # Jacobian Matrix (3x3)
                    nat_derivs = np.vstack([dN_dxi, dN_deta, dN_dzeta])
                    J = nat_derivs @ Coord
                    
                    detJ = max(np.linalg.det(J), 1e-12) # Prevent singularity
                    
                    # Cartesian Derivatives (3x8)
                    dN_xyz = np.linalg.solve(J, nat_derivs)
                    
                    # B-Matrix Construction (6x24)
                    B = np.zeros((6, 24))
                    for n in range(8):
                        idx = n * 3
                        dx, dy, dz = dN_xyz[0, n], dN_xyz[1, n], dN_xyz[2, n]
                        
                        B[0, idx]   = dx
                        B[1, idx+1] = dy
                        B[2, idx+2] = dz
                        B[3, idx:idx+2] = [dy, dx]
                        B[4, idx+1:idx+3] = [dz, dy]
                        B[5, [idx, idx+2]] = [dz, dx]
                        
                    # Stack B for Global Assembly
                    row_idx = gp_count * 6
                    Be_all[row_idx:row_idx+6, :] = B
                    
                    # Accumulate Stiffness
                    Ke += (B.T @ D @ B) * detJ * w
                    
                    # Body Force (Gravity)
                    if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                        b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                        N_mat = np.zeros((3, 24))
                        for n in range(8):
                            col = n * 3
                            N_mat[0, col]   = N[n]
                            N_mat[1, col+1] = N[n]
                            N_mat[2, col+2] = N[n]
                        Fb += (N_mat.T @ b_vec) * detJ * w
                        
                    gp_count += 1
                    
        F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, D, Be_all
    
    def Hexa8_ShapeFunctions(self, xi, eta, zeta):
        """Hexa8 Trilinear Shape Functions"""
        # Multipliers
        xi_m = np.array([-1, 1, 1, -1, -1, 1, 1, -1])
        eta_m = np.array([-1, -1, 1, 1, -1, -1, 1, 1])
        zeta_m = np.array([-1, -1, -1, -1, 1, 1, 1, 1])
        
        # Vectorized calculation avoids the for-loop
        N = 0.125 * (1 + xi*xi_m) * (1 + eta*eta_m) * (1 + zeta*zeta_m)
        dN_dxi = 0.125 * xi_m * (1 + eta*eta_m) * (1 + zeta*zeta_m)
        dN_deta = 0.125 * eta_m * (1 + xi*xi_m) * (1 + zeta*zeta_m)
        dN_dzeta = 0.125 * zeta_m * (1 + xi*xi_m) * (1 + eta*eta_m)
        
        return N, dN_dxi, dN_deta, dN_dzeta

    

    def Tet10_Element_Routine(self, Material, Coord, Loads, Settings):
        # TET10: 10-node Quadratic Tetrahedron
        E, nu = Material['E'], Material['nu']
        lambda_val = E*nu/((1+nu)*(1-2*nu))
        mu = E/(2*(1+nu))
        
        C = np.zeros((6, 6))
        C[0:3, 0:3] = lambda_val
        for i in range(3):
            C[i, i] = lambda_val + 2*mu
        C[3, 3] = C[4, 4] = C[5, 5] = mu
        
        if Settings.get('Integration', '').lower() == 'full':
            nGauss_vol = 4 
        else:
            nGauss_vol = 1  
            
        Be_all = np.zeros((6 * nGauss_vol, 30))
        g_pts, g_w = self.GetGaussTableTetrahedra(nGauss_vol) # Requires helper function
        
        Ke = np.zeros((30, 30))
        Fb = np.zeros(30)
        Vol_Scale = 1.0 / 6.0 
        
        for ig in range(nGauss_vol):
            xi, eta, zeta = g_pts[ig, 0], g_pts[ig, 1], g_pts[ig, 2]
            L4 = 1 - xi - eta - zeta
            w = g_w[ig] * Vol_Scale
            
            N, dN_nat = self.Tet10_ShapeFunctions(xi, eta, zeta, L4)
            
            # Jacobian
            J = dN_nat.T @ Coord
            detJ = abs(np.linalg.det(J))
            dN_dx = dN_nat @ np.linalg.inv(J).T 
            
            # B-Matrix Construction
            B = np.zeros((6, 30))
            for i in range(10):
                c = i * 3
                dx, dy, dz = dN_dx[i, 0], dN_dx[i, 1], dN_dx[i, 2]
                B[0, c]   = dx
                B[1, c+1] = dy
                B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]
                B[4, c+1:c+3] = [dz, dy]
                B[5, [c, c+2]] = [dz, dx]
                
            # Stack B
            row_idx = ig * 6
            Be_all[row_idx:row_idx+6, :] = B
            
            dV = detJ * w
            Ke += (B.T @ C @ B) * dV
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for i in range(10):
                    idx = i * 3
                    Fb[idx:idx+3] += N[i] * b_vec * dV
                    
        Fs = np.zeros(30)
        Fl = np.zeros(30)
        F_total = Fb + Fs + Fl
        return Ke, Fb, Fs, Fl, F_total, C, Be_all
    
    def Tet10_ShapeFunctions(self, xi, eta, zeta, L4):
        N = np.array([
            L4*(2*L4-1), xi*(2*xi-1), eta*(2*eta-1), zeta*(2*zeta-1), # Corners
            4*L4*xi, 4*xi*eta, 4*eta*L4, 4*L4*zeta, 4*xi*zeta, 4*eta*zeta # Mids
        ])
        
        dN_nat = np.zeros((10, 3))
        # Derivatives w.r.t xi, eta, zeta
        dN_nat[0, :] = -(4*L4-1) 
        dN_nat[1, 0] = 4*xi-1 
        dN_nat[2, 1] = 4*eta-1 
        dN_nat[3, 2] = 4*zeta-1
        
        dN_nat[4, :] = [4*(L4-xi), -4*xi, -4*xi]
        dN_nat[5, :] = [4*eta, 4*xi, 0]
        dN_nat[6, :] = [-4*eta, 4*(L4-eta), -4*eta]
        dN_nat[7, :] = [-4*zeta, -4*zeta, 4*(L4-zeta)]
        dN_nat[8, :] = [4*zeta, 0, 4*xi]
        dN_nat[9, :] = [0, 4*zeta, 4*eta]
        
        return N, dN_nat
    
    def Tet4_Element_Routine(self, Material, Coord, Loads, Settings):
        # 1. Initialization and Material Properties
        E = Material['E']
        nu = Material['nu']
        lambda_val = E * nu / ((1 + nu) * (1 - 2 * nu))
        mu = E / (2 * (1 + nu))
        
        C = np.zeros((6, 6))
        C[0:3, 0:3] = lambda_val
        for i in range(3):
            C[i, i] = lambda_val + 2 * mu
        C[3, 3] = C[4, 4] = C[5, 5] = mu
        
        # 2. Integration Setup
        g_pts, g_w = self.GetGaussTableTetrahedra(1)
        Ke = np.zeros((12, 12))
        Fb = np.zeros(12)
        Be_all = np.zeros((6, 12))
        
        # 3. Volume Integration
        for ig in range(len(g_w)):
            xi = g_pts[ig, 0]
            eta = g_pts[ig, 1]
            zeta = g_pts[ig, 2]
            w = g_w[ig] * (1.0 / 6.0)
            
            # Shape functions for Tet4 Body Force
            N = np.array([1 - xi - eta - zeta, xi, eta, zeta])
            
            dN_nat = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
            J = dN_nat.T @ Coord
            detJ = abs(np.linalg.det(J))
            dN_dx = dN_nat @ np.linalg.inv(J).T 
            
            B = np.zeros((6, 12))
            for i in range(4):
                c = i * 3
                dx, dy, dz = dN_dx[i, 0], dN_dx[i, 1], dN_dx[i, 2]
                B[0, c]   = dx
                B[1, c+1] = dy
                B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]
                B[4, c+1:c+3] = [dz, dy]
                B[5, [c, c+2]] = [dz, dx]
                
            Be_all[0:6, :] = B
            Ke += (B.T @ C @ B) * detJ * w
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for n in range(4):
                    idx = n * 3
                    Fb[idx:idx+3] += N[n] * b_vec * detJ * w
                    
        Fs = np.zeros(12)
        Fl = np.zeros(12)
        F_total = Fb + Fs + Fl
        
        return Ke, Fb, Fs, Fl, F_total, C, Be_all

    def Hexa20_Element_Routine(self, Material, Coord, Loads, Settings):
        # 1. Initialization and Material Properties
        E = Material['E']
        nu = Material['nu']
        D_const = E / ((1 + nu) * (1 - 2 * nu))
        D = D_const * np.array([
            [1-nu, nu,   nu,   0, 0, 0],
            [nu,   1-nu, nu,   0, 0, 0],
            [nu,   nu,   1-nu, 0, 0, 0],
            [0,    0,    0,    (1-2*nu)/2, 0, 0],
            [0,    0,    0,    0, (1-2*nu)/2, 0],
            [0,    0,    0,    0, 0, (1-2*nu)/2]
        ])
        
        Ke = np.zeros((60, 60))
        Fb = np.zeros(60)
        
        # 2. Integration Rule Selection Based on settings
        if Settings.get('Integration', '').lower() == 'full':
            n_order = 3 # 3x3x3 = 27 points
        else:
            n_order = 2 # 2x2x2 = 8 points (Reduced)
            
        g_pts, g_w = self.BuildHexaGauss(n_order)
        num_gp = n_order**3
        
        # Pre-allocate stacked B-Matrix
        Be_all = np.zeros((6 * num_gp, 60))
        gp_count = 0
        
        # 3. Volume Integration
        for ig in range(g_pts.shape[0]):
            xi, eta, zeta = g_pts[ig, 0], g_pts[ig, 1], g_pts[ig, 2]
            w = g_w[ig]
            
            N, dN_dxi, dN_deta, dN_dzeta = self.Hexa20_ShapeFunctions(xi, eta, zeta)
            
            nat_derivs = np.column_stack((dN_dxi, dN_deta, dN_dzeta)) # Size: (20, 3)
            J = nat_derivs.T @ Coord
            
            detJ = np.linalg.det(J)
            if abs(detJ) < 1e-12:
                detJ = 1e-12 if detJ >= 0 else -1e-12
                
            dN_dx = nat_derivs @ np.linalg.inv(J)
            
            B = np.zeros((6, 60))
            for n in range(20):
                c = n * 3
                dx, dy, dz = dN_dx[n, 0], dN_dx[n, 1], dN_dx[n, 2]
                B[0, c]   = dx
                B[1, c+1] = dy
                B[2, c+2] = dz
                B[3, c:c+2] = [dy, dx]
                B[4, c+1:c+3] = [dz, dy]
                B[5, [c, c+2]] = [dz, dx]
                
            # Stack B for Global Assembly
            row_idx = gp_count * 6
            Be_all[row_idx:row_idx+6, :] = B
            Ke += (B.T @ D @ B) * detJ * w
            
            if 'BodyForceDir' in Loads and len(Loads['BodyForceDir']) > 0:
                b_vec = np.array(Loads['BodyForceDir']) * Material['rho']
                for n in range(20):
                    idx = n * 3
                    Fb[idx:idx+3] += N[n] * b_vec * detJ * w
                    
            gp_count += 1
            
        Fs = np.zeros(60)
        Fl = np.zeros(60)
        F_total = Fb + Fs + Fl
        
        return Ke, Fb, Fs, Fl, F_total, D, Be_all
    
    def Hexa20_ShapeFunctions(self, xi, eta, zeta):
        # Initialize arrays (0-based indexing: 0 to 19)
        N = np.zeros(20)
        dN_dxi = np.zeros(20)
        dN_deta = np.zeros(20)
        dN_dzeta = np.zeros(20)
        
        # --- CORNER NODES (1-8) ---
        pts = np.array([
            [-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1],
            [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1]
        ])
        
        ri = pts[:, 0]
        si = pts[:, 1]
        ti = pts[:, 2]
        
        # Vectorized Corner Math (Calculates all 8 simultaneously)
        val = (1 + xi*ri) * (1 + eta*si) * (1 + zeta*ti)
        N[:8] = 0.125 * val * (xi*ri + eta*si + zeta*ti - 2)
        
        dN_dxi[:8]   = 0.125 * ri * (1+eta*si)*(1+zeta*ti) * (2*xi*ri + eta*si + zeta*ti - 1)
        dN_deta[:8]  = 0.125 * si * (1+xi*ri)*(1+zeta*ti)  * (xi*ri + 2*eta*si + zeta*ti - 1)
        dN_dzeta[:8] = 0.125 * ti * (1+xi*ri)*(1+eta*si)   * (xi*ri + eta*si + 2*zeta*ti - 1)
        
        # --- MIDSIDE NODES (9-20) ---
        mid_coords = np.array([
            [ 0, -1, -1], [ 1,  0, -1], [ 0,  1, -1], [-1,  0, -1],  # 9-12
            [ 0, -1,  1], [ 1,  0,  1], [ 0,  1,  1], [-1,  0,  1],  # 13-16
            [-1, -1,  0], [ 1, -1,  0], [ 1,  1,  0], [-1,  1,  0]   # 17-20
        ])
        
        for k in range(12):
            id_val = k + 8 # Maps k=0 to index 8 (Node 9)
            ri_m, si_m, ti_m = mid_coords[k]
            
            if ri_m == 0:  # Edge parallel to xi axis
                N[id_val]        = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_dxi[id_val]   = 0.25 * (-2*xi)     * (1 + eta*si_m) * (1 + zeta*ti_m)
                dN_deta[id_val]  = 0.25 * (1 - xi**2) * (si_m)         * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 - xi**2) * (1 + eta*si_m) * (ti_m)
                
            elif si_m == 0: # Edge parallel to eta axis
                N[id_val]        = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (1 + zeta*ti_m)
                dN_dxi[id_val]   = 0.25 * (ri_m)        * (1 - eta**2) * (1 + zeta*ti_m)
                dN_deta[id_val]  = 0.25 * (1 + xi*ri_m) * (-2*eta)     * (1 + zeta*ti_m)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 - eta**2) * (ti_m)
                
            elif ti_m == 0: # Edge parallel to zeta axis
                N[id_val]        = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (1 - zeta**2)
                dN_dxi[id_val]   = 0.25 * (ri_m)        * (1 + eta*si_m) * (1 - zeta**2)
                dN_deta[id_val]  = 0.25 * (1 + xi*ri_m) * (si_m)         * (1 - zeta**2)
                dN_dzeta[id_val] = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (-2*zeta)

        return N, dN_dxi, dN_deta, dN_dzeta
    

    def define_loads_at_pos(self, target_x, P_val):
        """
        Dynamically distributes a point load to the top surface nodes.
        Uses the Lever Rule if the target_x falls between mesh node slices.
        """
        X = self.node_coords[:, 0]
        Z = self.node_coords[:, 2]  # Z is the vertical axis in your setup
        tol = 1e-8
        max_z = np.max(Z)
        
        # --- 1. Identify Slices ---
        unique_x = np.unique(X)
        diffs = target_x - unique_x
        
        # Find the closest slice to the left (<= target_x)
        left_mask = np.where(diffs >= -tol)[0]
        left_idx = left_mask[-1] if len(left_mask) > 0 else 0
        
        # Find the closest slice to the right (>= target_x)
        right_mask = np.where(diffs <= tol)[0]
        right_idx = right_mask[0] if len(right_mask) > 0 else len(unique_x) - 1
        
        loads = {}
        
        # --- 2. Distribute Load using Lever Rule ---
        if left_idx == right_idx:
            # Case A: Exact match on a vertical slice
            x_val = unique_x[left_idx]
            
            # Find all nodes on this X-slice that are also on the top surface (max Z)
            point_nodes = np.where((np.abs(X - x_val) < tol) & (np.abs(Z - max_z) < tol))[0]
            num_n = len(point_nodes)
            
            # Create a 3 x N array for loads (Fx, Fy, Fz)
            point_load_values = np.zeros((3, num_n))
            if num_n > 0:
                point_load_values[2, :] = P_val / num_n  # Apply load in Z direction
                
            loads['point_nodes'] = point_nodes
            loads['point_load_values'] = point_load_values
            
        else:
            # Case B: Load is between two slices (Apply Lever Rule)
            x_L = unique_x[left_idx]
            x_R = unique_x[right_idx]
            
            ratio_R = (target_x - x_L) / (x_R - x_L)
            ratio_L = 1.0 - ratio_R
            
            # Find top-surface nodes for both slices
            nodes_L = np.where((np.abs(X - x_L) < tol) & (np.abs(Z - max_z) < tol))[0]
            nodes_R = np.where((np.abs(X - x_R) < tol) & (np.abs(Z - max_z) < tol))[0]
            
            # Combine nodes
            loads['point_nodes'] = np.concatenate((nodes_L, nodes_R))
            
            # Distribute loads based on the lever ratios
            num_L = len(nodes_L)
            num_R = len(nodes_R)
            
            val_L = (P_val * ratio_L) / num_L if num_L > 0 else 0
            val_R = (P_val * ratio_R) / num_R if num_R > 0 else 0
            
            # Build Left Load Vectors
            load_vecs_L = np.zeros((3, num_L))
            if num_L > 0:
                load_vecs_L[2, :] = val_L
                
            # Build Right Load Vectors
            load_vecs_R = np.zeros((3, num_R))
            if num_R > 0:
                load_vecs_R[2, :] = val_R
                
            # Horizontally stack the arrays [L, R]
            loads['point_load_values'] = np.hstack((load_vecs_L, load_vecs_R))
            
        return loads
    
    def boundary_conditions(self, K_global, F_global, node_coords, beam_type):
        """Applies Boundary Conditions by identifying fixed DOFs and reducing the global matrices."""
        # 1. Setup Tolerances and Geometry Bounds
        tol = 1e-5
        X = node_coords[:, 0]
        Z = node_coords[:, 2]
        
        x_min = np.min(X)
        x_max = np.max(X)
        z_min = np.min(Z)
        
        # 2. Apply Boundary Conditions Based on Beam Type
        if 'cantilever' in beam_type.lower():
            # --- CANTILEVER ---
            # Find all nodes on the left face
            fixed_nodes = np.where(np.abs(X - x_min) < tol)[0]
            # Lock X, Y, Z for all face nodes
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
            
        elif 'fixed' in beam_type.lower():
            # --- FIXED-FIXED ---
            # Find all nodes on both the left and right faces
            fixed_nodes = np.where((np.abs(X - x_min) < tol) | (np.abs(X - x_max) < tol))[0]
            # Lock X, Y, Z for both faces
            fixed_dofs = np.repeat(fixed_nodes, 3) * 3 + np.tile([0, 1, 2], len(fixed_nodes))
            
        else:
            # --- SIMPLY SUPPORTED ---
            # Find nodes on the bottom-left edge (Pin)
            left_edge_nodes = np.where((np.abs(X - x_min) < tol) & (np.abs(Z - z_min) < tol))[0]
            
            # Find nodes on the bottom-right edge (Roller)
            right_edge_nodes = np.where((np.abs(X - x_max) < tol) & (np.abs(Z - z_min) < tol))[0]
            
            # Anchor Left Edge (Lock X, Y, Z)
            pin_dofs = np.repeat(left_edge_nodes, 3) * 3 + np.tile([0, 1, 2], len(left_edge_nodes))
            
            # Roller Right Edge (Lock Y, Z ONLY. X is free!)
            # Notice we only tile [1, 2] which corresponds to the Y and Z directions
            roller_dofs = np.repeat(right_edge_nodes, 2) * 3 + np.tile([1, 2], len(right_edge_nodes))
            
            # Combine them
            fixed_dofs = np.concatenate((pin_dofs, roller_dofs))
            
        # 3. Clean and Sort DOFs
        fixed_dofs = np.unique(fixed_dofs).astype(int)
        num_total = K_global.shape[0]
        
        # 4. Create free DOF indices
        free_dofs = np.setdiff1d(np.arange(num_total), fixed_dofs)
        
        # 5. Partition the system matrices
        # We slice the rows and columns simultaneously for the sparse stiffness matrix
        K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F_global[free_dofs]
        
        # 6. UI Feedback
        print(f"   BC Applied ({beam_type}): {len(fixed_dofs)} DOFs fixed. Reduced system: {K_reduced.shape[0]} x {K_reduced.shape[1]}")
        
        return K_reduced, F_reduced, fixed_dofs, free_dofs
       
    def visualize_BC_3d(self, node_coords, element_connectivity, element_type, mesh_info, bc_info, F_global, targetAxes):
        # 1. NO targetAxes.clear() HERE!
        targetAxes.clear() 
        F_nodes = F_global.reshape(-1, 3)
        load_mag = np.linalg.norm(F_nodes, axis=1)
        
        max_load = np.max(load_mag)
        if max_load > 0:
            applied_idx = np.where(load_mag > max_load * 0.01)[0]
        else:
            applied_idx = np.array([])
            
        # --- Robust Dynamic Scaling ---
        bbox_min = np.min(node_coords, axis=0)
        bbox_max = np.max(node_coords, axis=0)
        diagonal = np.linalg.norm(bbox_max - bbox_min)
        
        sphere_radius = diagonal * 0.015  # Spheres are 1.5% of the beam size
        arrow_scale = diagonal * 0.15     # Arrows are 15% of the beam size
            
        # 2. RENDER MESH (Overwrites memory cleanly)
        if 'Hexa' in element_type:
            n_vis = 8
            vtk_type = pv.CellType.HEXAHEDRON
        else:
            n_vis = 4
            vtk_type = pv.CellType.TETRA
            
        vis_connectivity = element_connectivity[:, :n_vis]
        grid = pv.UnstructuredGrid({vtk_type: vis_connectivity}, node_coords)
        
        targetAxes.add_mesh(grid, name='bc_base_mesh', show_edges=True, color="silver", edge_color="gray", opacity=0.4, line_width=1)
        
        # 3. VISUALIZE CONSTRAINTS (Red Dots)
        fixed_dofs = np.array(bc_info.get('fixed_dofs_indices', []))
        if len(fixed_dofs) > 0:
            fixed_nodes = np.unique(fixed_dofs // 3)
            fixed_coords = np.atleast_2d(node_coords[fixed_nodes])
            
            spheres = pv.PolyData(fixed_coords).glyph(geom=pv.Sphere(radius=sphere_radius))
            targetAxes.add_mesh(spheres, name='bc_fixed_dofs', color="red", show_edges=True, edge_color="black") 
        else:
            # Safely remove constraints if the new BC doesn't have any
            try: targetAxes.remove_actor('bc_fixed_dofs')
            except: pass
            
        # 4. VISUALIZE LOADS (Blue Arrows)
        if len(applied_idx) > 0:
            load_coords = np.atleast_2d(node_coords[applied_idx])
            load_vectors = np.atleast_2d(F_nodes[applied_idx])
            
            mags = load_mag[applied_idx]
            load_dirs = load_vectors / mags[:, np.newaxis]
            
            cloud = pv.PolyData(load_coords)
            cloud["vectors"] = load_dirs * arrow_scale
            
            arrows = cloud.glyph(orient="vectors", scale="vectors", factor=1.0, geom=pv.Arrow())
            targetAxes.add_mesh(arrows, name='bc_force_arrows', color="blue")
        else:
            # Safely remove arrows if the new BC doesn't have any forces
            try: targetAxes.remove_actor('bc_force_arrows')
            except: pass

        # 5. AXES STYLING (THE CRASH FIX)
        # Only add the XYZ axes widget ONCE! If we add it repeatedly, VTK crashes.
        if not hasattr(targetAxes, 'axes_widget_added'):
            targetAxes.add_axes()
            targetAxes.axes_widget_added = True
            
        targetAxes.view_isometric() 
        targetAxes.reset_camera()
        targetAxes.update()

    def update_load_bar_chart(self, F_global, targetAxes):
        """Plots the nodal load distribution to verify the Lever Rule """
        targetAxes.clear() # Matplotlib can safely clear
        
        # 1. Extract and Calculate Magnitudes
        Fz = F_global[2::3]
        load_mag = np.abs(Fz) 
        
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
            targetAxes.set_xlabel('Global Node ID')
            targetAxes.set_ylabel('Vertical Force (kN)')
            targetAxes.set_title(r'$\bf{Nodal\ Load\ Distribution\ (Lever\ Rule\ Check)}$')
            targetAxes.set_ylim([0, total_kN * 1.2])
            
            from matplotlib.ticker import MaxNLocator
            targetAxes.xaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            targetAxes.set_title('No Significant Point Loads Applied')
            
        # THE CRASH FIX FOR MATPLOTLIB: 
        # Use draw_idle() instead of draw() so it doesn't lock up the main GUI thread!
        fig = targetAxes.figure
        fig.tight_layout()
        if hasattr(fig, 'canvas'):
            fig.canvas.draw_idle()

    ######################## Helper################
    def GetGaussTable(self, N):
        """1D Gauss Points and Weights"""
        if N == 2:
            loc = np.array([-0.57735026919, 0.57735026919])
            w = np.array([1.0, 1.0])
        elif N == 3:
            loc = np.array([-0.774596669, 0.0, 0.774596669])
            w = np.array([0.555555556, 0.888888889, 0.555555556])
        else:
            # Fallback for N=1
            loc = np.array([0.0])
            w = np.array([2.0])
        return loc, w

    def BuildHexaGauss(self, N):
        """3D Gauss Points for Hexahedral Elements (Hexa8 / Hexa20)"""
        loc1, w1 = self.GetGaussTable(N)
        
        # Create the 3D grid
        X, Y, Z = np.meshgrid(loc1, loc1, loc1, indexing='ij')
        WX, WY, WZ = np.meshgrid(w1, w1, w1, indexing='ij')
        
        # CRITICAL: Use order='F' (Fortran) to exactly match MATLAB's (:) column-major flattening
        loc3 = np.column_stack((X.ravel(order='F'), Y.ravel(order='F'), Z.ravel(order='F')))
        w3 = (WX * WY * WZ).ravel(order='F')
        
        return loc3, w3

    def GetGaussTableTetrahedra(self, n):
        """Gauss Points for Tetrahedral Elements (Tet4 / Tet10)"""
        if n == 1:
            g_pts = np.array([[0.25, 0.25, 0.25]])
            g_w = np.array([1.0])
        else:
            # 4-point integration rule for Quadratic Tetrahedrons
            a = 0.58541020
            b = 0.13819660
            g_pts = np.array([
                [a, b, b],
                [b, a, b],
                [b, b, a],
                [b, b, b]
            ])
            g_w = np.array([0.25, 0.25, 0.25, 0.25])
            
        return g_pts, g_w


    # =========================================================================
    # TAB 3 : SOLVE 
    # =========================================================================
    def SolveButtonPushed(self):
        # 1. Verification: Ensure BCs and Matrices are ready
        if not hasattr(self, 'K_reduced') or not hasattr(self, 'F_reduced'):
            print("Solver Error: Please apply Boundary Conditions first.")
            self.ComputationalInfromationTextArea.setText("Error: Please apply Boundary Conditions first.")
            return

        print("Solving sparse linear system...")
        
        # 2. Solve Reduced System
        # Using time.perf_counter() for high-resolution CPU time measurement
        solve_start = time.perf_counter()
        
        # Convert K_reduced to Compressed Sparse Row (CSR) format for maximum solving speed
        U_free = spsolve(self.K_reduced.tocsr(), self.F_reduced) 
        
        solve_cpu_time = time.perf_counter() - solve_start
        
        # 3. Reconstruct Full Solution Vector
        num_dof = self.K_global.shape[0]
        self.U_full = np.zeros(num_dof)
        
        # Inject the solved free DOFs back into the full vector (Fixed DOFs remain 0)
        free_idx = self.bc_info['free_dofs_indices']
        self.U_full[free_idx] = U_free

        # 4. Compute Reaction Forces & Equilibrium Check
        # R = K*U - F (Standard FEM equilibrium)
        reactions_full = self.K_global.dot(self.U_full) - self.F_global
        
        # Reaction forces occur at constrained DOFs
        fixed_idx = self.bc_info['fixed_dofs_indices']
        reaction_forces = reactions_full[fixed_idx]
        
        total_applied = np.sum(self.F_global)
        total_reaction = np.sum(reaction_forces)
        equilibrium_error = abs(total_applied + total_reaction)
        
        # Check if error is within 0.0001% of applied force
        norm_F = np.linalg.norm(self.F_global)
        if norm_F != 0 and (equilibrium_error / norm_F < 1e-6):
            eq_status = '✓ Equilibrium Satisfied'
        elif norm_F == 0 and equilibrium_error < 1e-6:
            eq_status = '✓ Equilibrium Satisfied (Zero Load)'
        else:
            eq_status = '⚠ Equilibrium Error Detected'

        # 5. Display Information in TextArea
        summary_text = (
            "--- SOLVER SUMMARY ---\n"
            f"CPU Solve Time: {solve_cpu_time:.4f} seconds\n"
            f"Max Displacement: {np.max(np.abs(self.U_full)):.3e} m\n\n"
            "--- REACTION CHECK ---\n"
            f"Total Applied Force: {total_applied:.3e} N\n"
            f"Total Reaction Force: {total_reaction:.3e} N\n"
            f"Equilibrium Error: {equilibrium_error:.3e} N\n"
            f"{eq_status}"
        )
        
        self.ComputationalInfromationTextArea.setText(summary_text)
        print("Solve Complete!")

    def get_status_flag(self, error_val):
        if error_val < 5:
            return '✓ PASS (Excellent Agreement)'
        elif error_val < 15:
            return '⚠ CAUTION (Convergence Required)'
        else:
            return '✗ FAIL (Check Mesh/Units)'    

    # =========================================================================
    # TAB 4 : Validation
    # =========================================================================
    
    def ValidationwithEulierBernoullisBeamTheoryButtonPushed(self):
        # --- 1. PRE-CHECK ---
        if not hasattr(self, 'U_full'):
            # In PyQt, you could use QMessageBox here, but a print/text update is safer
            print("Validation Error: Solve the 3D model first!")
            return
            
        print("Starting Euler-Bernoulli 1D vs 3D Validation...")

        # --- 2. PARAMETERS FROM APP ---
        L = self.geometry['Lx']
        b = self.geometry['Ly']
        h = self.geometry['Lz']
        E = self.material['E']
        
        # Pull load values dynamically
        P = float(self.LoadValueNEditField.text()) 
        # Convert slider % (0-100) back to true physical position (a)
        a = (self.LoadPositionSlider.value() / 100.0) * L 
        
        rho = self.material['rho']
        # Safely pull gravity Z-direction (0-indexed array, so Z is [2])
        if 'BodyForceDir' in self.loads:
            g = self.loads['BodyForceDir'][2]
        else:
            g = 0.0
            
        # Section Properties
        I = (b * h**3) / 12.0
        A = b * h
        q = -(A * rho * g) # UDL due to gravity (Negative for downward)
        
        # --- 3. ANALYTICAL 1D SOLUTION (Euler-Bernoulli) ---
        if hasattr(self, 'compute_1D_Analytical'):
            x_1d, u_1d, s_bending_1d, s_shear_1d, _, _ = self.compute_1D_Analytical(L, a, P, E, I, q, h)
        else:
            print("Warning: compute_1D_Analytical not found.")
            return
            
        # Perform Stress Recovery (Using the Sparse B-matrix)
        print("Recovering 3D Stresses...")
        solve_start = time.perf_counter()
        
        if hasattr(self, 'PostProcess_Stress_3Dsparse'):
            self.Sigma_Final2 = self.PostProcess_Stress_3Dsparse(
                self.B_global, self.D_mat, self.U_full, self.node_coords, 
                self.element_connectivity, self.element_type)
        else:
            print("Warning: PostProcess_Stress_3Dsparse not found.")
            return
            
        solve_cpu_time1 = time.perf_counter() - solve_start
        
        # --- 4. EXTRACT 3D RESULTS ALONG NEUTRAL AXIS ---
        if hasattr(self, 'extract_3D_results'):
            _, u_3d_z, s_bending_3d, s_shear_3d = self.extract_3D_results()
        else:
            print("Warning: extract_3D_results not found.")
            return

        # --- 5. VISUALIZATION: 1D RESULTS ---
        if hasattr(self, 'plot_1D_Validation'):
            self.plot_1D_Validation(x_1d, u_1d, s_bending_1d, s_shear_1d, self.canvas_1d_validation)
            
        # --- 6. VISUALIZATION: 3D RESULTS ---
        if hasattr(self, 'plot_3D_Validation'):
            self.plot_3D_Validation(self.UIAxes_3D_Validation)
            
        # --- 7. SUMMARY BOX ---
        if hasattr(self, 'update_Validation_Summary'):
            self.update_Validation_Summary(
                u_1d, u_3d_z, s_bending_1d, s_bending_3d, s_shear_1d, s_shear_3d, 
                solve_cpu_time1, self.ValidationSummaryTextArea)
                
        print("Validation Complete!")

    #############################################
    def compute_1D_Analytical(self, L, a, P, E, I, q, h):
        # --- 1. SETUP PARAMETERS ---
        EI = E * I
        A = self.geometry['Ly'] * h
        G = E / (2 * (1 + self.material['nu']))
        k_shear = 5.0 / 6.0 # Rectangular cross-section shape factor
        
        x_vals = np.linspace(0, L, 100)
        y_vals = np.zeros(100) 
        M_vals = np.zeros(100) 
        V_vals = np.zeros(100)
        
        b_dist = L - a
        current_beam = self.BeamTypeDropDown.currentText().lower()
        
        # --- 2. EXACT ANALYTICAL PIECEWISE FORMULAS (Vectorized) ---
        # Create boolean masks to apply the piecewise formulas instantly without a loop
        left_mask = x_vals <= a
        right_mask = x_vals > a
        
        x_L = x_vals[left_mask]
        x_R = x_vals[right_mask]
        
        if 'cantilever' in current_beam:
            # CANTILEVER BEAM
            y_vals[left_mask] = (P * x_L**2) / (6 * EI) * (3*a - x_L)
            M_vals[left_mask] = P * (a - x_L)
            V_vals[left_mask] = P
            
            y_vals[right_mask] = (P * a**2) / (6 * EI) * (3*x_R - a)
            M_vals[right_mask] = 0.0
            V_vals[right_mask] = 0.0
            
        elif 'fixed' in current_beam:
            # FIXED-FIXED BEAM
            R1 = P * b_dist**2 * (3*a + b_dist) / L**3
            M1 = -P * a * b_dist**2 / L**2
            
            y_vals[left_mask] = (P * b_dist**2 * x_L**2) / (6 * EI * L**3) * (3*a*L - (3*a + b_dist)*x_L)
            M_vals[left_mask] = M1 + R1 * x_L
            V_vals[left_mask] = R1
            
            y_vals[right_mask] = (P * a**2 * (L - x_R)**2) / (6 * EI * L**3) * (3*b_dist*L - (3*b_dist + a)*(L - x_R))
            M_vals[right_mask] = M1 + R1 * x_R - P * (x_R - a)
            V_vals[right_mask] = R1 - P
            
        else:
            # SIMPLY SUPPORTED BEAM (Fallback)
            y_vals[left_mask] = (P * b_dist * x_L) / (6 * L * EI) * (L**2 - b_dist**2 - x_L**2)
            M_vals[left_mask] = (P * b_dist / L) * x_L
            V_vals[left_mask] = P * b_dist / L
            
            y_vals[right_mask] = (P * a * (L - x_R)) / (6 * L * EI) * (L**2 - a**2 - (L - x_R)**2)
            M_vals[right_mask] = (P * a / L) * (L - x_R)
            V_vals[right_mask] = -P * a / L
            
        # --- 3. TIMOSHENKO SHEAR DEFORMATION ---
        # Numerically integrate the exact shear force diagram using Scipy
        y_shear = cumulative_trapezoid(V_vals, x_vals, initial=0) / (k_shear * G * A)
        
        # Correct the integration baseline for constrained ends
        if 'fix' in current_beam or 'support' in current_beam:
            drift = np.linspace(0, y_shear[-1], len(x_vals))
            y_shear = y_shear - drift
            
        # Superimpose Shear deformation onto Euler-Bernoulli Bending
        y_vals = y_vals + y_shear
        
        # --- 4. STRESS CALCULATIONS ---
        # Calculate full arrays of stress along the entire length of the beam
        S_bend_vals = (np.abs(M_vals) * (h / 2.0)) / I
        S_shear_vals = (3.0 * np.abs(V_vals)) / (2.0 * A)
        
        S_bend_max = (np.max(np.abs(M_vals)) * (h / 2.0)) / I
        S_shear_max = (3.0 * np.max(np.abs(V_vals))) / (2.0 * A)
        
        return x_vals, y_vals, S_bend_vals, S_shear_vals, S_bend_max, S_shear_max

    
    def PostProcess_Stress_3Dsparse(self, B_global, D, U_global, Coords, Connectivity, ElementType):
        Num_Nodes = Coords.shape[0]
        Num_Elem = Connectivity.shape[0]
        
        # --- 1. DETECT num_gp FROM B_global DIMENSIONS ---
        total_B_rows = B_global.shape[0]
        num_gp = total_B_rows // (6 * Num_Elem)
        
        if total_B_rows % (6 * Num_Elem) != 0:
            raise ValueError(f"B_global rows ({total_B_rows}) is not a multiple of 6 * Num_Elements ({6*Num_Elem}).")
            
        print(f"--- Starting Sparse Post-Processing ({ElementType}, GP: {num_gp}) ---")
        
        # --- 2. VECTORIZED STRESS CALCULATION ---
        # epsilon_all shape: (Num_Elem * num_gp * 6,)
        epsilon_all = B_global.dot(U_global)
        
        # Reshape to (6, Num_Elem * num_gp). 
        # Python uses row-major by default, so we reshape and transpose to match MATLAB's column-major reshaping.
        strain_matrix = epsilon_all.reshape(-1, 6).T
        
        # sigma_gauss_all shape: (6, Num_Elem * num_gp)
        sigma_gauss_all = D @ strain_matrix 
        
        # --- 3. GLOBAL EXTRAPOLATION & AVERAGING ---
        start_time = time.perf_counter()
        
        if hasattr(self, 'Get_Emat_3D_Full'):
            # Grab coordinates of the first element to compute the local extrapolation matrix
            E_mat = self.Get_Emat_3D_Full(Coords[Connectivity[0, :]], ElementType, num_gp)
        else:
            print("Warning: Get_Emat_3D_Full not found. Using uniform averaging as fallback.")
            E_mat = np.ones((Connectivity.shape[1], num_gp)) / num_gp
            
        nodes_per_elem = Connectivity.shape[1]
        
        # Python Speed Trick: Fully Vectorized Matrix Triplet Generation (Replaces the 3D nested loop)
        # row_idx: repeats each node in Connectivity `num_gp` times
        row_idx = np.repeat(Connectivity, num_gp, axis=1).ravel()
        
        # col_idx: global Gauss point IDs
        gp_ids_per_elem = np.arange(Num_Elem)[:, None] * num_gp + np.arange(num_gp)[None, :]
        col_idx = np.repeat(gp_ids_per_elem[:, None, :], nodes_per_elem, axis=1).ravel()
        
        # val_idx: tile the E_mat for every element
        val_idx = np.tile(E_mat, (Num_Elem, 1)).ravel()
        
        # Build the Sparse Extrapolation Matrix
        E_global = sp.csr_matrix((val_idx, (row_idx, col_idx)), shape=(Num_Nodes, Num_Elem * num_gp))
        
        # Create Adjacency matrix to count how many elements share each node
        adj_row = Connectivity.ravel()
        adj_col = np.repeat(np.arange(Num_Elem), nodes_per_elem)
        adj_val = np.ones(len(adj_row))
        Adj = sp.csr_matrix((adj_val, (adj_row, adj_col)), shape=(Num_Nodes, Num_Elem))
        
        Node_Counts = np.array(Adj.sum(axis=1)).flatten()
        Node_Counts[Node_Counts == 0] = 1 # Prevent division by zero
        
        # Multiply Extrapolation Matrix by Stresses
        Nodal_Stress_Sum = E_global.dot(sigma_gauss_all.T) 
        
        # Average the nodal stresses based on element connections
        Sigma_Final2 = Nodal_Stress_Sum / Node_Counts[:, np.newaxis]
        
        elapsed = time.perf_counter() - start_time
        print(f"   Sparse Extrapolation Completed in {elapsed:.4f} seconds.")
        
        return Sigma_Final2
    
    def extract_3D_results(self):
        # 1. Dynamically find the actual bounds of the current mesh
        z_coords = self.node_coords[:, 2]
        y_coords = self.node_coords[:, 1]
        
        z_max_actual = np.max(z_coords)
        z_min_actual = np.min(z_coords)
        z_mid_actual = (z_max_actual + z_min_actual) / 2.0
        y_mid_actual = (np.max(y_coords) + np.min(y_coords)) / 2.0
    
        # 2. Use a "Closest Match" tolerance (1% of height)
        tol = (z_max_actual - z_min_actual) * 0.01 
    
        # 3. Extract Top Centerline (for Bending and Deflection)
        top_idx = np.where((np.abs(z_coords - z_max_actual) < tol) & 
                           (np.abs(y_coords - y_mid_actual) < tol))[0]
        
        # 4. Extract Neutral Axis (for Shear Stress)
        mid_idx = np.where((np.abs(z_coords - z_mid_actual) < tol) & 
                           (np.abs(y_coords - y_mid_actual) < tol))[0]
    
        # --- Data Assignment ---
        x_3d = self.node_coords[top_idx, 0]
        
        # Z-displacement is index 2 in 0-based Python [X=0, Y=1, Z=2]
        u_3d_z = self.U_full[top_idx * 3 + 2] 
        
        # Sigma_Final2 indices: 0 = Sig_xx, 5 = Tau_xz (translated from MATLAB 1 and 6)
        s_bending_3d = self.Sigma_Final2[top_idx, 0] 
        s_shear_3d = self.Sigma_Final2[mid_idx, 5] 
        
        # Sort by X-axis to ensure 1D comparison plots look correct
        s_idx = np.argsort(x_3d)
        x_3d = x_3d[s_idx]
        u_3d_z = u_3d_z[s_idx]
        s_bending_3d = s_bending_3d[s_idx]
        
        return x_3d, u_3d_z, s_bending_3d, s_shear_3d

    def Get_Emat_3D_Full(self, Coords, ElementType, num_gp):
        nodes_per_elem = Coords.shape[0]
        
        if num_gp == 1:
            return np.ones((nodes_per_elem, 1))
            
        if ElementType == 'Hexa8':
            gpts = [-1/np.sqrt(3), 1/np.sqrt(3)]
            GP = np.zeros((8, 3))
            cnt = 0
            for i in range(2):
                for j in range(2):
                    for k in range(2):
                        GP[cnt, :] = [gpts[i], gpts[j], gpts[k]]
                        cnt += 1
                        
            Node_Loc = np.array([[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1], 
                                 [-1,-1, 1], [1,-1, 1], [1,1, 1], [-1,1, 1]])
            r = np.sqrt(3)
            E_mat = np.zeros((8, 8))
            for n in range(8):
                for k in range(8):
                    E_mat[n, k] = 0.125 * (1 + Node_Loc[n,0]*GP[k,0]*r) * \
                                          (1 + Node_Loc[n,1]*GP[k,1]*r) * \
                                          (1 + Node_Loc[n,2]*GP[k,2]*r)
            return E_mat
            
        elif ElementType == 'Hexa20':
            if num_gp == 8:
                g_pts, _ = self.BuildHexaGauss(2)
                Node_Loc = np.array([
                    [-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1], [-1,-1,1], [1,-1,1], [1,1,1], [-1,1,1],
                    [0,-1,-1], [1,0,-1], [0,1,-1], [-1,0,-1], [0,-1,1], [1,0,1], [0,1,1], [-1,0,1],
                    [-1,-1,0], [1,-1,0], [1,1,0], [-1,1,0]
                ])
                r = np.sqrt(3)
                E_mat = np.zeros((20, 8))
                for n in range(20):
                    for k in range(8):
                        E_mat[n, k] = 0.125 * (1 + Node_Loc[n,0]*g_pts[k,0]*r) * \
                                              (1 + Node_Loc[n,1]*g_pts[k,1]*r) * \
                                              (1 + Node_Loc[n,2]*g_pts[k,2]*r)
                return E_mat
                
            elif num_gp == 27:
                g_pts, _ = self.BuildHexaGauss(3)
                N_G = np.zeros((27, 20))
                for k in range(27):
                    xi, eta, zeta = g_pts[k,0], g_pts[k,1], g_pts[k,2]
                    N_shape, _, _, _ = self.Hexa20_ShapeFunctions(xi, eta, zeta)
                    N_G[k, :] = N_shape
                return np.linalg.pinv(N_G)
                
        elif ElementType == 'Tet10':
            a, b = 0.58541020, 0.13819660
            g_pts = np.array([[a, b, b], [b, a, b], [b, b, a], [b, b, b]])
            XYZ_G = np.zeros((4, 3))
            
            for k in range(4):
                xi, eta, zeta = g_pts[k,0], g_pts[k,1], g_pts[k,2]
                L4 = 1 - xi - eta - zeta
                N = np.array([
                    L4*(2*L4-1), xi*(2*xi-1), eta*(2*eta-1), zeta*(2*zeta-1),
                    4*L4*xi, 4*xi*eta, 4*eta*L4, 4*L4*zeta, 4*xi*zeta, 4*eta*zeta
                ])
                XYZ_G[k, :] = N.T @ Coords
                
            # Use Moore-Penrose pseudo-inverse for physical mapping
            M_nodes = np.column_stack((np.ones(10), Coords))
            M_gauss = np.column_stack((np.ones(4), XYZ_G))
            E_mat = M_nodes @ np.linalg.pinv(M_gauss)
            return E_mat
            
        elif ElementType == 'Tet4':
            return np.ones((4, 1))
            
        else:
            return np.ones((nodes_per_elem, num_gp)) / num_gp
        
    def plot_1D_Validation(self, x_1d, u_1d, s_bending_1d, s_shear_1d, targetPanel):
        """Plots the 1D Analytical Results with perfect automatic spacing"""
        fig = targetPanel.figure if hasattr(targetPanel, 'figure') else targetPanel
        fig.clf() 
        
        # 1. THE FIX: Use subplots instead of manual coordinates for auto-spacing
        axes = fig.subplots(3, 1)
        ax1, ax2, ax3 = axes[0], axes[1], axes[2]
        
        # Plot 1D Deflection
        ax1.plot(x_1d, u_1d * 1000, 'b-', linewidth=2.5) # Convert to mm
        ax1.grid(True, linestyle='--')
        ax1.set_ylabel('Deflection [mm]')
        ax1.set_title(r'$\bf{1D\ Euler-Bernoulli\ Analytical\ Results}$')
        
        # Plot 1D Bending Stress
        ax2.plot(x_1d, s_bending_1d / 1e6, 'r-', linewidth=2.5) # Convert to MPa
        ax2.grid(True, linestyle='--')
        ax2.set_ylabel(r'Bending $\sigma_{xx}$ [MPa]')
        
        # Plot 1D Shear Stress (X-label only on the bottom plot!)
        ax3.plot(x_1d, s_shear_1d / 1e6, 'g-', linewidth=2.5) # Convert to MPa
        ax3.grid(True, linestyle='--')
        ax3.set_xlabel('Beam Length [m]') 
        ax3.set_ylabel(r'Shear $\tau_{xz}$ [MPa]')
        
        # Add load marker (Using dynamic slider calculation)
        load_pos = (self.LoadPositionSlider.value() / 100.0) * self.geometry['Lx']
        ax1.axvline(load_pos, color='k', linestyle='--', label='P')
        ax2.axvline(load_pos, color='k', linestyle='--', label='P')
        ax3.axvline(load_pos, color='k', linestyle='--', label='P')
        
        # 2. THE MAGIC COMMAND: Forces Matplotlib to perfectly calculate margins
        fig.tight_layout(pad=1.5)
        
        # Trigger redraw
        if hasattr(fig, 'canvas'):
            fig.canvas.draw()

    def plot_3D_Validation(self, targetAxes):
        """Renders the deformed 3D mesh for Bending and Shear stress on split axes (Crash-Proof)"""
        targetAxes.clear() 
        # --- 0. SAFETY CHECK ---
        if not hasattr(self, 'U_full') or not hasattr(self, 'Sigma_Final2'):
            print("Validation data not found. Run 3D FEM solve first.")
            return
            
        if len(self.node_coords) != len(self.Sigma_Final2):
            print("CRITICAL ERROR: Mesh size and Validation Stress arrays do not match!")
            return

        # NOTICE: We REMOVED targetAxes.clear() to prevent C++ Segfaults!
        
        # --- 1. DEFORMATION SCALE ---
        U_nodes = self.U_full.reshape(-1, 3)
        max_u = np.max(np.abs(self.U_full))
        
        # Prevent division by zero if the beam didn't move
        scale = (self.geometry['Lx'] * 0.15) / max(max_u, 1e-9) 
        
        # Apply deformation to coordinates
        warped_coords = self.node_coords + (U_nodes * scale)
        
        # --- 2. BUILD MESH ---
        if 'Hexa' in self.element_type:
            n_vis = 8
            vtk_type = pv.CellType.HEXAHEDRON
        else:
            n_vis = 4
            vtk_type = pv.CellType.TETRA
            
        vis_connectivity = self.element_connectivity[:, :n_vis]
        cells_dict = {vtk_type: vis_connectivity}
        
        # We create a base grid using the warped coordinates
        grid = pv.UnstructuredGrid(cells_dict, warped_coords)
        
        # Extract Stresses (MATLAB 1 -> Python 0, MATLAB 6 -> Python 5)
        stress_bending_mpa = self.Sigma_Final2[:, 0] / 1e6
        stress_shear_mpa = self.Sigma_Final2[:, 5] / 1e6
        
        # --- COLOR BAR FORMATTING ---
        sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, 
                     fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)

        # --- 3. TOP PLOT: BENDING STRESS ---
        targetAxes.subplot(0, 0)
        
        grid_top = grid.copy()
        grid_top.point_data["Bending Stress (MPa)"] = stress_bending_mpa
        
        # Extract surface and silence the PyVista warning
        shell_top = grid_top.extract_surface(algorithm='dataset_surface')
        
        # THE MAGIC FIX: name='val_bending' prevents the crash!
        targetAxes.add_mesh(shell_top, name='val_bending', scalars="Bending Stress (MPa)", 
                            cmap="jet", show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
                            
        targetAxes.add_text("3D FEA: Bending Stress XX [MPa]", name='val_bend_txt', font_size=10, color='black')
        targetAxes.view_isometric()
        targetAxes.add_axes()
        targetAxes.reset_camera()
        
        # --- 4. BOTTOM PLOT: SHEAR STRESS ---
        targetAxes.subplot(1, 0)
        
        grid_bot = grid.copy()
        grid_bot.point_data["Shear Stress XZ (MPa)"] = stress_shear_mpa
        
        # Extract surface and silence the PyVista warning
        shell_bot = grid_bot.extract_surface(algorithm='dataset_surface')
        
        # THE MAGIC FIX: name='val_shear' prevents the crash!
        targetAxes.add_mesh(shell_bot, name='val_shear', scalars="Shear Stress XZ (MPa)", 
                            cmap="jet", show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
                            
        targetAxes.add_text("3D FEA: Shear Stress XZ [MPa]", name='val_shear_txt', font_size=10, color='black')
        targetAxes.view_isometric()
        targetAxes.add_axes()
        targetAxes.reset_camera()
        
        # --- 5. RENDER ---
        targetAxes.update()

    def update_Validation_Summary(self, u_1d, u_3d, s_1d, s_3d, ss_1d, ss_3d, cpu_time, targetTextArea):
        # Deflection [mm]
        max_u_3d = np.max(np.abs(u_3d)) * 1000 if len(u_3d) > 0 else np.max(np.abs(self.U_full)) * 1000
        # Bending Stress [MPa]
        max_s_3d = np.max(np.abs(s_3d)) / 1e6 if len(s_3d) > 0 else np.max(np.abs(self.Sigma_Final2[:, 0])) / 1e6
        # Shear Stress [MPa]
        max_ss_3d = np.max(np.abs(ss_3d)) / 1e6 if len(ss_3d) > 0 else np.max(np.abs(self.Sigma_Final2[:, 5])) / 1e6
        
        max_u_1d = np.max(np.abs(u_1d)) * 1000
        max_s_1d = np.max(np.abs(s_1d)) / 1e6
        max_ss_1d = np.max(np.abs(ss_1d)) / 1e6
        
        u_error = (abs(max_u_1d - max_u_3d) / max_u_1d * 100) if max_u_1d > 1e-12 else 0.0
        
        summary_text = (
            "================================\n"
            "      VALIDATION SUMMARY        \n"
            "================================\n"
            f"CPU Solve Time  : {cpu_time:.4f} seconds\n\n"
            "--- DEFLECTION (z-axis) ---\n"
            f"Analytical (1D) : {max_u_1d:.4f} mm\n"
            f"Numerical (3D)  : {max_u_3d:.4f} mm\n"
            f"Relative Error  : {u_error:.2f} %\n\n"
            "--- BENDING STRESS (sigma_xx) ---\n"
            f"Analytical (1D) : {max_s_1d:.2f} MPa\n"
            f"Numerical (3D)  : {max_s_3d:.2f} MPa\n\n"
            "--- SHEAR STRESS (tau_xz) ---\n"
            f"Analytical (1D) : {max_ss_1d:.2f} MPa\n"
            f"Numerical (3D)  : {max_ss_3d:.2f} MPa\n"
            "--------------------------------\n"
            f"Status: {self.get_status_flag(u_error)}"
        )
        
        targetTextArea.setText(summary_text)


   # =========================================================================
   # TAB 5 : Post-Processing
   # =========================================================================
    def OpenPostProcessingButtonPushed(self):
        # 1. Pre-check: Ensure the solver has actually run
        if not hasattr(self, 'Sigma_Final2') or not hasattr(self, 'U_full'):
            print("Post-Processing Error: Please run the 3D solver first!")
            return

        print("Generating Post-Processing Visuals...")

        # 2. Safely extract values from UI EditFields
        try:
            yield_strength = float(self.YieldStrengthMpaEditField.text())
        except ValueError:
            yield_strength = 250.0  
            print(f"Warning: Invalid Yield Strength. Using default {yield_strength} MPa.")

        try:
            self.scale_factor = float(self.ScaleFactorEditField.text())
        except ValueError:
            self.scale_factor = 1.0  
            print(f"Warning: Invalid Scale Factor. Using default {self.scale_factor}.")

        # Extract values from DropDowns
        self.stress_type = self.TypeofStressesDropDown.currentText()
        self.faliuremode = self.MethodDropDown.currentText()
        
        # THE FIX: Grab the user's choice from the new dropdown
        display_choice = self.DisplayChoiceDropDown.currentText()

        # 3. Call the plotting routines
        if hasattr(self, 'plot_stresses'):
            self.plot_stresses(
                self.Sigma_Final2, self.stress_type, self.UIAxes5, 
                self.U_full, self.scale_factor
            )
        else:
            print("Warning: plot_stresses method not found.")

        if hasattr(self, 'plot_FS'):
            # THE FIX: We only pass UIAxes6 now, and we feed it the display_choice!
            self.plot_FS(
                self.faliuremode, yield_strength, self.UIAxes6, 
                self.Sigma_Final2, self.U_full, self.scale_factor, display_type=display_choice
            )
        else:
            print("Warning: plot_FS method not found.")
            
        print("Post-Processing Render Complete!")
        
   ######################################################################
    def plot_stresses(self, Sigma_Final, stress_type, targetAxes, U_full, scale_factor):

        targetAxes.clear() 
        # --- 1. CRITICAL SAFETY CHECK ---
        if len(self.node_coords) != len(Sigma_Final):
            print("CRITICAL ERROR: Mesh size and Stress arrays do not match!")
            return
            
        # NOTICE: We removed clear_actors() entirely!
        
        # --- 3. Extract Stress ---
        stress_map = {
            'Sigma_xx': (0, 'Sigma_xx'), 'Sigma_yy': (1, 'Sigma_yy'), 'Sigma_zz': (2, 'Sigma_zz'),
            'Tau_xy':   (3, 'Tau_xy'),   'Tau_yz':   (4, 'Tau_yz'),   'Tau_zx':   (5, 'Tau_zx'),
            'Tau_xz':   (5, 'Tau_zx') 
        }
        col, lbl = stress_map.get(stress_type, (0, 'Sigma_xx'))
        stress_data = Sigma_Final[:, col] / 1e6  # Convert to MPa
        
        # --- 4. Deformation Scaling ---
        Max_Disp_mm = np.max(np.abs(U_full)) * 1000.0
        U_nodes = U_full.reshape(-1, 3)
        def_coords = self.node_coords + (U_nodes * scale_factor)
        
        # --- 5. Build Mesh & Extract Shell ---
        if 'Hexa' in self.element_type:
            n_vis = 8
            vtk_type = pv.CellType.HEXAHEDRON
        else:
            n_vis = 4
            vtk_type = pv.CellType.TETRA
            
        vis_connectivity = self.element_connectivity[:, :n_vis]
        cells_dict = {vtk_type: vis_connectivity}
        
        grid_undeformed = pv.UnstructuredGrid(cells_dict, self.node_coords)
        grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)
        
        grid_deformed.point_data["Stress (MPa)"] = stress_data
        
        # THE FIX: Added algorithm='dataset_surface' to silence the PyVista warning
        shell_undeformed = grid_undeformed.extract_surface(algorithm='dataset_surface')
        shell_deformed = grid_deformed.extract_surface(algorithm='dataset_surface')
        
        # --- 6. RENDER WITH NAMED MESHES (CRASH-PROOF) ---
        sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, 
                     fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)
                     
        # By adding name='...', PyVista gently updates the memory instead of destroying it!
        targetAxes.add_mesh(shell_undeformed, name='base_wireframe', style='wireframe', color='gray', opacity=0.4, line_width=1.0)
        targetAxes.add_mesh(shell_deformed, name='deformed_stress', scalars="Stress (MPa)", cmap="jet", 
                            show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
        
        # --- 7. Camera & Text ---
        title_str = f"Stress Component: {lbl}\nMax Deflection: {Max_Disp_mm:.3f} mm (Visual Scale: {scale_factor}x)"
        targetAxes.add_text(title_str, name='stress_title_text', font_size=10, color='black')
        
        min_c = np.min(self.node_coords, axis=0)
        max_c = np.max(self.node_coords, axis=0)
        span_x = max_c[0] - min_c[0]
        buf = span_x * 0.2
        fixed_bounds = [min_c[0]-buf, max_c[0]+buf, min_c[1]-buf, max_c[1]+buf, min_c[2]-(buf*2), max_c[2]+(buf*2)]
        
        targetAxes.add_axes()
        targetAxes.view_isometric()
        targetAxes.reset_camera(bounds=fixed_bounds)
        targetAxes.update()

    def plot_FS(self, failure_mode, yield_strength, targetAxes, Sigma_Final, U_full, scale_factor, display_type="FS"):
        # --- 1. CRITICAL SAFETY CHECK ---
        if len(self.node_coords) != len(Sigma_Final):
            print("CRITICAL ERROR: Mesh size and Stress arrays do not match!")
            return
            
        # --- 2. Vectorized Failure Metrics ---
        sx, sy, sz = Sigma_Final[:, 0], Sigma_Final[:, 1], Sigma_Final[:, 2]
        txy, tyz, tzx = Sigma_Final[:, 3], Sigma_Final[:, 4], Sigma_Final[:, 5]
        num_nodes = len(sx)
        
        if "von mises" in failure_mode.lower():
            C_data = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6
        elif "principal" in failure_mode.lower() or "tresca" in failure_mode.lower() or "shear" in failure_mode.lower():
            stress_tensors = np.zeros((num_nodes, 3, 3))
            stress_tensors[:, 0, 0] = sx; stress_tensors[:, 0, 1] = txy; stress_tensors[:, 0, 2] = tzx
            stress_tensors[:, 1, 0] = txy; stress_tensors[:, 1, 1] = sy;  stress_tensors[:, 1, 2] = tyz
            stress_tensors[:, 2, 0] = tzx; stress_tensors[:, 2, 1] = tyz; stress_tensors[:, 2, 2] = sz
            
            eigenvalues = np.linalg.eigvalsh(stress_tensors)
            if "principal" in failure_mode.lower():
                C_data = eigenvalues[:, 2] / 1e6
            else:
                C_data = (eigenvalues[:, 2] - eigenvalues[:, 0]) / 2.0 / 1e6
        else:
            C_data = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2 + 6*(txy**2 + tyz**2 + tzx**2))) / 1e6

        FS_data = yield_strength / np.maximum(C_data, 1e-6)
        
        # --- 3. DYNAMIC DATA SELECTION ---
        if "stress" in display_type.lower():
            plot_scalars = C_data
            plot_name = "Stress Data (MPa)"
            cmap_choice = "jet"
            c_limits = None # Auto-scale max stress
            title_str = f"{failure_mode} (MPa)\nMax Deflection: {(np.max(np.abs(U_full)) * 1000.0):.3f} mm"
        else:
            plot_scalars = FS_data
            plot_name = "Factor of Safety"
            cmap_choice = "jet_r" # Reversed for FS (Red = Bad)
            c_limits = [0, 10]    # Cap FS visualization at 10
            title_str = f"Factor of Safety (FS < 1 is Failure)\nMax Deflection: {(np.max(np.abs(U_full)) * 1000.0):.3f} mm"

        # --- 4. Deformation Scaling & Shell Extraction ---
        Max_Disp_mm = np.max(np.abs(U_full)) * 1000.0
        U_nodes = U_full.reshape(-1, 3)
        def_coords = self.node_coords + (U_nodes * scale_factor)
        
        if 'Hexa' in self.element_type: n_vis, vtk_type = 8, pv.CellType.HEXAHEDRON
        else: n_vis, vtk_type = 4, pv.CellType.TETRA
            
        cells_dict = {vtk_type: self.element_connectivity[:, :n_vis]}
        grid_undeformed = pv.UnstructuredGrid(cells_dict, self.node_coords)
        grid_deformed = pv.UnstructuredGrid(cells_dict, def_coords)
        
        grid_deformed.point_data[plot_name] = plot_scalars
        
        shell_undeformed = grid_undeformed.extract_surface(algorithm='dataset_surface')
        shell_deformed = grid_deformed.extract_surface(algorithm='dataset_surface')
        
        # --- 5. RENDER WITH NAMED MESHES ---
        sargs = dict(title_font_size=12, label_font_size=10, shadow=False, n_labels=5, 
                     fmt="%.1f", vertical=True, position_x=0.82, position_y=0.1, height=0.75, width=0.1)
                     
        min_c = np.min(self.node_coords, axis=0); max_c = np.max(self.node_coords, axis=0)
        span_x = max_c[0] - min_c[0]; buf = span_x * 0.2
        fixed_bounds = [min_c[0]-buf, max_c[0]+buf, min_c[1]-buf, max_c[1]+buf, min_c[2]-(buf*2), max_c[2]+(buf*2)]
        
        targetAxes.add_mesh(shell_undeformed, name='fs_wire', style='wireframe', color='gray', opacity=0.4, line_width=1.0)
        
        # Apply color limits only if Factor of Safety is selected
        if c_limits:
            targetAxes.add_mesh(shell_deformed, name='fs_solid', scalars=plot_name, cmap=cmap_choice, clim=c_limits, 
                                show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
        else:
            targetAxes.add_mesh(shell_deformed, name='fs_solid', scalars=plot_name, cmap=cmap_choice, 
                                show_edges=True, edge_color='black', line_width=0.1, scalar_bar_args=sargs)
                                
        targetAxes.add_text(title_str, name='fs_txt', font_size=10, color='black')
        
        # Safe Axes Check
        if not hasattr(targetAxes, 'axes_widget_added'):
            targetAxes.add_axes()
            targetAxes.axes_widget_added = True
            
        targetAxes.view_isometric()
        targetAxes.reset_camera(bounds=fixed_bounds)
        targetAxes.update()
    # =====================================
    # Tab6 ROM Trainnig
    # ====================================
    def TrainButtonPushed(self):
        # 1. Setup Training Parameters
        num_snapshots = int(self.num_snapshotsEditField.text())
        
        # Expand training envelope to learn boundary physics (1% to 99%)
        x_positions = np.linspace(0.01 * self.geometry['Lx'], 0.99 * self.geometry['Lx'], num_snapshots)
        
        free_dofs = self.bc_info['free_dofs_indices']
        num_free_dof = len(free_dofs)
        num_total_dof = self.K_global.shape[0]
        num_nodes = self.node_coords.shape[0]
        
        # Pre-allocate ONLY the Displacement Snapshot Matrix (saves memory)
        self.SnapshotMatrix = np.zeros((num_free_dof, num_snapshots))
        
        self.TrainningTimeTextArea.setText("*** Starting ROM Training ***\n")
        print("Starting ROM Training...")
        
        # Pre-convert K_reduced to CSR format outside the loop for maximum speed
        K_reduced_csr = self.K_reduced.tocsr()
        
        # --- 2. SNAPSHOT GENERATION LOOP ---
        for i in range(num_snapshots):
            # Assuming define_loads_at_pos returns a dictionary with nodes and forces
            load_val = float(self.LoadValueNEditField.text())
            temp_loads = self.define_loads_at_pos(x_positions[i], load_val)
            
            F_temp = np.zeros(num_total_dof)
            
            # Populate temporary force vector
            for j in range(len(temp_loads['point_nodes'])):
                node_id = temp_loads['point_nodes'][j]
                force_vec = temp_loads['point_load_values'][:, j]
                
                # Python 0-based indexing for DOFs
                dof_indices = node_id * 3 + np.array([0, 1, 2])
                F_temp[dof_indices] += force_vec
                
            F_red_i = F_temp[free_dofs]
            
            start_time = time.perf_counter()
            U_free_i = spla.spsolve(K_reduced_csr, F_red_i)
            elapsedTime = time.perf_counter() - start_time
            
            new_entry = f"Snap {i+1}: {elapsedTime:.4f}s at {x_positions[i]:.2f}m\n"
            
            # Prepend to text area and force UI update (Equivalent to MATLAB 'drawnow')
            current_text = self.TrainningTimeTextArea.toPlainText()
            self.TrainningTimeTextArea.setText(new_entry + current_text)
            QApplication.processEvents() 
            
            self.SnapshotMatrix[:, i] = U_free_i
            
        # --- 3. PERFORM POD (SVD) ON DISPLACEMENT ONLY ---
        print("Performing Singular Value Decomposition (SVD)...")
        # full_matrices=False is the exact equivalent to MATLAB's 'econ'
        U_svd, S_disp, Vt = np.linalg.svd(self.SnapshotMatrix, full_matrices=False)
        self.Phi = U_svd
        
        energy_disp = S_disp**2 
        cum_energy_disp = np.cumsum(energy_disp) / np.sum(energy_disp) * 100.0
        
        # --- 4. PLOT INVARIANCE (ENERGY) ---
        # Assuming self.UIAxes8 is a Matplotlib Canvas figure
        fig = self.UIAxes8.figure if hasattr(self.UIAxes8, 'figure') else self.UIAxes8
        fig.clf()
        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx() # Create dual Y-axis (Equivalent to MATLAB yyaxis)
        
        mode_numbers = np.arange(1, num_snapshots + 1)
        
        # Left Axis: Singular Values (Bar Chart)
        ax1.bar(mode_numbers, S_disp / np.max(S_disp), color='#3399CC', alpha=0.8)
        ax1.set_xlabel('Mode Number')
        ax1.set_ylabel('Relative Singular Values', color='black')
        ax1.tick_params(axis='y', colors='black')
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # Right Axis: Cumulative Energy (Line Chart)
        ax2.plot(mode_numbers, cum_energy_disp, '-bo', linewidth=2, markerfacecolor='b')
        ax2.set_ylabel('Cumulative Energy (%)', color='black')
        ax2.set_ylim([np.min(cum_energy_disp) - 5, 105])
        ax2.tick_params(axis='y', colors='black')
        
        ax1.set_title('ROM Invariance: Displacement Modes')
        if hasattr(fig, 'canvas'):
            fig.canvas.draw()
            
        # --- 5. FINALIZE ROM BASIS ---
        # Keep extremely high energy to capture sharp point loads
        modes_over_threshold = np.where(cum_energy_disp > 99.999)[0]
        if len(modes_over_threshold) > 0:
            n_modes_disp = modes_over_threshold[0] + 1 # +1 for 0-based index
        else:
            n_modes_disp = min(15, num_snapshots)
            
        self.Phi = self.Phi[:, :n_modes_disp]
        
        # Pre-calculate Reduced Stiffness Matrix K_rom
        print("Projecting Stiffness Matrix...")
        self.K_rom = self.Phi.T @ (self.K_reduced @ self.Phi)
        
        # --- 6. EXACT STRESS MODES GENERATION ---
        num_modes = self.Phi.shape[1]
        
        # OVERWRITE Phi_stress with exact dimensions: [(Nodes*6) x RetainedModes]
        self.Phi_stress = np.zeros((num_nodes * 6, num_modes)) 
        
        msg = "Generating Exact Stress Modes...\n"
        current_text = self.TrainningTimeTextArea.toPlainText()
        self.TrainningTimeTextArea.setText(msg + current_text)
        QApplication.processEvents()
        
        for m in range(num_modes):
            U_mode_full = np.zeros(num_total_dof)
            U_mode_full[free_dofs] = self.Phi[:, m]
            
            Sigma_mode = self.PostProcess_Stress_3Dsparse(
                self.B_global, self.D_mat, U_mode_full, 
                self.node_coords, self.element_connectivity, self.element_type
            )
            
            # Flatten to 1D vector and store
            self.Phi_stress[:, m] = Sigma_mode.flatten()
            
        # --- 7. SUCCESS MESSAGE ---
        success_msg = f"Training Complete!\nModes retained: {n_modes_disp}\nEnergy: {cum_energy_disp[n_modes_disp-1]:.4f}%"
        print(success_msg)
        
        # Assuming standard PyQt6 message box
        QMessageBox.information(None, "ROM Success", success_msg)

    # =====================================
    # TAB 7 : ROM Acuracy Check and Save
    # =========================================================================   
    def CheckAccuracyButtonPushed(self):
        # 1. Setup Validation Parameters
        # Convert slider % (0-100) to physical length
        x_pos = (self.ValidationLoadPositionSlider.value() / 100.0) * self.geometry['Lx'] 
        P_val = float(self.ValidationLoadNEditField.text())
        stress_type = self.TypeofStressesDropDown_2.currentText()
        
        self.AccuracyResultsTextArea.setText("*** Starting Accuracy Check ***\n")
        QApplication.processEvents() # Force UI to update text immediately
        
        # Generate Force Vector (Shared for both methods)
        temp_loads = self.define_loads_at_pos(x_pos, P_val) 
        F_temp = np.zeros(self.F_global.shape)
        
        for j in range(len(temp_loads['point_nodes'])):
            node_id = temp_loads['point_nodes'][j]
            force_vec = temp_loads['point_load_values'][:, j]
            dof_indices = node_id * 3 + np.array([0, 1, 2])
            F_temp[dof_indices] += force_vec
            
        free_dofs = self.bc_info['free_dofs_indices']
        F_red = F_temp[free_dofs]
    
        # =========================================================
        # --- 2. FEM CALCULATION (FULL SOLVER) ---
        # =========================================================
        t0 = time.perf_counter()
        U_free_fem = spla.spsolve(self.K_reduced.tocsr(), F_red)
        time_fem_solve = time.perf_counter() - t0
    
        num_dof = self.K_global.shape[0]
        U_full_fem = np.zeros(num_dof)
        U_full_fem[free_dofs] = U_free_fem
    
        t0 = time.perf_counter()
        Sigma_fem = self.PostProcess_Stress_3Dsparse(
            self.B_global, self.D_mat, U_full_fem, self.node_coords, 
            self.element_connectivity, self.element_type
        )
        time_fem_stress = time.perf_counter() - t0
        
        # Plot FEM Results on Left PyVista Canvas
        self.plot_stresses(Sigma_fem, stress_type, self.UIAxes9, U_full_fem, self.scale_factor)
        
        # =========================================================
        # --- 3. ROM CALCULATION (PURE MATRIX RECONSTRUCTION) ---
        # =========================================================
        t0 = time.perf_counter()
        # A. Solve for Displacement Modal Amplitudes (alpha)
        F_rom = self.Phi.T @ F_red
        # np.linalg.solve is extremely fast for small, dense ROM matrices
        alpha = np.linalg.solve(self.K_rom, F_rom) 
        
        # B. Reconstruct Full Displacement
        U_free_rom_proj = self.Phi @ alpha
        time_rom_solve = time.perf_counter() - t0
    
        self.U_full_rom = np.zeros(num_dof)
        self.U_full_rom[free_dofs] = U_free_rom_proj
    
        # ---------------------------------------------------------
        # C. FAST STRESS ROM RECONSTRUCTION (Using Phi_stress)
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        # 1. Multiply the Exact Stress Modes by the modal amplitudes
        Sigma_rom_flat = self.Phi_stress @ alpha
        
        # 2. Reshape back to [Nodes x 6] (Order 'C' is standard C-like row-major)
        num_nodes = self.node_coords.shape[0]
        Sigma_rom = Sigma_rom_flat.reshape((num_nodes, 6))
        time_rom_stress = time.perf_counter() - t0
        
        # Plot ROM Results on Right PyVista Canvas
        self.plot_stresses(Sigma_rom, stress_type, self.UIAxes10, self.U_full_rom, self.scale_factor)
       
        # =========================================================
        # --- 4. ACCURACY & SPEED METRICS ---
        # =========================================================
        # Prevent division by zero with max(..., 1e-12)
        norm_U_fem = np.linalg.norm(U_free_fem)
        rel_error_U = (np.linalg.norm(U_free_fem - U_free_rom_proj) / max(norm_U_fem, 1e-12)) * 100.0
        
        # L2 Relative Error for Stress Component (Sigma_xx)
        norm_S_fem = np.linalg.norm(Sigma_fem[:, 0])
        rel_error_Stress = (np.linalg.norm(Sigma_fem[:, 0] - Sigma_rom[:, 0]) / max(norm_S_fem, 1e-12)) * 100.0
        
        speed_up1 = time_fem_solve / max(time_rom_solve, 1e-9)                
        speed_up2 = time_fem_stress / max(time_rom_stress, 1e-9)               
    
        # --- 5. Display Results ---
        results_text = (
            "--- DISPLACEMENT COMPARISON ---\n"
            f"FEM Max U: {np.max(np.abs(U_full_fem)):.4e} m\n"
            f"ROM Max U: {np.max(np.abs(self.U_full_rom)):.4e} m\n"
            f"Relative Error: {rel_error_U:.4f} %\n\n"
            "--- PERFORMANCE ---\n"
            f"FEM Solve: {time_fem_solve:.4f} s\n"
            f"ROM Solve: {time_rom_solve:.4f} s\n"
            f"ROM is {speed_up1:.1f}x Faster\n\n"
            f"FEM Stress Reconstruction: {time_fem_stress:.4f} s\n"
            f"ROM Stress Reconstruction: {time_rom_stress:.4f} s\n"
            f"ROM Stress is {speed_up2:.1f}x Faster\n\n"
            "--- STRESS CHECK (\u03c3_xx) ---\n"
            f"FEM Max Stress: {np.max(np.abs(Sigma_fem[:,0]))/1e6:.2f} MPa\n"
            f"ROM Max Stress: {np.max(np.abs(Sigma_rom[:,0]))/1e6:.2f} MPa\n"
            f"Relative Error: {rel_error_Stress:.4f} %"
        )
        self.AccuracyResultsTextArea.setText(results_text)

    def SaveButtonPushed(self):
        # --- 1. VERIFICATION ---
        if not hasattr(self, 'Phi') or not hasattr(self, 'Phi_stress') or not hasattr(self, 'K_rom'):
            QMessageBox.critical(None, "Save Error", "No ROM data found! Please train the ROM first.")
            return
        
        # --- 2. USER LABELING (FIXED WITH INSTRUCTIONS) ---
        default_name = f"Cantilever_ROM_{datetime.now().strftime('%H%M%S')}"
        
        # We explicitly warn the user to use the correct keywords!
        instruction_text = (
            "CRITICAL FOR LIVE TWIN:\n"
            "The name MUST contain one of these keywords based on your current setup:\n"
            "- 'Simply' (for Simply Supported)\n"
            "- 'Cant' (for Cantilever)\n"
            "- 'Fix' (for Fixed-Fixed)\n\n"
            "Enter a label for this ROM state:"
        )
        
        rom_label, ok = QInputDialog.getText(None, "Save ROM Data for Digital Twin", 
                                             instruction_text, text=default_name)
        
        if not ok or not rom_label:
            return # User clicked Cancel or entered an empty string
            
        # --- 3. PACKAGE THE ROM STRUCT ---
        New_ROM = {
            'Label': rom_label,
            'Phi': self.Phi,
            'Phi_stress': self.Phi_stress,
            'K_rom': self.K_rom,
            'bc_info': self.bc_info,
            'NumNodes': self.node_coords.shape[0],
            'ElementType': self.element_type,
            'Nodes':self.node_coords
        }
        
        # --- 4. SAVE TO CENTRAL BANK ---
        save_filename = 'DigitalTwin_ROM_Bank.pkl'
        
        if os.path.exists(save_filename):
            with open(save_filename, 'rb') as f:
                ROM_Bank = pickle.load(f)
            ROM_Bank.append(New_ROM)
        else:
            ROM_Bank = [New_ROM]
            
        with open(save_filename, 'wb') as f:
            pickle.dump(ROM_Bank, f)
            
        # --- 5. THE FIX: UPDATE LIVE RAM CACHE INSTANTLY ---
        # If the Live Twin has already loaded the bank into memory, we must update it!
        if hasattr(self, 'DT_Bank'):
            self.DT_Bank = ROM_Bank
            
        # --- 6. SUCCESS CONFIRMATION ---
        msg = f"ROM '{rom_label}' successfully saved!\n\nTotal Models in Bank: {len(ROM_Bank)}"
        QMessageBox.information(None, "Save Successful", msg)

    def ClearBankButtonPushed(self):
        
        save_filename = 'DigitalTwin_ROM_Bank.pkl'
        
        # Ask for confirmation before deleting data
        reply = QMessageBox.question(self, 'Clear ROM Bank', 
                                     'Are you sure you want to delete all saved ROMs? This cannot be undone.',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(save_filename):
                os.remove(save_filename)
                QMessageBox.information(self, "Success", "ROM Bank has been cleared.")
            else:
                QMessageBox.information(self, "Notice", "ROM Bank is already empty.")    
    # ==========================================
    # TAB 8: LIVE DIGITAL TWIN CALLBACKS
    # ==========================================

    def StartLiveTwinButtonValueChanged(self):
        # Initialize flag if it doesn't exist yet
        if not hasattr(self, 'isLive'):
            self.isLive = False
            
        # Toggle the state
        self.isLive = not self.isLive 
        
        if self.isLive:
            self.StartLiveTwinButton.setText('Live Twin: ON')
            # Turn Green
            self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #66ff66; color: black; padding: 10px;") 
            
            # Run an immediate calculation
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()
            else:
                print("Warning: run_DigitalTwin_Update not found yet!")
        else:
            self.StartLiveTwinButton.setText('Start Live Twin')
            # Back to default gray
            self.StartLiveTwinButton.setStyleSheet("font-weight: bold; background-color: #e0e0e0; color: black; padding: 10px;")

    def LoadPositionSlider_2ValueChanged(self, value):
        # PyQt6 passes the new integer value directly when dragging
        if getattr(self, 'isLive', False):
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()

    def LoadValueNSliderValueChanged(self, value):
        # Sync the text field to match the slider dynamically
        if hasattr(self, 'LoadNEditField'):
            self.LoadNEditField.setText(str(value))
            
        if getattr(self, 'isLive', False):
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()

    def LoadNEditFieldValueChanged(self):
        # Sync the slider to match the typed text
        try:
            val = float(self.LoadNEditField.text())
            if hasattr(self, 'LoadValueNSlider'):
                # Block signals temporarily to prevent an infinite loop of updates
                self.LoadValueNSlider.blockSignals(True)
                self.LoadValueNSlider.setValue(int(val))
                self.LoadValueNSlider.blockSignals(False)
        except ValueError:
            pass # Ignore invalid text input (like letters)
            
        if getattr(self, 'isLive', False):
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()

    def StainGauge1SwitchValueChanged(self, state):
        if getattr(self, 'isLive', False):
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()

    def StainGauge2SwitchValueChanged(self, state):
        if getattr(self, 'isLive', False):
            if hasattr(self, 'run_DigitalTwin_Update'):
                self.run_DigitalTwin_Update()

   ####################################################
    def run_DigitalTwin_Update(self):
        # --- 1. MEMORY CACHING ---
        if not hasattr(self, 'DT_Bank'):
            if os.path.exists('DigitalTwin_ROM_Bank.pkl'):
                with open('DigitalTwin_ROM_Bank.pkl', 'rb') as f: self.DT_Bank = pickle.load(f)
            else:
                if hasattr(self, 'UIAxes5_2'):
                    self.UIAxes5_2.add_text("ERROR: ROM Bank Not Found!", name="err", font_size=14, color='red')
                    self.UIAxes5_2.update()
                return

        # --- 2. CLASSIFY BOUNDARY CONDITION ---
        def is_active(widget):
            if hasattr(widget, 'isChecked'): return widget.isChecked()
            return False

        sg1_active = is_active(self.StainGauge1Switch)
        sg2_active = is_active(self.StainGauge2Switch)
        
        if sg1_active and sg2_active: target_keyword = 'Fix'     
        elif sg1_active or sg2_active: target_keyword = 'Cant'    
        else: target_keyword = 'Simply'  
            
        Active_ROM = None
        for rom in self.DT_Bank:
            if target_keyword.lower() in rom['Label'].lower():
                Active_ROM = rom; break
                
        if Active_ROM is None:
            if hasattr(self, 'UIAxes5_2'):
                self.UIAxes5_2.add_text(f"ERROR: No ROM found for '{target_keyword}'", name="err", font_size=12, color='red')
                self.UIAxes5_2.update()
            return
            
        # --- 3. READ UI & BUILD GLOBAL FORCE ---
        load_pos = (self.LoadPositionSlider_2.value() / 100.0) * self.geometry['Lx']
        load_val = float(self.LoadValueNSlider.value()) * (-1000.0)
        
        if hasattr(self, 'define_loads_at_pos'): temp_loads = self.define_loads_at_pos(load_pos, load_val) 
        else: return
            
        num_nodes = Active_ROM['NumNodes']
        num_total_dof = num_nodes * 3
        F_temp = np.zeros(num_total_dof)
        
        for j in range(len(temp_loads['point_nodes'])):
            node_id = temp_loads['point_nodes'][j]; force_vec = temp_loads['point_load_values'][:, j]
            dof_indices = node_id * 3 + np.array([0, 1, 2]); F_temp[dof_indices] += force_vec
            
        active_free_dofs = Active_ROM['bc_info']['free_dofs_indices']
        F_red = F_temp[active_free_dofs]
        
        # --- 4. FAST ROM CALCULATION ---
        F_rom = Active_ROM['Phi'].T @ F_red
        alpha = np.linalg.solve(Active_ROM['K_rom'], F_rom) 
        U_free_rom_proj = Active_ROM['Phi'] @ alpha

        self.U_full_rom = np.zeros(num_total_dof)
        self.U_full_rom[active_free_dofs] = U_free_rom_proj
        Sigma_rom_flat = Active_ROM['Phi_stress'] @ alpha
        Sigma_rom = Sigma_rom_flat.reshape((num_nodes, 6))
        
        # --- 5. UI EXTRACTION & SMART SCALING ---
        stress_typeROM = self.TypeofStressesDropDown_3.currentText()
        failure_mode = self.MethodDropDown_2.currentText()
        display_choice = self.DisplayChoiceDropDown_2.currentText()
        
        scale_text = self.ScaleFactorEditField_2.text().strip().lower()
        if scale_text == 'auto':
            max_u = np.max(np.abs(self.U_full_rom))
            scale_factor2 = (self.geometry['Lx'] * 0.15) / max(max_u, 1e-9)
        else:
            try: scale_factor2 = float(scale_text)
            except ValueError: scale_factor2 = 500.0 
            
        try: yield_strength = float(self.YieldStrengthMpaEditField.text()) if hasattr(self, 'YieldStrengthMpaEditField') else 250.0
        except ValueError: yield_strength = 250.0 

        # --- 6. 2D PLOTTING LOGIC (FIXED) ---
        if hasattr(self, 'dt_figure'):
            self.dt_figure.clear()
            ax_defl = self.dt_figure.add_subplot(131)
            ax_bend = self.dt_figure.add_subplot(132)
            ax_shear = self.dt_figure.add_subplot(133)

            # FIX: Get coordinate array from ROM dictionary, not the integer count
            node_coords = Active_ROM['Nodes'] 
            y_coords = node_coords[:, 1]
            y_top, y_bot = np.max(y_coords), np.min(y_coords)

            # Sample 50 points along X (Span)
            x_line = np.linspace(0, self.geometry['Lx'], 50)
            v_line, s_top, s_bot, s_mid = [], [], [], []

            for x in x_line:
                # Find closest nodes at Top, Bottom, and Middle fibers
                # Horizontal Stress (Bending)
                idx_top = np.argmin(np.sqrt((node_coords[:, 0] - x)**2 + (node_coords[:, 1] - y_top)**2))
                idx_bot = np.argmin(np.sqrt((node_coords[:, 0] - x)**2 + (node_coords[:, 1] - y_bot)**2))
                # Shear Stress (Probe at Middle height)
                idx_mid = np.argmin(np.sqrt((node_coords[:, 0] - x)**2 + (node_coords[:, 1] - 0)**2))
                
                v_line.append(self.U_full_rom[idx_top * 3 + 1]) # Vertical Deflection (Y-DOF)
                s_top.append(Sigma_rom[idx_top, 0])             # Sigma_xx Top
                s_bot.append(Sigma_rom[idx_bot, 0])             # Sigma_xx Bottom
                s_mid.append(Sigma_rom[idx_mid, 3])             # Tau_xy Mid (Shear)

            # 1. Deflection Plot
            ax_defl.plot(x_line, v_line, color='blue', linewidth=2)
            ax_defl.set_title("Deflection (mm)"); ax_defl.set_xlabel("Span (mm)"); ax_defl.grid(True)

            # 2. Bending Stress Plot (Top vs Bottom)
            ax_bend.plot(x_line, s_top, 'r-', label='Top (Comp/Tens)')
            ax_bend.plot(x_line, s_bot, 'g-', label='Bottom (Tens/Comp)')
            ax_bend.set_title("Bending Stress (MPa)"); ax_bend.legend(); ax_bend.grid(True)

            # 3. Shear Stress Plot (Construction Line)
            ax_shear.plot(x_line, s_mid, 'k-', label='Neutral Axis Shear')
            ax_shear.set_title("Shear Stress (MPa)"); ax_shear.grid(True)

            self.dt_figure.tight_layout()
            self.dt_canvas.draw()
            
        # --- 7. 3D PLOTTING ---
        self.plot_stresses(Sigma_rom, stress_typeROM, self.UIAxes5_2, self.U_full_rom, scale_factor2)
        self.UIAxes5_2.add_text(f"Live Twin Active: {Active_ROM['Label']}", name="live_lbl", position='upper_right', font_size=10, color='red')
        self.UIAxes5_2.update()
        
        self.plot_FS(failure_mode, yield_strength, self.UIAxes6_2, Sigma_rom, self.U_full_rom, scale_factor2, display_type=display_choice)
        #############################################################
        # 
        # 
        # #################################################################           

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DigitalTwin_Mechanical_Testing()
    window.show()
    sys.exit(app.exec())