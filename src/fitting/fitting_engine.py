# ══════════════════════════════════════════════════════
# src/fitting/fitting_engine.py  –  피팅 모델 정의 + 피팅 수행
# ══════════════════════════════════════════════════════
import numpy as np
from scipy.optimize import curve_fit


class FittingEngine:
    """
    모든 피팅 모델과 피팅 로직을 담당.

    ── 모델 ──────────────────────────────────────────────
    fwd_model        : 순방향 Shockley + Rs  (Newton 반복)
    rev_model        : 역방향 Power-law 누설
    light_model      : 광전류 포함 Shockley

    ── 피팅 ──────────────────────────────────────────────
    fit_reference    : 12차 다항식 (Reference Spectrum)
    fit_dark_fwd     : 순방향 Dark Current
    fit_dark_rev     : 역방향 Dark Current
    fit_light        : Light Current (전 구간)

    ── 연산 ──────────────────────────────────────────────
    calc_photo_current  : Light − Dark 차감
    calc_responsivity   : 응답도 (편도 IL 보정)
    """

    # ── 물리 상수 ─────────────────────────────────────
    q  = 1.602e-19
    k  = 1.381e-23
    T  = 300.0
    VT = k * T / q          # ≈ 0.02585 V

    # ══════════════════════════════════════════════════
    # 모델 함수
    # ══════════════════════════════════════════════════

    @classmethod
    def fwd_model(cls, V, log_I0, n, Rs):
        """순방향 Shockley + Rs (Newton 반복으로 Vj 수치해)"""
        I0 = 10 ** log_I0
        Vj = V.copy().astype(float)
        for _ in range(80):
            ea    = np.clip(Vj / (n * cls.VT), -500, 500)
            Id    = I0 * (np.exp(ea) - 1)
            dId   = I0 * np.exp(ea) / (n * cls.VT)
            delta = (V - Vj - Id * Rs) / (-1 - dId * Rs)
            Vj   -= delta
            if np.max(np.abs(delta)) < 1e-14:
                break
        return I0 * (np.exp(np.clip(Vj / (n * cls.VT), -500, 500)) - 1)

    @classmethod
    def fwd_model_log(cls, V, log_I0, n, Rs):
        return np.log10(np.abs(cls.fwd_model(V, log_I0, n, Rs)) + 1e-20)

    @staticmethod
    def rev_model(V, log_I0, log_a, b):
        """역방향 Power-law 누설: I = -(I0 + a·|V|^b)"""
        return -(10 ** log_I0 + 10 ** log_a * np.abs(V) ** b)

    @classmethod
    def rev_model_log(cls, V, log_I0, log_a, b):
        return np.log10(np.abs(cls.rev_model(V, log_I0, log_a, b)) + 1e-20)

    @classmethod
    def light_model(cls, V, log_I0, n, Rs, Gp, Iph):
        """광전류 포함 Shockley: I = diode(V) + Gp·Vj − Iph"""
        I0 = 10 ** log_I0
        Vj = V.copy().astype(float)
        for _ in range(80):
            ea    = np.clip(Vj / (n * cls.VT), -500, 500)
            Id    = I0 * (np.exp(ea) - 1) + Gp * Vj
            dId   = I0 * np.exp(ea) / (n * cls.VT) + Gp
            delta = (V - Vj - Id * Rs) / (-1 - dId * Rs)
            Vj   -= delta
            if np.max(np.abs(delta)) < 1e-14:
                break
        return I0 * (np.exp(np.clip(Vj / (n * cls.VT), -500, 500)) - 1) + Gp * Vj - Iph

    @classmethod
    def light_model_log(cls, V, log_I0, n, Rs, Gp, Iph):
        return np.log10(np.abs(cls.light_model(V, log_I0, n, Rs, Gp, Iph)) + 1e-20)

    # ══════════════════════════════════════════════════
    # 내부 유틸
    # ══════════════════════════════════════════════════

    @staticmethod
    def _r2(y: np.ndarray, y_hat: np.ndarray) -> float:
        """결정계수 R²"""
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        return float(1 - ss_res / ss_tot) if ss_tot != 0 else np.nan

    # ══════════════════════════════════════════════════
    # 피팅 메서드
    # ══════════════════════════════════════════════════

    @classmethod
    def fit_reference(cls, L_ref: np.ndarray, IL_ref: np.ndarray,
                      deg: int = 12) -> dict:
        """
        Reference Spectrum 12차 다항식 피팅 (정규화 적용).

        Returns
        -------
        dict : L_norm, poly, IL_fit, r2
        """
        L_norm = (L_ref - L_ref.mean()) / L_ref.std()
        poly   = np.polyfit(L_norm, IL_ref, deg)
        IL_fit = np.polyval(poly, L_norm)
        r2     = cls._r2(IL_ref, IL_fit)
        return dict(L_norm=L_norm, poly=poly, IL_fit=IL_fit, r2=r2)

    @classmethod
    def fit_dark_fwd(cls, V_dark: np.ndarray, I_dark: np.ndarray) -> dict:
        """
        순방향 Dark Current 피팅 (V≥0, log|I| 기준).

        Returns
        -------
        dict : popt, I0, n, Rs, V_f, I_f, fit, r2, ok
        """
        m        = V_dark >= 0
        V_f, I_f = V_dark[m], I_dark[m]
        log_If   = np.log10(np.abs(I_f) + 1e-20)

        # 선형 구간 초기 추정 (0.05 ~ 0.35 V)
        ml  = (V_f > 0.05) & (V_f < 0.35) & (I_f > 0)
        # 빈 배열 방어: 조건에 맞는 데이터가 없으면 범위를 넓혀서 재시도
        if ml.sum() < 2:
            ml = (V_f > 0.0) & (I_f > 0)
        if ml.sum() < 2:
            # 그래도 없으면 기본값 사용
            n0 = 1.5
            sl = [1.0 / (n0 * cls.VT), np.log(1e-10)]
        else:
            sl  = np.polyfit(V_f[ml], np.log(I_f[ml]), 1)
            n0  = np.clip(1 / (sl[0] * cls.VT), 1.0, 2.0)

        try:
            popt, _ = curve_fit(
                cls.fwd_model_log, V_f, log_If,
                p0     = [np.log10(np.exp(sl[1])), n0, 5.0],
                bounds = ([-18, 0.8, 0], [-4, 2.0, 60]),
                maxfev = 50_000, method="trf",
            )
            log_I0, n, Rs = popt
            fit  = cls.fwd_model(V_f, *popt)
            logf = cls.fwd_model_log(V_f, *popt)
            r2   = cls._r2(log_If, logf)
            return dict(popt=popt, I0=10**log_I0, n=n, Rs=Rs,
                        V_f=V_f, I_f=I_f, fit=fit, r2=r2, ok=True)
        except Exception:
            return dict(popt=[np.nan]*3, I0=np.nan, n=np.nan, Rs=np.nan,
                        V_f=V_f, I_f=I_f, fit=np.zeros_like(V_f),
                        r2=np.nan, ok=False)

    @classmethod
    def fit_dark_rev(cls, V_dark: np.ndarray, I_dark: np.ndarray) -> dict:
        """
        역방향 Dark Current 피팅 (V<0, Power-law log|I|).

        Returns
        -------
        dict : popt, I0, a, b, V_r, I_r, fit, r2, ok
        """
        m        = V_dark < 0
        V_r, I_r = V_dark[m], I_dark[m]
        log_Ir   = np.log10(np.abs(I_r) + 1e-20)
        I0_init  = np.log10(np.abs(I_r[V_r > -0.1]).mean() + 1e-20)

        try:
            popt, _ = curve_fit(
                cls.rev_model_log, V_r, log_Ir,
                p0     = [I0_init, -7.0, 3.0],
                bounds = ([-18, -12, 0.5], [-3, -3, 6.0]),
                maxfev = 30_000,
            )
            log_I0, log_a, b = popt
            fit  = cls.rev_model(V_r, *popt)
            logf = cls.rev_model_log(V_r, *popt)
            r2   = cls._r2(log_Ir, logf)
            return dict(popt=popt, I0=10**log_I0, a=10**log_a, b=b,
                        V_r=V_r, I_r=I_r, fit=fit, r2=r2, ok=True)
        except Exception:
            return dict(popt=[np.nan]*3, I0=np.nan, a=np.nan, b=np.nan,
                        V_r=V_r, I_r=I_r, fit=np.zeros_like(V_r),
                        r2=np.nan, ok=False)

    @classmethod
    def fit_light(cls, V_light: np.ndarray, I_light: np.ndarray,
                  dark_fwd: dict, dark_rev: dict) -> dict:
        """
        Light Current 전 구간 피팅 (log|I| 기준).

        dark_fwd / dark_rev 의 파라미터를 초기값으로 재활용.

        Returns
        -------
        dict : popt, I0, n, Rs, Gp, Iph, fit, r2, ok
        """
        log_Il   = np.log10(np.abs(I_light) + 1e-20)
        Iph_init = abs(np.mean(I_light[V_light < -1.5]))
        Gp_init  = abs(np.polyfit(dark_rev['V_r'], dark_rev['I_r'], 1)[0])
        pf       = dark_fwd['popt']

        p0 = [
            pf[0] if dark_fwd['ok'] else -10,
            pf[1] if dark_fwd['ok'] else 1.5,
            pf[2] if dark_fwd['ok'] else 5.0,
            Gp_init, Iph_init,
        ]
        try:
            popt, _ = curve_fit(
                cls.light_model_log, V_light, log_Il,
                p0     = p0,
                bounds = ([-18, 0.8, 0.01, 1e-10, 1e-7],
                          [-4,  2.0, 60.0, 1e-4,  1e-2]),
                maxfev = 80_000, method="trf",
            )
            log_I0, n, Rs, Gp, Iph = popt
            fit  = cls.light_model(V_light, *popt)
            logf = cls.light_model_log(V_light, *popt)
            r2   = cls._r2(log_Il, logf)
            return dict(popt=popt, I0=10**log_I0, n=n, Rs=Rs,
                        Gp=Gp, Iph=Iph, fit=fit, r2=r2, ok=True)
        except Exception:
            return dict(popt=[np.nan]*5, I0=np.nan, n=np.nan, Rs=np.nan,
                        Gp=np.nan, Iph=np.nan, fit=np.zeros_like(I_light),
                        r2=np.nan, ok=False)

    # ══════════════════════════════════════════════════
    # 연산 메서드
    # ══════════════════════════════════════════════════

    @classmethod
    def calc_photo_current(cls,
                           V_light: np.ndarray, I_light: np.ndarray,
                           V_dark:  np.ndarray, I_dark:  np.ndarray) -> dict:
        """
        Photo Current = Light Current − Dark Current (보간 후 차감).

        역바이어스 포화 구간 (V < −1.5 V) 평균으로 Iph 추출.

        Returns
        -------
        dict : I_photo, Iph
        """
        I_dark_interp = np.interp(V_light, V_dark, I_dark)
        I_photo       = I_light - I_dark_interp
        mask          = V_light < -1.5
        Iph           = abs(np.mean(I_photo[mask])) if mask.sum() > 0 else np.nan
        return dict(I_photo=I_photo, Iph=Iph)

    @classmethod
    def calc_responsivity(cls, Iph: float,
                          fiber_dbm: float, IL_at_wl: float) -> dict:
        """
        응답도 계산 (편도 Insertion Loss 보정).

            Pin_dBm  = fiber_dBm + IL_oneway
            Pin_W    = 10^((Pin_dBm − 30) / 10)
            R [A/W]  = Iph / Pin_W

        Returns
        -------
        dict : IL_oneway, P_in_dbm, P_in_w, R_resp
        """
        IL_oneway = IL_at_wl / 2.0
        P_in_dbm  = fiber_dbm + IL_oneway
        P_in_w    = 10 ** (P_in_dbm / 10) * 1e-3
        R = (Iph / P_in_w
             if (not np.isnan(Iph) and P_in_w > 0) else np.nan)
        return dict(IL_oneway=IL_oneway, P_in_dbm=P_in_dbm,
                    P_in_w=P_in_w, R_resp=R)
