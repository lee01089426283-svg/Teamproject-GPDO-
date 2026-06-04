import os
from collections import defaultdict

from config import RES_DIR, PROJECT_NAME, WAFER_IDS
from src.mzm.parser import MZMParser
from src.mzm.plotter import Plotter
from src.mzm.csv import generate_csv, generate_total_csv
from src.heatmap_plotter import HeatmapPlotter


def _png_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', PROJECT_NAME, wafer, date)

def _heatmap_dir(wafer: str, date: str) -> str:
    return os.path.join(RES_DIR, 'png', 'MZM', PROJECT_NAME, wafer, date, 'heatmap')

def _csv_dir() -> str:
    return os.path.join(RES_DIR, 'csv', 'MZM', PROJECT_NAME)

def _csv_path(wafer: str) -> str:
    return os.path.join(_csv_dir(), f'{wafer}.csv')


class MZMAnalyzer:
    def run(self, verbose: bool = True) -> tuple[dict, dict]:
        csv_results = {}
        png_results = {}

        for wafer in WAFER_IDS:
            print(f'\n{"─"*50}')
            print(f'  Wafer: {wafer}')
            print(f'{"─"*50}')

            csv_results[wafer] = generate_csv(wafer, verbose=verbose)

            xml_files = MZMParser.get_mzm_xmls(wafer)
            if not xml_files:
                print(f'  [WARN] {wafer}: MZM XML 없음 → PNG/히트맵 생성 건너뜀')
                png_results[wafer] = []
                continue

            print(f'\n  [{wafer}] PNG 생성 시작 — {len(xml_files)}개 파일')
            pngs = []
            ts_data: dict[str, list] = defaultdict(list)

            for date, xml_file in xml_files:
                out = Plotter.plot(
                    xml_file,
                    save_dir=_png_dir(wafer, date),
                    verbose=verbose,
                )
                if out:
                    pngs.append(out)

                try:
                    parsed = MZMParser.parse(xml_file)
                    if parsed is not None:
                        ts_data[date].append(parsed)
                except Exception as e:
                    print(f'  [WARN] 히트맵 파싱 실패 {os.path.basename(xml_file)}: {e}')

            png_results[wafer] = pngs

            self._plot_heatmaps_by_timestamp(ts_data, wafer)

        print(f'\n{"─"*50}')
        generate_total_csv(verbose=verbose)

        return csv_results, png_results

    @staticmethod
    def _plot_heatmaps_by_timestamp(ts_data: dict, wafer: str) -> None:
        for date, rows in ts_data.items():
            if not rows:
                continue
            save_dir = _heatmap_dir(wafer, date)
            print(f'\n  [{wafer}/{date}] 히트맵 생성 — {len(rows)}개 다이')
            HeatmapPlotter.plot_mzm_all_from_rows(
                rows=rows,
                wafer_id=wafer,
                save_dir=save_dir,
            )
