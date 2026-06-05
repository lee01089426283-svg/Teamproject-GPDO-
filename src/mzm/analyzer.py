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
    def run_wafer(self, wafer_id: str) -> tuple[str, list]:
        xml_files = MZMParser.get_mzm_xmls(wafer_id)
        if not xml_files:
            print(f'  [WARN] {wafer_id}: MZM XML 없음')
            return '', []

        pngs        = []
        parsed_rows = []
        ts_data: dict[str, list] = defaultdict(list)

        print(f'  📂 {wafer_id}  →  {len(xml_files)}개 파일')
        for date, xml_file in xml_files:
            # XML 파싱 1회 → CSV + 히트맵 재사용
            try:
                parsed = MZMParser.parse(xml_file)
                if parsed is not None:
                    parsed_rows.append(parsed)
                    ts_data[date].append(parsed)
            except Exception as e:
                print(f'  [WARN] 파싱 실패 {os.path.basename(xml_file)}: {e}')

            # PNG 생성 (Plotter 내부에서 XML 재사용 불가)
            out = Plotter.plot(xml_file, save_dir=_png_dir(wafer_id, date), verbose=True)
            if out:
                pngs.append(out)

        # 파싱 결과로 CSV 저장 (별도 parse 없이 재사용)
        csv_path = save_rows_to_csv(wafer_id, parsed_rows, verbose=True)

        self._plot_heatmaps_by_timestamp(ts_data, wafer_id)
        return csv_path, pngs

    def run(self, verbose: bool = True) -> tuple[dict, dict]:
        csv_results = {}
        png_results = {}

        for wafer in WAFER_IDS:
            print(f'\n{"─"*50}')
            print(f'  Wafer: {wafer}')
            print(f'{"─"*50}')

            csv_path, pngs = self.run_wafer(wafer)
            csv_results[wafer] = csv_path
            png_results[wafer] = pngs

        print(f'\n{"─"*50}')
        generate_total_csv(verbose=verbose)

        return csv_results, png_results

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
