# Quick Reference - GUI Changes & Functions

## **NEW STYLING FUNCTION**
```python
ProfessionalTheme.create_button_style(bg_color, text_color="white", hover_color=None, width=None)
```
Creates professional buttons with auto-generated hover effects. Use anywhere instead of hardcoding QPushButton stylesheets.

---

## **COLOR CONSTANTS** (Updated)

```python
# Primary Colors
PRIMARY_BLUE = "#1e3a5f"      # Headers, main accent
ACCENT_BLUE = "#2980b9"       # Buttons, interactive
BRIGHT_BLUE = "#3498db"       # Highlights

# Status Colors
SUCCESS_GREEN = "#27ae60"      # Safe, ready
HOVER_GREEN = "#229954"        # Green hover state
ERROR_RED = "#c0392b"          # Critical failure
WARNING_ORANGE = "#e67e22"     # Warnings
INFO_PURPLE = "#8e44ad"        # Information

# UI Colors
TEXT_DARK = "#1a1a1a"          # Body text
TEXT_GRAY = "#7f8c8d"          # Secondary text
BORDER_LIGHT = "#d5dbdb"       # Subtle borders
CONSOLE_BG = "#1e1e1e"         # Terminal style
CONSOLE_TEXT = "#00ff00"       # Terminal text
```

---

## **GUI COMPONENTS UPDATED**

### Buttons
| Component | Change | Benefit |
|-----------|--------|---------|
| 🔌 Connect | Emoji + factory styling | Better recognition |
| ▶ LIVE | Play/stop icons | Universal symbols |
| ⏹ STOP | Red background | Clear stop state |
| 🎥 Reset View | Better labeled | More discoverable |
| 📊 Tare | Emoji indicators | Intuitive actions |

### Readouts
| Element | Before | After |
|---------|--------|-------|
| Font size | 10pt | 11pt |
| Width | 75px | 80px |
| Color | Yellow | Green (#00ff00) |
| Font | Courier | Courier New (monospace) |
| Border | 1px solid | 1px solid + 4px radius |

### Status Indicators
| State | Before | After |
|-------|--------|-------|
| Disconnected | Generic text | ⚪ Disconnected |
| Safe | Text only | ✓ FS: X.XX \| SAFE |
| Failure | "!!! FAILURE !!!" | ⚠️ FAILURE RISK ⚠️ |

### Combos
| Feature | Before | After |
|---------|--------|-------|
| Border | None | 1px BORDER_LIGHT |
| Radius | 0px | 4px |
| Padding | Default | 5px |
| Background | Default | White |

---

## **LIVE WINDOW METHODS - QUICK LOOKUP**

| Method | Trigger | Purpose |
|--------|---------|---------|
| `build_ui()` | Init | Build all GUI components |
| `attempt_connect()` | Connect button | Connect to hardware |
| `toggle_live_feed()` | LIVE button | Start/stop sensor reading |
| `process_live_data()` | Hardware signal | Update all displays, compute FS |
| `update_visuals_only()` | Combo change | Refresh graphics |
| `_update_graphics()` | Data ready | Render 3D/2D/plots |
| `get_plot_scalars()` | Graphics update | Determine colormap/values |
| `render_2d_orthographic()` | 3D update | Refresh 2D views |
| `render_line_plots()` | Any update | Refresh line charts |
| `on_section_change()` | Slider move | Update section cut |
| `reset_camera_view()` | Reset button | Reset all camera angles |
| `closeEvent()` | Window close | Clean shutdown |

---

## **STYLING CODE PATTERNS**

### Old Pattern (❌ Avoid)
```python
self.btn_connect.setStyleSheet(f"QPushButton {{ background-color: {ProfessionalTheme.ACCENT_BLUE}; color: white; font-weight: bold; padding: 5px; border-radius: 4px; }}")
```

### New Pattern (✅ Use)
```python
self.btn_connect.setStyleSheet(ProfessionalTheme.create_button_style(
    ProfessionalTheme.ACCENT_BLUE, 
    width=110
))
```

**Benefits:** Shorter, consistent, auto-hover effects

---

## **COMMON CUSTOMIZATIONS**

### Make a button with custom hover
```python
button.setStyleSheet(ProfessionalTheme.create_button_style(
    bg_color="#e74c3c",           # Error red
    hover_color="#c0392b",        # Darker red
    text_color="white",
    width=120
))
```

### Style a combo box
```python
combo.setStyleSheet(f"""
    border: 1px solid {ProfessionalTheme.BORDER_LIGHT};
    border-radius: 4px;
    padding: 5px;
    background: white;
""")
```

### Create a readout field
```python
readout = QLineEdit("0.0")
readout.setReadOnly(True)
readout.setStyleSheet(f"""
    background: {ProfessionalTheme.CONSOLE_BG};
    color: #00ff00;
    font-weight: bold;
    font-size: 11pt;
    border: 1px solid {ProfessionalTheme.BORDER_COLOR};
    border-radius: 4px;
    padding: 5px;
    font-family: 'Courier New';
""")
```

---

## **STATUS DISPLAY CODES**

### Safe Status
```python
self.lbl_fs_status.setText("✓ FS: 2.34 | SAFE")
self.lbl_fs_status.setStyleSheet(f"""
    font-size: 12pt;
    font-weight: bold;
    background: {ProfessionalTheme.SUCCESS_GREEN};
    color: white;
    padding: 10px;
    border-radius: 6px;
    border: 2px solid {ProfessionalTheme.HOVER_GREEN};
""")
```

### Failure Status
```python
self.lbl_fs_status.setText("⚠️ FAILURE RISK ⚠️")
self.lbl_fs_status.setStyleSheet(f"""
    font-size: 12pt;
    font-weight: bold;
    background: {ProfessionalTheme.ERROR_RED};
    color: white;
    padding: 10px;
    border-radius: 6px;
    border: 2px solid #8B0000;
""")
```

---

## **DOCUMENTATION FILES**

| File | Purpose |
|------|---------|
| `GUI_DOCUMENTATION.md` | Comprehensive API reference |
| `ENHANCEMENT_SUMMARY.md` | All changes explained |
| `VISUAL_COMPARISON.md` | Before/after comparison |
| `GUI_QUICK_REFERENCE.md` | This file - quick lookup |

---

## **TESTING CHECKLIST**

Before deployment, verify:
- [ ] All buttons render with new styling
- [ ] Hover effects work smoothly
- [ ] Status colors update correctly
- [ ] Hardware connection working
- [ ] Real-time data displays updating
- [ ] Graphics rendering properly
- [ ] No console errors
- [ ] Window resizing works
- [ ] All combos responding to selection
- [ ] Icons displaying correctly

---

## **TROUBLESHOOTING**

| Issue | Solution |
|-------|----------|
| Buttons look wrong | Check color hex codes, verify font name exists |
| Text hard to read | Increase font size, improve contrast ratio |
| Spacing looks off | Adjust padding/margins in stylesheet |
| Hover not working | Ensure `:hover` pseudo-selector in CSS |
| Colors not loading | Check if ProfessionalTheme imported before use |

---

## **FILE LOCATIONS**

Main file modified:
```
c:\SP Aung\FEMstucture DT\DT for Structure Bending Test\Python\
DigitalTwin Mechanical Bending Testing 8.py
```

Documentation files created:
```
c:\SP Aung\FEMstucture DT\DT for Structure Bending Test\Python\
├── GUI_DOCUMENTATION.md
├── ENHANCEMENT_SUMMARY.md
├── VISUAL_COMPARISON.md
└── GUI_QUICK_REFERENCE.md
```

---

## **QUICK START**

1. **Run the application:**
   ```bash
   python "DigitalTwin Mechanical Bending Testing 8.py"
   ```

2. **Connect to hardware:**
   - Click 🔌 Connect button
   - Verify "⚪ Disconnected" changes status

3. **Start monitoring:**
   - Click ▶ LIVE button
   - Button changes to "⏹ STOP" with red background
   - Real-time readouts update in green

4. **View results:**
   - Check ✓ FS status indicator (green = safe, red = failure)
   - Monitor strain predictions (P1, P2, P3)
   - Watch 3D/2D graphics update

5. **Stop monitoring:**
   - Click ⏹ STOP button
   - Button reverts to ▶ LIVE with green background

---

## **KEYBOARD SHORTCUTS**

| Key | Action |
|-----|--------|
| TAB | Move between controls |
| ENTER | Press focused button |
| SPACE | Toggle checkboxes/buttons |
| Arrow Keys | Adjust sliders/combos |
| ESC | Close window |

---

## **CONTACT & SUPPORT**

For GUI-related questions or enhancements:
1. Check GUI_DOCUMENTATION.md
2. Review ENHANCEMENT_SUMMARY.md
3. Consult VISUAL_COMPARISON.md
4. Check console output for errors

---

**Quick Reference Version:** 1.0  
**Last Updated:** May 2, 2026  
**Status:** ✅ Ready for Use
