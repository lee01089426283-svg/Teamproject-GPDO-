#!/usr/bin/env python3
# ══════════════════════════════════════════════════════
# run.py  –  실행 진입점  (GPDO / LMZC / LMZO 일괄 처리)
# ══════════════════════════════════════════════════════
"""
---------
    python run.py                   # 전체 디바이스 × 전체 웨이퍼 처리
    python run.py GPDO              # GPDO 만 (전체 웨이퍼)
    python run.py GPDO LMZC        # 복수 디바이스 선택 (전체 웨이퍼)
실행 방법

결과 폴더 구조
--------------
    res/
    ├── D07-GPDO/
    ├── D08-GPDO/
    ├── D23-GPDO/
    ├── D24-GPDO/
    └── csv/
        ├── D07_Result.csv
        ├── D08_Result.csv
        ├── D23_Result.csv
        ├── D24_Result.csv
        └── Total_Result.csv
"""

import matplotlib
matplotlib.use("Agg")   # GUI 없이 파일로만 저장

import sys
import os

# 프로젝트 루트를 sys.path 에 추가 (절대 import 보장)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, RES_DIR, DEVICE_CONFIG, WAFER_IDS, PROJECT_NAME
from src.analyzer import GPDOAnalyzer
from src.tocsv.gpdo_csv import save_results


# ══════════════════════════════════════════════════════
# 디바이스 타입별 실행기 레지스트리
# 새 디바이스를 추가하려면 이 dict 에만 추가
# ══════════════════════════════════════════════════════
RUNNER_REGISTRY: dict[str, type] = {
    "GPDO": GPDOAnalyzer,
    # "LMZC": LMZCAnalyzer,   ← 추후 구현 시 주석 해제
    # "LMZO": LMZOAnalyzer,   ← 추후 구현 시 주석 해제
}


def run_device_wafer(device_type: str, wafer_id: str) -> dict | None:
    """
    디바이스 타입 × 웨이퍼 ID 1쌍에 대한 파이프라인 실행.

    Parameters
    ----------
    device_type : DEVICE_CONFIG 의 키 (예: 'GPDO')
    wafer_id    : 처리할 웨이퍼 ID (예: 'D07')

    Returns
    -------
    { timestamp: results_list } dict 또는 실패 시 None
    """
    cfg = DEVICE_CONFIG.get(device_type)
    if cfg is None:
        print(f"⚠  '{device_type}' 는 config.py 에 정의되지 않은 디바이스 타입입니다.")
        return None

    runner_cls = RUNNER_REGISTRY.get(device_type)
    if runner_cls is None:
        print(f"⚠  '{device_type}' 에 대응하는 분석기가 아직 구현되지 않았습니다.")
        return None

    # res/{wafer_id}-{save_root}/  예: res/D08-GPDO/
    save_dir = os.path.join(RES_DIR, f"{wafer_id}-{cfg['save_root']}")

    print(f"\n{'='*60}")
    print(f"  디바이스: {device_type}  |  웨이퍼: {wafer_id}")
    print(f"  데이터 경로 : data/{PROJECT_NAME}/{wafer_id}/{{timestamp}}/")
    print(f"  저장 경로   : res/{wafer_id}-{cfg['save_root']}/{{timestamp}}/")
    print(f"{'='*60}")

    try:
        analyzer    = runner_cls(data_dir=DATA_DIR, wafer_id=wafer_id)
        results     = analyzer.run(save_dir=save_dir)

        # ── CSV 저장 ──────────────────────────────────
        csv_dir = os.path.join(RES_DIR, "csv")
        save_results(results, wafer_id=wafer_id, base_dir=csv_dir)

        return results
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다:\n   {e}")
        return None
    except Exception as e:
        print(f"\n❌ '{device_type} / {wafer_id}' 처리 중 오류 발생:\n   {e}")
        return None


def main(targets: list[str] | None = None) -> dict[str, dict[str, list]]:
    """
    지정된 디바이스 타입 × 전체 웨이퍼를 순차 실행.

    Parameters
    ----------
    targets : 처리할 디바이스 타입 목록.
              None 이면 DEVICE_CONFIG 전체를 처리.

    Returns
    -------
    { device_type: { wafer_id: results_list } } 중첩 dict
    """
    if targets is None:
        targets = list(DEVICE_CONFIG.keys())

    # 각 디바이스의 웨이퍼 목록 결정
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

    # ── 최종 요약 ─────────────────────────────────────
    print(f"\n{'='*60}")
    print("  📋 실행 요약")
    print(f"{'='*60}")
    for dtype in targets:
        cfg = DEVICE_CONFIG.get(dtype, {})
        for wafer_id in plan[dtype]:
            save_root   = cfg.get('save_root', dtype)
            save_subdir = f"{wafer_id}-{save_root}"
            if wafer_id in all_results.get(dtype, {}):
                ts_dict = all_results[dtype][wafer_id]   # {timestamp: results}
                n_ts    = len(ts_dict)
                n_dies  = sum(len(v) for v in ts_dict.values())
                print(f"  ✅ {dtype:6s} / {wafer_id}  →  "
                      f"{n_ts}개 측정시간  |  총 {n_dies}개 다이  "
                      f"|  res/{save_subdir}/")
                for ts in sorted(ts_dict):
                    print(f"       📁 {ts}  →  {len(ts_dict[ts])}개 다이")
            else:
                print(f"  ❌ {dtype:6s} / {wafer_id}  →  처리 실패 또는 건너뜀")
    print(f"{'='*60}\n")

    return all_results


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    # CLI 인수가 있으면 해당 타입만, 없으면 전체 실행
    cli_targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(cli_targets)
