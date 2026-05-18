# ══════════════════════════════════════════════════════
# analyzer/gpdo_analyzer.py  –  전체 파이프라인 통합
# ══════════════════════════════════════════════════════
import os
import glob
import numpy as np

from parser  import GPDOParser
from fitting import FittingEngine
from plotting import Plotter, HeatmapPlotter


class GPDOAnalyzer:
    """파싱 → 피팅 → 시각화 → 히트맵 전체 파이프라인"""

    HEATMAP_PARAMS = [
        ("Iph",    "Photo Current (Iph)",  "A",   "Blues"),
        ("n_d",    "Ideality Factor (n)",  "",    "RdYlGn_r"),
        ("Rs_d",   "Series Resistance Rs", "Ω",   "RdYlGn_r"),
        ("R_resp", "Responsivity R",       "A/W", "YlOrRd"),
        ("r2_fwd", "R² Dark fwd (log)",    "",    "RdYlGn"),
        ("r2_lgt", "R² Light Current",     "",    "RdYlGn"),
    ]

    def __init__(self, gpdo_dir: str, wafer_id: str = "D08"):
        self.gpdo_dir = gpdo_dir
        self.wafer_id = wafer_id

        # ── ① 폴더 + 하위 폴더까지 전체 XML 수집 ────────
        all_xml = sorted(
            glob.glob(os.path.join(gpdo_dir, "*.xml")) +           # 직접 경로
            glob.glob(os.path.join(gpdo_dir, "**", "*.xml"))       # 하위 폴더
        )
        # 중복 제거
        all_xml = sorted(set(all_xml))
        print(f"📂 전체 XML {len(all_xml)}개 발견  →  GPDO 필터링 중...")

        if not all_xml:
            raise FileNotFoundError(
                f"'{gpdo_dir}' 폴더에서 XML 파일을 찾을 수 없습니다.\n"
                f"  → 경로가 올바른지 확인해주세요: {gpdo_dir}")

        # ── ② GPDO 구조 검증 (TestSite + 필수 포트 태그) ─
        gpdo_all = [f for f in all_xml if GPDOParser.is_gpdo_xml(f)]
        skipped  = len(all_xml) - len(gpdo_all)
        print(f"   ✔  GPDO XML {len(gpdo_all)}개 통과  |  비(非)-GPDO {skipped}개 제외")

        # ── ③ wafer_id 필터 (XML 내부 TestSiteInfo Wafer 속성 기준) ─
        self.xml_files = [f for f in gpdo_all
                          if GPDOAnalyzer._match_wafer(f, wafer_id)]
        excluded = len(gpdo_all) - len(self.xml_files)
        if excluded:
            print(f"   ⚠  wafer='{wafer_id}' 미해당 {excluded}개 추가 제외")

        if not self.xml_files:
            raise FileNotFoundError(
                f"GPDO XML은 찾았으나 wafer_id='{wafer_id}'에 해당하는 파일이 없습니다.\n"
                f"  → config.py 의 WAFER_ID 값을 확인해주세요.")

        print(f"✅ 최종 처리 대상: {wafer_id} GPDO XML {len(self.xml_files)}개")

    @staticmethod
    def _match_wafer(xml_path: str, wafer_id: str) -> bool:
        """XML 내부 TestSiteInfo의 Wafer 속성으로 wafer_id 일치 여부 확인"""
        try:
            from lxml import etree
            with open(xml_path, "rb") as f:
                root = etree.parse(f).getroot()
            tsi = root.find("TestSiteInfo")
            return tsi is not None and tsi.get("Wafer", "") == wafer_id
        except Exception:
            return False

    def _process_one(self, xml_path: str) -> dict:
        """XML 1개 → 파싱 + 피팅 → 결과 dict"""
        raw = GPDOParser.parse(xml_path)
        fe  = FittingEngine

        # Reference
        ref_r    = fe.fit_reference(raw['L_ref'], raw['IL_ref'])
        idx_wl   = np.argmin(np.abs(raw['L_ref'] - raw['lc_wl']))
        IL_at_wl = raw['IL_ref'][idx_wl]

        # Dark Current
        df = fe.fit_dark_fwd(raw['V_dark'], raw['I_dark'])
        dr = fe.fit_dark_rev(raw['V_dark'], raw['I_dark'])

        # Light Current 피팅 (모델 파라미터용)
        lf = fe.fit_light(raw['V_light'], raw['I_light'], df, dr)

        # Photo Current = Light - Dark  →  Iph 추출
        pc  = fe.calc_photo_current(
            raw['V_light'], raw['I_light'],
            raw['V_dark'],  raw['I_dark'])
        Iph = pc['Iph']

        # Responsivity (Photo Current 기반 Iph 사용)
        resp = fe.calc_responsivity(Iph, raw['fiber_dbm'], IL_at_wl)

        return dict(
            **raw,
            ref_r=ref_r, IL_at_wl=IL_at_wl,
            df=df, dr=dr, lf=lf,
            pc=pc, resp=resp,
            # 히트맵용 flat 키
            Iph    = Iph,
            n_d    = df['n']  if df['ok'] else np.nan,
            Rs_d   = df['Rs'] if df['ok'] else np.nan,
            R_resp = resp['R_resp'],
            r2_fwd = df['r2'] if df['ok'] else np.nan,
            r2_lgt = lf['r2'] if lf['ok'] else np.nan,
        )

    def run(self, save_dir: str):
        """전체 파일 처리 + 그래프 저장 + 히트맵 저장"""
        os.makedirs(save_dir, exist_ok=True)
        self.results = []

        for i, fpath in enumerate(self.xml_files):
            fname = os.path.basename(fpath)
            print(f"[{i+1:2d}/{len(self.xml_files)}] {fname}")
            try:
                d = self._process_one(fpath)
                self.results.append(d)
                print(f"       n={d['n_d']:.3f}  Rs={d['Rs_d']:.2f}Ω  "
                      f"Iph={d['Iph']:.2e}A  R={d['R_resp']:.3f}A/W")
                Plotter.plot(d, d['ref_r'], d['df'], d['dr'],
                             d['lf'], d['pc'], d['resp'],
                             save_dir=save_dir)
            except Exception as e:
                print(f"       ⚠ 오류: {e}")

        print("\n📊 웨이퍼 히트맵 생성 중...")
        for key, title, unit, cmap in self.HEATMAP_PARAMS:
            HeatmapPlotter.plot(self.results, key, title, unit, cmap,
                                save_dir=save_dir)

        print(f"\n✅ 전체 분석 완료  |  📁 저장 위치: {save_dir}")
        return self.results
