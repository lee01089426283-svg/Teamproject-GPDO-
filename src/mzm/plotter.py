import os
import warnings

import numpy as np
import matplotlib.pyplot as plt

from src.mzm.fitting import (
    parse_array, fit_polynomials, remove_residual_baseline,
    fit_mzi, fit_iv,
)
from src.mzm.parser import MZMParser


class Plotter:
    """
    다이 1개의 측정 결과를 6개 서브플롯으로 시각화.

    패널 배치
    ---------
    (a) Transmission Spectra         (b) Reference Spectrum & Poly Fitting
    (c) Flat Transmission Spectra    (d) MZI Fitting
    (e) IV Measurement (Log Scale)   (f) IV Analysis
    """

    @classmethod
    def plot(cls, xml_path: str,
             save_dir: str = None,
             verbose: bool = True) -> str:
        """xml_path에서 직접 로드해 PNG 생성 (하위 호환용)."""
        basename = os.path.basename(xml_path)
        try:
            root = MZMParser._load_root(xml_path)
        except Exception as e:
            print(f'  [ERROR] XML 로드 실패 {basename}: {e}')
            return ''
        return cls.plot_from_root(root, basename, save_dir=save_dir, verbose=verbose)

    @classmethod
    def _check_iv_errors(cls, root) -> dict:
        """
        IV 측정 데이터 품질을 검사해 오류 플래그 dict 반환.

        반환 키
        -------
        iv_flat      : 전류가 노이즈 수준(<1nA)으로 flat — 측정 불량
        iv_no_diode  : forward bias에서 지수 증가 없음 — junction 불량
        errors       : list[str] — 사람이 읽을 수 있는 오류 설명
        """
        result = {'iv_flat': False, 'iv_no_diode': False, 'errors': []}

        iv = root.find('.//{*}IVMeasurement')
        if iv is None:
            return result

        v_elem = iv.find('.//{*}Voltage')
        i_elem = iv.find('.//{*}Current')
        if v_elem is None or i_elem is None:
            return result

        try:
            v = np.array([float(x) for x in v_elem.text.split(',') if x.strip()])
            i = np.array([float(x) for x in i_elem.text.split(',') if x.strip()])
        except Exception:
            return result

        # ① 전체 전류가 노이즈 수준(< 1nA) → 측정 불량
        if np.max(np.abs(i)) < 1e-9:
            result['iv_flat'] = True
            result['errors'].append('IV Error: Current at noise level (<1 nA)')

        # ② forward bias(V > 0.3V)에서 지수 증가 없음 → junction 불량
        fwd_mask = v > 0.3
        if fwd_mask.sum() >= 2:
            i_fwd = np.abs(i[fwd_mask])
            # 최대/최소 비율이 10배 미만이면 flat으로 판단
            if i_fwd.min() > 0 and i_fwd.max() / i_fwd.min() < 10:
                result['iv_no_diode'] = True
                result['errors'].append('IV Error: No diode characteristic in forward bias')

        return result

    @classmethod
    def _add_error_overlay(cls, ax, messages: list[str]) -> None:
        """서브플롯 위에 빨간 오류 박스를 오버레이."""
        text = '\n'.join(messages)
        ax.text(0.5, 0.5, f'[!] Measurement Data Error\n\n{text}',
                transform=ax.transAxes,
                fontsize=9, color='red', fontweight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.6',
                          facecolor='lightyellow', edgecolor='red',
                          linewidth=2, alpha=0.92))

    @classmethod
    def plot_from_root(cls, root, basename: str,
                       save_dir: str = None,
                       verbose: bool = True,
                       extra_info: dict = None) -> str:
        """이미 로드된 root 객체로 PNG 생성 — XML 재파싱 없음."""
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        stem = os.path.splitext(basename)[0]

        # IV 오류 감지
        iv_errors = cls._check_iv_errors(root)
        has_error = bool(iv_errors['errors'])

        # 제목 구성
        if extra_info:
            er  = extra_info.get('Extinction Ratio (dB)')
            fsr = extra_info.get('FSR (nm)')
            parts = []
            if er  is not None: parts.append(f"ER: {er:.1f} dB")
            if fsr is not None: parts.append(f"FSR: {fsr:.3f} nm")
            subtitle = '  |  '.join(parts)
            title = f'{stem}\n{subtitle}'
        else:
            title = stem

        if has_error:
            title += '\n[!] Measurement Data Error  (Not a code error)'
        fig.suptitle(title, fontsize=11, fontweight='bold')

        # 6개 패널 항상 그리기
        cls._panel_transmission_spectra(axes[0, 0], root)
        cls._panel_ref_fitting(         axes[0, 1], root)
        cls._panel_flat_spectra(        axes[0, 2], root)
        cls._panel_mzi_fitting(         axes[1, 0], root)
        cls._panel_iv_raw(              axes[1, 1], root)
        cls._panel_iv_fitting(          axes[1, 2], root)

        if has_error:
            # 6개 패널 위에 에러 박스 오버레이
            error_ax = fig.add_axes([0, 0, 1, 1])
            error_ax.axis('off')
            error_ax.patch.set_alpha(0)
            error_text = '\n'.join(f'- {e}' for e in iv_errors['errors'])
            error_ax.text(0.5, 0.5,
                          f'Measurement Data Error\n\n{error_text}',
                          ha='center', va='center', fontsize=16,
                          color='red', fontweight='bold',
                          transform=error_ax.transAxes,
                          bbox=dict(boxstyle='round,pad=1.2',
                                    facecolor='lightyellow', edgecolor='red',
                                    linewidth=3, alpha=0.92))

        top = 0.92 if (extra_info or has_error) else 0.96
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*tight_layout.*')
            plt.tight_layout(rect=[0, 0, 1, top])

        out_path = ''
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            png_name = os.path.splitext(basename)[0] + '.png'
            out_path = os.path.join(save_dir, png_name)
            fig.savefig(out_path, dpi=150, bbox_inches='tight')
            if verbose:
                print(f'       저장: {out_path}')

        plt.close(fig)
        return out_path

    @classmethod
    def _panel_transmission_spectra(cls, ax, root):
        mzm_mod = ref_mod = None
        for mod in root.findall('.//{*}Modulator'):
            name = mod.attrib.get('Name', '')
            if 'ALIGN' in name.upper():
                ref_mod = mod
            else:
                mzm_mod = mod

        if mzm_mod is not None:
            for sweep in mzm_mod.findall('.//{*}WavelengthSweep'):
                bias_str = sweep.attrib.get('DCBias')
                l_node   = sweep.find('L')  or sweep.find('.//{*}L')
                il_node  = sweep.find('IL') or sweep.find('.//{*}IL')
                if bias_str is None or l_node is None or il_node is None:
                    continue
                try:
                    ax.plot(parse_array(l_node.text),
                            parse_array(il_node.text),
                            label=f'{float(bias_str):.2f} V')
                except Exception:
                    continue

        if ref_mod is not None:
            for sweep in ref_mod.findall('.//{*}WavelengthSweep'):
                l_node  = sweep.find('L')  or sweep.find('.//{*}L')
                il_node = sweep.find('IL') or sweep.find('.//{*}IL')
                if l_node is None or il_node is None:
                    continue
                try:
                    ax.plot(parse_array(l_node.text),
                            parse_array(il_node.text),
                            label='Reference', color='pink')
                except Exception:
                    continue

        ax.set_xlabel('Wavelength [nm]')
        ax.set_ylabel('Transmission [dB]')
        ax.set_title('Transmission Spectra', fontweight='bold')
        ax.legend(fontsize=6, ncol=2)
        ax.grid(True, alpha=0.3)

    @classmethod
    def _panel_ref_fitting(cls, ax, root):
        wl = il = None
        for mod in root.findall('.//{*}Modulator'):
            if 'ALIGN' in mod.attrib.get('Name', '').upper():
                for sweep in mod.findall('.//{*}WavelengthSweep'):
                    if sweep.attrib.get('DCBias', '').strip() == '0.0':
                        l_node  = sweep.find('L')  or sweep.find('.//{*}L')
                        il_node = sweep.find('IL') or sweep.find('.//{*}IL')
                        if l_node is not None and il_node is not None:
                            wl = parse_array(l_node.text)
                            il = parse_array(il_node.text)
                        break
            if wl is not None:
                break

        if wl is None:
            for sweep in root.findall('.//{*}WavelengthSweep'):
                if sweep.attrib.get('DCBias', '').strip() == '0.0':
                    l_node  = sweep.find('L')  or sweep.find('.//{*}L')
                    il_node = sweep.find('IL') or sweep.find('.//{*}IL')
                    if l_node is not None and il_node is not None:
                        wl = parse_array(l_node.text)
                        il = parse_array(il_node.text)
                    break

        if wl is None:
            ax.set_title('Ref Spectrum Fitting\n(데이터 없음)')
            return

        fit_results = fit_polynomials(wl, il, orders=[2, 3, 4, 5, 6])
        colors  = {2: 'orange', 3: 'green', 4: 'red', 5: 'purple', 6: 'brown'}
        ordinal = {2: '2nd', 3: '3rd', 4: '4th', 5: '5th', 6: '6th'}

        ax.plot(wl, il, '.', color='steelblue', markersize=1.5,
                label='Reference data', alpha=0.7)
        for order, res in fit_results.items():
            ax.plot(wl, res['fitted'], color=colors[order], linewidth=1.2,
                    label=f"{ordinal[order]} poly (R²={res['r2']:.4f})")

        r2_text = '\n'.join(
            f"{ordinal[o]} fit: R²={fit_results[o]['r2']:.4f}" for o in fit_results
        )
        ax.text(0.98, 0.97, r2_text, transform=ax.transAxes, fontsize=6,
                va='top', ha='right',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        ax.set_xlabel('Wavelength [nm]')
        ax.set_ylabel('Transmission [dB]')
        ax.set_title('Reference Spectrum & Polynomial Fitting', fontweight='bold')
        ax.legend(fontsize=5, loc='lower center', ncol=2)
        ax.grid(True, linestyle='--', alpha=0.3)

    @classmethod
    def _panel_flat_spectra(cls, ax, root):
        ref_wl = ref_int = None
        for mod in root.findall('.//{*}Modulator'):
            if 'ALIGN' in mod.attrib.get('Name', '').upper():
                for sweep in mod.findall('.//{*}WavelengthSweep'):
                    if sweep.attrib.get('DCBias', '').strip() == '0.0':
                        l_node  = sweep.find('L')  or sweep.find('.//{*}L')
                        il_node = sweep.find('IL') or sweep.find('.//{*}IL')
                        if l_node is not None and il_node is not None:
                            ref_wl  = parse_array(l_node.text)
                            ref_int = parse_array(il_node.text)
                        break
            if ref_wl is not None:
                break

        if ref_wl is None:
            ax.set_title('Flat Transmission\n(Reference 없음)')
            return

        sort_idx = np.argsort(ref_wl)
        ref_wl, ref_int = ref_wl[sort_idx], ref_int[sort_idx]

        for mod in root.findall('.//{*}Modulator'):
            if 'ALIGN' in mod.attrib.get('Name', '').upper():
                continue
            for sweep in mod.findall('.//{*}WavelengthSweep'):
                bias_str = sweep.attrib.get('DCBias')
                l_node   = sweep.find('L')  or sweep.find('.//{*}L')
                il_node  = sweep.find('IL') or sweep.find('.//{*}IL')
                if bias_str is None or l_node is None or il_node is None:
                    continue
                try:
                    wl_s  = parse_array(l_node.text)
                    int_s = parse_array(il_node.text)
                    s = np.argsort(wl_s)
                    wl_s, int_s = wl_s[s], int_s[s]
                    flat1 = int_s - np.interp(wl_s, ref_wl, ref_int)
                    flat2, _ = remove_residual_baseline(wl_s, flat1, degree=2, top_percent=30)
                    flat2 = flat2 - np.percentile(flat2, 92)
                    ax.plot(wl_s, flat2, label=f'{float(bias_str):.2f} V', linewidth=0.8)
                except Exception:
                    continue

        ax.set_xlabel('Wavelength [nm]')
        ax.set_ylabel('Flat Transmission [dB]')
        ax.set_title('Flat Transmission Spectra', fontweight='bold')
        ax.set_ylim(-50, 5)
        ax.legend(fontsize=6, ncol=2)
        ax.grid(True, alpha=0.3)

    @classmethod
    def _panel_mzi_fitting(cls, ax, root):
        best_sweep = best_bias = None
        best_dist  = 1e9
        for sweep in root.findall('.//{*}WavelengthSweep'):
            try:
                b = float(sweep.attrib.get('DCBias', 'nan'))
            except ValueError:
                continue
            if abs(b - (-1.0)) < best_dist:
                best_dist, best_bias, best_sweep = abs(b - (-1.0)), b, sweep

        if best_sweep is None:
            ax.set_title('MZI Fitting\n(데이터 없음)')
            return

        l_node  = best_sweep.find('L')  or best_sweep.find('.//{*}L')
        il_node = best_sweep.find('IL') or best_sweep.find('.//{*}IL')
        if l_node is None or il_node is None:
            ax.set_title('MZI Fitting\n(L/IL 없음)')
            return

        device_type = MZMParser.detect_device_type(root)

        # ALIGN modulator DCBias=0.0 sweep을 reference로 사용
        ref_wl = ref_dB = None
        for mod in root.findall('.//{*}Modulator'):
            if 'ALIGN' in mod.attrib.get('Name', '').upper():
                for sweep in mod.findall('.//{*}WavelengthSweep'):
                    if sweep.attrib.get('DCBias', '').strip() == '0.0':
                        rl = sweep.find('L')  or sweep.find('.//{*}L')
                        ri = sweep.find('IL') or sweep.find('.//{*}IL')
                        if rl is not None and ri is not None:
                            ref_wl = parse_array(rl.text)
                            ref_dB = parse_array(ri.text)
                        break
            if ref_wl is not None:
                break

        try:
            wl  = parse_array(l_node.text)
            res = fit_mzi(wl, parse_array(il_node.text),
                          bias_voltage=best_bias, device_type=device_type,
                          ref_wl=ref_wl, ref_dB=ref_dB)
        except Exception as e:
            ax.set_title(f'MZI Fitting\n(오류: {e})')
            return

        ax.plot(wl, res['T_norm_dB'], color='steelblue', lw=0.9,
                label=f'MZM ({best_bias:.1f} V)')
        ax.plot(wl, res['T_fit_dB'],  color='black', lw=1.5, ls='--',
                label=f"MZI fit R²={res['R2']:.4f}")
        ax.set_xlabel('Wavelength [nm]')
        ax.set_ylabel('Transmission [dB]')
        ax.set_title(f'MZI Fitting ({best_bias:.1f} V) [{device_type}]', fontweight='bold')
        ax.set_xlim(wl.min(), wl.max())
        y_min = min(res['T_norm_dB'].min(), res['T_fit_dB'].min())
        ax.set_ylim(max(y_min - 3, -50), 2)
        ax.legend(fontsize=7)
        ax.grid(True, linestyle='--', alpha=0.3)

    @classmethod
    def _panel_iv_raw(cls, ax, root):
        import re
        iv_data = MZMParser._find_tag(root, 'ivmeasurement')
        if iv_data is None:
            ax.set_title('IV Measurement\n(데이터 없음)')
            return

        v_elem = MZMParser._find_tag(iv_data, 'voltage')
        i_elem = MZMParser._find_tag(iv_data, 'current')
        if v_elem is None or i_elem is None:
            ax.set_title('IV Measurement\n(Voltage/Current 없음)')
            return

        try:
            voltage = np.array([float(v) for v in re.split(r'[,\s]+', v_elem.text.strip()) if v])
            current = np.array([float(i) for i in re.split(r'[,\s]+', i_elem.text.strip()) if i])
        except Exception as e:
            ax.set_title(f'IV Measurement\n(파싱 오류: {e})')
            return

        current_abs = np.abs(current)
        current_abs[current_abs == 0] = 1e-12

        ax.semilogy(voltage, current_abs, 'o', color='steelblue',
                    markersize=3, label='IV Curve')
        ax.set_xlabel('Voltage [V]')
        ax.set_ylabel('|Current| [A]')
        ax.set_title('IV Measurement (Log Scale)', fontweight='bold')
        ax.legend(fontsize=7)
        ax.grid(True, which='both', linestyle='--', alpha=0.3)

    @classmethod
    def _panel_iv_fitting(cls, ax, root):
        iv_data = MZMParser._find_tag(root, 'ivmeasurement')
        if iv_data is None:
            ax.set_title('IV Analysis\n(데이터 없음)')
            return

        v_elem = MZMParser._find_tag(iv_data, 'voltage')
        i_elem = MZMParser._find_tag(iv_data, 'current')
        if v_elem is None or i_elem is None:
            ax.set_title('IV Analysis\n(데이터 없음)')
            return

        try:
            def _parse(text):
                return [float(t.strip().replace(' ', ''))
                        for t in text.strip().split(',') if t.strip()]
            res = fit_iv(np.array(_parse(v_elem.text)),
                         np.array(_parse(i_elem.text)))
        except Exception as e:
            ax.set_title(f'IV Analysis\n(오류: {e})')
            return

        ax.semilogy(res['V_all'], np.abs(res['I_all']), 'o', color='steelblue',
                    label='Measured IV', markersize=4, zorder=5)
        ax.semilogy(res['V_rev_line'], res['I_rev_line'], '-',
                    color='orange', lw=2, label='Rev. poly fit')
        ax.semilogy(res['V_fwd_line'], res['I_fwd_line'], '-',
                    color='green',  lw=2, label='Fwd. diode fit')

        info = (f"$I_s$={res['Is']:.3e} A\n"
                f"$n$={res['n']:.3f}\n"
                f"$R^2_{{fwd}}$={res['R2_fwd']:.4f}\n"
                f"$R^2_{{rev}}$={res['R2_rev']:.4f}")
        ax.text(0.03, 0.97, info, transform=ax.transAxes, fontsize=7,
                va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        ax.set_xlabel('Voltage [V]')
        ax.set_ylabel('|Current| [A]')
        ax.set_title('IV Analysis', fontweight='bold')
        ax.legend(fontsize=7, loc='lower right')
        ax.grid(True, which='both', linestyle='--', alpha=0.4)
        ax.set_xlim(res['V_all'].min() - 0.1, res['V_all'].max() + 0.1)
