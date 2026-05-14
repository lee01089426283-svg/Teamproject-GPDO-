import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import root_scalar

# ==========================================
# Step 1: Input parameters (굴절률, d, 람다)
# ==========================================
wl = 1.55  # Wavelength in um
n_core = 3.44  # InGaAsP Active Region Refractive Index
n_clad = 3.17  # InP Cladding Refractive Index (Symmetric: n1 = n3 = n_clad)
d = 0.1  # Core thickness in um (100 nm = 0.1 um)


# TE Mode 분산 방정식 (Symmetric Slab) 정의 -> neff 구하기
def te_dispersion(neff, m):
    k0 = 2 * np.pi / wl
    kappa = k0 * np.sqrt(n_core ** 2 - neff ** 2)
    gamma = k0 * np.sqrt(neff ** 2 - n_clad ** 2)
    # kappa * d - m * pi - 2 * arctan(gamma / kappa) = 0
    return kappa * d - m * np.pi - 2 * np.arctan(gamma / kappa)


# 지원되는 모드 찾기 (neff는 n_clad와 n_core 사이에 존재)
supported_modes = []
for m in [0, 1, 2]:  # TE0, TE1, TE2 확인
    try:
        # root_scalar를 이용하여 분산 방정식의 해(neff)를 찾음
        sol = root_scalar(te_dispersion, args=(m,), bracket=[n_clad + 1e-6, n_core - 1e-6], method='brentq')
        if sol.converged:
            supported_modes.append((m, sol.root))
    except ValueError:
        # Bracket 내에 해가 없으면 해당 모드는 지원되지 않음 (Cut-off)
        print(f"TE{m} mode is Not Supported.")

# 그래프 설정을 위한 준비
fig, ax1 = plt.subplots(figsize=(8, 6))
ax2 = ax1.twinx()  # 굴절률 프로파일을 겹쳐 그리기 위한 두 번째 y축

# ==========================================
# Step 4: Define x-range (계산할 공간 범위 설정)
# ==========================================
# 도파로 중심을 x=0으로 설정. -1.0um ~ 1.0um 범위
x = np.linspace(-1.0, 1.0, 1000)

# 굴절률 프로파일 생성 및 플롯
n_profile = np.where(np.abs(x) <= d / 2, n_core, n_clad)
ax2.plot(x, n_profile, 'k--', linewidth=1.5, alpha=0.6, label='Refractive Index')
ax2.set_ylabel('Refractive Index', color='k')
ax2.set_ylim(3.1, 3.5)

# 지원되는 각 모드에 대해 Step 2, 3, 5, 6 수행
colors = ['blue', 'red', 'green']

for idx, (m, neff) in enumerate(supported_modes):
    print(f"TE{m} mode: Calculated n_eff = {neff:.4f}")

    # ==========================================
    # Step 2: Calculate k0, 베타 (Propagation constant)
    # ==========================================
    k0 = 2 * np.pi / wl
    beta = k0 * neff

    # ==========================================
    # Step 3: q1, q2, q3 Calculate transverse constants
    # ==========================================
    # q1: 상부 클래딩 붕괴상수 (gamma)
    # q2: 코어 횡방향 파수 (kappa)
    # q3: 하부 클래딩 붕괴상수 (gamma, 대칭이므로 q1=q3)
    q2 = np.sqrt(k0 ** 2 * n_core ** 2 - beta ** 2)
    q1 = np.sqrt(beta ** 2 - k0 ** 2 * n_clad ** 2)
    q3 = q1

    # ==========================================
    # Step 5: Evaluate piecewise field E(x)
    # ==========================================
    E = np.zeros_like(x)

    for i, xi in enumerate(x):
        if xi > d / 2:
            # Upper cladding (지수함수적 감소)
            boundary_val = np.cos(q2 * d / 2) if m % 2 == 0 else np.sin(q2 * d / 2)
            E[i] = boundary_val * np.exp(-q1 * (xi - d / 2))

        elif xi < -d / 2:
            # Lower cladding (지수함수적 감소)
            boundary_val = np.cos(-q2 * d / 2) if m % 2 == 0 else np.sin(-q2 * d / 2)
            E[i] = boundary_val * np.exp(q3 * (xi + d / 2))

        else:
            # Core (진동)
            if m % 2 == 0:  # Even modes (TE0, TE2...)
                E[i] = np.cos(q2 * xi)
            else:  # Odd modes (TE1, TE3...)
                E[i] = np.sin(q2 * xi)

    # ==========================================
    # Step 6: Normalize field and calculate Intensity
    # ==========================================
    Intensity = np.abs(E) ** 2
    Intensity_norm = Intensity / np.max(Intensity)  # 최대값을 1로 정규화

    # 플롯 그리기
    ax1.plot(x, Intensity_norm, color=colors[idx], linewidth=2, label=f'TE{m} Intensity (n_eff={neff:.4f})')
    ax1.fill_between(x, Intensity_norm, color=colors[idx], alpha=0.2)

# 축 및 레이블 설정
ax1.set_xlabel('Position x (μm)', fontsize=12)
ax1.set_ylabel('Normalized Intensity |E(x)|²', color='b', fontsize=12)
ax1.set_xlim(-1.0, 1.0)
ax1.set_ylim(0, 1.1)

# 코어 영역 배경색 칠하기
ax1.axvspan(-d / 2, d / 2, color='gray', alpha=0.1)
ax1.text(0, 0.5, 'Core\n(InGaAsP)', horizontalalignment='center', verticalalignment='center')

# 범례 추가
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.title('Mode Intensity Profile of Symmetric Slab Waveguide (λ=1.55μm)')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()