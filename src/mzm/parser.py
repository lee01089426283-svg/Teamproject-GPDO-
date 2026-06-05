import os
import xml.etree.ElementTree as ET

import numpy as np

from config import DATA_DIR
from src.mzm.fitting import (
    parse_array, process_spectrum, process_iv,
    fit_mzi, SCRIPT_VERSION, SCRIPT_OWNER,
)


class MZMParser:
    MZM_KEYWORDS      = ("LMZC", "LMZO")
    MZM_FILENAME_TAG  = "DCM_LMZ"

    @staticmethod
    def _load_root(xml_path: str):
        return ET.parse(xml_path).getroot()

    @staticmethod
    def _find_tag(root, name: str):
        for elem in root.iter():
            if elem.tag.split('}')[-1].lower() == name.lower():
                return elem
        return None

    @classmethod
    def get_mzm_xmls(cls, wafer: str) -> list[tuple[str, str]]:
        base = os.path.join(DATA_DIR, wafer)
        if not os.path.isdir(base):
            return []
        results = []
        for date in sorted(os.listdir(base)):
            date_dir = os.path.join(base, date)
            if not os.path.isdir(date_dir):
                continue
            for fname in sorted(os.listdir(date_dir)):
                if fname.endswith('.xml') and cls.MZM_FILENAME_TAG in fname:
                    results.append((date, os.path.join(date_dir, fname)))
        return results

    @classmethod
    def is_mzm_xml(cls, xml_path: str) -> bool:
        try:
            if cls.MZM_FILENAME_TAG not in os.path.basename(xml_path):
                return False
            root = cls._load_root(xml_path)
            return cls.detect_device_type(root) in cls.MZM_KEYWORDS
        except Exception:
            return False

    @classmethod
    def detect_device_type(cls, root) -> str:
        tsi = root.find('.//{*}TestSiteInfo')
        if tsi is not None:
            ts = tsi.attrib.get('TestSite', '')
            if 'LMZC' in ts.upper():
                return 'LMZC'
            if 'LMZO' in ts.upper():
                return 'LMZO'
        for mod in root.findall('.//{*}Modulator'):
            name = mod.attrib.get('Name', '')
            if 'LMZC' in name.upper():
                return 'LMZC'
            if 'LMZO' in name.upper():
                return 'LMZO'
        return 'LMZC'

    @classmethod
    def parse(cls, xml_path: str) -> dict | None:
        data, _ = cls.parse_with_root(xml_path)
        return data

    @classmethod
    def parse_with_root(cls, xml_path: str) -> tuple:
        """XML을 1회만 파싱해 (data_dict, root) 를 함께 반환."""
        fname = os.path.basename(xml_path)
        try:
            root = cls._load_root(xml_path)
        except Exception as e:
            print(f'  [ERROR] XML 로드 실패 {fname}: {e}')
            return None, None
        return cls._extract(root, fname), root

    @classmethod
    def _extract(cls, root, filename: str) -> dict | None:
        data = {}
        tsi = root.find('.//{*}TestSiteInfo')
        if tsi is None:
            return None

        data['Lot']      = tsi.attrib.get('Batch')
        data['Wafer']    = tsi.attrib.get('Wafer')
        data['Mask']     = tsi.attrib.get('Maskset')
        data['Testsite'] = tsi.attrib.get('TestSite')
        data['Row']      = tsi.attrib.get('DieRow')
        data['Column']   = tsi.attrib.get('DieColumn')

        dev = root.find('.//{*}DeviceInfo')
        data['Name'] = dev.attrib.get('Name') if dev is not None else None

        data['Date']           = root.attrib.get('CreationDate')
        data['Script ID']      = os.path.splitext(os.path.basename(filename))[0]
        data['Script Version'] = SCRIPT_VERSION
        data['Script Owner']   = SCRIPT_OWNER
        data['Operator']       = root.attrib.get('Operator')

        ref_ws = cls._find_ref_sweep(root)
        rsq_ref, max_trans = (process_spectrum(ref_ws)
                              if ref_ws is not None else (None, None))
        data['Rsq of Ref. spectrum (Nth)']         = rsq_ref
        data['Max transmission of Ref. spec (dB)'] = max_trans

        iv_elem = root.find('.//{*}IVMeasurement')
        rsq_iv, i_neg1, i_pos1, n_fit = (process_iv(iv_elem)
                                          if iv_elem is not None
                                          else (None, None, None, None))
        data['Rsq of IV']       = rsq_iv
        data['I at -1V [A]']    = i_neg1
        data['I at 1V [A]']     = i_pos1
        data['Ideality Factor'] = n_fit

        aw = root.find('.//{*}AlignWavelength')
        if aw is not None and aw.text:
            data['Analysis Wavelength'] = aw.text.strip()
        else:
            data['Analysis Wavelength'] = None
            for dp in root.findall('.//{*}DesignParameter'):
                if 'wavelength' in dp.attrib.get('Name', '').lower():
                    data['Analysis Wavelength'] = (dp.text or '').strip()
                    break

        # ── MZI fitting: ER / FSR 추출 ──────────────────
        data['Extinction Ratio (dB)'] = None
        data['FSR (nm)']              = None

        ref_ws = cls._find_ref_sweep(root)
        ref_wl_arr = ref_dB_arr = None
        if ref_ws is not None:
            rl = ref_ws.find('L') or ref_ws.find('.//{*}L')
            ri = ref_ws.find('IL') or ref_ws.find('.//{*}IL')
            if rl is not None and ri is not None:
                ref_wl_arr = parse_array(rl.text)
                ref_dB_arr = parse_array(ri.text)

        device_type   = cls.detect_device_type(root)
        best_sweep    = None
        best_dist_mzi = 1e9
        for sweep in root.findall('.//{*}WavelengthSweep'):
            try:
                b = float(sweep.attrib.get('DCBias', 'nan'))
            except ValueError:
                continue
            if abs(b - (-1.0)) < best_dist_mzi:
                best_dist_mzi, best_sweep = abs(b - (-1.0)), sweep

        if best_sweep is not None:
            l_node  = best_sweep.find('L')  or best_sweep.find('.//{*}L')
            il_node = best_sweep.find('IL') or best_sweep.find('.//{*}IL')
            if l_node is not None and il_node is not None:
                try:
                    wl      = parse_array(l_node.text)
                    mzi_res = fit_mzi(wl, parse_array(il_node.text),
                                      device_type=device_type,
                                      ref_wl=ref_wl_arr, ref_dB=ref_dB_arr)
                    data['Extinction Ratio (dB)'] = round(mzi_res['ER'],  2)
                    data['FSR (nm)']              = round(mzi_res['FSR'], 4)
                except Exception:
                    pass

        errors = []
        if rsq_iv   is not None and rsq_iv   < 0.98:   errors.append('IV_fit')
        if rsq_ref  is not None and rsq_ref  < 0.95:   errors.append('Ref_fit')
        if max_trans is not None and max_trans < -10.0: errors.append('Low_transmission')
        data['ErrorFlag']         = len(errors)
        data['Error description'] = ', '.join(errors) if errors else 'No Error'

        return data

    @staticmethod
    def _find_ref_sweep(root):
        for mod in root.findall('.//{*}Modulator'):
            desc = mod.findtext('.//{*}DesignDescription') or ''
            name = mod.attrib.get('Name', '')
            if 'reference' in desc.lower() or 'align' in name.lower():
                for ws in mod.findall('.//{*}WavelengthSweep'):
                    if ws.attrib.get('DCBias', '').strip() == '0.0':
                        return ws
        for ws in root.findall('.//{*}WavelengthSweep'):
            if ws.attrib.get('DCBias', '').strip() == '0.0':
                return ws
        return None
