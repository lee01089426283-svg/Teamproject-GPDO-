import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


class HeatmapPlotter:
    """
    웨이퍼 레이아웃 히트맵 시각화.

    GPDO
    ----
    plot(results, param_key, ...)
        results : GPDOAnalyzer.run() 반환 dict 리스트
                  각 dict에 'col', 'row', param_key 키 필요

    MZM  (주 진입점)
    ----
    plot_mzm_all_from_rows(rows, wafer_id, save_dir)
        rows     : MZMParser.parse() 반환 dict 리스트 (timestamp 1개분)
                   'Row', 'Column', 각 param_key 키 필요
        → MZM_HEATMAP_PARAMS 4개를 timestamp 폴더/heatmap/ 에 저장

    MZM  (보조 — CSV 경유)
    ----
    plot_from_csv(csv_path, param_key, ...)
    plot_mzm_all(csv_path, ...)
    """

    MZM_HEATMAP_PARAMS = [
        ("Max transmission of Ref. spec (dB)", "Max Transmission of Ref. Spec", "dB", "RdYlGn"),
        ("Rsq of Ref. spectrum (Nth)",          "Rsq of Ref. Spectrum",          "",   "RdYlGn"),
        ("Rsq of IV",                           "Rsq of IV",                     "",   "RdYlGn"),
        ("I at -1V [A]",                        "I at -1V",                      "A",  "RdYlBu"),
        ("Extinction Ratio (dB)",               "Extinction Ratio",              "dB", "RdYlGn"),
        ("FSR (nm)",                            "FSR",                           "nm", "RdYlBu"),
    ]

    # ── GPDO 진입점 ───────────────────────────────────────

    @staticmethod
    def plot(results: list, param_key: str, title: str,
             unit: str, cmap: str = "RdYlGn",
             wafer_id: str = "D08",
             save_dir: str = None) -> None:
        cols = [r['col'] for r in results]
        rows = [r['row'] for r in results]
        vals = [r.get(param_key, np.nan) for r in results]

        HeatmapPlotter._draw_and_save(
            cols=cols, rows=rows, vals=vals,
            param_key=param_key, title=title, unit=unit, cmap=cmap,
            wafer_id=wafer_id, save_dir=save_dir,
        )

    # ── MZM 주 진입점 — dict 리스트 직접 사용 ─────────────

    @classmethod
    def plot_mzm_all_from_rows(cls, rows: list,
                                wafer_id: str = "",
                                save_dir: str = None) -> None:
        for param_key, title, unit, cmap in cls.MZM_HEATMAP_PARAMS:
            try:
                cols = [r.get('Column') for r in rows]
                _rows = [r.get('Row') for r in rows]
                vals = []
                for r in rows:
                    v = r.get(param_key)
                    try:
                        vals.append(float(v) if v is not None else np.nan)
                    except (TypeError, ValueError):
                        vals.append(np.nan)

                safe_key = (param_key.replace(' ', '_')
                                     .replace('/', '_')
                                     .replace('.', '')
                                     .replace('[', '')
                                     .replace(']', ''))
                cls._draw_and_save(
                    cols=cols, rows=_rows, vals=vals,
                    param_key=safe_key, title=title, unit=unit, cmap=cmap,
                    wafer_id=wafer_id, save_dir=save_dir,
                )
            except Exception as e:
                print(f'  [WARN] 히트맵 실패 [{param_key}]: {e}')

    # ── MZM 보조 진입점 — CSV 파일 경유 ──────────────────

    @classmethod
    def plot_from_csv(cls, csv_path: str,
                      param_key: str, title: str,
                      unit: str, cmap: str = "RdYlGn",
                      wafer_id: str = "",
                      group_key: str = "device_type",
                      save_dir: str = None) -> None:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except Exception as e:
            print(f'  [ERROR] CSV 로드 실패: {e}')
            return

        if 'device_type' not in df.columns and 'Script ID' in df.columns:
            df['device_type'] = df['Script ID'].str.extract(r'DCM_(LMZC|LMZO)')

        if not wafer_id and 'Wafer' in df.columns:
            wafer_id = str(df['Wafer'].iloc[0])

        if param_key not in df.columns:
            print(f'  [WARN] {param_key} 컬럼 없음: {csv_path}')
            return

        safe_key = (param_key.replace(' ', '_').replace('/', '_')
                             .replace('.', '').replace('[', '').replace(']', ''))

        if group_key and group_key in df.columns:
            for group_val, group_df in df.groupby(group_key):
                cols = group_df['Column'].tolist()
                rows = group_df['Row'].tolist()
                vals = pd.to_numeric(group_df[param_key], errors='coerce').tolist()
                cls._draw_and_save(
                    cols=cols, rows=rows, vals=vals,
                    param_key=f"{safe_key}_{group_val}",
                    title=title, unit=unit, cmap=cmap,
                    wafer_id=f"{wafer_id} [{group_val}]",
                    save_dir=save_dir,
                )
        else:
            cols = df['Column'].tolist()
            rows = df['Row'].tolist()
            vals = pd.to_numeric(df[param_key], errors='coerce').tolist()
            cls._draw_and_save(
                cols=cols, rows=rows, vals=vals,
                param_key=safe_key, title=title, unit=unit, cmap=cmap,
                wafer_id=wafer_id, save_dir=save_dir,
            )

    @classmethod
    def plot_mzm_all(cls, csv_path: str,
                     wafer_id: str = "",
                     save_dir: str = None) -> None:
        for param_key, title, unit, cmap in cls.MZM_HEATMAP_PARAMS:
            try:
                cls.plot_from_csv(
                    csv_path=csv_path, param_key=param_key,
                    title=title, unit=unit, cmap=cmap,
                    wafer_id=wafer_id, group_key='device_type',
                    save_dir=save_dir,
                )
            except Exception as e:
                print(f'  [WARN] 히트맵 실패 [{param_key}]: {e}')

    # ── 공통 드로잉 엔진 ──────────────────────────────────

    @staticmethod
    def _draw_and_save(cols: list, rows: list, vals: list,
                       param_key: str, title: str, unit: str,
                       cmap: str, wafer_id: str,
                       save_dir: str = None) -> None:
        valid   = [(int(c), int(r), float(v))
                   for c, r, v in zip(cols, rows, vals)
                   if v is not None and not np.isnan(float(v))]
        missing = [(int(c), int(r))
                   for c, r, v in zip(cols, rows, vals)
                   if v is None or np.isnan(float(v))]

        if not valid:
            print(f"  ⚠ {param_key}: 유효 데이터 없음")
            return

        cs, rs, vs = zip(*valid)
        norm = Normalize(vmin=min(vs), vmax=max(vs))
        sm   = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        fig, ax = plt.subplots(figsize=(7, 6))

        for c, r, v in zip(cs, rs, vs):
            rect = mpatches.FancyBboxPatch(
                (c - 0.45, r - 0.45), 0.9, 0.9,
                boxstyle="round,pad=0.05",
                facecolor=sm.to_rgba(v),
                edgecolor="white", linewidth=1.5,
            )
            ax.add_patch(rect)
            txt_color = "white" if norm(v) < 0.5 else "black"
            ax.text(c, r, f"{v:.3g}",
                    ha="center", va="center",
                    fontsize=8, fontweight="bold", color=txt_color)

        for c, r in missing:
            rect = mpatches.FancyBboxPatch(
                (c - 0.45, r - 0.45), 0.9, 0.9,
                boxstyle="round,pad=0.05",
                facecolor="#EEEEEE", edgecolor="gray",
                linewidth=1, linestyle="--",
            )
            ax.add_patch(rect)
            ax.text(c, r, "N/A",
                    ha="center", va="center",
                    fontsize=7, color="gray")

        all_c = list(cs) + [c for c, _ in missing]
        all_r = list(rs) + [r for _, r in missing]
        ax.set_xlim(min(all_c) - 0.7, max(all_c) + 0.7)
        ax.set_ylim(min(all_r) - 0.7, max(all_r) + 0.7)
        ax.set_aspect("equal")

        unit_str = f" [{unit}]" if unit else ""
        ax.set_xlabel("Column (Die X)", fontsize=10)
        ax.set_ylabel("Row (Die Y)",    fontsize=10)
        ax.set_title(f"Wafer {wafer_id} Heatmap – {title}{unit_str}",
                     fontweight="bold", fontsize=11)
        ax.grid(True, alpha=0.15, linestyle=":")
        plt.colorbar(sm, ax=ax, label=f"{title}{unit_str}", shrink=0.85)
        plt.tight_layout()

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            fpath = os.path.join(save_dir, f"heatmap_{param_key}.png")
            fig.savefig(fpath, dpi=150, bbox_inches="tight")
            print(f"       💾 저장: {fpath}")
        plt.close(fig)
