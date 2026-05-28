# ══════════════════════════════════════════════════════
# src/parser/gpdo_parser.py  –  XML 파싱
# ══════════════════════════════════════════════════════
import os
import numpy as np
from lxml import etree


class GPDOParser:
    """
    XML 1개를 파싱하여 원시 데이터 dict 반환.

    is_gpdo_xml()  : GPDO 구조 검증 (TestSite 키워드 + 필수 포트)
    is_device_xml(): 임의 키워드로 디바이스 타입 검증 (LMZC / LMZO 확장용)
    parse()        : 데이터 추출 → dict 반환
    """

    # ── GPDO 판별 기준 ────────────────────────────────
    GPDO_TESTSITE_KEYWORD = "GPDO"
    GPDO_REQUIRED_PORTS   = ["REFIN_TE", "IN_TE_3"]

    # ── 공통 헬퍼 ─────────────────────────────────────

    @staticmethod
    def _arr(element, tag) -> np.ndarray:
        """XML 태그 내 쉼표 구분 숫자열 → numpy 배열"""
        return np.array([float(x)
                         for x in element.find(tag).text.strip().split(",")])

    @staticmethod
    def _load_root(xml_path: str):
        with open(xml_path, "rb") as f:
            return etree.parse(f).getroot()

    # ── 검증 메서드 ───────────────────────────────────

    @classmethod
    def is_gpdo_xml(cls, xml_path: str) -> bool:
        """
        GPDO XML 파일 여부를 두 단계로 검증.

        ① TestSiteInfo.TestSite 속성에 'GPDO' 포함
        ② 필수 PortLossMeasurement (REFIN_TE, IN_TE_3) 존재
        """
        return cls.is_device_xml(
            xml_path,
            testsite_keyword = cls.GPDO_TESTSITE_KEYWORD,
            required_ports   = cls.GPDO_REQUIRED_PORTS,
        )

    @classmethod
    def is_device_xml(cls, xml_path: str,
                      testsite_keyword: str,
                      required_ports: list[str] | None = None) -> bool:
        """
        범용 디바이스 XML 검증 메서드.

        Parameters
        ----------
        testsite_keyword : TestSiteInfo.TestSite 에 포함되어야 하는 문자열
        required_ports   : PortLossMeasurement Left 속성에 존재해야 하는 포트 목록
                           None 이면 포트 검사 생략
        """
        try:
            root = cls._load_root(xml_path)

            # 1단계: TestSite 속성 검사
            tsi = root.find("TestSiteInfo")
            if tsi is None:
                return False
            test_site = tsi.get("TestSite", "")
            if testsite_keyword.lower() not in test_site.lower():
                return False

            # 2단계: 필수 포트 태그 검사
            if required_ports:
                existing_ports = {
                    pm.get("Left")
                    for pm in root.findall(".//PortLossMeasurement")
                }
                for port in required_ports:
                    if port not in existing_ports:
                        return False

            return True

        except Exception:
            return False

    # ── 파싱 ──────────────────────────────────────────

    @classmethod
    def parse(cls, xml_path: str) -> dict:
        """
        GPDO XML → 원시 측정 데이터 dict.

        반환 키
        -------
        fname, col, row, fiber_dbm,
        L_ref, IL_ref,
        V_dark, I_dark,
        V_light, I_light,
        L_spec, I_spec,
        lc_wl, lcs_bias
        """
        fname = os.path.basename(xml_path)
        root  = cls._load_root(xml_path)

        # ── 위치 정보 (파일명 의존 없이 XML 내부 값 사용) ──
        tsi = root.find("TestSiteInfo")
        col = int(tsi.get("DieColumn", 0))
        row = int(tsi.get("DieRow",    0))

        # ── 설정 정보 ────────────────────────────────────
        si        = root.find("SetupInfo")
        fiber_dbm = float(si.find("FiberOutput").text.split()[0])

        # ── 레퍼런스 포트 ─────────────────────────────────
        ref  = root.find(".//PortLossMeasurement[@Left='REFIN_TE']")
        mr   = ref.find("MeasurementResult")

        # ── 검출기 포트 ───────────────────────────────────
        det  = root.find(".//PortLossMeasurement[@Left='IN_TE_3']")
        lc_e = det.find("LightCurrent")
        lcs_e= det.find("LightCurrentSpectrum")

        return dict(
            fname     = fname,
            col       = col,
            row       = row,
            fiber_dbm = fiber_dbm,
            # Reference
            L_ref     = cls._arr(mr, "L"),
            IL_ref    = cls._arr(mr, "IL"),
            # Dark Current
            V_dark    = cls._arr(det.find("DarkCurrent"), "V"),
            I_dark    = cls._arr(det.find("DarkCurrent"), "I"),
            # Light Current (단일 파장)
            V_light   = cls._arr(lc_e, "V"),
            I_light   = cls._arr(lc_e, "I"),
            # Light Current Spectrum (파장 스윕)
            L_spec    = cls._arr(lcs_e, "L"),
            I_spec    = cls._arr(lcs_e, "I"),
            # 메타
            lc_wl     = float(lc_e.get("Wavelength")),
            lcs_bias  = lcs_e.get("DCBias"),
        )
