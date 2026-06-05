# ══════════════════════════════════════════════════════
# src/gpdo/csv.py  –  GPDO 분석 결과 CSV 저장
# ══════════════════════════════════════════════════════
import os
import numpy as np
import pandas as pd


# CSV에 추출할 컬럼 목록
COLUMNS = [
    "wafer_id",
    "timestamp",
    "col",
    "row",
    "lc_wl",
    "peak_wl",
    "fiber_dbm",
    "Iph",
    "n_d",
    "R_resp",
]


def _extract_row(result: dict, wafer_id: str, timestamp: str) -> dict:
    """_process_one() 반환 dict에서 CSV 한 행에 필요한 값만 추출."""
    return {
        "wafer_id"  : wafer_id,
        "timestamp" : timestamp,
        "col"       : result.get("col",       np.nan),
        "row"       : result.get("row",       np.nan),
        "lc_wl"     : result.get("lc_wl",     np.nan),
        "peak_wl"   : result.get("peak_wl",   np.nan),
        "fiber_dbm" : result.get("fiber_dbm", np.nan),
        "Iph"       : result.get("Iph",       np.nan),
        "n_d"       : result.get("n_d",       np.nan),
        "R_resp"    : result.get("R_resp",     np.nan),
    }


def save_results(all_results: dict, wafer_id: str,
                 base_dir: str = "./res/csv") -> None:
    """웨이퍼별 CSV만 저장. Total CSV는 save_total_csv()로 별도 호출."""
    os.makedirs(base_dir, exist_ok=True)

    rows = []
    for timestamp, results in all_results.items():
        for r in results:
            rows.append(_extract_row(r, wafer_id, timestamp))

    if not rows:
        print(f"[gpdo_csv] {wafer_id}: 저장할 결과가 없습니다.")
        return

    df = pd.DataFrame(rows, columns=COLUMNS)
    wafer_csv = os.path.join(base_dir, f"{wafer_id}_Result.csv")
    df.to_csv(wafer_csv, index=False, encoding="utf-8-sig")
    print(f"[gpdo_csv] {wafer_id} CSV 저장 완료 → {wafer_csv}")


def save_total_csv(base_dir: str) -> None:
    """base_dir 내 모든 웨이퍼 CSV를 합쳐 Total_Result.csv 생성 (마지막에 한 번 호출)."""
    wafer_csvs = sorted([
        os.path.join(base_dir, f)
        for f in os.listdir(base_dir)
        if f.endswith("_Result.csv") and f != "Total_Result.csv"
    ]) if os.path.isdir(base_dir) else []

    if not wafer_csvs:
        print("[gpdo_csv] Total CSV 생성 실패: 웨이퍼 CSV 없음")
        return

    df_total = pd.concat(
        [pd.read_csv(p, encoding="utf-8-sig") for p in wafer_csvs],
        ignore_index=True,
    )
    total_csv = os.path.join(base_dir, "Total_Result.csv")
    df_total.to_csv(total_csv, index=False, encoding="utf-8-sig")
    print(f"[gpdo_csv] Total CSV 업데이트 완료 → {total_csv}")
