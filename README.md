# GPDO Wafer Analyzer

> **Germanium Photodetector (GPDO) XML 측정 데이터를 자동으로 파싱·피팅·시각화하는 웨이퍼 분석 파이프라인**

---

## 왜 만들었나?

광소자 공정 연구에서 웨이퍼 한 장에는 수십 개의 GPDO 다이가 있고, 다이마다 XML 측정 파일이 생성됩니다.
이 파일들을 수작업으로 열어 그래프를 그리고 파라미터를 뽑아내는 작업은 시간이 오래 걸리고 실수가 생기기 쉽습니다.

이 프로젝트는 다음을 자동화합니다.

| 단계 | 내용 |
|------|------|
| **파싱** | GPDO XML에서 Dark/Light/Spectrum 전류, Reference IL 추출 |
| **피팅** | Shockley 다이오드 모델, Power-law 역바이어스, 광전류 계산 |
| **시각화** | 다이별 6-패널 PNG + 웨이퍼 전체 히트맵 |
| **CSV 출력** | 다이별 핵심 파라미터(Iph, n, R, peak λ 등) 정리 |

---

## 분석 파라미터 설명

| 파라미터 | 기호 | 설명 |
|----------|------|------|
| 광전류 | `Iph` | 역바이어스(-1.5V 이하)에서 Light − Dark 차감으로 추출한 포토커런트 |
| 이상계수 | `n_d` | Shockley 다이오드 이상계수. 1에 가까울수록 이상적인 pn 접합 |
| 응답도 | `R_resp` | 단위 광파워당 전류 [A/W]. GPDO 성능의 핵심 지표 |
| 측정 파장 | `lc_wl` | Light Current 측정에 사용된 단일 파장 [nm] |
| 스펙트럼 피크 파장 | `peak_wl` | 파장 스윕에서 전류가 최대인 파장 [nm] |
| 순방향 R² | `r2_fwd` | 순방향 Dark Current 피팅 결정계수 (1에 가까울수록 피팅 품질 우수) |
| 광전류 R² | `r2_photo` | 역바이어스 구간 광전류 포화 균일도 (1에 가까울수록 안정적인 포화) |

---

## 빠른 시작

### 1. 설치

```bash
pip install numpy scipy matplotlib lxml pandas
```

### 2. 데이터 배치

```
data/
└── HY202103/           ← config.py의 PROJECT_NAME과 일치
    ├── D08/
    │   └── 20190526_082853/
    │       ├── HY202103_D08_(-1,-1)_LION1_DCM_GPDO.xml
    │       └── ...
    └── D24/
        └── 20190531_151815/
            └── ...
```

### 3. 실행

```bash
# 전체 처리 (config.py에 정의된 모든 웨이퍼)
python run.py

# GPDO만 처리
python run.py GPDO

# 특정 디바이스 여러 개 선택
python run.py GPDO LMZC
```

### 4. 결과 확인

```
res/
├── D08-GPDO/
│   └── 20190526_082853/
│       ├── png/                                        ← 다이별 6-패널 분석 그래프
│       │   ├── HY202103_D08_(-1,-1)_LION1_DCM_GPDO.png
│       │   └── ...
│       └── heatmap/                                    ← 웨이퍼 히트맵
│           ├── heatmap_R_resp.png
│           └── heatmap_n_d.png
└── csv/
    ├── D08_Result.csv     ← 웨이퍼별 CSV
    └── Total_Result.csv   ← 전체 통합 CSV
```

---

## 출력 그래프 예시

### 다이 단위 6-패널 분석 그래프

```
┌─────────────────────┬─────────────────────┐
│ (a) Reference       │ (b) Dark Current     │
│     Spectrum        │     I–V [Log]        │
├─────────────────────┼─────────────────────┤
│ (c) Light Current   │ (d) Photo Current    │
│     I–V [Log]       │     [Log]            │
├─────────────────────┼─────────────────────┤
│ (e) Light Current   │ (f) Responsivity     │
│     Spectrum        │     R(λ) [A/W]       │
└─────────────────────┴─────────────────────┘
```

| 패널 | 내용 |
|------|------|
| (a) Reference Spectrum | 12차 다항식 피팅 + 최솟값 마커 |
| (b) Dark Current I–V | 순방향 Shockley + 역방향 Power-law |
| (c) Light Current I–V | 광전류 포함 Shockley 피팅 |
| (d) Photo Current | Light − Dark 차감 결과 |
| (e) Light Current Spectrum | 파장 스윕 전류 (피크 파장 강조) |
| (f) R(λ) | 파장별 Responsivity — 편도 IL 보정 적용 |

### 히트맵

웨이퍼 내 다이 위치(col, row)별로 **Responsivity** 와 **이상계수 n** 을 색상으로 표시합니다.
데이터가 없는 다이는 회색 `N/A` 로 표시됩니다.

---

## CSV 컬럼 설명

| 컬럼 | 단위 | 설명 |
|------|------|------|
| `wafer_id` | — | 웨이퍼 ID (D07, D08 등) |
| `timestamp` | — | 측정시간 폴더명 (`YYYYMMDD_HHMMSS`) |
| `col` / `row` | — | 다이 위치 (X / Y) |
| `lc_wl` | nm | Light Current 측정 파장 |
| `peak_wl` | nm | 스펙트럼 피크 파장 |
| `fiber_dbm` | dBm | 파이버 출력 파워 |
| `Iph` | A | 광전류 |
| `n_d` | — | 이상계수 (이상적: 1, 재결합 우세: 2) |
| `R_resp` | A/W | 응답도 |
| `r2_fwd` | — | 순방향 Dark Current 피팅 R² |
| `r2_photo` | — | 역바이어스 광전류 포화 균일도 R² |

---

## 프로젝트 구조

```
project/
├── run.py                      # 실행 진입점
├── config.py                   # 경로·웨이퍼·디바이스 설정
├── data/                       # 원본 XML (Git 미추적)
└── src/
    ├── parser/
    │   └── gpdo_parser.py      # XML 파싱 (GPDOParser)
    ├── fitting/
    │   └── fitting_engine.py   # 피팅 모델 + 연산 (FittingEngine)
    ├── plotting/
    │   ├── plotter.py          # 다이 6-패널 PNG (Plotter)
    │   └── heatmap_plotter.py  # 웨이퍼 히트맵 PNG (HeatmapPlotter)
    ├── analyzer/
    │   └── gpdo_analyzer.py    # 전체 파이프라인 통합 (GPDOAnalyzer)
    └── tocsv/
        └── gpdo_csv.py         # CSV 저장 (save_results)
```

---

## 설정 변경

### 웨이퍼 추가 / 제거

```python
# config.py
WAFER_IDS = ["D07", "D08", "D23", "D24"]
```

### 프로젝트 데이터셋 변경

```python
# config.py
PROJECT_NAME = "HY202103"   # data/ 바로 아래 폴더명과 일치
```

### 특정 디바이스에 다른 웨이퍼 셋 지정

```python
# config.py
DEVICE_CONFIG = {
    "GPDO": dict(
        wafer_ids = ["D08", "D24"],   # 이 디바이스만 D08·D24 처리
        save_root = "GPDO",
    ),
}
```

---

## 새 디바이스 추가 방법

LMZC, LMZO 등 다른 디바이스를 추가할 때:

1. `src/analyzer/` 에 새 분석기 클래스 작성 (`GPDOAnalyzer` 참고)
2. `config.py` → `DEVICE_CONFIG` 에 항목 추가
3. `run.py` → `RUNNER_REGISTRY` 에 등록

```python
# run.py
RUNNER_REGISTRY = {
    "GPDO": GPDOAnalyzer,
    "LMZC": LMZCAnalyzer,   # 주석 해제
}
```

---

## 환경

- Python 3.10 이상
- 의존 패키지: `numpy` `scipy` `matplotlib` `lxml` `pandas`
