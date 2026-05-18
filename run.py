# ══════════════════════════════════════════════════════
# run.py  –  실행 진입점
# ══════════════════════════════════════════════════════
import matplotlib
matplotlib.use("Agg")  # 화면 출력 없이 파일만 저장

import sys
import os

# 프로젝트 루트를 sys.path에 추가 (상대 import 보장)
sys.path.insert(0, os.path.dirname(__file__))

from config import GPDO_DIR, SAVE_DIR, WAFER_ID
from analyzer import GPDOAnalyzer


if __name__ == "__main__":
    analyzer = GPDOAnalyzer(gpdo_dir=GPDO_DIR, wafer_id=WAFER_ID)
    results  = analyzer.run(save_dir=SAVE_DIR)
