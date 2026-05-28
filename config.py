# ══════════════════════════════════════════════════════
# config.py  –  경로 및 전역 설정
# ══════════════════════════════════════════════════════
import os

# 이 파일(config.py)이 있는 폴더 = 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 데이터 폴더 (XMLfile 하위 구조 자동 탐색) ──────────
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── 결과 저장 루트 폴더 ────────────────────────────────
RES_DIR = os.path.join(BASE_DIR, "res")

# ── 디바이스 타입별 설정 ──────────────────────────────
# key   : 디바이스 타입 식별자 (XML TestSite 속성에서 검색)
# value : (save_subdir, wafer_id)
DEVICE_CONFIG = {
    "GPDO": dict(
        save_subdir = "D08-GPDO",
        wafer_id    = "D08",
    ),
    "LMZC": dict(
        save_subdir = "D08-LMZC",
        wafer_id    = "D08",
    ),
    "LMZO": dict(
        save_subdir = "D08-LMZO",
        wafer_id    = "D08",
    ),
}
