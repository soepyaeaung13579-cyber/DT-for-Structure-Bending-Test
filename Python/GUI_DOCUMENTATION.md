# Digital Twin GUI Documentation
## LiveDigitalTwinWindow Class - GUI Methods Reference

### Overview
The `LiveDigitalTwinWindow` class (Module 3) provides a professional real-time digital twin monitoring interface with hardware integration, visualization controls, and safety status indicators. This document catalogs all GUI-related methods.

---

## **BUILD & INITIALIZATION METHODS**

### `__init__(sensor_manager, dt_bank, geometry, launcher)`
**Purpose:** Initialize the Live Digital Twin Window with all GUI components and background threading.

**Parameters:**
- `sensor_manager`: Hardware communication handler (SensorManager instance)
- `dt_bank`: Database of ROM models for different boundary conditions
- `geometry`: Dictionary containing beam dimensions {'Lx', 'Ly', 'Lz'}
- `launcher`: Reference to parent application launcher for inter-window communication

**GUI Setup:**
- Sets window title: "Module 3: Online Digital Twin Monitor"
- Geometry: 1450×950 pixels
- Initializes HardwareWorker thread for async sensor reading
- Connects data_ready signal to `process_live_data()` method

---

### `build_ui()`
**Purpose:** Construct the complete professional GUI layout using a 2-row grid system.

**Layout Structure:**

#### **ROW 0 - Analysis Dashboard**
1. **Header Widget** (Col 0, 1 row height)
   - Logo and application title
   - Subtitle: "Digital Twin Monitoring System"
   - Professional gradient background

2. **Live Predictions Panel** (Col 1)
   - Displays P1, P2, P3 strain predictions (microstrains)
   - FS (Factor of Safety) status indicator
   - Color-coded: Green (safe) / Red (failure risk)
   - Real-time update via `process_live_data()`

3. **Visualization Controls** (Col 2)
   - Primary Mode selector: "Failure" or "Stress"
   - Conditional option stacks based on mode selection
   - Failure mode: Display type (FS/Intensity) + Method (Von Mises/Principal/Shear)
   - Stress mode: Sigma component selector (Sigma_xx/yy/zz/Tau_xy/yz/zx)
   - Reset Camera button (🎥)
   - All combos styled with light borders and white background

#### **ROW 1 - Hardware Interface Panel**
- **Connection Controls:**
  - 🔌 Connect button (blue, connects/disconnects Arduino)
  - ▶ LIVE button (green when ready, red when active) - toggles live feed
  
- **Separator:** Vertical line dividing buttons from data displays

- **Real-Time Readouts (5 vertical clusters):**
  - LOAD (N) - Load cell force reading
  - SG-1 (uE) - Strain gauge 1
  - SG-2 (uE) - Strain gauge 2
  - SG-3 (uE) - Strain gauge 3
  - POS (mm) - Position/deflection reading
  
  Each readout displays in green-on-black console styling with monospace font

#### **MAIN CONTENT AREA**
**3D Graphics Tabs:**
1. **3D Isometric View** - Full 3D stress/failure visualization with live deformation
2. **2D Orthographic Views** - Three synchronized 2D views:
   - Top View (XY plane with selected layer)
   - Front View (XZ plane with deformed mesh)
   - Section View (YZ plane at adjustable X-position)

**Right Panel - Analysis Plots**
- Matplotlib figure with 3 subplots:
  1. Deflection profile along beam length (mm)
  2. Bending stress at top/bottom fiber surfaces (MPa)
  3. Shear stress at neutral axis (MPa)
- Live updates via `render_line_plots()` method

---

## **USER INTERACTION METHODS**

### `attempt_connect()`
**Triggered by:** 🔌 Connect button clicked
**Function:** Initiates hardware connection
**Behavior:**
- If calibration window exists: delegates to calibration window handler
- Otherwise: attempts direct Arduino connection via SensorManager
- Shows success/failure message box to user

---

### `toggle_live_feed(checked)`
**Triggered by:** ▶ LIVE button toggle
**Parameters:** `checked` - Boolean state of toggle

**ON (checked=True):**
- Changes button to: "⏹ STOP"
- Styling: Red background (error color) for visibility
- Starts HardwareWorker thread for async sensor reading
- `process_live_data()` called on signal reception

**OFF (checked=False):**
- Changes button back to: "▶ LIVE"
- Styling: Green background (success color)
- Gracefully stops HardwareWorker thread
- Halts real-time visualization updates

---

### `handle_thread_error(err_msg)`
**Triggered by:** HardwareWorker.error_occurred signal
**Parameters:** `err_msg` - Exception traceback message

**Function:** Safety handler for thread exceptions
- Prints error to console
- Automatically stops live feed (unchecks LIVE button)
- Prevents GUI freeze from hardware errors

---

### `switch_render_options(index)`
**Triggered by:** PrimaryModeCombo.currentIndexChanged signal
**Parameters:** `index` - 0 (Failure) or 1 (Stress)

**Function:** Switches between failure analysis and stress analysis control panels
- Shows appropriate combo boxes for selected mode
- Triggers visualization update

---

### `toggle_color_limits()`
**Triggered by:** AutoColorLimitSwitch checkbox (if implemented)
**Function:** Enables/disables manual color scale adjustment
- When auto: Uses min/max of current data
- When manual: Allows CMinEdit and CMaxEdit inputs

---

### `on_section_change(val)`
**Triggered by:** ViewSectionSlider.valueChanged signal
**Parameters:** `val` - Slider value (0-100)

**Function:** Updates 2D section view cut position
- Converts slider to physical X-coordinate: `pos_m = (val/100) * Lx`
- Updates label: "Section Cut (X): {pos_m:.2f} m"
- Re-renders 2D view if on Tab 1

---

### `reset_camera_view()`
**Triggered by:** 🎥 Reset View button clicked
**Function:** Resets all 3D/2D camera positions to standard orientations

**Camera Views Set:**
1. **3D View:** Isometric perspective with auto-scaled bounds
2. **Top View (XY):** Orthographic projection, selected layer
3. **Front View (XZ):** Orthographic projection, deformed mesh slice
4. **Section View (YZ):** Orthographic projection, X-position cut

---

## **DATA PROCESSING METHODS**

### `process_live_data(strains, force_n, p_mm)`
**Triggered by:** HardwareWorker.data_ready signal (every ~50ms)
**Parameters:**
- `strains`: [ε₁, ε₂, ε₃] microstrains from three gauges
- `force_n`: Applied load in Newtons
- `p_mm`: Position/displacement in mm

**Main Workflow:**

1. **Lock Rendering** - Set `_is_rendering = True` to prevent concurrent updates

2. **Update Input Displays** - Update real-time readout fields:
   ```
   in_Load.setText(f"{force_n:.1f}")
   in_S1/S2/S3.setText(f"{strains[i]:.1f}")
   in_Ultra.setText(f"{p_mm:.1f}")
   ```

3. **ROM Selection** - Auto-detect boundary condition based on strain distribution:
   - If outer strains > center strain → Fixed-Fixed
   - If center strain is max → Simply Supported
   - If one end strain >> others → Cantilever
   - Selects matching ROM from DT_Bank

4. **Inject Geometry** - Update offline studio with active ROM:
   - Node coordinates
   - Element type and connectivity
   - Boundary condition info

5. **Load Projection** - Convert sensor position to FEM load application:
   - Clamp position within beam length: `load_pos_m = max(0, min(p_mm/1000, Lx))`
   - Call `define_loads_at_pos(load_pos_m, force_n)`
   - Build reduced force vector F_red for free DOFs

6. **ROM Solution** - Solve reduced system:
   ```
   α = inv(K_rom) @ (Φᵀ @ F_red)
   U_full = Φ @ α
   Sigma = (Φ_stress @ α).reshape(num_nodes, 6)
   ```

7. **Prediction Extraction** - Find strain predictions at sensor locations:
   - Locate nodes near user-specified X positions (±2% tolerance)
   - Extract σ_xx from lowest Z-node at each position
   - Convert to micro-strain: `ε = σ/E × 10⁶`
   - Calculate error: `error% = |ε_predicted - ε_measured| / |ε_measured| × 100`

8. **Factor of Safety Calculation:**
   - Compute Von Mises stress: `σ_vm = √[σ_x² - σ_x·σ_y + σ_y² + 3τ_xy²]`
   - Calculate FS: `FS = σ_yield / max(σ_vm)`
   - Update `lbl_fs_status` with color coding

9. **Trigger Graphics Update** - Call `_update_graphics()` to refresh all views

**Error Handling:** Try-except wraps entire process; on exception:
- Stops hardware worker
- Unchecks LIVE button
- Prints traceback

---

### `update_visuals_only(*args)`
**Triggered by:** Combo box changes (PrimaryModeCombo, FailDisplayCombo, etc.)
**Function:** Refresh graphics without processing new hardware data

**Guard Conditions:**
- Returns if no data loaded (`current_U is None`)
- Returns if already rendering to prevent concurrent updates

---

### `_update_graphics()`
**Triggered by:** `process_live_data()` or `update_visuals_only()`
**Function:** Master graphics rendering orchestrator

**Logic Flow:**

1. **Extract visualization parameters:**
   - Scale factor (deformation magnification)
   - Yield strength (for FS calculation)
   - Color limits (auto or manual)

2. **Branch on Active Tab:**

   **If 3D View (Tab 0):**
   - If Stress mode: Call `offline_studio.plot_stresses()`
   - If Failure mode: Call `offline_studio.plot_FS()`
   - Add live label in red text
   - Update 3D renderer

   **If 2D Views (Tab 1):**
   - Call `render_2d_orthographic()` for synchronized updates

3. **Always Update Line Plots:**
   - Call `render_line_plots()` for bottom-right analysis graphs

---

### `get_plot_scalars()`
**Purpose:** Determine which scalar field to visualize based on mode selection
**Returns:** `(scalars_array, colormap_name, plot_label)`

**Logic:**
- **Stress Mode:** Return component from Sigma matrix (MPa)
  - Direct mapping: Sigma_xx→col 0, Sigma_yy→col 1, etc.
- **Failure Mode:** Compute factor of safety
  - Von Mises: `σ_vm = √[0.5·((σ_x-σ_y)² + (σ_y-σ_z)² + (σ_z-σ_x)² + 6(τ²))]`
  - Principal: Eigenvalue extraction from stress tensors
  - Factor of Safety: `FS = σ_yield / σ_equivalent`
  - If FailDisplay="Stress": Return stress field
  - If FailDisplay="FS": Return FS field (inverted colormap jet_r)

---

### `render_2d_orthographic(custom_clim=None)`
**Purpose:** Update three synchronized 2D orthographic views
**Parameters:** `custom_clim` - Optional [min, max] color limits

**Three Views Rendered:**

1. **Top View (XY):**
   - Slices mesh at selected Z-layer (Top/Bottom/Middle)
   - Creates Delaunay triangulation from 2D points
   - Projects scalars onto surface

2. **Front View (XZ):**
   - Slices deformed mesh at mid-Y position
   - Shows bending deformation in XZ plane
   - Uses user's deformation scale factor

3. **Section View (YZ):**
   - Vertical slice at X-position (from slider)
   - Shows section profile with stress distribution
   - Static undeformed geometry displayed

**Setup on First Call:**
- Initialize camera positions and parallel projection
- Set view angles (XY, XZ, YZ)
- Reset cameras

**Updates on Subsequent Calls:**
- Clear old scalar bars
- Update mesh geometry and colors
- Preserve camera positions

---

### `render_line_plots()`
**Purpose:** Update matplotlib plots on right panel
**Frequency:** Called every time graphics update

**Plot 1 - Deflection Profile:**
- X-axis: Beam length (m)
- Y-axis: Vertical deflection at top surface (mm)
- Computed by: `U[node_3+1] * 1000`

**Plot 2 - Bending Stress Profile:**
- Two lines: Top fiber (red), Bottom fiber (green)
- Y-axis: Normal stress σ_xx (MPa)
- Shows bending stress distribution

**Plot 3 - Shear Stress Profile:**
- Single line: Neutral axis shear (black)
- Y-axis: Shear stress τ_xy (MPa)
- Used for understanding failure modes

**Initialization (First Call):**
- Clear figure, create 3 subplots
- Set titles, labels, legends
- Tight layout

**Updates (Subsequent Calls):**
- Replace Y-data only (X unchanged)
- Relimit axes automatically
- Refresh canvas (draw_idle)

---

## **WINDOW LIFECYCLE METHODS**

### `closeEvent(event)`
**Triggered by:** User closes window or application exit
**Function:** Clean shutdown sequence

**Cleanup Operations:**
1. Stop hardware worker thread gracefully
2. Close all PyVista interactor windows:
   - UIAxes_3D
   - UIAxes_2D_Top/Front/Sec
3. Notify launcher that window is closed (set to None)
4. Accept close event

---

## **STYLING & THEMING**

### Professional Color Scheme (ProfessionalTheme class)
- **Primary:** `#1e3a5f` (dark blue for headers)
- **Accent:** `#2980b9` (bright blue for buttons)
- **Success:** `#27ae60` (green for safe status)
- **Error:** `#c0392b` (red for failures)
- **Console:** Black background with green text
- **Text:** Dark gray on light backgrounds

### Button Style Factory
```python
ProfessionalTheme.create_button_style(bg_color, text_color, hover_color, width)
```
Produces professional buttons with:
- Rounded corners (5px)
- Hover effects (auto-darkened)
- Pressed state (inset effect)
- Disabled state (grayed out)

---

## **KEYBOARD SHORTCUTS & CONTROLS**

| Control | Function |
|---------|----------|
| 🔌 Connect | Open hardware connection dialog |
| ▶ LIVE | Toggle real-time sensor streaming |
| 🎥 Reset View | Reset all camera angles |
| ViewSectionSlider | Adjust 2D section cut position |
| TopSliceCombo | Select XY plane layer |
| PrimaryModeCombo | Switch Failure/Stress visualization |

---

## **DATA FLOW DIAGRAM**

---

## **Performance: Solver & Online Reconstruction Speed-ups**

### Overview
Practical recommendations to accelerate reduced-order solves and online reconstruction during live operation of the Digital Twin.

### Solver speed-ups
- Precompute reduced operators (Φᵀ K Φ) and factorize offline (Cholesky/LU); reuse the factorization in the online loop.
- Cache decompositions and reuse across timesteps when boundary conditions and DOF ordering remain unchanged.
- Use iterative solvers with preconditioners for large reduced systems and exploit sparsity/symmetry using sparse linear-algebra libraries.
- Ensure NumPy is linked to a multi-threaded BLAS (OpenBLAS/MKL) or use optimized sparse solvers to improve throughput.
- Apply energy-based basis truncation and investigate hyper-reduction techniques (DEIM, GNAT) for nonlinear costs.

### Online reconstruction speed-ups
- Precompute mapping matrices for sensors and stress outputs (Φ_sensor, Φ_stress) so predictions compute as small dense multiplies: `predicted = Φ_sensor @ α`.
- Avoid full-field reconstruction `U_full = Φ @ α` if only sensor/readout values are required; evaluate outputs directly in reduced space.
- Preallocate arrays and reuse buffers to minimize allocation overhead on each update.
- Decouple physics solve frequency from GUI rendering frequency to reduce render-induced stalls.
- Vectorize and batch sensor evaluations to leverage BLAS; consider JIT (Numba) or GPU acceleration for dense projection kernels.

### Quick checklist for integration
- Profile the live update loop to find hotspots.  
- Cache reduced operator factorization as the first optimization.  
- Compute sensor outputs directly from modal coefficients as the second optimization.  
- Validate accuracy after any basis reduction or hyper-reduction step.


```
Hardware (Arduino)
    ↓
SensorManager (serial communication)
    ↓
HardwareWorker (background thread)
    ↓ (data_ready signal)
process_live_data()
    ├→ Update input displays
    ├→ Auto-detect ROM boundary condition
    ├→ Project load to FEM coordinates
    ├→ Solve ROM: α = inv(K_rom) @ Φᵀ @ F_red
    ├→ Extract predictions vs measurements
    ├→ Calculate Factor of Safety
    └→ _update_graphics()
          ├→ get_plot_scalars()
          ├→ _update_graphics() [3D or 2D branch]
          ├→ render_line_plots()
          └→ Update display labels
```

---

## **COMMON ISSUES & DEBUGGING**

### Issue: "CRITICAL: ROM missing Connectivity"
**Cause:** ROM model incomplete (saved without element connectivity)
**Fix:** Regenerate ROM in Module 1, ensure all fields populated before save

### Issue: Graphics frozen during live feed
**Cause:** `_is_rendering` lock preventing updates
**Fix:** Check hardware thread for errors; restart live feed

### Issue: Section view not updating
**Cause:** Wrong tab selected
**Fix:** Ensure Tab 1 (2D Views) is active for section slider to work

### Issue: Predictions far from measurements
**Cause:** Incorrect sensor location in code
**Fix:** Update `pre_s1_loc`, `pre_s2_loc`, `pre_s3_loc` text fields to match physical installation

---

## **INTEGRATION POINTS**

### Connects to OfflinePreparationStudio:
- `launcher.offline_studio.element_type`
- `launcher.offline_studio.element_connectivity`
- `launcher.offline_studio.define_loads_at_pos()`
- `launcher.offline_studio.plot_stresses()`
- `launcher.offline_studio.plot_FS()`
- `launcher.offline_studio.YieldStrengthMpaEditField`

### Receives from CalibrationWindow:
- Tared sensor offsets
- Calibration factors
- Hardware connection status

---

**Document Version:** 1.0  
**Last Updated:** May 2026  
**Compatible with:** Python 3.10+, PyQt6, PyVista
