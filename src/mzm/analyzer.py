import os
from collections import defaultdict

from config import RES_DIR, PROJECT_NAME, WAFER_IDS
from src.mzm.parser import MZMParser
from src.mzm.plotter import Plotter
from src.mzm.csv import generate_csv, generate_total_csv
from src.heatmap_plotter import HeatmapPlotter


def _png_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', wafer, date)

def _heatmap_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', wafer, date, 'heatmap')

def _csv_dir() -> str:
    return os.path.join(RES_DIR, 'csv', 'MZM', PROJECT_NAME)

def _csv_path(wafer: str) -> str:
    return os.path.join(_csv_dir(), f'{wafer}.csv')


class MZMAnalyzer:
    def run_wafer(self, wafer_id: str) -> tuple[list, list]:
        csv_rows = generate_csv(wafer_id, verbose=True)

        xml_files = MZMParser.get_mzm_xmls(wafer_id)
        if not xml_files:
            return csv_rows, []

        pngs = []
        ts_data: dict[str, list] = defaultdict(list)

        print(f'  📂 {wafer_id}  →  {len(xml_files)}개 파일')
        for date, xml_file in xml_files:
            out = Plotter.plot(
                xml_file,
                save_dir=_png_dir(wafer_id, date),
                verbose=True,
            )
            if out:
                pngs.append(out)

            try:
                parsed = MZMParser.parse(xml_file)
                if parsed is not None:
                    ts_data[date].append(parsed)
            except Exception as e:
                print(f'  [WARN] 히트맵 파싱 실패 {os.path.basename(xml_file)}: {e}')

        self._plot_heatmaps_by_timestamp(ts_data, wafer_id)
        return csv_rows, pngs

    def run(self, verbose: bool = True) -> tuple[dict, dict]:
        csv_results = {}
        png_results = {}

        for wafer in WAFER_IDS:
            print(f'\n{"─"*50}')
            print(f'  Wafer: {wafer}')
            print(f'{"─"*50}')

            csv_rows, pngs = self.run_wafer(wafer)
            csv_results[wafer] = csv_rows
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
