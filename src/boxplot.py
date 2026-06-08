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

def _raincloud_ax(ax, data_by_wafer: dict, ylabel: str, title: str) -> None:
    """
    단일 axes에 Raincloud Plot 그리기.
    data_by_wafer: {'D07': array, 'D08': array, ...}
    """
    wafers = [w for w, v in data_by_wafer.items() if len(v) >= 2]
    if not wafers:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                transform=ax.transAxes, color='gray')
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
    ax.set_title(title, fontweight='bold', fontsize=10)
    ax.grid(axis='y', alpha=0.25)
    ax.set_xlim(-0.6, n - 0.4)


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

                fig, ax = plt.subplots(figsize=(max(4, len(data_by_wafer) * 1.8), 5))
                _raincloud_ax(ax, data_by_wafer, ylabel,
                              f'{dtype_label} — {ylabel}  [{project_name}]')
                plt.tight_layout()
                fpath = os.path.join(out_dir, f'{stem}.png')
                fig.savefig(fpath, dpi=150, bbox_inches='tight')
                plt.close(fig)
                saved.append(fpath)
                print(f'       [Boxplot] 저장: {fpath}')
    else:
        print(f'       [Boxplot] MZM CSV 없음: {mzm_csv}')

    return saved
