# ══════════════════════════════════════════════════════
# src/analyzer/gpdo_analyzer.py  –  전체 파이프라인 통합
# ══════════════════════════════════════════════════════
import os
import re
import glob
import numpy as np
from collections import defaultdict

from src.parser   import GPDOParser
from src.fitting import FittingEngine
from src.plotting import Plotter, HeatmapPlotter


class GPDOAnalyzer:
    """
    파싱 → 피팅 → 시각화 → 히트맵  전체 파이프라인.

    데이터 구조: data/{wafer_id}/{timestamp}/*.xml
    결과 구조:   res/{wafer_id}-GPDO/{timestamp}/

    Parameters
    ----------
    data_dir : data/ 루트 폴더 (config.py DATA_DIR)
    wafer_id : 처리할 웨이퍼 ID (예: 'D08')
    """

    # ── 측정시간 폴더 패턴: YYYYMMDD_HHMMSS ──────────
    TIMESTAMP_PATTERN = re.compile(r'^\d{8}_\d{6}$')

    # ── 히트맵 파라미터 목록 ──────────────────────────
    HEATMAP_PARAMS = [
        ("Iph",    "Photo Current (Iph)",  "A",   "Blues"),
        ("n_d",    "Ideality Factor (n)",  "",    "RdYlGn_r"),
        ("Rs_d",   "Series Resistance Rs", "Ω",   "RdYlGn_r"),
        ("R_resp", "Responsivity R",       "A/W", "YlOrRd"),
        ("r2_fwd", "R² Dark fwd (log)",    "",    "RdYlGn"),
        ("r2_lgt", "R² Light Current",     "",    "RdYlGn"),
    ]

    def __init__(self, data_dir: str, wafer_id: str = "D08"):
        self.data_dir = data_dir
        self.wafer_id = wafer_id

        # data/{wafer_id}/ 경로
        wafer_dir = os.path.join(data_dir, wafer_id)
        if not os.path.isdir(wafer_dir):
            raise FileNotFoundError(
                f"웨이퍼 폴더를 찾을 수 없습니다: '{wafer_dir}'\n"
                f"  → data/ 아래에 '{wafer_id}' 폴더가 있는지 확인해주세요.")

        # ① 전체 XML 수집
        all_xml = sorted(set(
            glob.glob(os.path.join(wafer_dir, "*.xml")) +
            glob.glob(os.path.join(wafer_dir, "**", "*.xml"), recursive=True)
        ))
        print(f"📂 [{wafer_id}] 전체 XML {len(all_xml)}개 발견  →  GPDO 필터링 중...")

        if not all_xml:
            raise FileNotFoundError(
                f"'{wafer_dir}' 폴더에서 XML 파일을 찾을 수 없습니다.")

        # ② GPDO 구조 검증
        gpdo_all = [f for f in all_xml if GPDOParser.is_gpdo_xml(f)]
        skipped  = len(all_xml) - len(gpdo_all)
        print(f"   ✔  GPDO XML {len(gpdo_all)}개 통과  |  비-GPDO {skipped}개 제외")

        if not gpdo_all:
            raise FileNotFoundError(
                f"GPDO XML 파일이 없습니다. (wafer='{wafer_id}')")

        # ③ timestamp 폴더별로 그룹핑
        #    data/D08/20190526_082853/foo.xml  →  timestamp = '20190526_082853'
        self.groups: dict[str, list[str]] = defaultdict(list)
        for fpath in gpdo_all:
            ts = GPDOAnalyzer._extract_timestamp(fpath)
            self.groups[ts].append(fpath)

        total = sum(len(v) for v in self.groups.values())
        print(f"✅ 최종 처리 대상: {wafer_id}  "
              f"{len(self.groups)}개 측정시간  |  총 {total}개 XML")
        for ts, files in sorted(self.groups.items()):
            print(f"   📁 {ts}  →  {len(files)}개")

    # ══════════════════════════════════════════════════
    # 내부 헬퍼
    # ══════════════════════════════════════════════════

    @staticmethod
    def _extract_timestamp(xml_path: str) -> str:
        """
        파일 경로에서 측정시간 폴더명(YYYYMMDD_HHMMSS)을 추출.

        data/D08/20190526_082853/foo.xml  →  '20190526_082853'
        패턴에 맞는 폴더가 없으면 'unknown' 반환.
        """
        parts = xml_path.replace("\\", "/").split("/")
        for part in reversed(parts[:-1]):   # 파일명 제외, 역순 탐색
            if re.match(r'^\d{8}_\d{6}$', part):
                return part
        return "unknown"

    def _process_one(self, xml_path: str) -> dict:
        """XML 1개 → 파싱 + 피팅 → 결과 dict."""
        raw = GPDOParser.parse(xml_path)
        fe  = FittingEngine

        ref_r    = fe.fit_reference(raw['L_ref'], raw['IL_ref'])
        idx_wl   = np.argmin(np.abs(raw['L_ref'] - raw['lc_wl']))
        IL_at_wl = raw['IL_ref'][idx_wl]

        df = fe.fit_dark_fwd(raw['V_dark'], raw['I_dark'])
        dr = fe.fit_dark_rev(raw['V_dark'], raw['I_dark'])
        lf = fe.fit_light(raw['V_light'], raw['I_light'], df, dr)

        pc  = fe.calc_photo_current(
            raw['V_light'], raw['I_light'],
            raw['V_dark'],  raw['I_dark'])
        Iph = pc['Iph']

        resp = fe.calc_responsivity(Iph, raw['fiber_dbm'], IL_at_wl)

        return dict(
            **raw,
            ref_r=ref_r, IL_at_wl=IL_at_wl,
            df=df, dr=dr, lf=lf,
            pc=pc, resp=resp,
            Iph    = Iph,
            n_d    = df['n']  if df['ok'] else np.nan,
            Rs_d   = df['Rs'] if df['ok'] else np.nan,
            R_resp = resp['R_resp'],
            r2_fwd = df['r2'] if df['ok'] else np.nan,
            r2_lgt = lf['r2'] if lf['ok'] else np.nan,
        )

    def _run_one_timestamp(self, timestamp: str,
                           xml_files: list[str],
                           save_dir: str) -> list[dict]:
        """
        단일 측정시간 그룹 처리 → save_dir/{timestamp}/ 에 저장.

        Returns
        -------
        해당 timestamp 의 results 리스트
        """
        ts_save_dir = os.path.join(save_dir, timestamp)
        os.makedirs(ts_save_dir, exist_ok=True)

        print(f"\n  ⏱  [{timestamp}]  {len(xml_files)}개 처리 시작")
        results: list[dict] = []

        for i, fpath in enumerate(xml_files):
            fname = os.path.basename(fpath)
            print(f"  [{i+1:2d}/{len(xml_files)}] {fname}")
            try:
                d = self._process_one(fpath)
                results.append(d)
                print(f"         n={d['n_d']:.3f}  Rs={d['Rs_d']:.2f}Ω  "
                      f"Iph={d['Iph']:.2e}A  R={d['R_resp']:.3f}A/W")
                Plotter.plot(
                    d, d['ref_r'], d['df'], d['dr'],
                    d['lf'], d['pc'], d['resp'],
                    save_dir=ts_save_dir,
                    wafer_id=self.wafer_id,
                    fname=d['fname'],
                )
            except Exception as e:
                print(f"         ⚠ 오류: {e}")

        # 해당 timestamp 히트맵
        print(f"  📊 [{timestamp}] 히트맵 생성 중...")
        for key, title, unit, cmap in self.HEATMAP_PARAMS:
            HeatmapPlotter.plot(
                results, key, title, unit, cmap,
                wafer_id = self.wafer_id,
                save_dir = ts_save_dir,
            )

        return results

    # ══════════════════════════════════════════════════
    # 공개 진입점
    # ══════════════════════════════════════════════════

    def run(self, save_dir: str) -> dict[str, list[dict]]:
        """
        전체 측정시간 그룹을 순차 처리.

        저장 구조
        ---------
        save_dir/
        └── {timestamp}/
            ├── {wafer_id}_(col,row)_analysis.png
            ├── ...
            └── heatmap_*.png

        Parameters
        ----------
        save_dir : res/{wafer_id}-GPDO/ 경로

        Returns
        -------
        { timestamp: results_list } dict
        """
        os.makedirs(save_dir, exist_ok=True)
        all_results: dict[str, list[dict]] = {}

        for timestamp in sorted(self.groups.keys()):
            xml_files = self.groups[timestamp]
            results   = self._run_one_timestamp(timestamp, xml_files, save_dir)
            all_results[timestamp] = results

        # ── 전체 요약 ──────────────────────────────────
        print(f"\n{'─'*50}")
        print(f"✅ [{self.wafer_id}] 전체 분석 완료")
        for ts, res in sorted(all_results.items()):
            print(f"   {ts}  →  {len(res)}개 다이  |  {save_dir}/{ts}/")
        print(f"{'─'*50}")

        return all_results