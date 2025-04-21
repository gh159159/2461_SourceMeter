import sys
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
plt.rc('font', family='Malgun Gothic') 
plt.rcParams['axes.unicode_minus'] =False

from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox, QTabWidget, QGroupBox, QGridLayout,
    QRadioButton, QComboBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime

# VISA 리소스 매니저
rm = pyvisa.ResourceManager('@py')
gate_instrument = None
drain_instrument = None

class MOSFETCharacterizationApp(QMainWindow):
    def __init__(self, gate_visa, drain_visa):
        super().__init__()
        self.setWindowTitle("MOSFET 특성 측정 (Gate: 2400, Drain: 2410)")
        self.setGeometry(500, 100, 1200, 950)
        
        self.gate_visa = gate_visa    # 게이트용 SMU (2400)
        self.drain_visa = drain_visa  # 드레인용 SMU (2410)
        
        # 중앙 위젯과 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 탭 위젯 생성 (Id-Vds 곡선용, Id-Vgs 곡선용)
        self.tabs = QTabWidget()
        self.output_tab = QWidget()  # Id-Vds (출력 특성)
        self.transfer_tab = QWidget()  # Id-Vgs (전달 특성)
        
        self.tabs.addTab(self.output_tab, "출력 특성 (Id-Vds)")
        self.tabs.addTab(self.transfer_tab, "전달 특성 (Id-Vgs)")
        
        # 출력 특성 탭 구성
        self.setup_output_tab()
        
        # 전달 특성 탭 구성
        self.setup_transfer_tab()
        
        main_layout.addWidget(self.tabs)
        
        # 데이터 저장용 플롯
        self.output_data = {}  # Id-Vds 데이터 저장 (각 Vgs 별)
        self.transfer_data = {}  # Id-Vgs 데이터 저장 (각 Vds 별)

    def setup_output_tab(self):
        """Id-Vds (출력 특성) 탭 설정"""
        layout = QVBoxLayout(self.output_tab)
        
        # 게이트 전압 설정 그룹
        gate_group = QGroupBox("게이트 전압 설정 (Vgs)")
        gate_layout = QGridLayout()
        
        gate_layout.addWidget(QLabel("시작 값 (V):"), 0, 0)
        self.vgs_start = QLineEdit("0")
        gate_layout.addWidget(self.vgs_start, 0, 1)
        
        gate_layout.addWidget(QLabel("끝 값 (V):"), 0, 2)
        self.vgs_end = QLineEdit("5")
        gate_layout.addWidget(self.vgs_end, 0, 3)
        
        gate_layout.addWidget(QLabel("스텝 (V):"), 0, 4)
        self.vgs_step = QLineEdit("1")
        gate_layout.addWidget(self.vgs_step, 0, 5)
        
        gate_layout.addWidget(QLabel("전류 제한 (A):"), 0, 6)
        self.gate_ilimit = QLineEdit("0.01")
        gate_layout.addWidget(self.gate_ilimit, 0, 7)
        
        gate_group.setLayout(gate_layout)
        layout.addWidget(gate_group)
        
        # 드레인 전압 설정 그룹
        drain_group = QGroupBox("드레인 전압 설정 (Vds)")
        drain_layout = QGridLayout()
        
        drain_layout.addWidget(QLabel("시작 값 (V):"), 0, 0)
        self.vds_start = QLineEdit("0")
        drain_layout.addWidget(self.vds_start, 0, 1)
        
        drain_layout.addWidget(QLabel("끝 값 (V):"), 0, 2)
        self.vds_end = QLineEdit("20")
        drain_layout.addWidget(self.vds_end, 0, 3)
        
        drain_layout.addWidget(QLabel("스텝 (V):"), 0, 4)
        self.vds_step = QLineEdit("1")
        drain_layout.addWidget(self.vds_step, 0, 5)
        
        drain_layout.addWidget(QLabel("전류 제한 (A):"), 0, 6)
        self.drain_ilimit = QLineEdit("0.1")
        drain_layout.addWidget(self.drain_ilimit, 0, 7)
        
        drain_group.setLayout(drain_layout)
        layout.addWidget(drain_group)
        
        # 버튼 그룹
        button_layout = QHBoxLayout()
        self.output_sweep_button = QPushButton("Id-Vds 측정 시작")
        self.output_sweep_button.clicked.connect(self.perform_output_sweep)
        button_layout.addWidget(self.output_sweep_button)
        
        self.output_save_button = QPushButton("결과 저장")
        self.output_save_button.clicked.connect(lambda: self.save_data("output"))
        button_layout.addWidget(self.output_save_button)
        
        layout.addLayout(button_layout)
        
        # 그래프 캔버스
        self.output_canvas = FigureCanvas(Figure(figsize=(7, 6)))
        layout.addWidget(self.output_canvas)

    def setup_transfer_tab(self):
        """Id-Vgs (전달 특성) 탭 설정"""
        layout = QVBoxLayout(self.transfer_tab)
        
        # 드레인 전압 설정 그룹
        vds_group = QGroupBox("드레인 전압 설정 (Vds)")
        vds_layout = QGridLayout()
        
        vds_layout.addWidget(QLabel("시작 값 (V):"), 0, 0)
        self.vds_transfer_start = QLineEdit("0")
        vds_layout.addWidget(self.vds_transfer_start, 0, 1)
        
        vds_layout.addWidget(QLabel("끝 값 (V):"), 0, 2)
        self.vds_transfer_end = QLineEdit("10")
        vds_layout.addWidget(self.vds_transfer_end, 0, 3)
        
        vds_layout.addWidget(QLabel("스텝 (V):"), 0, 4)
        self.vds_transfer_step = QLineEdit("2")
        vds_layout.addWidget(self.vds_transfer_step, 0, 5)
        
        vds_layout.addWidget(QLabel("전류 제한 (A):"), 0, 6)
        self.drain_transfer_ilimit = QLineEdit("0.1")
        vds_layout.addWidget(self.drain_transfer_ilimit, 0, 7)
        
        vds_group.setLayout(vds_layout)
        layout.addWidget(vds_group)
        
        # 게이트 전압 설정 그룹
        vgs_group = QGroupBox("게이트 전압 설정 (Vgs)")
        vgs_layout = QGridLayout()
        
        vgs_layout.addWidget(QLabel("시작 값 (V):"), 0, 0)
        self.vgs_transfer_start = QLineEdit("0")
        vgs_layout.addWidget(self.vgs_transfer_start, 0, 1)
        
        vgs_layout.addWidget(QLabel("끝 값 (V):"), 0, 2)
        self.vgs_transfer_end = QLineEdit("5")
        vgs_layout.addWidget(self.vgs_transfer_end, 0, 3)
        
        vgs_layout.addWidget(QLabel("스텝 (V):"), 0, 4)
        self.vgs_transfer_step = QLineEdit("0.1")
        vgs_layout.addWidget(self.vgs_transfer_step, 0, 5)
        
        vgs_layout.addWidget(QLabel("전류 제한 (A):"), 0, 6)
        self.gate_transfer_ilimit = QLineEdit("0.01")
        vgs_layout.addWidget(self.gate_transfer_ilimit, 0, 7)
        
        vgs_group.setLayout(vgs_layout)
        layout.addWidget(vgs_group)
        
        # 그래프 타입 선택 (선형 또는 로그)
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(QLabel("그래프 타입:"))
        self.linear_plot = QRadioButton("선형")
        self.linear_plot.setChecked(True)
        self.log_plot = QRadioButton("로그 (Id)")
        plot_type_layout.addWidget(self.linear_plot)
        plot_type_layout.addWidget(self.log_plot)
        plot_type_layout.addStretch()
        layout.addLayout(plot_type_layout)
        
        # 버튼 그룹
        button_layout = QHBoxLayout()
        self.transfer_sweep_button = QPushButton("Id-Vgs 측정 시작")
        self.transfer_sweep_button.clicked.connect(self.perform_transfer_sweep)
        button_layout.addWidget(self.transfer_sweep_button)
        
        self.transfer_save_button = QPushButton("결과 저장")
        self.transfer_save_button.clicked.connect(lambda: self.save_data("transfer"))
        button_layout.addWidget(self.transfer_save_button)
        
        layout.addLayout(button_layout)
        
        # 그래프 캔버스
        self.transfer_canvas = FigureCanvas(Figure(figsize=(7, 6)))
        layout.addWidget(self.transfer_canvas)

    def perform_output_sweep(self):
        """Id-Vds 출력 특성 측정 수행"""
        try:
            # 파라미터 가져오기
            vgs_start = float(self.vgs_start.text())
            vgs_end = float(self.vgs_end.text())
            vgs_step = float(self.vgs_step.text())
            gate_ilimit = float(self.gate_ilimit.text())
            
            vds_start = float(self.vds_start.text())
            vds_end = float(self.vds_end.text())
            vds_step = float(self.vds_step.text())
            drain_ilimit = float(self.drain_ilimit.text())
            
            # 전압 범위 계산
            vgs_values = np.arange(vgs_start, vgs_end + vgs_step/2, vgs_step)
            vds_values = np.arange(vds_start, vds_end + vds_step/2, vds_step)
            
            # 장비 초기화
            global gate_instrument, drain_instrument
            gate_instrument = rm.open_resource(self.gate_visa)
            drain_instrument = rm.open_resource(self.drain_visa)
            
            # 게이트 SMU (2400) 설정
            gate_instrument.write("*RST")
            gate_instrument.write(":SOUR:FUNC VOLT")
            gate_instrument.write(":SENS:FUNC 'CURR'")
            gate_instrument.write(":FORMat:ELEMents CURR")
            gate_instrument.write(f":SENS:CURR:PROT {gate_ilimit}")
            
            # 드레인 SMU (2410) 설정
            drain_instrument.write("*RST")
            drain_instrument.write(":SOUR:FUNC VOLT")
            drain_instrument.write(":SENS:FUNC 'CURR'")
            drain_instrument.write(":FORMat:ELEMents CURR")
            drain_instrument.write(f":SENS:CURR:PROT {drain_ilimit}")
            
            # 데이터 초기화
            self.output_data = {}
            
            # 그래프 초기화
            ax = self.output_canvas.figure.clf()
            ax = self.output_canvas.figure.add_subplot(111)
            
            # 색상 설정
            colors = plt.cm.jet(np.linspace(0, 1, len(vgs_values)))
            
            # 각 게이트 전압(Vgs)에 대해 드레인 전압(Vds) 스윕
            for idx, vgs in enumerate(vgs_values):
                # 게이트 전압 설정
                gate_instrument.write(f":SOUR:VOLT {vgs}")
                gate_instrument.write(":OUTP ON")
                
                # 드레인 전류 측정을 위한 배열
                ids_values = []
                
                # 드레인 전압 스윕
                for vds in vds_values:
                    # 드레인 전압 설정
                    drain_instrument.write(f":SOUR:VOLT {vds}")
                    drain_instrument.write(":OUTP ON")
                    
                    # 드레인 전류 측정
                    drain_instrument.query("*OPC?")  # 작업 완료 대기
                    current = float(drain_instrument.query(":MEAS:CURR?"))
                    ids_values.append(current)
                    
                # 데이터 저장
                self.output_data[vgs] = (vds_values.copy(), np.array(ids_values))
                
                # 그래프 플로팅
                ax.plot(vds_values, ids_values, marker='o', markersize=4, 
                        color=colors[idx], label=f"Vgs = {vgs:.1f}V")
            
            # 그래프 설정
            ax.set_title("MOSFET 출력 특성 (Id-Vds)", fontsize=14)
            ax.set_xlabel("드레인 전압 Vds (V)", fontsize=12)
            ax.set_ylabel("드레인 전류 Id (A)", fontsize=12)
            ax.grid(True)
            ax.legend(fontsize=10)
            
            # 그래프 업데이트
            self.output_canvas.draw()
            
            # 장비 출력 OFF
            gate_instrument.write(":OUTP OFF")
            drain_instrument.write(":OUTP OFF")
            
            # 장비 연결 종료
            gate_instrument.close()
            drain_instrument.close()
            
            QMessageBox.information(self, "완료", "Id-Vds 측정이 완료되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"측정 중 오류 발생: {str(e)}")
            
            # 오류 발생 시 장비 출력 종료
            if gate_instrument:
                gate_instrument.write(":OUTP OFF")
                gate_instrument.close()
            if drain_instrument:
                drain_instrument.write(":OUTP OFF")
                drain_instrument.close()

    def perform_transfer_sweep(self):
        """Id-Vgs 전달 특성 측정 수행"""
        try:
            # 파라미터 가져오기
            vds_start = float(self.vds_transfer_start.text())
            vds_end = float(self.vds_transfer_end.text())
            vds_step = float(self.vds_transfer_step.text())
            drain_ilimit = float(self.drain_transfer_ilimit.text())
            
            vgs_start = float(self.vgs_transfer_start.text())
            vgs_end = float(self.vgs_transfer_end.text())
            vgs_step = float(self.vgs_transfer_step.text())
            gate_ilimit = float(self.gate_transfer_ilimit.text())
            
            # 전압 범위 계산
            vds_values = np.arange(vds_start, vds_end + vds_step/2, vds_step)
            vgs_values = np.arange(vgs_start, vgs_end + vgs_step/2, vgs_step)
            
            # 장비 초기화
            global gate_instrument, drain_instrument
            gate_instrument = rm.open_resource(self.gate_visa)
            drain_instrument = rm.open_resource(self.drain_visa)
            
            # 게이트 SMU (2400) 설정
            gate_instrument.write("*RST")
            gate_instrument.write(":SOUR:FUNC VOLT")
            gate_instrument.write(":SENS:FUNC 'CURR'")
            gate_instrument.write(":FORMat:ELEMents CURR")
            gate_instrument.write(f":SENS:CURR:PROT {gate_ilimit}")
            
            # 드레인 SMU (2410) 설정
            drain_instrument.write("*RST")
            drain_instrument.write(":SOUR:FUNC VOLT")
            drain_instrument.write(":SENS:FUNC 'CURR'")
            drain_instrument.write(":FORMat:ELEMents CURR")
            drain_instrument.write(f":SENS:CURR:PROT {drain_ilimit}")
            
            # 데이터 초기화
            self.transfer_data = {}
            
            # 그래프 초기화
            self.transfer_canvas.figure.clf()
            ax = self.transfer_canvas.figure.add_subplot(111)
            
            # 색상 설정
            colors = plt.cm.jet(np.linspace(0, 1, len(vds_values)))
            
            # 각 드레인 전압(Vds)에 대해 게이트 전압(Vgs) 스윕
            for idx, vds in enumerate(vds_values):
                # 드레인 전압 설정
                drain_instrument.write(f":SOUR:VOLT {vds}")
                drain_instrument.write(":OUTP ON")
                
                # 드레인 전류 측정을 위한 배열
                ids_values = []
                
                # 게이트 전압 스윕
                for vgs in vgs_values:
                    # 게이트 전압 설정
                    gate_instrument.write(f":SOUR:VOLT {vgs}")
                    gate_instrument.write(":OUTP ON")
                    
                    # 드레인 전류 측정
                    drain_instrument.query("*OPC?")  # 작업 완료 대기
                    response = drain_instrument.query(":READ?")
                    current = float(response.strip().split(',')[0])
                    ids_values.append(current)
                
                # 데이터 저장
                self.transfer_data[vds] = (vgs_values.copy(), np.array(ids_values))
                
                # 그래프 플로팅 (선형 또는 로그)
                if self.linear_plot.isChecked():
                    ax.plot(vgs_values, ids_values, marker='o', markersize=4, 
                            color=colors[idx], label=f"Vds = {vds:.1f}V")
                else:
                    # 로그 스케일 (음수 값 처리)
                    log_ids = np.array(ids_values)
                    # 음수 값 또는 0을 작은 양수로 대체
                    log_ids[log_ids <= 0] = 1e-12
                    ax.semilogy(vgs_values, log_ids, marker='o', markersize=4,
                               color=colors[idx], label=f"Vds = {vds:.1f}V")
            
            # 그래프 설정
            ax.set_title("MOSFET 전달 특성 (Id-Vgs)", fontsize=14)
            ax.set_xlabel("게이트 전압 Vgs (V)", fontsize=12)
            if self.linear_plot.isChecked():
                ax.set_ylabel("드레인 전류 Id (A)", fontsize=12)
            else:
                ax.set_ylabel("드레인 전류 Id (A, 로그 스케일)", fontsize=12)
            ax.grid(True)
            ax.legend(fontsize=10)
            
            # 그래프 업데이트
            self.transfer_canvas.draw()
            
            # 장비 출력 OFF
            gate_instrument.write(":OUTP OFF")
            drain_instrument.write(":OUTP OFF")
            
            # 장비 연결 종료
            gate_instrument.close()
            drain_instrument.close()
            
            QMessageBox.information(self, "완료", "Id-Vgs 측정이 완료되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"측정 중 오류 발생: {str(e)}")
            
            # 오류 발생 시 장비 출력 종료
            if gate_instrument:
                gate_instrument.write(":OUTP OFF")
                gate_instrument.close()
            if drain_instrument:
                drain_instrument.write(":OUTP OFF")
                drain_instrument.close()
    
    def save_data(self, data_type):
        """측정 데이터 저장"""
        try:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            if data_type == "output":
                # Id-Vds 데이터 저장
                if not self.output_data:
                    raise ValueError("저장할 Id-Vds 데이터가 없습니다.")
                
                # 이미지 저장
                img_filename = f"MOSFET_IdVds_{now}.png"
                self.output_canvas.figure.savefig(img_filename, dpi=300)
                
                # CSV 데이터 저장
                csv_filename = f"MOSFET_IdVds_{now}.csv"
                with open(csv_filename, "w") as f:
                    # 헤더 작성
                    f.write("Vgs(V),Vds(V),Id(A)\n")
                    
                    # 데이터 작성
                    for vgs, (vds_arr, ids_arr) in self.output_data.items():
                        for vds, ids in zip(vds_arr, ids_arr):
                            f.write(f"{vgs},{vds},{ids}\n")
                
                QMessageBox.information(self, "저장 완료", 
                                        f"Id-Vds 데이터가 저장되었습니다.\n그래프: {img_filename}\n데이터: {csv_filename}")
            
            elif data_type == "transfer":
                # Id-Vgs 데이터 저장
                if not self.transfer_data:
                    raise ValueError("저장할 Id-Vgs 데이터가 없습니다.")
                
                # 이미지 저장
                img_filename = f"MOSFET_IdVgs_{now}.png"
                self.transfer_canvas.figure.savefig(img_filename, dpi=300)
                
                # CSV 데이터 저장
                csv_filename = f"MOSFET_IdVgs_{now}.csv"
                with open(csv_filename, "w") as f:
                    # 헤더 작성
                    f.write("Vds(V),Vgs(V),Id(A)\n")
                    
                    # 데이터 작성
                    for vds, (vgs_arr, ids_arr) in self.transfer_data.items():
                        for vgs, ids in zip(vgs_arr, ids_arr):
                            f.write(f"{vds},{vgs},{ids}\n")
                
                QMessageBox.information(self, "저장 완료", 
                                        f"Id-Vgs 데이터가 저장되었습니다.\n그래프: {img_filename}\n데이터: {csv_filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"데이터 저장 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MOSFETCharacterizationApp()
    window.show()
    sys.exit(app.exec_())
