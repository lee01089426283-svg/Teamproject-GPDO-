# 🔬 Silicon Photonics Wafer Analyzer

> 반도체 웨이퍼 광소자(GPDO / MZM)의 XML 측정 데이터를 자동으로 파싱·피팅·시각화하는 분석 파이프라인

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Device](https://img.shields.io/badge/device-GPDO%20%7C%20LMZC%20%7C%20LMZO-orange)

---

## 📖 1. 프로젝트 소개 (About The Project)

실리콘 포토닉스 공정에서 웨이퍼 한 장에는 수십 개의 광소자 다이(die)가 존재하며, 각 다이마다 별도의 XML 측정 파일이 생성됩니다. 이 파일들을 수작업으로 열어 그래프를 그리고 파라미터를 추출하는 작업은 시간이 오래 걸리고 실수가 발생하기 쉽습니다.

이 프로젝트는 **GPDO(Germanium Photodetector)** 와 **MZM(Mach-Zehnder Modulator)** 두 종류의 광소자에 대해 파싱부터 피팅, 시각화, CSV 출력까지의 전 과정을 완전히 자동화합니다.

특히 측정 데이터 자체의 품질 이상(probe contact 불량, 노이즈 수준 전류 등)을 자동으로 감지해 결과물에 명시적으로 표시하는 기능을 포함하고 있어, **코드 오류와 측정 오류를 명확히 구분**할 수 있습니다.

### ✨ 주요 기능 (Key Features)

* 📂 **자동 데이터 탐색** — `data/` 폴더 하위의 프로젝트명·웨이퍼·타임스탬프 구조를 자동으로 인식
* 📈 **다이별 6-패널 분석 그래프** — GPDO(IV 피팅, 응답도) / MZM(MZI 피팅, 소광비, FSR) PNG 자동 생성
* 🗺️ **웨이퍼 히트맵** — 웨이퍼 내 다이 위치별 파라미터 분포를 색상으로 시각화
* 🚨 **측정 데이터 오류 자동 감지** — 노이즈 수준 전류·다이오드 특성 부재 탐지 후 오류 오버레이 표시
* 📊 **CSV 자동 저장** — 웨이퍼별 + 전체 통합 `Total_Result.csv` 자동 생성

### 🛠 기술 스택 (Built With)

* `Python 3.10+`
* `NumPy` / `SciPy` — 수치 계산 및 커브 피팅 (`curve_fit`)
* `Matplotlib` — 6-패널 그래프 및 히트맵 시각화 (Agg 백엔드, GUI 없음)
* `Pandas` — CSV 생성 및 통합
* `xml.etree.ElementTree` — XML 측정 파일 파싱

---

## 📸 2. 결과물 미리보기 (Screenshots)

### GPDO — 다이 단위 6-패널 분석 그래프
> Reference Spectrum · Dark/Light IV · Photo Current · Spectrum · Responsivity R(λ)

![GPDO 6-panel](res/png/GPDO/HY202103/D08/20190526_082853/HY202103_D08_(0,2)_LION1_DCM_GPDO.png)

---

### MZM — 다이 단위 6-패널 분석 그래프
> Transmission Spectra · Ref Fitting · Flat Spectra · MZI Fitting · IV Measurement · IV Analysis

![MZM 6-panel](res/png/MZM/HY202103/D08/20190526_082853/HY202103_D08_(0,2)_LION1_DCM_LMZO.png)

---

### 측정 데이터 오류 감지 — Error Overlay
> probe contact 불량 등으로 IV 데이터가 비정상인 경우, 6개 패널 위에 오류 박스를 오버레이합니다.

![Error Overlay](res/png/MZM/HY202103/D23/20190531_072042/HY202103_D23_(0,0)_LION1_DCM_LMZO.png)

---

### 웨이퍼 히트맵 — GPDO Responsivity / MZM Extinction Ratio

| GPDO — Responsivity [A/W] | MZM — Extinction Ratio [dB] |
|:---:|:---:|
| ![GPDO Heatmap](res/png/GPDO/HY202103/D08/20190526_082853/heatmap/heatmap_R_resp.png) | ![MZM Heatmap](res/png/MZM/HY202103/D08/20190526_082853/heatmap/heatmap_Extinction_Ratio_(dB).png) |

---

## 💻 3. 시작하기 (Getting Started)

### 요구 사항 (Prerequisites)

* Python **3.10** 이상
* 가상환경(venv) 세팅 권장

### 설치 가이드 (Installation)

1. 저장소 클론

   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

2. 필수 패키지 설치

   ```bash
   pip install numpy scipy matplotlib pandas lxml
   ```

3. 측정 데이터 배치

   ```
   data/
   └── HY202103/               ← 프로젝트 폴더명 (자동 인식)
       ├── D07/
       │   └── 20190715_190855/
       │       ├── HY202103_D07_(0,0)_LION1_DCM_LMZC.xml
       │       └── ...
       ├── D08/
       │   └── 20190526_082853/
       │       ├── HY202103_D08_(0,0)_LION1_DCM_GPDO.xml
       │       ├── HY202103_D08_(0,0)_LION1_DCM_LMZO.xml
       │       └── ...
       ├── D23/
       └── D24/
   ```

   > `data/` 하위 폴더 구조(프로젝트명 → 웨이퍼ID → 타임스탬프)를 자동 탐색하므로, `config.py` 수정 없이 폴더만 추가하면 됩니다.

---

## 🚀 4. 사용 방법 (Usage)

```bash
# GPDO + MZM 전체 처리
python run.py

# GPDO만 처리
python run.py GPDO

# MZM만 처리 (LMZC / LMZO 모두 포함)
python run.py MZM
```

실행이 완료되면 아래와 같이 결과가 출력됩니다.

```
============================================================
  📋 실행 요약
============================================================
  ✅ GPDO   / D08  →  res/png/GPDO/HY202103/D08/{timestamp}/
  ✅ GPDO   / D23  →  res/png/GPDO/HY202103/D23/{timestamp}/
  ✅ MZM    / D07  →  res/png/MZM/HY202103/D07/{timestamp}/
  ✅ MZM    / D08  →  res/png/MZM/HY202103/D08/{timestamp}/
============================================================
```

---

## 📂 5. 파일 구조 (Project Structure)

```
project/
├── run.py                        # 실행 진입점 — CLI 인자로 디바이스 타입 선택
├── config.py                     # 경로 및 디바이스 설정 (웨이퍼·프로젝트 자동 탐색)
│
├── data/                         # 원본 XML 측정 파일 (Git 미추적)
│   └── HY202103/
│       └── D08/ ...
│
├── res/                          # 분석 결과물 (Git 미추적)
│   ├── png/
│   │   ├── GPDO/HY202103/D08/{timestamp}/   ← 다이 6-패널 PNG + heatmap/
│   │   └── MZM/ HY202103/D08/{timestamp}/   ← 다이 6-패널 PNG + heatmap/
│   └── csv/
│       ├── GPDO/HY202103/D08_Result.csv
│       ├── GPDO/HY202103/Total_Result.csv
│       ├── MZM/ HY202103/D08_Result.csv
│       └── MZM/ HY202103/Total_Result.csv
│
└── src/
    ├── gpdo/
    │   ├── analyzer.py           # GPDOAnalyzer — 전체 파이프라인 통합
    │   ├── parser.py             # GPDOParser — XML 파싱
    │   ├── fitting.py            # FittingEngine — Shockley / Power-law 피팅
    │   ├── plotter.py            # Plotter — 다이 6-패널 PNG 생성
    │   └── csv.py                # 웨이퍼별 CSV 및 Total CSV 저장
    ├── mzm/
    │   ├── analyzer.py           # MZMAnalyzer — 전체 파이프라인 통합
    │   ├── parser.py             # MZMParser — XML 파싱 + 디바이스 타입 감지
    │   ├── fitting.py            # fit_mzi / process_iv / fit_polynomials
    │   ├── plotter.py            # Plotter — 다이 6-패널 PNG 생성
    │   └── csv.py                # 웨이퍼별 CSV 및 Total CSV 저장
    └── heatmap_plotter.py        # HeatmapPlotter — 웨이퍼 단위 히트맵 생성
```

---

## 🔬 6. 분석 모델 상세 (Analysis Models)

### GPDO IV 피팅

| 구간 | 모델 | 파라미터 |
|------|------|----------|
| 순방향 (V > 0.3V) | Shockley 다이오드: `I = Is · exp(V / n·Vt)` | `Is` (포화전류), `n` (이상계수) |
| 역방향 (V ≤ 0.3V) | 3차 다항식 | 역방향 포화 특성 |
| 광전류 | `I_photo = I_light − I_dark` | `Iph`, `R = Iph / P_in` |

### MZM MZI 피팅 (고정 -40 dB Floor)

참고 코드를 바탕으로 소광비 floor를 **-40 dB 고정**하는 모델을 적용합니다.  
자유 파라미터를 줄여 피팅 안정성을 높이고 로컬 미니멈 함정을 방지합니다.

```
T(λ) = c + d · cos(a·λ + b)

  floor = 10^(-40/10) = 1×10⁻⁴  (고정)
  c = (t_max + floor) / 2
  d = (t_max - floor) / 2

자유 파라미터:  a (→ FSR = 2π/a),  b (위상),  t_max (최대 투과율)
```

### 측정 데이터 품질 검사

| 조건 | 판정 |
|------|------|
| `max(│I│) < 1 nA` | IV 전류가 노이즈 수준 — probe contact 불량 의심 |
| Forward bias (V > 0.3V) 에서 `I_max / I_min < 10` | 다이오드 특성 없음 — junction 불량 의심 |

오류가 감지된 경우, 6개 분석 패널 위에 `Measurement Data Error` 박스를 **오버레이**해 저장합니다.  
*(코드 오류가 아닌 측정 데이터 자체의 문제임을 명시)*

---

## 📊 7. CSV 출력 컬럼 (Output Columns)

### GPDO

| 컬럼 | 단위 | 설명 |
|------|------|------|
| `wafer_id` | — | 웨이퍼 ID |
| `timestamp` | — | 측정 타임스탬프 폴더명 |
| `col` / `row` | — | 다이 위치 (X / Y) |
| `lc_wl` | nm | Light Current 측정 파장 |
| `fiber_dbm` | dBm | 파이버 출력 파워 |
| `Iph` | A | 광전류 |
| `n_d` | — | 이상계수 |
| `R_resp` | A/W | 응답도 |
| `r2_fwd` | — | 순방향 피팅 R² |

### MZM

| 컬럼 | 설명 |
|------|------|
| `Lot` / `Wafer` / `Mask` / `Testsite` | 웨이퍼 식별 정보 |
| `Row` / `Column` | 다이 위치 |
| `Analysis Wavelength` | 분석 파장 [nm] |
| `Rsq of Ref. spectrum (Nth)` | Reference 스펙트럼 피팅 R² |
| `Rsq of IV` | IV 피팅 R² |
| `I at -1V [A]` / `I at 1V [A]` | 각 전압에서의 전류 |
| `Ideality Factor` | 다이오드 이상계수 |
| `Extinction Ratio (dB)` | MZI 소광비 |
| `FSR (nm)` | Free Spectral Range |
| `ErrorFlag` / `Error description` | 데이터 품질 플래그 |

---

## ⚙️ 8. 설정 변경 (Configuration)

### 새 프로젝트 / 웨이퍼 추가

`data/` 하위에 폴더를 추가하기만 하면 자동으로 인식됩니다. **`config.py` 수정 불필요.**

```
data/
├── HY202103/   ← 기존
└── HY202104/   ← 폴더 추가만으로 자동 처리
    └── D07/ ...
```

### 특정 웨이퍼만 처리하도록 제한

```python
# config.py
DEVICE_CONFIG = {
    "GPDO": dict(wafer_ids=["D08", "D24"]),   # D08, D24만 처리
    "MZM":  dict(wafer_ids=None),              # None → 전체 처리
}
```
---

## ✉️ 9. 연락처 (Contact)

문의 및 피드백은 GitHub Issues를 이용해 주세요.

**Project Link:** `https://github.com/H1SKIM/Teamproject-GPDO-/issues`
