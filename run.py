#!/usr/bin/env python3
# ══════════════════════════════════════════════════════
# run.py  –  실행 진입점  (GPDO / LMZC / LMZO 일괄 처리)
# ══════════════════════════════════════════════════════
"""
실행 방법
---------
    python run.py              # config.py 기준 전체 디바이스 처리
    python run.py GPDO         # GPDO 만 처리
    python run.py GPDO LMZC    # 복수 디바이스 선택 처리
"""

import matplotlib
matplotlib.use("Agg")   # GUI 없이 파일로만 저장

import sys
import os

# 프로젝트 루트를 sys.path 에 추가 (절대 import 보장)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, RES_DIR, DEVICE_CONFIG
from src.analyzer import GPDOAnalyzer


# ══════════════════════════════════════════════════════
# 디바이스 타입별 실행기 레지스트리
# 새 디바이스를 추가하려면 이 dict 에만 추가
# ══════════════════════════════════════════════════════
RUNNER_REGISTRY: dict[str, type] = {
    "GPDO": GPDOAnalyzer,
    # "LMZC": LMZCAnalyzer,   ← 추후 구현 시 주석 해제
    # "LMZO": LMZOAnalyzer,   ← 추후 구현 시 주석 해제
}


def run_device(device_type: str) -> list | None:
    """
    단일 디바이스 타입에 대한 파이프라인 실행.

    Parameters
    ----------
    device_type : DEVICE_CONFIG 의 키 (예: 'GPDO')

    Returns
    -------
    results 리스트 또는 실패 시 None
    """
    cfg = DEVICE_CONFIG.get(device_type)
    if cfg is None:
        print(f"⚠  '{device_type}' 는 config.py 에 정의되지 않은 디바이스 타입입니다.")
        return None

    runner_cls = RUNNER_REGISTRY.get(device_type)
    if runner_cls is None:
        print(f"⚠  '{device_type}' 에 대응하는 분석기가 아직 구현되지 않았습니다.")
        return None

    wafer_id   = cfg["wafer_id"]
    save_dir   = os.path.join(RES_DIR, cfg["save_subdir"])

    print(f"\n{'='*60}")
    print(f"  디바이스: {device_type}  |  웨이퍼: {wafer_id}")
    print(f"  데이터 경로 : {DATA_DIR}")
    print(f"  저장 경로   : {save_dir}")
    print(f"{'='*60}")

    try:
        analyzer = runner_cls(gpdo_dir=DATA_DIR, wafer_id=wafer_id)
        results  = analyzer.run(save_dir=save_dir)
        return results
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다:\n   {e}")
        return None
    except Exception as e:
        print(f"\n❌ '{device_type}' 처리 중 오류 발생:\n   {e}")
        return None


def main(targets: list[str] | None = None) -> dict[str, list]:
    """
    지정된 디바이스 타입(들)을 순차 실행.

    Parameters
    ----------
    targets : 처리할 디바이스 타입 목록.
              None 이면 DEVICE_CONFIG 전체를 처리.

    Returns
    -------
    {device_type: results_list} dict
    """
    if targets is None:
        targets = list(DEVICE_CONFIG.keys())

    print(f"\n🚀 처리 대상: {targets}")

    all_results: dict[str, list] = {}
    for dtype in targets:
        res = run_device(dtype)
        if res is not None:
            all_results[dtype] = res

    # ── 최종 요약 ─────────────────────────────────────
    print(f"\n{'='*60}")
    print("  📋 실행 요약")
    print(f"{'='*60}")
    for dtype in targets:
        if dtype in all_results:
            n = len(all_results[dtype])
            sub = DEVICE_CONFIG[dtype]["save_subdir"]
            print(f"  ✅ {dtype:6s}  →  {n}개 다이 처리  |  res/{sub}/")
        else:
            print(f"  ❌ {dtype:6s}  →  처리 실패 또는 건너뜀")
    print(f"{'='*60}\n")

    return all_results


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    # CLI 인수가 있으면 해당 타입만, 없으면 전체 실행
    cli_targets = sys.argv[1:] if len(sys.argv) > 1 else None
    main(cli_targets)
