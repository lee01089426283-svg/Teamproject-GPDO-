# ══════════════════════════════════════════════════════
# src/plotting/plotter.py  –  다이 단위 6-패널 그래프
# ══════════════════════════════════════════════════════
import os
import numpy as np
import matplotlib.pyplot as plt

from src.fitting import FittingEngine


class Plotter:
    """
    다이 1개의 분석 결과를 6개 서브플롯으로 시각화.

    패널 배치
    ---------
    (a) Reference Spectrum                   (b) Dark Current [Log Scale]
    (c) Light Current [Log Scale]            (d) Photo Current [Log Scale]
    (e) Light Current Spectrum               (f) Wavelength-dependent R(λ)
    """

    # ── 팔레트 ────────────────────────────────────────
    BLUE   = "#1565C0"
    RED    = "#C62828"
    GREEN  = "#2E7D32"
    PURPLE = "#6A1B9A"
    ORANGE = "#E65100"
    TEAL   = "#00695C"
    GRAY   = "#546E7A"

    # ── 공통 플롯 키워드 ──────────────────────────────
    DKW = dict(ms=3, alpha=0.8, zorder=3)   # data marker
    FKW = dict(lw=2.0, zorder=4)            # fit line

    # ══════════════════════════════════════════════════
    # 공개 진입점
    # ══════════════════════════════════════════════════

    @classmethod
    def plot(cls, raw: dict, ref_r: dict, df: dict, dr: dict,
             lf: dict, pc: dict, resp: dict,
             save_dir: str = None, wafer_id: str = "D08",
             fname: str = None) -> None:
        """
        6-패널 분석 그래프를 생성하고 PNG로 저장.

        Parameters
        ----------
        raw      : GPDOParser.parse() 반환 dict
        ref_r    : FittingEngine.fit_reference() 결과
        df       : FittingEngine.fit_dark_fwd() 결과
        dr       : FittingEngine.fit_dark_rev() 결과
        lf       : FittingEngine.fit_light() 결과
        pc       : FittingEngine.calc_photo_current() 결과
        resp     : FittingEngine.calc_responsivity() 결과
        save_dir : PNG 저장 폴더 (None 이면 저장 생략)
        """
        col, row = raw['col'], raw['row']
        R        = resp['R_resp']
        Iph      = pc['Iph']
        I_photo  = pc['I_photo']

        # ── dense 피팅 곡선 (시각화용) ─────────────────
        V_dr = np.linspace(dr['V_r'].min(), -0.005, 300)
        V_df = np.linspace(0.005, df['V_f'].max(), 300)
        I_dr = FittingEngine.rev_model(V_dr, *dr['popt'])
        I_df = FittingEngine.fwd_model(V_df, *df['popt'])

        # ── 파장별 응답도 R(λ) ─────────────────────────
        R_lambda = cls._calc_r_lambda(raw)

        # ── 파라미터 텍스트 박스 ──────────────────────
        ptxt_dark  = cls._ptxt_dark(df, dr)
        ptxt_light = cls._ptxt_light(lf)
        ptxt_photo = cls._ptxt_photo(Iph, R)

        # ── 그림 생성 ─────────────────────────────────
        fig, axes = plt.subplots(3, 2, figsize=(20, 15))
        plt.subplots_adjust(hspace=0.50, wspace=0.32)
        fig.suptitle(
            f"{fname or f'{wafer_id} ({col},{row})'}  GPDO_PDK\n"
            f"Fiber: {raw['fiber_dbm']:.2f} dBm  |  "
            f"Pin: {resp['P_in_dbm']:.2f} dBm  |  "
            f"R = {R:.3f} A/W",
            fontsize=12, fontweight="bold",
        )

        cls._panel_ref(    axes[0,0], raw, ref_r)
        cls._panel_dark(   axes[0,1], raw, V_df, I_df, V_dr, I_dr, df, dr, ptxt_dark)
        cls._panel_light(  axes[1,0], raw, lf, ptxt_light)
        cls._panel_photo(  axes[1,1], raw, I_photo, ptxt_photo)
        cls._panel_spec(   axes[2,0], raw)
        cls._panel_rlambda(axes[2,1], raw, R_lambda)

        # ── 저장 ──────────────────────────────────────
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            # XML 파일명 그대로 PNG로 저장
            png_name = (fname.replace(".xml", ".png")
                        if fname else f"{wafer_id}_({col},{row})_analysis.png")
            fpath = os.path.join(save_dir, png_name)
            fig.savefig(fpath, dpi=150, bbox_inches="tight")
            print(f"       💾 저장: {fpath}")
        plt.close(fig)

    # ══════════════════════════════════════════════════
    # 내부 헬퍼
    # ══════════════════════════════════════════════════

    @classmethod
    def _calc_r_lambda(cls, raw: dict) -> np.ndarray:
        """파장별 Responsivity R(λ) 연산 (교정 수식 적용)."""
        lcs_L    = raw['L_spec']
        lcs_I    = raw['I_spec']
        ref_L    = raw['L_ref']
        ref_IL   = raw['IL_ref']
        fiber_dbm= raw['fiber_dbm']

        # −1.2V 지점 암전류 기준값
        idx_dark = np.argmin(np.abs(raw['V_dark'] - (-1.2)))
        I_dark_12= raw['I_dark'][idx_dark]

        R_list = []
        for wl, I_light in zip(lcs_L, lcs_I):
            idx_match  = np.argmin(np.abs(ref_L - wl))
            matched_il = ref_IL[idx_match]
            pin_dbm    = fiber_dbm + (matched_il / 2)
            pin_watt   = 10 ** ((pin_dbm - 30) / 10)
            I_photo    = np.abs(I_light - I_dark_12)
            R_list.append(I_photo / pin_watt)

        return np.array(R_list)

    # ── 텍스트 박스 ───────────────────────────────────

    @staticmethod
    def _ptxt_dark(df: dict, dr: dict) -> str:
        return (f"$I_0$={df['I0']:.2e} A\n$n$={df['n']:.3f}\n"
                f"$R_s$={df['Rs']:.2f} $\\Omega$\n"
                f"$R^2$(fwd)={df['r2']:.4f}\n"
                f"$b$={dr['b']:.3f}\n$R^2$(rev)={dr['r2']:.4f}")

    @staticmethod
    def _ptxt_light(lf: dict) -> str:
        return (f"$I_0$={lf['I0']:.2e} A\n$n$={lf['n']:.3f}\n"
                f"$R_s$={lf['Rs']:.2f} $\\Omega$\n$R^2$={lf['r2']:.4f}")

    @staticmethod
    def _ptxt_photo(Iph: float, R: float) -> str:
        return (f"$I_{{ph}}$(PhotoCurrent)={Iph*1e6:.2f} $\\mu$A\n"
                f"$R$ = {R:.3f} A/W")

    # ── 서브패널 ──────────────────────────────────────

    @classmethod
    def _panel_ref(cls, ax, raw, ref_r):
        ax.plot(raw['L_ref'], raw['IL_ref'],
                color=cls.GRAY, lw=0.8, alpha=0.6, label="Data")
        ax.plot(raw['L_ref'], ref_r['IL_fit'],
                color=cls.RED, lw=1.8,
                label=f"Poly fit  $R^2$={ref_r['r2']:.4f}")
        im = np.argmin(raw['IL_ref'])
        ax.plot(raw['L_ref'][im], raw['IL_ref'][im], "v",
                color=cls.RED, ms=7, zorder=5,
                label=f"Min {raw['IL_ref'][im]:.2f} dBm")
        ax.axvline(raw['lc_wl'], color=cls.ORANGE, lw=1.2, ls=":", alpha=0.8,
                   label=f"$\\lambda$={raw['lc_wl']:.0f} nm")
        ax.set(xlabel="Wavelength (nm)", ylabel="IL (dBm)",
               title="Reference Spectrum")
        ax.set_title("Reference Spectrum", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25)

    @classmethod
    def _panel_dark(cls, ax, raw, V_df, I_df, V_dr, I_dr, df, dr, ptxt):
        pos = raw['I_dark'] > 0
        neg = raw['I_dark'] < 0
        ax.semilogy(raw['V_dark'][pos],  raw['I_dark'][pos]*1e6,
                    "o", color=cls.BLUE, **cls.DKW, label="Data (+I)")
        ax.semilogy(raw['V_dark'][neg], -raw['I_dark'][neg]*1e6,
                    "^", color=cls.TEAL, **cls.DKW, label="Data (−I)")
        ax.semilogy(V_df[I_df > 0], I_df[I_df > 0]*1e6,
                    "-", color=cls.RED, **cls.FKW,
                    label=f"Fit fwd  $R^2$={df['r2']:.4f}")
        ax.semilogy(V_dr, np.abs(I_dr)*1e6, "--",
                    color=cls.ORANGE, lw=2.0,
                    label=f"Fit rev  $R^2$={dr['r2']:.4f}")
        ax.text(0.03, 0.97, ptxt, transform=ax.transAxes,
                fontsize=7.5, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#E3F2FD", alpha=0.9))
        ax.set(xlabel="Voltage (V)", ylabel="|Current| ($\\mu$A)")
        ax.set_title("Dark Current I–V  [Log Scale]", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

    @classmethod
    def _panel_light(cls, ax, raw, lf, ptxt):
        pos_l = raw['I_light'] > 0
        neg_l = raw['I_light'] < 0
        ax.semilogy(raw['V_light'][pos_l],  raw['I_light'][pos_l]*1e6,
                    "o", color=cls.GREEN, **cls.DKW, label="Data (+I)")
        ax.semilogy(raw['V_light'][neg_l], -raw['I_light'][neg_l]*1e6,
                    "^", color=cls.TEAL, **cls.DKW, label="Data (−I)")
        pos_lf = lf['fit'] > 0
        neg_lf = lf['fit'] < 0
        if pos_lf.sum() > 1:
            ax.semilogy(raw['V_light'][pos_lf], lf['fit'][pos_lf]*1e6,
                        "-", color=cls.RED, **cls.FKW,
                        label=f"Fit (+)  $R^2$={lf['r2']:.4f}")
        if neg_lf.sum() > 1:
            ax.semilogy(raw['V_light'][neg_lf], -lf['fit'][neg_lf]*1e6,
                        "--", color=cls.ORANGE, lw=2.0, label="Fit (−)")
        ax.text(0.03, 0.97, ptxt, transform=ax.transAxes,
                fontsize=7.5, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#E8F5E9", alpha=0.9))
        ax.set(xlabel="Voltage (V)", ylabel="|Current| ($\\mu$A)")
        ax.set_title(
            f"Light Current I–V  [Log Scale]  $\\lambda$={raw['lc_wl']:.0f} nm",
            fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

    @classmethod
    def _panel_photo(cls, ax, raw, I_photo, ptxt):
        pos_p = I_photo > 0
        neg_p = I_photo < 0
        if pos_p.sum() > 0:
            ax.semilogy(raw['V_light'][pos_p], I_photo[pos_p]*1e6,
                        "o", color="#AD1457", **cls.DKW, label="Photo (+I)")
        if neg_p.sum() > 0:
            ax.semilogy(raw['V_light'][neg_p], -I_photo[neg_p]*1e6,
                        "^", color="#880E4F", **cls.DKW, label="Photo (−I)")
        ax.text(0.03, 0.97, ptxt, transform=ax.transAxes,
                fontsize=8, va="top", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#FCE4EC", alpha=0.9))
        ax.set(xlabel="Voltage (V)", ylabel="|Photo Current| ($\\mu$A)")
        ax.set_title("Photo Current  [Log Scale]", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25, which="both")

    @classmethod
    def _panel_spec(cls, ax, raw):
        lcs_L = raw['L_spec']
        lcs_I = raw['I_spec']
        I_abs = np.abs(lcs_I)
        ax.bar(lcs_L, I_abs*1e6, width=2.8,
               color=cls.PURPLE, alpha=0.35,
               edgecolor=cls.PURPLE, lw=0.8)
        ax.plot(lcs_L, I_abs*1e6, "o-", color=cls.PURPLE, ms=6, lw=1.5,
                markeredgecolor="white", markeredgewidth=0.5,
                label="|I($\\lambda$)|")
        ip = np.argmax(I_abs)
        ax.axvline(lcs_L[ip], color=cls.ORANGE, lw=1.3, ls="--",
                   label=f"Peak {lcs_L[ip]:.0f} nm  "
                         f"({I_abs[ip]*1e6:.3f} $\\mu$A)")
        ax.text(0.98, 0.03, f"DCBias={raw['lcs_bias']} V",
                transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", alpha=0.8))
        ax.set(xlabel="Wavelength (nm)", ylabel="|Current| ($\\mu$A)")
        ax.set_title("Light Current Spectrum", fontweight="bold")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.25)
        ax.set_xlim(lcs_L[0]-5, lcs_L[-1]+5)

    @classmethod
    def _panel_rlambda(cls, ax, raw, R_lambda):
        lcs_L = raw['L_spec']
        ax.plot(lcs_L, R_lambda, "s--", color=cls.ORANGE, ms=6, lw=1.5,
                markeredgecolor="white", markeredgewidth=0.5,
                label="Responsivity $R(\\lambda)$")
        ir_max = np.argmax(R_lambda)
        ax.plot(lcs_L[ir_max], R_lambda[ir_max], "*",
                color=cls.RED, ms=10, zorder=6,
                label=f"Peak $R$: {R_lambda[ir_max]:.3f} A/W\n"
                      f"@ {lcs_L[ir_max]:.1f} nm")
        ax.text(0.98, 0.03, f"DCBias={raw['lcs_bias']} V",
                transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", alpha=0.8))
        ax.set(xlabel="Wavelength (nm)",
               ylabel="Responsivity $R(\\lambda)$ (A/W)")
        ax.set_title("Wavelength-dependent Responsivity $R(\\lambda)$",
                     fontweight="bold")
        ax.legend(loc="upper left", fontsize=7.5)
        ax.grid(True, alpha=0.25)
        ax.set_xlim(lcs_L[0]-5, lcs_L[-1]+5)
