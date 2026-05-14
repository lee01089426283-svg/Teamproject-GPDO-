import xml.etree.ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt

# 1. 대상 XML 파일 경로 설정
file_path = 'HY202103_D08_(0,0)_LION1_DCM_GPDO.xml'

try:
    # 2. XML 파일 파싱
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 3. 데이터 트리에서 DarkCurrent 태그 찾기
    dark_node = root.find('.//DarkCurrent')

    if dark_node is not None:
        # 4. 전압(V)과 전류(I) 텍스트 데이터를 쉼표(,) 기준으로 분리하여 Numpy 배열로 변환
        v_str = dark_node.find('V').text
        i_str = dark_node.find('I').text

        v_data = np.array([float(x) for x in v_str.split(',')])
        i_data = np.array([float(x) for x in i_str.split(',')])

        # 5. Y축 로그 스케일 적용을 위해 전류값에 절대값(Absolute) 처리
        i_abs_data = np.abs(i_data)

        # 6. 그래프 시각화 (Plotting)
        plt.figure(figsize=(8, 6))

        # 데이터 포인트가 잘 보이도록 마커(marker) 추가
        plt.plot(v_data, i_abs_data, marker='o', markersize=4, linestyle='-', color='#1f77b4', label='Dark Current')

        # 핵심: Y축 로그 스케일 설정
        plt.yscale('log')

        # 축 라벨 및 타이틀 설정
        plt.xlabel('Voltage [V]', fontsize=12)
        plt.ylabel('Absolute Dark Current [A]', fontsize=12)
        plt.title('Ge Photodetector Dark Current I-V Characteristic', fontsize=14, pad=15)

        # 그리드 추가 (로그 스케일에서는 보조 그리드까지 켜주는 것이 가독성에 좋습니다)
        plt.grid(True, which='major', linestyle='-', alpha=0.5)
        plt.grid(True, which='minor', linestyle=':', alpha=0.5)

        plt.legend(loc='lower right')
        plt.tight_layout()

        # 그래프 출력
        plt.show()

    else:
        print("에러: XML 파일 내부에 <DarkCurrent> 태그가 존재하지 않습니다.")

except FileNotFoundError:
    print(f"에러: '{file_path}' 파일을 찾을 수 없습니다. 파일명과 경로를 확인해주세요.")
except Exception as e:
    print(f"데이터 처리 중 오류가 발생했습니다: {e}")