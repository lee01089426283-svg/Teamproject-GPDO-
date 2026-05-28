# Teamproject-GPDO-
# GPDO Analyzer

GPDO XML 측정 데이터를 파싱·피팅·시각화하는 웨이퍼 분석 파이프라인입니다.

---

## 프로젝트 구조

```
project/
├── run.py                      # 실행 진입점
├── config.py                   # 경로 및 전역 설정
├── .gitattributes              # 줄바꿈 통일 설정 (LF)
├── data/
│   ├── .gitignore              # XML 파일 Git 추적 제외
│   └── HY202103/               # 프로젝트명 폴더 (PROJECT_NAME)
│       ├── D07/
│       │   └── 20190526_082853/
│       │       └── *.xml
│       ├── D08/
│       │   └── 20190526_082853/
│       │       └── *.xml
│       ├── D23/
│       └── D24/
├── res/                        # 분석 결과 PNG 자동 저장
│   ├── D07-GPDO/
│   │   └── 20190526_082853/
│   ├── D08-GPDO/
│   │   └── 20190526_082853/
│   ├── D23-GPDO/
│   └── D24-GPDO/
└── src/
    ├── parser/
    │   └── gpdo_parser.py      # XML 파싱
    ├── fitting/
    │   └── fitting_engine.py   # 피팅 모델 및 연산
    ├── plotting/
    │   ├── plotter.py          # 다이 단위 6-패널 그래프
    │   └── heatmap_plotter.py  # 웨이퍼 히트맵
    └── analyzer/
        └── gpdo_analyzer.py    # 전체 파이프라인 통합
```

---

## 환경 설정

**Python 3.10 이상** 권장

```bash
pip install numpy scipy matplotlib lxml
```

---

## 데이터 준비

`data/` 아래에 **프로젝트명 → 웨이퍼 ID → 측정시간** 3단계 구조로 XML을 위치시킵니다.

```
data/
└── HY202103/               ← config.py의 PROJECT_NAME
    ├── D07/
    │   ├── 20190526_082853/
    │   │   └── *.xml
    │   └── 20190620_134500/    ← 측정시간이 여러 개여도 자동 분류
    │       └── *.xml
    └── D08/
        └── 20190526_082853/
            └── *.xml
```

> XML 파일은 `data/.gitignore` 에 의해 Git에 추적되지 않습니다.

---

## 실행 방법

```bash
# 전체 디바이스 × 전체 웨이퍼 처리
python run.py

# GPDO 만 처리 (전체 웨이퍼)
python run.py GPDO

# 복수 디바이스 선택
python run.py GPDO LMZC
```

---

## 결과물

실행 후 `res/` 폴더에 **웨이퍼 → 디바이스 → 측정시간** 순으로 분류되어 저장됩니다.

```
res/
├── D07-GPDO/
│   └── 20190526_082853/
│       ├── D07_(0,0)_analysis.png      # 다이 단위 6-패널 분석 그래프
│       ├── D07_(0,1)_analysis.png
│       ├── ...
│       ├── heatmap_Iph.png             # 웨이퍼 히트맵 (Photo Current)
│       ├── heatmap_n_d.png             # 웨이퍼 히트맵 (Ideality Factor)
│       ├── heatmap_Rs_d.png            # 웨이퍼 히트맵 (Series Resistance)
│       ├── heatmap_R_resp.png          # 웨이퍼 히트맵 (Responsivity)
│       ├── heatmap_r2_fwd.png          # 웨이퍼 히트맵 (R² Dark fwd)
│       └── heatmap_r2_lgt.png          # 웨이퍼 히트맵 (R² Light)
├── D08-GPDO/
│   └── 20190526_082853/
├── D23-GPDO/
└── D24-GPDO/
```

측정시간 폴더는 `YYYYMMDD_HHMMSS` 형식을 자동으로 인식합니다.
같은 웨이퍼에 측정시간이 여러 개 있어도 각각 별도 폴더로 분리 저장됩니다.

### 다이 단위 6-패널 그래프

| 패널 | 내용 |
|------|------|
| (a) Reference Spectrum | 12차 다항식 피팅 + 최솟값 마커 |
| (b) Dark Current I–V | 순방향 Shockley + 역방향 Power-law 피팅 |
| (c) Light Current I–V | 광전류 포함 Shockley 피팅 |
| (d) Photo Current | Light − Dark 차감 결과 |
| (e) Light Current Spectrum | 파장 스윕 전류 스펙트럼 |
| (f) R(λ) | 파장별 Responsivity (교정 수식 적용) |

---

## 설정 변경

### 프로젝트명 변경

`config.py` 의 `PROJECT_NAME` 한 줄만 수정합니다.

```python
# config.py
PROJECT_NAME = "HY202103"   # data/ 바로 아래 폴더명과 일치시킬 것
```

### 웨이퍼 추가 / 제거

```python
# config.py
WAFER_IDS = ["D07", "D08", "D23", "D24"]   # 원하는 웨이퍼만 남기거나 추가
```

### 특정 디바이스에만 다른 웨이퍼 셋 지정

```python
# config.py
DEVICE_CONFIG = {
    "GPDO": dict(
        wafer_ids = ["D08"],    # 이 디바이스는 D08 만 처리
        save_root = "GPDO",
    ),
    ...
}
```

`wafer_ids = None` 이면 `WAFER_IDS` 전체를 사용합니다.

---

## 모듈 설명

### `src/parser/gpdo_parser.py`

| 메서드 | 설명 |
|--------|------|
| `is_gpdo_xml(path)` | GPDO XML 여부 2단계 검증 (TestSite 키워드 + 필수 포트) |
| `is_device_xml(path, keyword, ports)` | 범용 디바이스 XML 검증 (LMZC/LMZO 확장용) |
| `parse(path)` | XML → 원시 측정 데이터 dict 반환 |

### `src/fitting/fitting_engine.py`

| 메서드 | 설명 |
|--------|------|
| `fit_reference` | Reference Spectrum 12차 다항식 피팅 |
| `fit_dark_fwd` | 순방향 Dark Current 피팅 (Shockley + Rs) |
| `fit_dark_rev` | 역방향 Dark Current 피팅 (Power-law) |
| `fit_light` | Light Current 전 구간 피팅 |
| `calc_photo_current` | Light − Dark 차감으로 Iph 추출 |
| `calc_responsivity` | 편도 IL 보정 Responsivity 계산 |

### `src/plotting/plotter.py`

다이 1개의 분석 결과를 3행 2열 6-패널 PNG로 저장합니다.

### `src/plotting/heatmap_plotter.py`

전체 다이의 파라미터를 웨이퍼 레이아웃 히트맵으로 저장합니다.
유효하지 않은 다이는 `N/A` 로 표시됩니다.

### `src/analyzer/gpdo_analyzer.py`

파싱 → 피팅 → 시각화 → 히트맵 전체 파이프라인을 통합합니다.

- XML 수집 경로: `data/{PROJECT_NAME}/{wafer_id}/**/*.xml`
- 측정시간 폴더(`YYYYMMDD_HHMMSS`)를 경로에서 자동 추출해 그룹핑
- 측정시간 패턴이 없는 경우 `unknown/` 폴더로 자동 분류

---

## Git 설정

### XML 파일 추적 제외

`data/.gitignore` 에 `*.xml` 이 등록되어 있습니다.

### 줄바꿈 통일 (LF)

`.gitattributes` 에 의해 모든 텍스트 파일이 LF로 통일됩니다.
Windows 환경에서 발생하는 `LF will be replaced by CRLF` 경고를 방지합니다.

`.gitattributes` 추가 후 기존 파일에 소급 적용하려면:

```bash
git rm -r --cached .
git add .
git commit -m "chore: reset git cache and reapply .gitattributes"
```

---

## 새 디바이스 타입 추가 방법

1. `src/analyzer/` 에 새 분석기 클래스 작성 (GPDOAnalyzer 참고)
2. `config.py` 의 `DEVICE_CONFIG` 에 항목 추가
3. `run.py` 의 `RUNNER_REGISTRY` 에 등록

```python
# run.py
RUNNER_REGISTRY = {
    "GPDO": GPDOAnalyzer,
    "LMZC": LMZCAnalyzer,   # 주석 해제
    "LMZO": LMZOAnalyzer,   # 주석 해제
}
```
