# ══════════════════════════════════════════════════════
# config.py  –  경로 및 전역 설정
# ══════════════════════════════════════════════════════
import os

# 이 파일(config.py)이 있는 폴더 = 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 데이터 루트 폴더 ──────────────────────────────────
_DATA_ROOT = os.path.join(BASE_DIR, "data")

# ── 결과 저장 루트 폴더 ────────────────────────────────
RES_DIR = os.path.join(BASE_DIR, "res")

# ── data/ 바로 아래 폴더들을 자동 탐색 ───────────────
# 예) data/HY202103/ → PROJECT_NAMES = ["HY202103"]
def _get_project_names() -> list[str]:
    if not os.path.isdir(_DATA_ROOT):
        return []
    return sorted([
        d for d in os.listdir(_DATA_ROOT)
        if os.path.isdir(os.path.join(_DATA_ROOT, d))
    ])

PROJECT_NAMES = _get_project_names()
PROJECT_NAME  = PROJECT_NAMES[0] if PROJECT_NAMES else ""

# ── 각 프로젝트 내 웨이퍼 ID 자동 탐색 ──────────────
def _get_wafer_ids(project_name: str) -> list[str]:
    project_dir = os.path.join(_DATA_ROOT, project_name)
    if not os.path.isdir(project_dir):
        return []
    return sorted([
        d for d in os.listdir(project_dir)
        if os.path.isdir(os.path.join(project_dir, d))
    ])

# DATA_DIR, WAFER_IDS는 첫 번째 프로젝트 기준 (하위 호환)
DATA_DIR  = os.path.join(_DATA_ROOT, PROJECT_NAME) if PROJECT_NAME else _DATA_ROOT
WAFER_IDS = _get_wafer_ids(PROJECT_NAME) if PROJECT_NAME else []

# ── 디바이스 타입별 설정 ──────────────────────────────
# wafer_ids : 처리할 웨이퍼 ID 목록 (None 이면 WAFER_IDS 전체 사용)
# save_root : res/ 하위 저장 폴더명 규칙 → f"{wafer_id}-{save_root}"
DEVICE_CONFIG = {
    "GPDO": dict(
        wafer_ids = None,       # None → WAFER_IDS 전체 사용
        save_root = "GPDO",     # 실제 저장: res/D07-GPDO/, res/D08-GPDO/ ...
    ),
    "MZM": dict(
        wafer_ids = None,
        save_root = "MZM",
    ),
}