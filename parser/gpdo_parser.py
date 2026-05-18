# ══════════════════════════════════════════════════════
# parser/gpdo_parser.py  –  XML 파싱
# ══════════════════════════════════════════════════════
import os
import numpy as np
from lxml import etree

# ── GPDO XML 판별 기준 ────────────────────────────────
# TestSiteInfo의 TestSite 속성에 포함되어야 하는 키워드
GPDO_TESTSITE_KEYWORD = "GPDO"

# XML 내부에 반드시 존재해야 하는 PortLossMeasurement Left 속성값
GPDO_REQUIRED_PORTS = [
    "REFIN_TE",   # 레퍼런스 포트
    "IN_TE_3",    # 검출기 포트
]


class GPDOParser:
    """XML 1개를 파싱하여 원시 데이터 dict 반환"""

    @staticmethod
    def is_gpdo_xml(xml_path: str) -> bool:
        """
        GPDO XML 파일인지 두 단계로 검증.

        ① XML 내부 TestSiteInfo의 TestSite 속성에 'GPDO' 포함 여부
        ② 필수 PortLossMeasurement (REFIN_TE, IN_TE_3) 존재 여부

        두 조건을 모두 만족해야 True 반환.
        """
        try:
            with open(xml_path, "rb") as f:
                root = etree.parse(f).getroot()

            # ── 1단계: TestSite 속성 검사 ──────────────
            tsi = root.find("TestSiteInfo")
            if tsi is None:
                return False
            test_site = tsi.get("TestSite", "")
            if GPDO_TESTSITE_KEYWORD.lower() not in test_site.lower():
                return False

            # ── 2단계: 필수 포트 태그 존재 검사 ───────
            existing_ports = {
                pm.get("Left")
                for pm in root.findall(".//PortLossMeasurement")
            }
            for required in GPDO_REQUIRED_PORTS:
                if required not in existing_ports:
                    return False

            return True

        except Exception:
            return False

    @staticmethod
    def _arr(element, tag):
        return np.array([float(x)
                         for x in element.find(tag).text.strip().split(",")])

    @classmethod
    def parse(cls, xml_path: str) -> dict:
        fname = os.path.basename(xml_path)

        with open(xml_path, "rb") as f:
            root = etree.parse(f).getroot()

        # ── col, row: TestSiteInfo 속성에서 직접 읽기 ──
        # 파일명 패턴(HY202103_D08__0_0__LION1_DCM_GPDO.xml)에
        # 의존하지 않고 XML 내부 값을 사용
        tsi = root.find("TestSiteInfo")
        col = int(tsi.get("DieColumn", 0))
        row = int(tsi.get("DieRow",    0))

        si        = root.find("SetupInfo")
        fiber_dbm = float(si.find("FiberOutput").text.split()[0])

        ref  = root.find(".//PortLossMeasurement[@Left='REFIN_TE']")
        mr   = ref.find("MeasurementResult")
        det  = root.find(".//PortLossMeasurement[@Left='IN_TE_3']")
        lc_e = det.find("LightCurrent")
        lcs_e= det.find("LightCurrentSpectrum")

        return dict(
            fname    = fname,
            col      = col,
            row      = row,
            fiber_dbm= fiber_dbm,
            L_ref    = cls._arr(mr, "L"),
            IL_ref   = cls._arr(mr, "IL"),
            V_dark   = cls._arr(det.find("DarkCurrent"), "V"),
            I_dark   = cls._arr(det.find("DarkCurrent"), "I"),
            V_light  = cls._arr(lc_e, "V"),
            I_light  = cls._arr(lc_e, "I"),
            L_spec   = cls._arr(lcs_e, "L"),
            I_spec   = cls._arr(lcs_e, "I"),
            lc_wl    = float(lc_e.get("Wavelength")),
            lcs_bias = lcs_e.get("DCBias"),
        )
