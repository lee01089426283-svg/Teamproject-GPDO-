# ══════════════════════════════════════════════════════
# fitting/fitting_engine.py  –  피팅 모델 정의 + 피팅 수행
# ══════════════════════════════════════════════════════
import numpy as np
from scipy.optimize import curve_fit


class FittingEngine:
    """모든 피팅 모델과 피팅 로직을 담당"""

    q  = 1.602e-19
    k  = 1.381e-23
    T  = 300.0
    VT = k * T / q

    # ── 모델 함수들 ──────────────────────────────────────

    @classmethod
    def fwd_model(cls, V, log_I0, n, Rs):
        """순방향 Shockley + Rs (Newton 반복)"""
        I0 = 10**log_I0
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
        """역방향 Power-law 누설: I = -(I0 + a*|V|^b)"""
        return -(10**log_I0 + 10**log_a * np.abs(V)**b)

    @classmethod
    def rev_model_log(cls, V, log_I0, log_a, b):
        return np.log10(np.abs(cls.rev_model(V, log_I0, log_a, b)) + 1e-20)

    @classmethod
    def light_model(cls, V, log_I0, n, Rs, Gp, Iph):
        """광전류 포함 Shockley: I = diode(V) + Gp*Vj - Iph"""
        I0 = 10**log_I0
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

    @staticmethod
    def _r2(y, y_hat):
        return 1 - np.sum((y - y_hat)**2) / np.sum((y - y.mean())**2)

    # ── 피팅 수행 ─────────────────────────────────────────

    @classmethod
    def fit_reference(cls, L_ref, IL_ref, deg=12):
        """12차 다항식 피팅 (정규화)"""
        L_norm = (L_ref - L_ref.mean()) / L_ref.std()
        poly   = np.polyfit(L_norm, IL_ref, deg)
        IL_fit = np.polyval(poly, L_norm)
        r2     = cls._r2(IL_ref, IL_fit)
        return dict(L_norm=L_norm, poly=poly, IL_fit=IL_fit, r2=r2)

    @classmethod
    def fit_dark_fwd(cls, V_dark, I_dark):
        """순방향 Dark Current 피팅 (V≥0, log|I| 기준)"""
        m        = V_dark >= 0
        V_f, I_f = V_dark[m], I_dark[m]
        log_If   = np.log10(np.abs(I_f) + 1e-20)
        ml       = (V_f > 0.05) & (V_f < 0.35) & (I_f > 0)
        sl       = np.polyfit(V_f[ml], np.log(I_f[ml]), 1)
        n0       = np.clip(1 / (sl[0] * cls.VT), 1.0, 2.0)
        try:
            popt, _ = curve_fit(
                cls.fwd_model_log, V_f, log_If,
                p0=[np.log10(np.exp(sl[1])), n0, 5.0],
                bounds=([-18, 0.8, 0], [-4, 2.0, 60]),
                maxfev=50000, method="trf"
            )
            log_I0, n, Rs = popt
            fit  = cls.fwd_model(V_f, *popt)
            logf = cls.fwd_model_log(V_f, *popt)
            r2   = cls._r2(log_If, logf)
            return dict(popt=popt, I0=10**log_I0, n=n, Rs=Rs,
                        V_f=V_f, I_f=I_f, fit=fit, r2=r2, ok=True)
        except Exception:
            return dict(popt=[np.nan]*3, I0=np.nan, n=np.nan, Rs=np.nan,
                        V_f=V_f, I_f=I_f, fit=np.zeros_like(V_f), r2=np.nan, ok=False)

    @classmethod
    def fit_dark_rev(cls, V_dark, I_dark):
        """역방향 Dark Current 피팅 (V<0, power-law log|I|)"""
        m        = V_dark < 0
        V_r, I_r = V_dark[m], I_dark[m]
        log_Ir   = np.log10(np.abs(I_r) + 1e-20)
        I0_init  = np.log10(np.abs(I_r[V_r > -0.1]).mean() + 1e-20)
        try:
            popt, _ = curve_fit(
                cls.rev_model_log, V_r, log_Ir,
                p0=[I0_init, -7.0, 3.0],
                bounds=([-18, -12, 0.5], [-3, -3, 6.0]),
                maxfev=30000
            )
            log_I0, log_a, b = popt
            fit  = cls.rev_model(V_r, *popt)
            logf = cls.rev_model_log(V_r, *popt)
            r2   = cls._r2(log_Ir, logf)
            return dict(popt=popt, I0=10**log_I0, a=10**log_a, b=b,
                        V_r=V_r, I_r=I_r, fit=fit, r2=r2, ok=True)
        except Exception:
            return dict(popt=[np.nan]*3, I0=np.nan, a=np.nan, b=np.nan,
                        V_r=V_r, I_r=I_r, fit=np.zeros_like(V_r), r2=np.nan, ok=False)

    @classmethod
    def fit_light(cls, V_light, I_light, dark_fwd: dict, dark_rev: dict):
        """Light Current 피팅 (log|I| 기준, 전 구간)"""
        log_Il   = np.log10(np.abs(I_light) + 1e-20)
        Iph_init = abs(np.mean(I_light[V_light < -1.5]))
        Gp_init  = abs(np.polyfit(dark_rev['V_r'], dark_rev['I_r'], 1)[0])
        pf = dark_fwd['popt']
        p0 = [
            pf[0] if dark_fwd['ok'] else -10,
            pf[1] if dark_fwd['ok'] else 1.5,
            pf[2] if dark_fwd['ok'] else 5.0,
            Gp_init, Iph_init
        ]
        try:
            popt, _ = curve_fit(
                cls.light_model_log, V_light, log_Il,
                p0=p0,
                bounds=([-18, 0.8, 0.01, 1e-10, 1e-7],
                        [-4,  2.0, 60.0, 1e-4,  1e-2]),
                maxfev=80000, method="trf"
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

    @classmethod
    def calc_photo_current(cls, V_light, I_light, V_dark, I_dark):
        """Photo Current = Light Current - Dark Current (보간 후 차감)"""
        I_dark_interp = np.interp(V_light, V_dark, I_dark)
        I_photo       = I_light - I_dark_interp
        # 역바이어스 포화 구간(-1.5V 이하) 평균으로 Iph 추출
        mask = V_light < -1.5
        Iph  = abs(np.mean(I_photo[mask])) if mask.sum() > 0 else np.nan
        return dict(I_photo=I_photo, Iph=Iph)

    @classmethod
    def calc_responsivity(cls, Iph, fiber_dbm, IL_at_wl):
        """응답도 계산 (편도 IL 보정)"""
        IL_oneway = IL_at_wl / 2.0
        P_in_dbm  = fiber_dbm + IL_oneway
        P_in_w    = 10**(P_in_dbm / 10) * 1e-3
        R = Iph / P_in_w if (not np.isnan(Iph) and P_in_w > 0) else np.nan
        return dict(IL_oneway=IL_oneway, P_in_dbm=P_in_dbm,
                    P_in_w=P_in_w, R_resp=R)
