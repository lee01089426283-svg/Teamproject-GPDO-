# ══════════════════════════════════════════════════════
# config.py  –  경로 및 전역 설정
# ══════════════════════════════════════════════════════
import os

# 이 파일(config.py)이 있는 폴더 = 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# XML 데이터가 있는 폴더 (프로젝트 루트 기준 상대경로)
GPDO_DIR = os.path.join(BASE_DIR, "XMLfile")

# 결과 이미지 저장 폴더 (프로젝트 루트 기준 상대경로)
SAVE_DIR = os.path.join(BASE_DIR, "results")

# 분석 대상 웨이퍼 ID
WAFER_ID = "D08"
