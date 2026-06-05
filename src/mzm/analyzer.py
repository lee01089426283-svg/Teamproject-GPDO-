import os
from collections import defaultdict

from config import RES_DIR, PROJECT_NAME, WAFER_IDS
from src.mzm.parser import MZMParser
from src.mzm.plotter import Plotter
from src.mzm.csv import save_rows_to_csv, generate_total_csv
from src.heatmap_plotter import HeatmapPlotter


def _png_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', PROJECT_NAME, wafer, date)

def _heatmap_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', PROJECT_NAME, wafer, date, 'heatmap')


class MZMAnalyzer:
    def __init__(self, wafer_id: str):
        self.wafer_id = wafer_id

    def run_wafer(self) -> tuple[str, list]:
        wafer_id = self.wafer_id
        xml_files = MZMParser.get_mzm_xmls(self.wafer_id)
        if not xml_files:
            print(f'  [WARN] {self.wafer_id}: MZM XML 없음')
            return '', []

        pngs        = []
        parsed_rows = []
        ts_data: dict[str, list] = defaultdict(list)

        print(f'  📂 {wafer_id}  →  {len(xml_files)}개 파일')
        for date, xml_file in xml_files:
            fname = os.path.basename(xml_file)

            # XML 1회 파싱 → parsed dict + root 동시 획득
            try:
                parsed, root = MZMParser.parse_with_root(xml_file)
            except Exception as e:
                print(f'  [WARN] 파싱 실패 {fname}: {e}')
                parsed, root = None, None

            # CSV + 히트맵용 데이터 수집
            if parsed is not None:
                parsed['timestamp'] = date   # GPDO와 동일하게 폴더명 timestamp 추가
                parsed_rows.append(parsed)
                ts_data[date].append(parsed)

            # PNG 생성 — 이미 로드된 root 재사용 (XML 재파싱 없음)
            if root is not None:
                out = Plotter.plot_from_root(
                    root, fname,
                    save_dir=_png_dir(wafer_id, date),
                    verbose=True,
                )
                if out:
                    pngs.append(out)

        # 파싱 결과로 CSV 저장 (별도 parse 없이 재사용)
        csv_path = save_rows_to_csv(self.wafer_id, parsed_rows, verbose=True)

        self._plot_heatmaps_by_timestamp(ts_data, self.wafer_id)
        return csv_path, pngs

    @staticmethod
    def _plot_heatmaps_by_timestamp(ts_data: dict, wafer: str) -> None:
        for date, rows in ts_data.items():
            if not rows:
                continue
            save_dir = _heatmap_dir(wafer, date)
            print(f'  📊 [{wafer}/{date}] 히트맵 생성 중...')
            HeatmapPlotter.plot_mzm_all_from_rows(
                rows=rows,
                wafer_id=wafer,
                save_dir=save_dir,
            )
