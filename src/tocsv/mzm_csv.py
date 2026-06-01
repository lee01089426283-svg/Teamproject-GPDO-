import os
import xml.etree.ElementTree as ET
import pandas as pd

from config import PROJECT_NAME, DATA_DIR, RES_DIR, WAFER_IDS
from src.fitting.mzm_fitting import parse_xml

COLUMNS_ORDER = [
    'Lot', 'Wafer', 'Mask', 'Testsite', 'Name', 'Date',
    'Script ID', 'Script Version', 'Script Owner', 'Operator',
    'Row', 'Column',
    'ErrorFlag', 'Error description',
    'Analysis Wavelength',
    'Rsq of Ref. spectrum (Nth)',
    'Max transmission of Ref. spec (dB)',
    'Rsq of IV',
    'I at -1V [A]',
    'I at 1V [A]',
]


def _get_mzm_xmls(wafer: str) -> list:
    base = os.path.join(DATA_DIR, wafer)
    if not os.path.isdir(base):
        return []
    results = []
    for date in sorted(os.listdir(base)):
        date_dir = os.path.join(base, date)
        if not os.path.isdir(date_dir):
            continue
        for fname in sorted(os.listdir(date_dir)):
            if fname.endswith('.xml') and 'DCM_LMZ' in fname:
                results.append((date, os.path.join(date_dir, fname)))
    return results


def _csv_dir() -> str:
    return os.path.join(RES_DIR, 'csv', 'MZM', PROJECT_NAME)

def _csv_path(wafer: str) -> str:
    return os.path.join(_csv_dir(), f'{wafer}.csv')

def _csv_total_path() -> str:
    return os.path.join(_csv_dir(), f'{PROJECT_NAME}_total.csv')


def generate_csv(wafer: str, verbose: bool = True) -> str:
    os.makedirs(_csv_dir(), exist_ok=True)
    xml_files = _get_mzm_xmls(wafer)

    if not xml_files:
        print(f'  [WARN] {wafer}: DCM_LMZ* XML 파일 없음')
        return ''

    if verbose:
        print(f'\n[{wafer}] CSV 생성 — {len(xml_files)}개 파일')

    rows = []
    for date, path in xml_files:
        fname = os.path.basename(path)
        if verbose:
            print(f'  파싱: {fname}')
        try:
            row = parse_xml(ET.parse(path).getroot(), fname)
            if row is not None:
                rows.append(row)
        except Exception as e:
            print(f'  [ERROR] {fname}: {e}')

    df  = pd.DataFrame(rows).reindex(columns=COLUMNS_ORDER)
    out = _csv_path(wafer)
    df.to_csv(out, index=False, encoding='utf-8-sig')

    if verbose:
        print(f'  → {len(df)}행 저장: {out}')
    return out


def generate_total_csv(verbose: bool = True) -> str:
    dfs = []
    for wafer in WAFER_IDS:
        p = _csv_path(wafer)
        if os.path.exists(p):
            dfs.append(pd.read_csv(p, encoding='utf-8-sig'))

    if not dfs:
        print('  [WARN] total CSV 생성 실패: 웨이퍼 CSV 없음')
        return ''

    df_total = pd.concat(dfs, ignore_index=True)
    out = _csv_total_path()
    df_total.to_csv(out, index=False, encoding='utf-8-sig')

    if verbose:
        print(f'\n[Total] {len(df_total)}행 저장: {out}')
    return out
