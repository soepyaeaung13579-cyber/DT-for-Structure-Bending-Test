# Dual-ROM Framework for 3D Structural Bending Analysis

This repository contains the source code for the numerical case studies and the GUI-based framework used to evaluate Reduced-Order Modeling (ROM) strategies for 3D structural beam bending.

The repository includes two separate interactive Python applications:

1. **Dual ROM Framework (Method II & Method III)**:
   - File: `Dual ROM (Selected Snapshot Method(Mehtod II +Method III) .py`
   - Features the novel Dual ROM approach which pre-computes per-mode nodal stress vectors during offline training. This allows online stress recovery to be reduced to a single matrix-vector product, drastically increasing stress recovery speed.
   - Implements advanced snapshot strategies like Boundary-Clustered Snapshot Sampling (BCSS).

2. **Traditional Displacement ROM (Method I)**:
   - File: `Traditional Displacement  ROM.py`
   - The conventional baseline ROM approach. It projects only the displacement field and recomputes stresses online via the full strain-displacement operator followed by Gauss-to-node extrapolation.
   - Implements Uniform Snapshot Sampling (USS).

Both applications are built with PyQt6 for the interactive user interface and PyVista/VTK for real-time 3D rendering of the finite element models, loads, boundaries, and resulting stress/displacement fields.

## Features

- **Element types**: Hexa8, Hexa20, Tet4, Tet10
- **Boundary conditions**: Cantilever, Fixed-Fixed, Simply Supported
- **Snapshot strategies**: Uniform (USS) and Boundary-Clustered (BCSS)
- **Stress recovery**: Gauss-to-node extrapolation with element-specific operators
- **Interactive GUI**: Build models, apply loads, train the ROM, and visualize real-time 3D stress contours and displacement fields.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/<your-username>/Dual-ROM-Framework.git
cd Dual-ROM-Framework

# Install dependencies (We recommend using a virtual environment)
pip install -r requirements.txt

# Run the Dual ROM application
python "Dual ROM (Selected Snapshot Method(Mehtod II +Method III) .py"

# Or run the Traditional ROM baseline
python "Traditional Displacement  ROM.py"
```

## Repository Structure

```
.
├── Dual ROM (Selected Snapshot Method(Mehtod II +Method III) .py
├── Traditional Displacement  ROM.py
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
├── .gitignore
└── README.md                    # This file
```

## Citation

If you use this code in your research, please cite:

```bibtex
@software{dual_rom_framework,
  title   = {Dual-ROM Framework for 3D Structural Bending Analysis},
  author  = {CSE Lab},
  year    = {2026},
  url     = {https://github.com/<your-username>/Dual-ROM-Framework}
}
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
