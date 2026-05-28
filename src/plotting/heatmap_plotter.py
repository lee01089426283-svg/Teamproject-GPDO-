# ══════════════════════════════════════════════════════
# src/plotting/heatmap_plotter.py  –  웨이퍼 히트맵 시각화
# ══════════════════════════════════════════════════════
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


class HeatmapPlotter:
    """
    results 리스트(각 다이의 분석 결과 dict)에서
    특정 파라미터를 웨이퍼 레이아웃 히트맵으로 시각화.
    """

    @staticmethod
    def plot(results: list, param_key: str, title: str,
             unit: str, cmap: str = "RdYlGn",
             wafer_id: str = "D08",
             save_dir: str = None) -> None:
        """
        Parameters
        ----------
        results   : GPDOAnalyzer.run() 이 반환하는 dict 리스트
        param_key : 히트맵에 표시할 값의 키 (예: 'Iph', 'n_d' 등)
        title     : 플롯 제목 (사람이 읽기 좋은 설명)
        unit      : 단위 문자열 (없으면 빈 문자열 "")
        cmap      : matplotlib colormap 이름
        wafer_id  : 제목에 표시할 웨이퍼 ID
        save_dir  : PNG 저장 폴더 (None 이면 저장 생략)
        """
        cols = [r['col'] for r in results]
        rows = [r['row'] for r in results]
        vals = [r.get(param_key, np.nan) for r in results]

        valid   = [(c, ro, v) for c, ro, v in zip(cols, rows, vals)
                   if not np.isnan(v)]
        missing = [(c, ro)    for c, ro, v in zip(cols, rows, vals)
                   if np.isnan(v)]

        if not valid:
            print(f"  ⚠ {param_key}: 유효 데이터 없음")
            return

        cs, rs, vs = zip(*valid)
        norm = Normalize(vmin=min(vs), vmax=max(vs))
        sm   = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        fig, ax = plt.subplots(figsize=(7, 6))

        # ── 유효 다이 ─────────────────────────────────
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

        # ── 누락 다이 ─────────────────────────────────
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

        # ── 축 범위 ───────────────────────────────────
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
        plt.colorbar(sm, ax=ax,
                     label=f"{title}{unit_str}",
                     shrink=0.85)
        plt.tight_layout()

        # ── 저장 ──────────────────────────────────────
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            fpath = os.path.join(save_dir, f"heatmap_{param_key}.png")
            fig.savefig(fpath, dpi=150, bbox_inches="tight")
            print(f"       💾 저장: {fpath}")
        plt.close(fig)
