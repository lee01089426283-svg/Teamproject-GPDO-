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

from config import DATA_DIR, RES_DIR, DEVICE_CONFIG, WAFER_IDS, PROJECT_NAME
from src.gpdo import GPDOAnalyzer
from src.mzm import MZMAnalyzer
from src.gpdo.csv import save_results
from src.mzm.csv import generate_total_csv as mzm_save_total

RUNNER_REGISTRY: dict[str, type] = {
    "GPDO": GPDOAnalyzer,
    "LMZC": MZMAnalyzer,
    "LMZO": MZMAnalyzer,
}

PNG_SUBDIR = {
    "GPDO": "GPDO",
    "LMZC": "MZM",
    "LMZO": "MZM",
}


def run_device_wafer(device_type: str, wafer_id: str) -> dict | None:
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
    print(f"  데이터 경로 : data/{PROJECT_NAME}/{wafer_id}/{{timestamp}}/")
    print(f"  저장 경로   : res/png/{png_sub}/{wafer_id}/{{timestamp}}/")
    print(f"{'='*60}")

    try:
        if device_type == "GPDO":
            png_dir  = os.path.join(RES_DIR, "png", "GPDO", wafer_id)
            analyzer = runner_cls(data_dir=DATA_DIR, wafer_id=wafer_id)
            results  = analyzer.run(save_dir=png_dir)
            csv_dir  = os.path.join(RES_DIR, "csv", "GPDO")
            save_results(results, wafer_id=wafer_id, base_dir=csv_dir)
            return results
        else:  # LMZC / LMZO
            analyzer = runner_cls()
            csv_rows, pngs = analyzer.run_wafer(wafer_id)
            if not pngs:
                print(f"  ⚠ MZM XML 없음: {wafer_id}")
            else:
                print(f"  총 {len(pngs)}개 PNG 저장 완료")
            return {"csv": csv_rows, "png": pngs} if csv_rows else None
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다:\n   {e}")
        return None
    except Exception as e:
        print(f"\n❌ '{device_type} / {wafer_id}' 처리 중 오류 발생:\n   {e}")
        return None


def main(targets: list[str] | None = None) -> dict[str, dict[str, list]]:
    if targets is None:
        targets = list(DEVICE_CONFIG.keys())

    plan: dict[str, list[str]] = {}
    for dtype in targets:
        cfg = DEVICE_CONFIG.get(dtype, {})
        plan[dtype] = cfg.get("wafer_ids") or WAFER_IDS

    total_jobs = sum(len(v) for v in plan.values())
    print(f"\n🚀 처리 대상: {targets}")
    print(f"   웨이퍼 목록: {WAFER_IDS}")
    print(f"   총 {total_jobs}개 작업 예정")

    all_results: dict[str, dict[str, list]] = {}

    for dtype in targets:
        all_results[dtype] = {}
        for wafer_id in plan[dtype]:
            res = run_device_wafer(dtype, wafer_id)
            if res is not None:
                all_results[dtype][wafer_id] = res

    if any(d in targets for d in ("LMZC", "LMZO")):
        mzm_save_total(verbose=True)

    print(f"\n{'='*60}")
    print("  📋 실행 요약")
    print(f"{'='*60}")
    for dtype in targets:
        for wafer_id in plan[dtype]:
            png_sub = PNG_SUBDIR.get(dtype, dtype)
            if wafer_id in all_results.get(dtype, {}):
                print(f"  ✅ {dtype:6s} / {wafer_id}  →  res/png/{png_sub}/{wafer_id}/")
            else:
                print(f"  ❌ {dtype:6s} / {wafer_id}  →  처리 실패 또는 건너뜀")
    print(f"{'='*60}\n")

    return all_results


if __name__ == "__main__":
    cli_targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(cli_targets)
