# AGENTS

## Purpose
This repository is a Python-based digital twin and reduced-order modeling project for structural bending tests. The primary work happens in `Python/`, with legacy or supporting Matlab scripts in `Matlab/`.

## What AI agents should know
- The main codebase is in `Python/` and includes PyQt6 GUI applications, PyVista/Vtk visualizations, and FEM/ROM numerical code.
- The active application files are variants of `Dual ROM*.py` and `DigitalTwin Mechanical*.py`.
- Many Python filenames contain spaces; do not rename files unless the user explicitly asks.
- The repository also contains documentation artifacts under `Python/` such as `GUI_DOCUMENTATION.md`, `ENHANCEMENT_SUMMARY.md`, and `COMPLETION_REPORT.md`.

## Dependencies and environment
- The project depends on Python packages: `PyQt6`, `pyvista`, `pyvistaqt`, `vtk`, `numpy`, `scipy`, `matplotlib`, `serial`, and related scientific/GUI libraries.
- A local virtual environment exists at `Python/.venv/`; prefer that environment for Python execution if available.
- There is no explicit `requirements.txt` or `pyproject.toml` in the repository.

## Editing guidance
- Preserve existing UI behavior and numerical logic unless the user requests refactoring or fixes.
- Prefer small, targeted changes in the current file under active development.
- Avoid modifying `.venv/`, binary data files (`*.pkl`), `__pycache__/`, and generated artifacts.
- Do not add broad packaging or build system changes unless the user asks for project setup or dependency management.

## Useful references
- `README.md` — project overview
- `Python/GUI_DOCUMENTATION.md` — GUI architecture and method reference
- `Python/ENHANCEMENT_SUMMARY.md` — enhancement notes and UI polish
- `Python/GUI_QUICK_REFERENCE.md` — quick guidance for GUI behavior
- `Python/COMPLETION_REPORT.md` — project completion summary
- `Python/VISUAL_COMPARISON.md` — before/after comparisons

## When asked for new features
- Clarify whether the requested work should be applied to the GUI app, the numerical ROM/FEM core, or a Matlab helper script.
- If adding new functionality, keep the solution isolated to the relevant Python module and do not reorganize the whole repository.
