#!/usr/bin/env python3
import matplotlib
matplotlib.use("Agg")

import sys
import os

# Windows 터미널 CP949 환경에서 UTF-8 출력 강제
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, RES_DIR, DEVICE_CONFIG, WAFER_IDS, PROJECT_NAME, PROJECT_NAMES, _DATA_ROOT, _get_wafer_ids
from src.gpdo import GPDOAnalyzer
from src.mzm import MZMAnalyzer
from src.gpdo.csv import save_results, save_total_csv as gpdo_save_total
from src.mzm.csv import generate_total_csv as mzm_save_total
from src.boxplot import generate_boxplots

RUNNER_REGISTRY: dict[str, type] = {
    "GPDO": GPDOAnalyzer,
    "MZM":  MZMAnalyzer,
}

PNG_SUBDIR = {
    "GPDO": "GPDO",
    "MZM":  "MZM",
}


def run_device_wafer(device_type: str, wafer_id: str,
                     data_dir: str = None, project_name: str = None) -> dict | None:
    data_dir     = data_dir     or DATA_DIR
    project_name = project_name or PROJECT_NAME

    cfg = DEVICE_CONFIG.get(device_type)
    if cfg is None:
        print(f"⚠  '{device_type}' 는 config.py 에 정의되지 않은 디바이스 타입입니다.")
        return None

    runner_cls = RUNNER_REGISTRY.get(device_type)
    if runner_cls is None:
        print(f"⚠  '{device_type}' 에 대응하는 분석기가 아직 구현되지 않았습니다.")
        return None

    png_sub = PNG_SUBDIR[device_type]

    print(f"\n{'='*60}")
    print(f"  디바이스: {device_type}  |  웨이퍼: {wafer_id}")
    print(f"  데이터 경로 : data/{project_name}/{wafer_id}/{{timestamp}}/")
    print(f"  저장 경로   : res/png/{png_sub}/{project_name}/{wafer_id}/{{timestamp}}/")
    print(f"{'='*60}")

    try:
        if device_type == "GPDO":
            png_dir  = os.path.join(RES_DIR, "png", "GPDO", project_name, wafer_id)
            analyzer = runner_cls(data_dir=data_dir, wafer_id=wafer_id)
            results  = analyzer.run(save_dir=png_dir)
            if not results:
                return None
            csv_dir  = os.path.join(RES_DIR, "csv", "GPDO", PROJECT_NAME)
            save_results(results, wafer_id=wafer_id, base_dir=csv_dir)
            return results
        else:  # MZM
            analyzer = runner_cls(wafer_id=wafer_id)
            csv_path, pngs = analyzer.run_wafer()
            if not csv_path and not pngs:
                print(f"  ⚠ {device_type} 데이터 없음: {wafer_id}")
                return None
            return {"csv": csv_path, "png": pngs}
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다:\n   {e}")
        return None
    except Exception as e:
        print(f"\n❌ '{device_type} / {wafer_id}' 처리 중 오류 발생:\n   {e}")
        return None


def main(targets: list[str] | None = None) -> dict[str, dict[str, list]]:
    if targets is None:
        targets = list(DEVICE_CONFIG.keys())

    all_results: dict[str, dict[str, list]] = {}

    for project_name in PROJECT_NAMES:
        wafer_ids = _get_wafer_ids(project_name)
        data_dir  = os.path.join(_DATA_ROOT, project_name)

        print(f"\n{'='*60}")
        print(f"  프로젝트: {project_name}  |  웨이퍼: {wafer_ids}")
        print(f"{'='*60}")

        plan: dict[str, list[str]] = {}
        for dtype in targets:
            cfg = DEVICE_CONFIG.get(dtype, {})
            plan[dtype] = cfg.get("wafer_ids") or wafer_ids

        total_jobs = sum(len(v) for v in plan.values())
        print(f"\n🚀 처리 대상: {targets}")
        print(f"   총 {total_jobs}개 작업 예정")

        for dtype in targets:
            if dtype not in all_results:
                all_results[dtype] = {}
            for wafer_id in plan[dtype]:
                res = run_device_wafer(dtype, wafer_id, data_dir=data_dir, project_name=project_name)
                if res is not None:
                    all_results[dtype][wafer_id] = res

    # Total CSV — 모든 웨이퍼 처리 후 한 번만
    if "GPDO" in targets:
        gpdo_csv_dir = os.path.join(RES_DIR, "csv", "GPDO", project_name)
        gpdo_save_total(gpdo_csv_dir)
    if "MZM" in targets:
        mzm_save_total(verbose=True)

    # Boxplot (Raincloud) — 실행된 디바이스만
    print(f"\n{'='*60}")
    print("  📊 Boxplot (Raincloud) 생성 중...")
    print(f"{'='*60}")
    gpdo_total  = os.path.join(RES_DIR, "csv", "GPDO", project_name, "Total_Result.csv") if "GPDO" in targets else None
    mzm_total   = os.path.join(RES_DIR, "csv", "MZM",  project_name, "Total_Result.csv") if "MZM"  in targets else None
    gpdo_bp_dir = os.path.join(RES_DIR, "png", "GPDO", project_name, "Total")            if "GPDO" in targets else None
    mzm_bp_dir  = os.path.join(RES_DIR, "png", "MZM",  project_name, "Total")            if "MZM"  in targets else None
    generate_boxplots(project_name, gpdo_total, mzm_total, gpdo_bp_dir, mzm_bp_dir)

    print(f"\n{'='*60}")
    print("  📋 실행 요약")
    print(f"{'='*60}")
    for dtype in targets:
        png_sub = PNG_SUBDIR.get(dtype, dtype)
        for wafer_id in plan[dtype]:
            base_path = f"res/png/{png_sub}/{project_name}/{wafer_id}"
            if wafer_id in all_results.get(dtype, {}):
                print(f"  ✅ {dtype:6s} / {wafer_id}  →  {base_path}/{{timestamp}}/")
            else:
                print(f"  ❌ {dtype:6s} / {wafer_id}  →  처리 실패 또는 건너뜀")
    print(f"{'='*60}\n")

    return all_results


if __name__ == "__main__":
    cli_targets = [t.upper() for t in sys.argv[1:]] if len(sys.argv) > 1 else None
    main(cli_targets)