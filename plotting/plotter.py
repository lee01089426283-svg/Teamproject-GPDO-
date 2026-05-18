import os
import numpy as np
import matplotlib.pyplot as plt


class Plotter:
    BLUE = "#1565C0"
    RED = "#C62828"
    GREEN = "#2E7D32"
    PURPLE = "#6A1B9A"
    ORANGE = "#E65100"
    TEAL = "#00695C"
    GRAY = "#546E7A"
    DKW = dict(ms=3, alpha=0.8, zorder=3)
    FKW = dict(lw=2.0, zorder=4)

    @classmethod
    def plot(cls, raw: dict, ref_r: dict, df: dict, dr: dict,
             lf: dict, pc: dict, resp: dict, save_dir: str = None):
        """
        새로운 6개 패널 배치 구성:
        (a) Reference Spectrum                 (b) Dark Current [Log Scale]
        (c) Light Current [Log Scale]          (d) Photo Current [Log Scale]
        (e) Light Current Spectrum             (f) Wavelength-dependent Responsivity R($\lambda$)
        """
        col, row = raw['col'], raw['row']
        R = resp['R_resp']
        Iph = pc['Iph']
        I_photo = pc['I_photo']

        # 공통 계산 (피팅 dense 곡선)
        V_dr = np.linspace(dr['V_r'].min(), -0.005, 300)
        V_df = np.linspace(0.005, df['V_f'].max(), 300)
        from fitting import FittingEngine
        I_dr = FittingEngine.rev_model(V_dr, *dr['popt'])
        I_df = FittingEngine.fwd_model(V_df, *df['popt'])

        # ──────────────────────────────────────────────────────────
        # 💡 파장별 Responsivity R($\lambda$) 정밀 연산 로직 (교정 수식)
        # ──────────────────────────────────────────────────────────
        # 1. Dark Current 데이터에서 -1.2V 바이어스 지점의 암전류 스크랩
        idx_dark_12 = np.argmin(np.abs(raw['V_dark'] - (-1.2)))
        I_dark_at_12 = raw['I_dark'][idx_dark_12]

        # 2. 파장별 정밀 Nearest Neighbor 매칭 변수
        lcs_L = raw['L_spec']  # LightCurrentSpectrum 파장축
        lcs_I = raw['I_spec']  # LightCurrentSpectrum 전류축
        ref_L = raw['L_ref']  # Reference Spectrum 고해상도 파장축
        ref_IL = raw['IL_ref']  # Reference Spectrum 고해상도 Insertion Loss축
        fiber_dbm = raw['fiber_dbm']  # SetupInfo FiberOutput Base

        R_lambda_list = []

        for wl, I_light in zip(lcs_L, lcs_I):
            idx_match = np.argmin(np.abs(ref_L - wl))
            matched_il = ref_IL[idx_match]

            # 0.8~0.95 A/W 대역 매칭을 위한 입력 광량 차감 계산식
            pin_dbm = fiber_dbm + (matched_il / 2)
            pin_watt = 10 ** ((pin_dbm - 30) / 10)

            # 순수 광전류 계산: |현재 파장 전류 - Dark Current(-1.2V)|
            I_photo_spec = np.abs(I_light - I_dark_at_12)

            # 파장별 Responsivity (A/W)
            R_wl = I_photo_spec / pin_watt
            R_lambda_list.append(R_wl)

        R_lambda = np.array(R_lambda_list)
        # ──────────────────────────────────────────────────────────

        # 파라미터 박스 텍스트 기호 LaTeX 수식화
        ptxt_dark = (f"$I_0$={df['I0']:.2e} A\n$n$={df['n']:.3f}\n"
                     f"$R_s$={df['Rs']:.2f} $\Omega$\n"
                     f"$R^2$(fwd)={df['r2']:.4f}\n"
                     f"$b$={dr['b']:.3f}\n$R^2$(rev)={dr['r2']:.4f}")
        ptxt_light = (f"$I_0$={lf['I0']:.2e} A\n$n$={lf['n']:.3f}\n"
                      f"$R_s$={lf['Rs']:.2f} $\Omega$\n$R^2$={lf['r2']:.4f}")
        ptxt_photo = (f"$I_{{ph}}$(PhotoCurrent)={Iph * 1e6:.2f} $\mu$A\n"
                      f"$R$ = {R:.3f} A/W")

        # 3행 2열 서브플롯 시스템 빌드 (가이드라인 준수)
        fig, axes = plt.subplots(3, 2, figsize=(20, 15))
        plt.subplots_adjust(hspace=0.50, wspace=0.32)

        fig.suptitle(
            f"HY202103 – D08 ({col},{row})  GPDO_PDK\n"
            f"Fiber: {raw['fiber_dbm']:.2f} dBm  |  "
            f"Pin: {resp['P_in_dbm']:.2f} dBm  |  "
            f"R = {R:.3f} A/W",
            fontsize=12, fontweight="bold"
        )

        # ── (a) Reference Spectrum ──────────────────────
        ax = axes[0, 0]
        ax.plot(raw['L_ref'], raw['IL_ref'], color=cls.GRAY,
                lw=0.8, alpha=0.6, label="Data")
        ax.plot(raw['L_ref'], ref_r['IL_fit'], color=cls.RED,
                lw=1.8, label=f"Poly fit  $R^2$={ref_r['r2']:.4f}")
        im = np.argmin(raw['IL_ref'])
        ax.plot(raw['L_ref'][im], raw['IL_ref'][im], "v",
                color=cls.RED, ms=7, zorder=5,
                label=f"Min {raw['IL_ref'][im]:.2f} dBm")
        ax.axvline(raw['lc_wl'], color=cls.ORANGE, lw=1.2, ls=":", alpha=0.8,
                   label=f"$\lambda$={raw['lc_wl']:.0f} nm")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("IL (dBm)")
        ax.set_title("Reference Spectrum", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25)

        # ── (b) Dark Current [Log Scale] ────────────────
        ax = axes[0, 1]
        pos = raw['I_dark'] > 0;
        neg = raw['I_dark'] < 0
        ax.semilogy(raw['V_dark'][pos], raw['I_dark'][pos] * 1e6, "o",
                    color=cls.BLUE, **cls.DKW, label="Data (+I)")
        ax.semilogy(raw['V_dark'][neg], -raw['I_dark'][neg] * 1e6, "^",
                    color=cls.TEAL, **cls.DKW, label="Data (−I)")
        ax.semilogy(V_df[I_df > 0], I_df[I_df > 0] * 1e6, "-",
                    color=cls.RED, **cls.FKW,
                    label=f"Fit fwd  $R^2$={df['r2']:.4f}")
        ax.semilogy(V_dr, np.abs(I_dr) * 1e6, "--",
                    color=cls.ORANGE, lw=2.0,
                    label=f"Fit rev  $R^2$={dr['r2']:.4f}")
        ax.text(0.03, 0.97, ptxt_dark, transform=ax.transAxes,
                fontsize=7.5, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#E3F2FD", alpha=0.9))
        ax.set_xlabel("Voltage (V)")
        ax.set_ylabel("|Current| ($\mu$A)")
        ax.set_title("Dark Current I–V  [Log Scale]", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

        # ── (c) Light Current [Log Scale] ───────────────
        ax = axes[1, 0]
        pos_l = raw['I_light'] > 0;
        neg_l = raw['I_light'] < 0
        ax.semilogy(raw['V_light'][pos_l], raw['I_light'][pos_l] * 1e6, "o",
                    color=cls.GREEN, **cls.DKW, label="Data (+I)")
        ax.semilogy(raw['V_light'][neg_l], -raw['I_light'][neg_l] * 1e6, "^",
                    color=cls.TEAL, **cls.DKW, label="Data (−I)")
        pos_lf = lf['fit'] > 0;
        neg_lf = lf['fit'] < 0
        if pos_lf.sum() > 1:
            ax.semilogy(raw['V_light'][pos_lf], lf['fit'][pos_lf] * 1e6,
                        "-", color=cls.RED, **cls.FKW,
                        label=f"Fit (+)  $R^2$={lf['r2']:.4f}")
        if neg_lf.sum() > 1:
            ax.semilogy(raw['V_light'][neg_lf], -lf['fit'][neg_lf] * 1e6,
                        "--", color=cls.ORANGE, lw=2.0, label="Fit (−)")
        ax.text(0.03, 0.97, ptxt_light, transform=ax.transAxes,
                fontsize=7.5, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#E8F5E9", alpha=0.9))
        ax.set_xlabel("Voltage (V)")
        ax.set_ylabel("|Current| ($\mu$A)")
        ax.set_title(f"Light Current I–V  [Log Scale]  $\lambda$={raw['lc_wl']:.0f} nm", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

        # ── (d) Photo Current [Log Scale] ───────────────
        ax = axes[1, 1]
        pos_p = I_photo > 0;
        neg_p = I_photo < 0
        if pos_p.sum() > 0:
            ax.semilogy(raw['V_light'][pos_p], I_photo[pos_p] * 1e6, "o",
                        color="#AD1457", **cls.DKW, label="Photo (+I)")
        if neg_p.sum() > 0:
            ax.semilogy(raw['V_light'][neg_p], -I_photo[neg_p] * 1e6, "^",
                        color="#880E4F", **cls.DKW, label="Photo (−I)")
        ax.text(0.03, 0.97, ptxt_photo, transform=ax.transAxes,
                fontsize=8, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#FCE4EC", alpha=0.9))
        ax.set_xlabel("Voltage (V)")
        ax.set_ylabel("|Photo Current| ($\mu$A)")
        ax.set_title("Photo Current  [Log Scale]", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

        # ── (e) Light Current Spectrum ──────────────────
        ax = axes[2, 0]
        I_abs = np.abs(lcs_I)
        ax.bar(lcs_L, I_abs * 1e6, width=2.8,
               color=cls.PURPLE, alpha=0.35, edgecolor=cls.PURPLE, lw=0.8)
        ax.plot(lcs_L, I_abs * 1e6, "o-", color=cls.PURPLE, ms=6,
                lw=1.5, markeredgecolor="white", markeredgewidth=0.5,
                label="|I($\lambda$)|")
        ip = np.argmax(I_abs)
        ax.axvline(lcs_L[ip], color=cls.ORANGE, lw=1.3, ls="--",
                   label=f"Peak {lcs_L[ip]:.0f} nm  ({I_abs[ip] * 1e6:.3f} $\mu$A)")
        ax.text(0.98, 0.03, f"DCBias={raw['lcs_bias']} V",
                transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("|Current| ($\mu$A)")
        ax.set_title("Light Current Spectrum", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25)
        ax.set_xlim(lcs_L[0] - 5, lcs_L[-1] + 5)

        # ── (f) Wavelength-dependent Responsivity R($\lambda$) ──
        ax = axes[2, 1]
        ax.plot(lcs_L, R_lambda, "s--", color=cls.ORANGE, ms=6, lw=1.5,
                markeredgecolor="white", markeredgewidth=0.5,
                label="Responsivity $R(\lambda)$")
        ax.set_ylabel("Responsivity $R(\lambda)$ (A/W)", fontweight="bold")

        ir_max = np.argmax(R_lambda)
        ax.plot(lcs_L[ir_max], R_lambda[ir_max], "*", color=cls.RED, ms=10, zorder=6,
                label=f"Peak $R$: {R_lambda[ir_max]:.3f} A/W\n@ {lcs_L[ir_max]:.1f} nm")

        ax.legend(loc="upper left", fontsize=7.5)
        ax.text(0.98, 0.03, f"DCBias={raw['lcs_bias']} V",
                transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        ax.set_xlabel("Wavelength (nm)")
        ax.set_title("Wavelength-dependent Responsivity $R(\lambda)$", fontweight="bold")
        ax.grid(True, alpha=0.25)
        ax.set_xlim(lcs_L[0] - 5, lcs_L[-1] + 5)

        # ── 파일 자동 저장 및 축 정보 닫기 ───────────────
        os.makedirs(save_dir, exist_ok=True)
        fname = f"D08_({col},{row})_analysis.png"
        fpath = os.path.join(save_dir, fname)
        fig.savefig(fpath, dpi=150, bbox_inches="tight")
        print(f"       💾 저장: {fpath}")

        plt.close(fig)