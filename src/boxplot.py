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

        # ── 스트립 플롯 (오른쪽 jitter) ──
        rng = np.random.default_rng(42)
        jitter = rng.uniform(-0.08, 0.08, size=len(vals))
        ax.scatter(i + 0.25 + jitter, vals,
                   color=color, s=12, alpha=0.55,
                   edgecolors='none', zorder=3)

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
    """Raincloud plot with a skipped y interval for sparse high-value points."""
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=figsize, sharex=True,
        gridspec_kw={'height_ratios': [1, 3], 'hspace': 0.05}
    )

    _raincloud_ax(ax_top, data_by_wafer, '', title)
    _raincloud_ax(ax_bottom, data_by_wafer, ylabel)

    break_lo, break_hi = break_range
    all_vals = _all_finite_values(data_by_wafer)
    low_vals = all_vals[all_vals <= break_lo]
    high_vals = all_vals[all_vals >= break_hi]

    bottom_lo, _ = _padded_limits(low_vals, (break_lo - 0.2, break_lo))
    _, top_hi = _padded_limits(high_vals, (break_hi, break_hi + 0.2))
    ax_bottom.set_ylim(bottom_lo, break_lo)
    ax_top.set_ylim(break_hi, top_hi)

    ax_top.spines['bottom'].set_visible(False)
    ax_bottom.spines['top'].set_visible(False)
    ax_top.tick_params(labelbottom=False, bottom=False)
    ax_bottom.xaxis.tick_bottom()
    ax_top.set_xlabel('')

    kwargs = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=10,
                  linestyle='none', color='k', mec='k', mew=1, clip_on=False)
    ax_top.plot([0, 1], [0, 0], transform=ax_top.transAxes, **kwargs)
    ax_bottom.plot([0, 1], [1, 1], transform=ax_bottom.transAxes, **kwargs)
    ax_bottom.text(1.01, 1.02, '~~', transform=ax_bottom.transAxes,
                   ha='left', va='bottom', fontsize=12, fontweight='bold')

    return fig, (ax_top, ax_bottom)


# ══════════════════════════════════════════════════════════
# 공개 API
# ══════════════════════════════════════════════════════════

def generate_boxplots(project_name: str,
                      gpdo_csv: str,
                      mzm_csv: str,
                      out_dir: str) -> list[str]:
    """
    GPDO / LMZC / LMZO 그룹별 Raincloud Plot을 생성하고 PNG 경로 목록을 반환.

    Parameters
    ----------
    project_name : str          예) 'HY202103'
    gpdo_csv     : str          GPDO Total_Result.csv 경로
    mzm_csv      : str          MZM  Total_Result.csv 경로
    out_dir      : str          PNG 저장 폴더
    """
    os.makedirs(out_dir, exist_ok=True)
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

            fig, ax = plt.subplots(figsize=(max(4, len(data_by_wafer) * 1.8), 5))
            _raincloud_ax(ax, data_by_wafer, ylabel,
                          f'GPDO — {ylabel}  [{project_name}]')
            plt.tight_layout()
            fpath = os.path.join(out_dir, f'{stem}.png')
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

                figsize = (max(4, len(data_by_wafer) * 1.8), 5)
                title = f'{dtype_label} — {ylabel}  [{project_name}]'
                if dtype_label == 'LMZO' and col == 'Ideality Factor':
                    fig, _ = _raincloud_broken_y_fig(
                        data_by_wafer, ylabel, title,
                        break_range=(1.55, 2.15),
                        figsize=figsize,
                    )
                else:
                    fig, ax = plt.subplots(figsize=figsize)
                    _raincloud_ax(ax, data_by_wafer, ylabel, title)

                plt.tight_layout()
                fpath = os.path.join(out_dir, f'{stem}.png')
                fig.savefig(fpath, dpi=150, bbox_inches='tight')
                plt.close(fig)
                saved.append(fpath)
                print(f'       [Boxplot] 저장: {fpath}')
    else:
        print(f'       [Boxplot] MZM CSV 없음: {mzm_csv}')

    return saved
