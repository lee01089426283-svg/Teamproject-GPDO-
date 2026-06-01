# ══════════════════════════════════════════════════════
# src/tocsv/gpdo_csv.py  –  GPDO 분석 결과 CSV 저장
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
    "fiber_dbm",
    "Iph",
    "n_d",
    "Rs_d",
    "R_resp",
    "peak_wl",
]


def _extract_row(result: dict, wafer_id: str, timestamp: str) -> dict:
    """_process_one() 반환 dict에서 CSV 한 행에 필요한 값만 추출."""
    return {
        "wafer_id"  : wafer_id,
        "timestamp" : timestamp,
        "col"       : result.get("col",       np.nan),
        "row"       : result.get("row",       np.nan),
        "lc_wl"     : result.get("lc_wl",     np.nan),
        "fiber_dbm" : result.get("fiber_dbm", np.nan),
        "Iph"       : result.get("Iph",       np.nan),
        "n_d"       : result.get("n_d",       np.nan),
        "Rs_d"      : result.get("Rs_d",      np.nan),
        "R_resp"    : result.get("R_resp",     np.nan),
        "peak_wl"   : result.get("peak_wl",   np.nan),
    }


def save_results(all_results: dict, wafer_id: str,
                 base_dir: str = "./res/csv") -> None:
    """
    GPDOAnalyzer.run() 이 반환하는 { timestamp: results_list } dict를 받아
    - res/csv/{wafer_id}_Result.csv  (해당 웨이퍼 단독)
    - res/csv/Total_Result.csv       (전체 누적)
    로 저장합니다.

    Parameters
    ----------
    all_results : { timestamp: [result_dict, ...] }
    wafer_id    : 'D08' 등 웨이퍼/다이 ID
    base_dir    : CSV 저장 루트 폴더 (기본값: ./res/csv)
    """
    os.makedirs(base_dir, exist_ok=True)

    # ── 1. 전체 행 수집 ───────────────────────────────
    rows = []
    for timestamp, results in all_results.items():
        for r in results:
            rows.append(_extract_row(r, wafer_id, timestamp))

    if not rows:
        print(f"[gpdo_csv] {wafer_id}: 저장할 결과가 없습니다.")
        return

    df = pd.DataFrame(rows, columns=COLUMNS)

    # ── 2. 웨이퍼별 CSV 저장 ─────────────────────────
    wafer_csv = os.path.join(base_dir, f"{wafer_id}_Result.csv")
    df.to_csv(wafer_csv, index=False, encoding="utf-8-sig")
    print(f"[gpdo_csv] {wafer_id} CSV 저장 완료 → {wafer_csv}")

    # ── 3. Total CSV 누적 저장 ────────────────────────
    total_csv = os.path.join(base_dir, "Total_Result.csv")
    if os.path.exists(total_csv):
        df_existing = pd.read_csv(total_csv, encoding="utf-8-sig")
        df_existing = df_existing[df_existing["wafer_id"] != wafer_id]
        df_total = pd.concat([df_existing, df], ignore_index=True)
    else:
        df_total = df

    df_total.to_csv(total_csv, index=False, encoding="utf-8-sig")
    print(f"[gpdo_csv] Total CSV 업데이트 완료 → {total_csv}")