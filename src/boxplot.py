# ══════════════════════════════════════════════════════
# src/boxplot.py  –  디바이스별 Raincloud Plot 생성
# ══════════════════════════════════════════════════════
"""
GPDO / LMZC / LMZO 세 그룹으로 나눠 파라미터별 Raincloud Plot을 생성한다.

Raincloud = 반 바이올린(KDE) + 박스플롯 + 스트립(jitter)
출력 위치: res/png/boxplot/{project_name}/
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from scipy.stats import gaussian_kde


# ── 파라미터 정의 ──────────────────────────────────────────
GPDO_PARAMS = [
    ('R_resp',   'Responsivity [A/W]',     'GPDO_Responsivity'),
    ('n_d',      'Ideality Factor',         'GPDO_IdealityFactor'),
    ('Iph',      'Photo Current [A]',       'GPDO_PhotoCurrent'),
]

MZM_PARAMS = [
    ('Extinction Ratio (dB)', 'Extinction Ratio [dB]',    '{dtype}_ExtinctionRatio'),
    ('FSR (nm)',              'FSR [nm]',                  '{dtype}_FSR'),
    ('I at -1V [A]',         'I at -1V [A]',              '{dtype}_I_at_-1V'),
    ('Ideality Factor',      'Ideality Factor',            '{dtype}_IdealityFactor'),
]

PALETTE = {
    'D07': '#1565C0',
    'D08': '#2E7D32',
    'D23': '#C62828',
    'D24': '#6A1B9A',
}
DEFAULT_COLOR = '#455A64'


# ══════════════════════════════════════════════════════════
# 내부 헬퍼
# ══════════════════════════════════════════════════════════

def _raincloud_ax(ax, data_by_wafer: dict, ylabel: str, title: str = '') -> None:
    """
    단일 axes에 Raincloud Plot 그리기.
    data_by_wafer: {'D07': array, 'D08': array, ...}
    """
    wafers = [w for w, v in data_by_wafer.items() if len(v) >= 2]
    if not wafers:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                transform=ax.transAxes, color='gray')
        if title:
            ax.set_title(title, fontweight='bold')
        return

    n = len(wafers)
    positions = np.arange(n)

    for i, wafer in enumerate(wafers):
        vals = data_by_wafer[wafer]
        vals = vals[np.isfinite(vals)]
        if len(vals) < 2:
            continue
        color = PALETTE.get(wafer, DEFAULT_COLOR)

        # ── 박스플롯 ──
        bp = ax.boxplot(vals, positions=[i], widths=0.25,
                        patch_artist=True, manage_ticks=False,
                        medianprops=dict(color='black', lw=2),
                        boxprops=dict(facecolor=color, alpha=0.55),
                        whiskerprops=dict(color=color, lw=1.2),
                        capprops=dict(color=color, lw=1.5),
                        flierprops=dict(marker='', linestyle='none'))

        # ── KDE 바이올린 반쪽 (왼쪽) ──
        try:
            kde = gaussian_kde(vals, bw_method='scott')
            y_range = np.linspace(vals.min(), vals.max(), 200)
            k = kde(y_range)
            k = k / k.max() * 0.22          # 너비 정규화
            ax.fill_betweenx(y_range,
                             i - 0.14 - k,
                             i - 0.14,
                             alpha=0.40, color=color)
            ax.plot(i - 0.14 - k, y_range,
                    color=color, lw=0.8, alpha=0.7)
        except Exception:
            pass

        # ── jitter 제거 (다이 좌표 scatter는 별도 axes에서 표시) ──

    ax.set_xticks(positions)
    ax.set_xticklabels(wafers)
    ax.set_ylabel(ylabel, fontsize=9)
    if title:
        ax.set_title(title, fontweight='bold', fontsize=10)
    ax.grid(axis='y', alpha=0.25)
    ax.set_xlim(-0.6, n - 0.4)


def _all_finite_values(data_by_wafer: dict) -> np.ndarray:
    vals = [
        np.asarray(v, dtype=float)[np.isfinite(np.asarray(v, dtype=float))]
        for v in data_by_wafer.values()
    ]
    vals = [v for v in vals if len(v)]
    return np.concatenate(vals) if vals else np.array([])


def _padded_limits(vals: np.ndarray, fallback: tuple[float, float]) -> tuple[float, float]:
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return fallback
    lo, hi = float(vals.min()), float(vals.max())
    pad = max((hi - lo) * 0.08, 0.01)
    return lo - pad, hi + pad


def _raincloud_broken_y_fig(data_by_wafer: dict,
                            ylabel: str,
                            title: str,
                            break_range: tuple[float, float],
                            figsize: tuple[float, float]):
    """Raincloud plot with an in-axis compressed y interval."""
    fig, ax = plt.subplots(figsize=figsize)
    break_lo, break_hi = break_range
    gap = break_hi - break_lo
    visible_gap = 0.045

    def compress_y(vals):
        scalar_input = np.isscalar(vals)
        vals = np.asarray(vals, dtype=float)
        compressed = np.where(vals >= break_hi, vals - gap + visible_gap, vals)
        return float(compressed) if scalar_input else compressed

    all_vals = _all_finite_values(data_by_wafer)
    low_vals = all_vals[all_vals <= break_lo]
    high_vals = all_vals[all_vals >= break_hi]
    low_data_by_wafer = {
        w: np.asarray(v, dtype=float)[np.asarray(v, dtype=float) <= break_lo]
        for w, v in data_by_wafer.items()
    }

    _raincloud_ax(ax, low_data_by_wafer, ylabel, title)

    wafers = [w for w, v in data_by_wafer.items() if len(v) >= 2]
    rng = np.random.default_rng(42)
    for i, wafer in enumerate(wafers):
        vals = np.asarray(data_by_wafer[wafer], dtype=float)
        vals = vals[np.isfinite(vals) & (vals >= break_hi)]
        if len(vals) == 0:
            continue
        jitter = rng.uniform(-0.08, 0.08, size=len(vals))
        color = PALETTE.get(wafer, DEFAULT_COLOR)
        ax.scatter(i + 0.25 + jitter, compress_y(vals),
                   color=color, s=18, alpha=0.65,
                   edgecolors='none', zorder=3)

    bottom_lo, _ = _padded_limits(low_vals, (break_lo - 0.2, break_lo))
    _, high_top = _padded_limits(high_vals, (break_hi, break_hi + 0.2))
    ax.set_ylim(bottom_lo, compress_y(high_top))

    low_ticks = [1.30, 1.35, 1.40, 1.45, 1.50, 1.55]
    high_ticks = [2.15, 2.20]
    ticks = low_ticks + [compress_y(t) for t in high_ticks]
    labels = [f'{t:.2f}' for t in low_ticks + high_ticks]
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)

    break_y = break_lo + visible_gap / 2
    x_wave = np.linspace(-0.018, 0.018, 80)
    y_wave = break_y + 0.008 * np.sin(np.linspace(0, 2 * np.pi, len(x_wave)))
    for x0 in (0, 1):
        ax.plot(x0 + x_wave, y_wave, transform=ax.get_yaxis_transform(),
                color='black', lw=1.2, clip_on=False)

    return fig, ax




def _scatter_ax(ax, data_by_wafer: dict, coords_by_wafer: dict,
                ylabel: str, title: str = '') -> None:
    """
    다이 좌표 기반 scatter plot.
    coords_by_wafer: {'D08': [(col,row), ...], ...}
    data_by_wafer:   {'D08': array, ...}
    """
    wafers = [w for w, v in data_by_wafer.items() if len(v) >= 2]
    if not wafers:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                transform=ax.transAxes, color='gray')
        return

    all_labels = []
    for wafer in wafers:
        coords = coords_by_wafer.get(wafer, [])
        vals   = data_by_wafer[wafer]
        color  = PALETTE.get(wafer, DEFAULT_COLOR)
        labels = [f"({c},{r})" for c, r in coords] if coords else [str(j+1) for j in range(len(vals))]
        for j, (lbl, v) in enumerate(zip(labels, vals)):
            if lbl not in all_labels:
                all_labels.append(lbl)
            xi = all_labels.index(lbl)
            ax.scatter(xi, v, color=color, s=30, alpha=0.75,
                       edgecolors=color, linewidths=0.5, zorder=3,
                       label=wafer if j == 0 else '_nolegend_')

    ax.set_xticks(range(len(all_labels)))
    ax.set_xticklabels(all_labels, rotation=45, ha='right', fontsize=7)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xlabel('Die (col, row)', fontsize=9)
    if title:
        ax.set_title(title, fontweight='bold', fontsize=10)
    ax.grid(axis='y', alpha=0.25)
    ax.legend(fontsize=8, loc='upper right')

# ══════════════════════════════════════════════════════════
# 공개 API
# ══════════════════════════════════════════════════════════

def generate_boxplots(project_name: str,
                      gpdo_csv: str,
                      mzm_csv: str,
                      gpdo_out_dir: str,
                      mzm_out_dir: str) -> list[str]:
    ...
    os.makedirs(gpdo_out_dir, exist_ok=True)
    os.makedirs(mzm_out_dir,  exist_ok=True)
    saved = []

    # ── GPDO ──────────────────────────────────────────
    if os.path.isfile(gpdo_csv):
        gdf = pd.read_csv(gpdo_csv)
        wafers = sorted(gdf['wafer_id'].unique()) if 'wafer_id' in gdf.columns else []

        for col, ylabel, stem in GPDO_PARAMS:
            if col not in gdf.columns:
                continue
            data_by_wafer = {}
            for w in wafers:
                sub = gdf[gdf['wafer_id'] == w][col].dropna().values
                if len(sub) > 0:
                    data_by_wafer[w] = sub.astype(float)

            if not data_by_wafer:
                continue

            # 다이 좌표 수집
            coords_by_wafer = {}
            for w in wafers:
                sub = gdf[gdf['wafer_id'] == w][['col', 'row', col]].dropna()
                coords_by_wafer[w] = list(zip(sub['col'].astype(int), sub['row'].astype(int)))
                data_by_wafer[w] = sub[col].values.astype(float)

            fig, axes = plt.subplots(1, 2, figsize=(max(8, len(data_by_wafer) * 3.5), 5))
            _raincloud_ax(axes[0], data_by_wafer, ylabel,
                          f'GPDO — {ylabel}  [{project_name}]')
            _scatter_ax(axes[1], data_by_wafer, coords_by_wafer,
                        ylabel, f'GPDO — {ylabel} per Die  [{project_name}]')
            plt.tight_layout()
            fpath = os.path.join(gpdo_out_dir, f'{stem}.png')
            fig.savefig(fpath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            saved.append(fpath)
            print(f'       [Boxplot] 저장: {fpath}')
    else:
        print(f'       [Boxplot] GPDO CSV 없음: {gpdo_csv}')

    # ── MZM (LMZC / LMZO 분리) ────────────────────────
    if os.path.isfile(mzm_csv):
        mdf = pd.read_csv(mzm_csv)
        if 'ErrorFlag' in mdf.columns:
            before = len(mdf)
            mdf = mdf[pd.to_numeric(mdf['ErrorFlag'], errors='coerce').fillna(0) == 0].copy()
            excluded = before - len(mdf)
            if excluded:
                print(f'       [Boxplot] MZM ErrorFlag 행 제외: {excluded}개')

        for dtype_key, dtype_label in [('DCM_LMZC', 'LMZC'), ('DCM_LMZO', 'LMZO')]:
            sub_df = mdf[mdf['Testsite'] == dtype_key] if 'Testsite' in mdf.columns else mdf
            if sub_df.empty:
                continue

            wafer_col = 'Wafer' if 'Wafer' in sub_df.columns else None
            wafers = sorted(sub_df[wafer_col].unique()) if wafer_col else ['All']

            for col, ylabel, stem_tmpl in MZM_PARAMS:
                if col not in sub_df.columns:
                    continue
                stem = stem_tmpl.format(dtype=dtype_label)
                data_by_wafer = {}
                for w in wafers:
                    if wafer_col:
                        vals = sub_df[sub_df[wafer_col] == w][col].dropna().values
                    else:
                        vals = sub_df[col].dropna().values
                    if len(vals) > 0:
                        data_by_wafer[w] = vals.astype(float)

                if not data_by_wafer:
                    continue

                # 다이 좌표 수집
                coords_by_wafer_mzm = {}
                for w in wafers:
                    if wafer_col:
                        sub = sub_df[sub_df[wafer_col] == w][['Row', 'Column', col]].dropna()
                        coords_by_wafer_mzm[w] = list(zip(sub['Column'].astype(int), sub['Row'].astype(int)))
                        data_by_wafer[w] = sub[col].values.astype(float)
                    else:
                        coords_by_wafer_mzm[w] = []

                figsize = (max(8, len(data_by_wafer) * 3.5), 5)
                title = f'{dtype_label} — {ylabel}  [{project_name}]'
                fig, axes = plt.subplots(1, 2, figsize=figsize)
                _raincloud_ax(axes[0], data_by_wafer, ylabel, title)
                _scatter_ax(axes[1], data_by_wafer, coords_by_wafer_mzm,
                            ylabel, f'{dtype_label} — {ylabel} per Die  [{project_name}]')

                plt.tight_layout()
                fpath = os.path.join(mzm_out_dir, f'{stem}.png')
                fig.savefig(fpath, dpi=150, bbox_inches='tight')
                plt.close(fig)
                saved.append(fpath)
                print(f'       [Boxplot] 저장: {fpath}')
    else:
        print(f'       [Boxplot] MZM CSV 없음: {mzm_csv}')

    return saved