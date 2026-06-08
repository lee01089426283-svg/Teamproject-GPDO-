# 🔬 Silicon Photonics Wafer Analyzer

> An automated analysis pipeline for parsing, fitting, and visualizing XML measurement data from semiconductor wafer optical devices (GPDO / MZM).

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Device](https://img.shields.io/badge/device-GPDO%20%7C%20LMZC%20%7C%20LMZO-orange)

---

## 📖 1. About The Project

In silicon photonics fabrication, a single wafer contains dozens of optical device dies, each producing a separate XML measurement file. Manually opening these files, plotting graphs, and extracting parameters is time-consuming and error-prone.

This project fully automates the entire workflow — from parsing to fitting, visualization, and CSV export — for two types of optical devices: **GPDO (Germanium Photodetector)** and **MZM (Mach-Zehnder Modulator)**.

A key feature is the automatic detection of measurement data quality issues (e.g., probe contact failures, noise-level currents), which are explicitly flagged in the output, allowing users to **clearly distinguish between code errors and measurement errors**.

### ✨ Key Features

* 📂 **Auto Data Discovery** — Automatically detects project, wafer, and timestamp folder structure under `data/`
* 📈 **Per-Die 6-Panel Analysis Graphs** — Auto-generates PNG plots for GPDO (IV fitting, responsivity) and MZM (MZI fitting, extinction ratio, FSR)
* 🗺️ **Wafer-Level Heatmaps** — Visualizes parameter distribution across die positions on the wafer
* 🚨 **Measurement Error Detection** — Detects noise-level current and missing diode characteristics; overlays error box on output plots
* 📊 **Automatic CSV Export** — Saves per-wafer CSVs and a unified `Total_Result.csv`

### 🛠 Built With

* `Python 3.10+`
* `NumPy` / `SciPy` — Numerical computation and curve fitting (`curve_fit`)
* `Matplotlib` — 6-panel plots and heatmap visualization (Agg backend, no GUI)
* `Pandas` — CSV generation and aggregation
* `xml.etree.ElementTree` — XML measurement file parsing

---

## 📸 2. Screenshots

### GPDO — Per-Die 6-Panel Analysis Graph
> Reference Spectrum · Dark/Light IV · Photo Current · Spectrum · Responsivity R(λ)

![GPDO 6-panel](res/png/GPDO/HY202103/D08/20190526_082853/HY202103_D08_(0,2)_LION1_DCM_GPDO.png)

---

### MZM — Per-Die 6-Panel Analysis Graph
> Transmission Spectra · Ref Fitting · Flat Spectra · MZI Fitting · IV Measurement · IV Analysis

![MZM 6-panel](res/png/MZM/HY202103/D08/20190526_082853/HY202103_D08_(0,2)_LION1_DCM_LMZO.png)

---

### Measurement Data Error Detection — Error Overlay
> When IV data is abnormal (e.g., probe contact failure), an error box is overlaid on top of the 6 analysis panels.

![Error Overlay](res/png/MZM/HY202103/D23/20190531_072042/HY202103_D23_(0,0)_LION1_DCM_LMZO.png)

---

### Wafer Heatmaps — GPDO Responsivity / MZM Extinction Ratio

| GPDO — Responsivity [A/W] | MZM — Extinction Ratio [dB] |
|:---:|:---:|
| ![GPDO Heatmap](res/png/GPDO/HY202103/D08/20190526_082853/heatmap/heatmap_R_resp.png) | ![MZM Heatmap](res/png/MZM/HY202103/D08/20190526_082853/heatmap/heatmap_Extinction_Ratio_(dB).png) |

---

## 💻 3. Getting Started

### Prerequisites

* Python **3.10** or higher
* Virtual environment (venv) recommended

### Installation

1. Clone the repository

   ```bash
   git clone https://github.com/H1SKIM/Teamproject-GPDO-.git
   cd Teamproject-GPDO-
   ```

2. Install required packages

   ```bash
   pip install numpy scipy matplotlib pandas lxml
   ```

3. Place measurement data

   ```
   data/
   └── HY202103/               ← Project folder name (auto-detected)
       ├── D07/
       │   └── 20190715_190855/
       │       ├── HY202103_D07_(0,0)_LION1_DCM_LMZC.xml
       │       └── ...
       ├── D08/
       │   └── 20190526_082853/
       │       ├── HY202103_D08_(0,0)_LION1_DCM_GPDO.xml
       │       ├── HY202103_D08_(0,0)_LION1_DCM_LMZO.xml
       │       └── ...
       ├── D23/
       └── D24/
   ```

   > The folder structure (`project name → wafer ID → timestamp`) is auto-detected. No changes to `config.py` are needed — simply add folders.

---

## 🚀 4. Usage

```bash
# Process all devices (GPDO + MZM)
python run.py

# Process GPDO only
python run.py GPDO

# Process MZM only (includes both LMZC and LMZO)
python run.py MZM
```

When execution completes, a summary is printed:

```
============================================================
  📋 Run Summary
============================================================
  ✅ GPDO   / D08  →  res/png/GPDO/HY202103/D08/{timestamp}/
  ✅ GPDO   / D23  →  res/png/GPDO/HY202103/D23/{timestamp}/
  ✅ MZM    / D07  →  res/png/MZM/HY202103/D07/{timestamp}/
  ✅ MZM    / D08  →  res/png/MZM/HY202103/D08/{timestamp}/
============================================================
```

---

## 📂 5. Project Structure

```
project/
├── run.py                        # Entry point — select device type via CLI args
├── config.py                     # Path and device config (auto-detects wafers and projects)
│
├── data/                         # Raw XML measurement files (not tracked by Git)
│   └── HY202103/
│       └── D08/ ...
│
├── res/                          # Analysis output (not tracked by Git)
│   ├── png/
│   │   ├── GPDO/HY202103/D08/{timestamp}/   ← Per-die 6-panel PNG + heatmap/
│   │   └── MZM/ HY202103/D08/{timestamp}/   ← Per-die 6-panel PNG + heatmap/
│   └── csv/
│       ├── GPDO/HY202103/D08_Result.csv
│       ├── GPDO/HY202103/Total_Result.csv
│       ├── MZM/ HY202103/D08_Result.csv
│       └── MZM/ HY202103/Total_Result.csv
│
└── src/
    ├── gpdo/
    │   ├── analyzer.py           # GPDOAnalyzer — full pipeline integration
    │   ├── parser.py             # GPDOParser — XML parsing
    │   ├── fitting.py            # FittingEngine — Shockley / power-law fitting
    │   ├── plotter.py            # Plotter — per-die 6-panel PNG generation
    │   └── csv.py                # Per-wafer CSV and Total CSV export
    ├── mzm/
    │   ├── analyzer.py           # MZMAnalyzer — full pipeline integration
    │   ├── parser.py             # MZMParser — XML parsing + device type detection
    │   ├── fitting.py            # fit_mzi / process_iv / fit_polynomials
    │   ├── plotter.py            # Plotter — per-die 6-panel PNG generation
    │   └── csv.py                # Per-wafer CSV and Total CSV export
    └── heatmap_plotter.py        # HeatmapPlotter — wafer-level heatmap generation
```

---

## 🔬 6. Analysis Models

### GPDO IV Fitting

| Region | Model | Parameters |
|--------|-------|------------|
| Forward bias (V > 0.3V) | Shockley diode: `I = Is · exp(V / n·Vt)` | `Is` (saturation current), `n` (ideality factor) |
| Reverse bias (V ≤ 0.3V) | 3rd-order polynomial | Reverse saturation characteristics |
| Photo current | `I_photo = I_light − I_dark` | `Iph`, `R = Iph / P_in` |

### MZM MZI Fitting (Fixed -40 dB Floor)

The extinction ratio floor is fixed at **-40 dB**, reducing free parameters to improve fitting stability and avoid local minima.

```
T(λ) = c + d · cos(a·λ + b)

  floor = 10^(-40/10) = 1×10⁻⁴  (fixed)
  c = (t_max + floor) / 2
  d = (t_max - floor) / 2

Free parameters:  a (→ FSR = 2π/a),  b (phase),  t_max (peak transmission)
```

### Measurement Data Quality Check

| Condition | Judgment |
|-----------|----------|
| `max(│I│) < 1 nA` | Current at noise level — suspected probe contact failure |
| `I_max / I_min < 10` at forward bias (V > 0.3V) | No diode characteristic — suspected junction failure |

When an error is detected, a `Measurement Data Error` box is **overlaid** on the 6 analysis panels and saved to the PNG.
*(Explicitly indicates a measurement data issue, not a code error)*

---

## 📊 7. Output CSV Columns

### GPDO

| Column      | Unit | Description |
|-------------|------|-------------|
| `Lot` / `Wafer` / `Mask` / `Testsite`  | — | Wafer identification info |
| `col` / `row` | — | Die position (X / Y) |
| `lc_wl`     | nm | Light current measurement wavelength |
| `fiber_dbm` | dBm | Fiber output power |
| `Iph`       | A | Photo current |
| `n_d`       | — | Ideality factor |
| `R_resp`    | A/W | Responsivity |
| `r2_fwd`    | — | Forward bias fitting R² |

### MZM

| Column                                | Unit | Description |
|---------------------------------------|------|-------------|
| `Lot` / `Wafer` / `Mask` / `Testsite` | — | Wafer identification info |
| `col` / `row`                         | — | Die position |
| `Analysis Wavelength`                 | nm | Analysis wavelength |
| `Rsq of Ref. spectrum (Nth)`          | — | Reference spectrum fitting R² |
| `Rsq of IV`                           | — | IV fitting R² |
| `I at -1V [A]` / `I at 1V [A]`        | A | Current at each voltage |
| `Ideality Factor`                     | — | Diode ideality factor |
| `Extinction Ratio`                    | dB | MZI extinction ratio |
| `FSR `                                | nm | Free Spectral Range |
| `ErrorFlag` / `Error description`     | — | Data quality flag |


---

## ⚙️ 8. Configuration

### Adding a New Project or Wafer

Simply add a folder under `data/` — it will be **auto-detected**. No changes to `config.py` required.

```
data/
├── HY202103/   ← existing
└── HY202104/   ← auto-processed by adding folder only
    └── D07/ ...
```

### Restricting to Specific Wafers

```python
# config.py
DEVICE_CONFIG = {
    "GPDO": dict(wafer_ids=["D08", "D24"]),   # process D08 and D24 only
    "MZM":  dict(wafer_ids=None),              # None → process all wafers
}
```

## ✉️ 9. Contact

For questions or feedback, please use GitHub Issues.

**Project Link:** [https://github.com/H1SKIM/Teamproject-GPDO-](https://github.com/H1SKIM/Teamproject-GPDO-)
