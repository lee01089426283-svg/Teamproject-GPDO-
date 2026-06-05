import warnings
import numpy as np
from scipy.optimize import curve_fit
from scipy.ndimage import uniform_filter1d
from scipy.signal import argrelmax

SCRIPT_VERSION = "0.1"
SCRIPT_OWNER   = "A2"


def parse_array(text: str) -> np.ndarray:
    return np.array([float(x.strip()) for x in text.split(',') if x.strip()])

def calc_rsq(y: np.ndarray, y_fit: np.ndarray):
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot != 0 else None

def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot != 0 else 0.0


def process_spectrum(ws_elem) -> tuple:
    try:
        wl = parse_array(ws_elem.find('.//{*}L').text)
        il = parse_array(ws_elem.find('.//{*}IL').text)
        n  = min(len(wl), len(il))
        wl, il = wl[:n], il[:n]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.exceptions.RankWarning)
            coeffs = np.polyfit(wl, il, 4)
        il_fit = np.polyval(coeffs, wl)
        return calc_rsq(il, il_fit), float(np.max(il))
    except Exception as e:
        print(f"  [spectrum error] {e}")
        return None, None

def process_iv(iv_elem) -> tuple:
    try:
        v = parse_array(iv_elem.find('.//{*}Voltage').text)
        i = parse_array(iv_elem.find('.//{*}Current').text)
        idx = np.argsort(v)
        v, i = v[idx], i[idx]

        mask_rev = v < 0
        v_rev, i_rev = v[mask_rev], i[mask_rev]
        if len(v_rev) >= 4:
            coeffs = np.polyfit(v_rev, i_rev, 3)
            rsq_iv = calc_rsq(i_rev, np.polyval(coeffs, v_rev))
        else:
            rsq_iv = None

        i_neg1 = float(i[np.argmin(np.abs(v + 1))])
        i_pos1 = float(abs(i[np.argmin(np.abs(v - 1))]))

        mask_fwd = v > 0.3
        v_fwd, i_fwd = v[mask_fwd], np.abs(i[mask_fwd])
        n_fit = None
        if len(v_fwd) >= 3:
            try:
                popt, _ = curve_fit(diode_model, v_fwd, i_fwd,
                                    p0=[1e-14, 1.5],
                                    bounds=([1e-20, 0.5], [1e-4, 5.0]),
                                    maxfev=50000)
                n_fit = float(popt[1])
            except Exception:
                pass

        return rsq_iv, i_neg1, i_pos1, n_fit
    except Exception as e:
        print(f"  [IV error] {e}")
        return None, None, None, None

def parse_xml(root, filename: str = "") -> dict | None:
    import os
    data = {}
    tsi = root.find('.//{*}TestSiteInfo')
    if tsi is None:
        return None
    data['Lot']      = tsi.attrib.get('Batch')
    data['Wafer']    = tsi.attrib.get('Wafer')
    data['Mask']     = tsi.attrib.get('Maskset')
    data['Testsite'] = tsi.attrib.get('TestSite')
    data['Row']      = tsi.attrib.get('DieRow')
    data['Column']   = tsi.attrib.get('DieColumn')
    dev = root.find('.//{*}DeviceInfo')
    data['Name'] = dev.attrib.get('Name') if dev is not None else None
    data['Date']           = root.attrib.get('CreationDate')
    data['Script ID']      = os.path.splitext(os.path.basename(filename))[0]
    data['Script Version'] = SCRIPT_VERSION
    data['Script Owner']   = SCRIPT_OWNER
    data['Operator']       = root.attrib.get('Operator')

    ref_ws = None
    for mod in root.findall('.//{*}Modulator'):
        desc = mod.findtext('.//{*}DesignDescription') or ''
        name = mod.attrib.get('Name', '')
        if 'reference' in desc.lower() or 'align' in name.lower():
            for ws in mod.findall('.//{*}WavelengthSweep'):
                if ws.attrib.get('DCBias', '').strip() == '0.0':
                    ref_ws = ws
                    break
        if ref_ws is not None:
            break
    if ref_ws is None:
        for ws in root.findall('.//{*}WavelengthSweep'):
            if ws.attrib.get('DCBias', '').strip() == '0.0':
                ref_ws = ws
                break

    rsq_ref, max_trans = process_spectrum(ref_ws) if ref_ws is not None else (None, None)
    data['Rsq of Ref. spectrum (Nth)']         = rsq_ref
    data['Max transmission of Ref. spec (dB)'] = max_trans

    iv_elem = root.find('.//{*}IVMeasurement')
    rsq_iv, i_neg1, i_pos1, n_fit = (process_iv(iv_elem) if iv_elem is not None
                                      else (None, None, None, None))
    data['Rsq of IV']        = rsq_iv
    data['I at -1V [A]']     = i_neg1
    data['I at 1V [A]']      = i_pos1
    data['Ideality Factor']  = n_fit

    aw = root.find('.//{*}AlignWavelength')
    if aw is not None and aw.text:
        data['Analysis Wavelength'] = aw.text.strip()
    else:
        data['Analysis Wavelength'] = None
        for dp in root.findall('.//{*}DesignParameter'):
            if 'wavelength' in dp.attrib.get('Name', '').lower():
                data['Analysis Wavelength'] = (dp.text or '').strip()
                break

    errors = []
    if rsq_iv  is not None and rsq_iv  < 0.98:  errors.append('IV_fit')
    if rsq_ref is not None and rsq_ref < 0.95:  errors.append('Ref_fit')
    if max_trans is not None and max_trans < -10.0: errors.append('Low_transmission')
    data['ErrorFlag']         = len(errors)
    data['Error description'] = ', '.join(errors) if errors else 'No Error'
    return data


def fit_polynomials(wavelengths: np.ndarray, transmissions: np.ndarray,
                    orders=(2, 3, 4, 5, 6)) -> dict:
    results = {}
    for order in orders:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.exceptions.RankWarning)
            coeffs = np.polyfit(wavelengths, transmissions, order)
        fitted = np.polyval(coeffs, wavelengths)
        results[order] = {'coeffs': coeffs, 'fitted': fitted, 'r2': r_squared(transmissions, fitted)}
    return results


def remove_residual_baseline(wl: np.ndarray, y: np.ndarray,
                              degree: int = 3, top_percent: int = 20) -> tuple:
    threshold = np.percentile(y, 100 - top_percent)
    mask = y >= threshold
    x_fit, y_fit = wl[mask], y[mask]
    weights = np.ones_like(x_fit)
    weights[0] = 20
    weights[-1] = 5
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.exceptions.RankWarning)
        coeffs = np.polyfit(x_fit, y_fit, degree, w=weights)
    baseline = np.polyval(coeffs, wl)
    return y - baseline, baseline


FSR_PRIOR = {
    'LMZC': {'center': 14.3,  'min': 10.0, 'max': 20.0},
    'LMZO': {'center':  9.87, 'min':  6.0, 'max': 13.0},
}

def mzi_model(lam: np.ndarray, A: float, B: float,
              FSR: float, lam0: float) -> np.ndarray:
    return A + B * np.cos(np.pi * (lam - lam0) / FSR) ** 2

def fit_mzi(wavelength: np.ndarray, T_raw_dB: np.ndarray,
            bias_voltage: float = -1.0,
            device_type: str = 'LMZC',
            ref_wl: np.ndarray = None,
            ref_dB: np.ndarray = None) -> dict:
    prior = FSR_PRIOR.get(device_type.upper(), FSR_PRIOR['LMZC'])
    dλ    = wavelength[1] - wavelength[0]

    FSR_pts = int(round(prior['center'] / dλ))

    if ref_wl is not None and ref_dB is not None:
        # reference 보간 후 차감 → 파장 전체 일관된 baseline 제거
        ref_interp = np.interp(wavelength, ref_wl, ref_dB)
        T_flat_dB  = T_raw_dB - ref_interp
        # 잔류 기울기 제거 (Fix 3: 두 modulator baseline 불일치 보정)
        T_flat_dB, _ = remove_residual_baseline(wavelength, T_flat_dB,
                                                 degree=2, top_percent=30)
        T_flat = 10.0 ** (T_flat_dB / 10.0)
        T_norm = T_flat / np.clip(T_flat.max(), 1e-12, None)
    else:
        # fallback: reference 없을 때 envelope 정규화
        T_lin = 10.0 ** (T_raw_dB / 10.0)
        w1    = 3 * FSR_pts
        env1  = uniform_filter1d(T_lin, size=w1, mode='nearest')
        s1    = T_lin / np.clip(env1, 1e-12, None)
        w2    = int(1.5 * FSR_pts)
        env2  = uniform_filter1d(s1, size=w2, mode='nearest')
        T_flat    = s1 / np.clip(env2, 1e-12, None)
        T_flat_dB = 10 * np.log10(np.clip(T_flat, 1e-9, None))
        T_norm    = T_flat / T_flat.max()

    T_flat_dB = 10 * np.log10(np.clip(T_norm, 1e-9, None))

    # FSR 추정 (자기상관)
    sig_ac = T_norm - T_norm.mean()
    ac     = np.correlate(sig_ac, sig_ac, mode='full')[len(sig_ac)-1:]
    ac_peaks = argrelmax(ac, order=max(1, int(FSR_pts * 0.3)))[0]
    FSR_g    = ac_peaks[0] * dλ if len(ac_peaks) else prior['center']
    FSR_g    = float(np.clip(FSR_g, prior['min'], prior['max']))

    # Fix 1 & 2: lam0 초기값 → T_norm의 첫 번째 피크 위치로 추정
    t_peaks = argrelmax(T_norm, order=max(1, int(FSR_pts * 0.3)))[0]
    lam0_g  = wavelength[t_peaks[0]] if len(t_peaks) > 0 else wavelength[len(wavelength)//4]

    # A 하한 1e-4 = -40 dB floor, lam0 범위를 ±FSR로 확장
    p0 = [0.01, 0.97, FSR_g,        lam0_g]
    lo = [1e-4, 0.50, prior['min'], wavelength[0]  - FSR_g]
    hi = [0.35, 1.05, prior['max'], wavelength[-1] + FSR_g]

    try:
        popt, _ = curve_fit(mzi_model, wavelength, T_norm,
                            p0=p0, bounds=(lo, hi), maxfev=40000)
    except Exception:
        # fallback도 bounds 유지 → 물결 발산 방지 (Fix 2)
        popt, _ = curve_fit(mzi_model, wavelength, T_norm,
                            p0=p0, bounds=(lo, hi), maxfev=80000)

    A, B, FSR, lam0 = popt
    T_fit_norm = mzi_model(wavelength, *popt)
    R2 = r_squared(T_norm, T_fit_norm)

    return {
        'T_norm':     T_norm,
        'T_fit_norm': T_fit_norm,
        'T_norm_dB':  10 * np.log10(np.clip(T_norm,     1e-9, None)),
        'T_fit_dB':   10 * np.log10(np.clip(T_fit_norm, 1e-9, None)),
        'T_flat_dB':  T_flat_dB,
        'A': A, 'B': B, 'FSR': FSR, 'lam0': lam0, 'R2': R2,
    }


Vt = 0.02585

def diode_model(V: np.ndarray, Is: float, n: float) -> np.ndarray:
    return Is * (np.exp(V / (n * Vt)) - 1)

def poly_model(V: np.ndarray, a: float, b: float,
               c: float, d: float) -> np.ndarray:
    return a*V**3 + b*V**2 + c*V + d

def fit_iv(V_all: np.ndarray, I_all: np.ndarray) -> dict:
    idx   = np.argsort(V_all)
    V_all, I_all = V_all[idx], I_all[idx]
    mask_rev = V_all <= 0.3
    mask_fwd = V_all >  0.3
    V_rev, I_rev = V_all[mask_rev], I_all[mask_rev]
    V_fwd, I_fwd = V_all[mask_fwd], I_all[mask_fwd]
    I_rev_abs = np.abs(I_rev)
    I_fwd_abs = np.abs(I_fwd)

    popt_rev, _ = curve_fit(poly_model, V_rev, I_rev_abs, maxfev=20000)
    R2_rev = r_squared(I_rev_abs, poly_model(V_rev, *popt_rev))

    p0, bounds = [1e-14, 1.5], ([1e-20, 0.5], [1e-4, 5.0])
    popt_fwd, _ = curve_fit(diode_model, V_fwd, I_fwd_abs,
                             p0=p0, bounds=bounds, maxfev=100000)
    Is_fit, n_fit = popt_fwd
    R2_fwd = r_squared(I_fwd_abs, diode_model(V_fwd, *popt_fwd))

    V_rev_line = np.linspace(V_rev.min(), V_rev.max(), 300)
    V_fwd_line = np.linspace(V_fwd.min(), V_fwd.max(), 300)
    return {
        'V_all': V_all, 'I_all': I_all,
        'V_rev': V_rev, 'I_rev_abs': I_rev_abs,
        'V_fwd': V_fwd, 'I_fwd_abs': I_fwd_abs,
        'popt_rev': popt_rev, 'R2_rev': R2_rev,
        'popt_fwd': popt_fwd, 'Is': Is_fit, 'n': n_fit, 'R2_fwd': R2_fwd,
        'V_rev_line': V_rev_line,
        'I_rev_line': np.abs(poly_model(V_rev_line, *popt_rev)),
        'V_fwd_line': V_fwd_line,
        'I_fwd_line': diode_model(V_fwd_line, *popt_fwd),
    }
