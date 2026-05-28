# ══════════════════════════════════════════════════════
# config.py  –  경로 및 전역 설정
# ══════════════════════════════════════════════════════
import os

# 이 파일(config.py)이 있는 폴더 = 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 데이터 폴더 (XML 파일이 위치하는 루트) ─────────────
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── 결과 저장 루트 폴더 ────────────────────────────────
RES_DIR = os.path.join(BASE_DIR, "res")

# ── 처리할 웨이퍼 ID 목록 ─────────────────────────────
# 여기에 원하는 웨이퍼를 추가/제거하면 run.py 전체에 반영됨
WAFER_IDS = ["D07", "D08", "D23", "D24"]

# ── 디바이스 타입별 설정 ──────────────────────────────
# wafer_ids : 처리할 웨이퍼 ID 목록 (None 이면 WAFER_IDS 전체 사용)
# save_root : res/ 하위 저장 폴더명 규칙 → f"{wafer_id}-{save_root}"
DEVICE_CONFIG = {
    "GPDO": dict(
        wafer_ids = None,       # None → WAFER_IDS 전체 사용
        save_root = "GPDO",     # 실제 저장: res/D07-GPDO/, res/D08-GPDO/ ...
    ),
    "LMZC": dict(
        wafer_ids = None,
        save_root = "LMZC",
    ),
    "LMZO": dict(
        wafer_ids = None,
        save_root = "LMZO",
    ),
}