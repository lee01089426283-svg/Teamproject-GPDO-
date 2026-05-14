import xml.etree.ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt

# 1. 파일 경로 설정
file_path = 'HY202103_D08_(0,0)_LION1_DCM_GPDO.xml'

try:
    # 2. XML 파싱
    tree = ET.parse(file_path)
    root = tree.getroot()

    # XML 내의 모든 PortLossMeasurement 태그 찾기
    port_loss_nodes = root.findall('.//PortLossMeasurement')

    if len(port_loss_nodes) >= 2:
        # ---------------------------------------------------------
        # [데이터 추출 1] Port Loss Measurement (파장 vs 삽입 손실)
        # 첫 번째 PortLossMeasurement 태그 사용
        # ---------------------------------------------------------
        il_result_node = port_loss_nodes[0].find('MeasurementResult')
        wl_str = il_result_node.find('L').text  # Wavelength
        il_str = il_result_node.find('IL').text  # Insertion Loss

        wl_data = np.array([float(x) for x in wl_str.split(',')])
        il_data = np.array([float(x) for x in il_str.split(',')])

        # ---------------------------------------------------------
        # [데이터 추출 2] Opto-Electrical Alignment (X, Y vs 광전류)
        # 두 번째 PortLossMeasurement 태그 내부의 OptoElectricalAlignment 사용
        # ---------------------------------------------------------
        align_node = port_loss_nodes[1].find('OptoElectricalAlignment')
        x_str = align_node.find('X').text
        y_str = align_node.find('Y').text
        i_str = align_node.find('I').text

        x_data = np.array([float(val) for val in x_str.split(',')])
        y_data = np.array([float(val) for val in y_str.split(',')])
        i_data = np.array([float(val) for val in i_str.split(',')])

        # 전류 강도를 직관적으로 보기 위해 절대값 취함 (역방향 바이어스이므로 음수값임)
        i_abs_data = np.abs(i_data)

        # ---------------------------------------------------------
        # [그래프 시각화] 1행 2열 서브플롯 구성
        # ---------------------------------------------------------
        fig, axs = plt.subplots(1, 2, figsize=(14, 5))

        # 서브플롯 1: Port Loss Spectrum
        axs[0].plot(wl_data, il_data, color='purple', linewidth=2)
        axs[0].set_title('Port Loss Spectrum', fontsize=13, pad=10)
        axs[0].set_xlabel('Wavelength [nm]', fontsize=11)
        axs[0].set_ylabel('Insertion Loss [dB]', fontsize=11)
        axs[0].grid(True, linestyle='--', alpha=0.7)

        # 서브플롯 2: Opto-Electrical Alignment (2D Heatmap Scatter)
        # c=i_abs_data 를 통해 전류값이 높을수록 밝은 색상(노란색)으로 표시됨
        scatter = axs[1].scatter(x_data, y_data, c=i_abs_data, cmap='viridis', s=100, alpha=0.9, edgecolors='k')
        axs[1].set_title('Opto-Electrical Alignment (Sweet Spot)', fontsize=13, pad=10)
        axs[1].set_xlabel('Fiber X Position [μm]', fontsize=11)
        axs[1].set_ylabel('Fiber Y Position [μm]', fontsize=11)
        axs[1].grid(True, linestyle='--', alpha=0.5)

        # 컬러바(Colorbar) 추가
        cbar = plt.colorbar(scatter, ax=axs[1])
        cbar.set_label('Absolute Photocurrent [A]', fontsize=10)

        plt.tight_layout()
        plt.show()

    else:
        print("에러: XML 구조에서 필요한 PortLossMeasurement 태그를 충분히 찾지 못했습니다.")

except FileNotFoundError:
    print(f"에러: '{file_path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
except Exception as e:
    print(f"오류가 발생했습니다: {e}")