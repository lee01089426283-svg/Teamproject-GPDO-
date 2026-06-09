# ══════════════════════════════════════════════════════
# src/analyzer/gpdo_analyzer.py  –  GPDO 전체 파이프라인
# ══════════════════════════════════════════════════════
import os
import numpy as np

from src.gpdo.parser import GPDOParser


def _calc_r2_photo(V_light: "np.ndarray", I_photo: "np.ndarray") -> float:
    """역바이어스 구간(V < −1 V) 광전류의 포화 균일도 R² (직선 피팅 기준)."""
    import numpy as np
    mask = V_light < -1.0
    if mask.sum() < 2:
        return float("nan")
    y = np.abs(I_photo[mask])
    x = V_light[mask]
    p = np.polyfit(x, y, 1)
    y_hat = np.polyval(p, x)
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return float(1 - ss_res / ss_tot) if ss_tot != 0 else float("nan")
from src.gpdo.fitting import FittingEngine
from src.gpdo.plotter import Plotter
from src.heatmap_plotter import HeatmapPlotter


class GPDOAnalyzer:
    """
    웨이퍼 1개의 모든 타임스탬프 × 다이를 일괄 처리.

    Parameters
    ----------
    data_dir : data/{PROJECT_NAME}/ 경로
    wafer_id : 'D07', 'D08' 등

    run() 반환값
    ------------
    { timestamp: [result_dict, ...] }
    result_dict 키: col, row, lc_wl, fiber_dbm,
                    Iph, n_d, Rs_d, R_resp, peak_wl
    """

    # 히트맵으로 그릴 파라미터 목록 (responsivity, ideality factor만 표시)
    HEATMAP_PARAMS = [
        ("R_resp", "Responsivity", "A/W", "RdYlGn", "heatmap_Responsivity"),
        ("n_d", "Ideality Factor", "", "coolwarm", "heatmap_Ideality_Factor"),
    ]

    def __init__(self, data_dir: str, wafer_id: str):
        self.data_dir = data_dir
        self.wafer_id = wafer_id
        self.wafer_dir = os.path.join(data_dir, wafer_id)

    # ── 공개 진입점 ───────────────────────────────────

    def run(self, save_dir: str) -> dict:
        """
        웨이퍼 내 모든 타임스탬프를 처리하고 결과를 반환.

        Returns
        -------
        { timestamp: [result_dict, ...] }
        """
        if not os.path.isdir(self.wafer_dir):
            print(f"  ⚠ 웨이퍼 폴더 없음: {self.wafer_dir}")
            return {}

        timestamps = sorted([
            d for d in os.listdir(self.wafer_dir)
            if os.path.isdir(os.path.join(self.wafer_dir, d))
        ])

        if not timestamps:
            print(f"  ⚠ 타임스탬프 폴더 없음: {self.wafer_dir}")
            return {}

        all_results: dict[str, list] = {}

        for ts in timestamps:
            ts_dir      = os.path.join(self.wafer_dir, ts)
            ts_png      = os.path.join(save_dir, ts)
            ts_heatmap  = os.path.join(save_dir, ts, "heatmap")
            results = self._process_timestamp(ts_dir, ts_png)
            if results:
                all_results[ts] = results
                self._plot_heatmaps(results, ts_heatmap)

        return all_results

    # ── 내부 처리 ─────────────────────────────────────

    def _process_timestamp(self, ts_dir: str, save_dir: str) -> list:
        """타임스탬프 폴더 내 모든 GPDO XML을 처리."""
        xml_files = sorted([
            os.path.join(ts_dir, f)
            for f in os.listdir(ts_dir)
            if f.lower().endswith(".xml") and GPDOParser.is_gpdo_xml(
                os.path.join(ts_dir, f)
            )
        ])

        if not xml_files:
            print(f"  ⚠ GPDO XML 없음: {ts_dir}")
            return []

        print(f"  📂 {os.path.basename(ts_dir)}  →  {len(xml_files)}개 파일")
        results = []
        for xml_path in xml_files:
            result = self._process_one(xml_path, save_dir)
            if result is not None:
                results.append(result)

        return results

    @staticmethod
    def _check_data_quality(raw: dict) -> list[str]:
        """측정 데이터 품질 검사. 오류 메시지 리스트 반환 (정상이면 빈 리스트)."""
        errors = []
        i_dark = raw['I_dark']

        # ① 전류가 노이즈 수준(<1nA) — probe contact 불량 등
        if np.max(np.abs(i_dark)) < 1e-9:
            errors.append('IV Error: Current at noise level (<1 nA)')

        # ② forward bias에서 지수 증가 없음 — junction 불량
        v_dark = raw['V_dark']
        fwd_mask = v_dark > 0.3
        if fwd_mask.sum() >= 2:
            i_fwd = np.abs(i_dark[fwd_mask])
            if i_fwd.min() > 0 and i_fwd.max() / i_fwd.min() < 10:
                errors.append('IV Error: No diode characteristic in forward bias')

        return errors

    def _process_one(self, xml_path: str, png_dir: str) -> dict | None:
        """XML 1개 파싱 → 피팅 → 플롯 → result dict 반환."""
        fname = os.path.basename(xml_path)
        try:
            raw = GPDOParser.parse(xml_path)
        except Exception as e:
            print(f"       ⚠ 파싱 실패 [{fname}]: {e}")
            return None

        # 측정 데이터 품질 검사
        data_errors = self._check_data_quality(raw)
        if data_errors:
            print(f"       ⚠ 측정 데이터 오류 [{fname}]: {data_errors}")

        try:
            ref_r = FittingEngine.fit_reference(raw['L_ref'], raw['IL_ref'])
            df    = FittingEngine.fit_dark_fwd(raw['V_dark'], raw['I_dark'])
            dr    = FittingEngine.fit_dark_rev(raw['V_dark'], raw['I_dark'])
            lf    = FittingEngine.fit_light(raw['V_light'], raw['I_light'], df, dr)
            pc    = FittingEngine.calc_photo_current(
                        raw['V_light'], raw['I_light'],
                        raw['V_dark'],  raw['I_dark'])

            # 측정 파장에서의 Reference IL 추출
            idx_wl   = np.argmin(np.abs(raw['L_ref'] - raw['lc_wl']))
            il_at_wl = raw['IL_ref'][idx_wl]
            resp     = FittingEngine.calc_responsivity(
                           pc['Iph'], raw['fiber_dbm'], il_at_wl)
        except Exception as e:
            print(f"       ⚠ 피팅 실패 [{fname}]: {e}")
            if data_errors:
                self._save_error_png(raw, data_errors, png_dir, fname)
            return None

        # 플롯 저장 (png/ 하위 폴더) — 데이터 오류 시 에러 오버레이 포함
        try:
            Plotter.plot(raw, ref_r, df, dr, lf, pc, resp,
                         save_dir=png_dir,
                         wafer_id=self.wafer_id,
                         fname=fname,
                         error_messages=data_errors if data_errors else None)
        except Exception as e:
            print(f"       ⚠ 플롯 실패 [{fname}]: {e}")

        if data_errors:
            return None  # CSV 행에는 포함하지 않음

        # 스펙트럼 피크 파장
        peak_wl = (float(raw['L_spec'][np.argmax(np.abs(raw['I_spec']))])
                   if len(raw['L_spec']) > 0 else np.nan)

        # 광전류 R² (photo current = light - dark, 역바이어스 구간 선형 적합)
        r2_photo = _calc_r2_photo(raw['V_light'], pc['I_photo'])

        return dict(
            col      = raw['col'],
            row      = raw['row'],
            lc_wl    = raw['lc_wl'],
            fiber_dbm= raw['fiber_dbm'],
            Iph      = pc['Iph'],
            n_d      = df['n'],
            R_resp   = resp['R_resp'],
            peak_wl  = peak_wl,
            r2_fwd   = df['r2'],
            r2_photo = r2_photo,
        )

    @staticmethod
    def _save_error_png(raw: dict, errors: list, png_dir: str, fname: str) -> None:
        """피팅 자체 실패 시 에러 메시지만 담은 fallback PNG 저장."""
        import matplotlib.pyplot as plt
        stem = os.path.splitext(fname)[0]
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('off')
        error_text = '\n'.join(f'- {e}' for e in errors)
        ax.text(0.5, 0.5,
                f'Measurement Data Error\n\n{error_text}',
                ha='center', va='center', fontsize=16,
                color='red', fontweight='bold',
                transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=1.2',
                          facecolor='lightyellow',
                          edgecolor='red', linewidth=3))
        fig.suptitle(f'{stem}\n[!] Measurement Data Error  (Not a code error)',
                     fontsize=11, fontweight='bold')
        os.makedirs(png_dir, exist_ok=True)
        out = os.path.join(png_dir, fname.replace('.xml', '.png'))
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"       저장: {out}")

    def _plot_heatmaps(self, results: list, save_dir: str) -> None:
        """타임스탬프별 히트맵 일괄 생성."""
        for key, title, unit, cmap, file_stem in self.HEATMAP_PARAMS:
            try:
                HeatmapPlotter.plot(
                    results, param_key=key, title=title,
                    unit=unit, cmap=cmap,
                    wafer_id=self.wafer_id,
                    save_dir=save_dir,
                    file_stem=file_stem,
                )
            except Exception as e:
                print(f"       ⚠ 히트맵 실패 [{key}]: {e}")
