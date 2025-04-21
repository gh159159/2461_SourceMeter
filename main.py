import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox, QComboBox, QLineEdit
from realtimecurrent import MainWindow as RealtimeCurrentWindow
from sweepvoltage import VoltageSweepApp as SweepVoltageWindow
from mosfetsweep import MOSFETCharacterizationApp as MosfetSweepWindow
from compare import DiodeComparisonApp as CompareWindow
import pyvisa

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley Control Panel")
        self.setGeometry(100, 100, 400, 200)
        self.setStyleSheet("""
            QPushButton {
                font-size: 30px;
                padding: 20px;
                min-height: 60px;
            }
        """)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # VISA 주소 선택 콤보박스
        self.visa_label = QLabel("장비 VISA 주소 선택:")
        self.visa_combobox = QComboBox()
        self.refresh_devices()  # 콤보박스에 장비 추가

        # 새로고침 버튼
        self.refresh_button = QPushButton("장비 새로고침")
        self.refresh_button.clicked.connect(self.refresh_devices)

        # 버튼 추가
        layout.addWidget(self.visa_label)
        layout.addWidget(self.visa_combobox)
        layout.addWidget(self.refresh_button)

        # Buttons to switch modes
        self.realtime_button = QPushButton("실시간 전류")
        self.realtime_button.clicked.connect(self.show_realtime_current)

        self.sweep_button = QPushButton("전압 스윕")
        self.sweep_button.clicked.connect(self.show_sweep_voltage)

        self.mosfet_button = QPushButton("MOSFET 스윕")
        self.mosfet_button.clicked.connect(self.show_mosfet_sweep)
        
        self.compare_button = QPushButton("그래프 비교하기")
        self.compare_button.clicked.connect(self.show_compare_mode)

        layout.addWidget(self.realtime_button)
        layout.addWidget(self.sweep_button)
        layout.addWidget(self.mosfet_button)
        layout.addWidget(self.compare_button)

        # Placeholder for the mode windows
        self.realtime_window = None
        self.sweep_window = None
        self.mosfet_window = None
        self.compare_window = None


    def refresh_devices(self):
        """연결된 장비 목록을 새로고침"""
        try:
            devices = get_connected_devices()  # PyVISA로 장비 검색
            self.visa_combobox.clear()  # 기존 항목 제거
            if devices:
                self.visa_combobox.addItems(devices)  # 새 항목 추가
            else:
                self.visa_combobox.addItem("연결된 장비 없음")
        except Exception as e:
            self.visa_combobox.clear()
            self.visa_combobox.addItem(f"오류: {str(e)}")
    
    def get_device_model(self, visa_address):
        """VISA 주소로 연결된 장비의 모델 확인"""
        try:
            rm = pyvisa.ResourceManager()
            device = rm.open_resource(visa_address)
            idn = device.query("*IDN?").strip()
            device.close()
            if "2461" in idn:
                return "2461"
            elif "2410" in idn:
                return "2410"
            elif "2400" in idn:
                return "2400"
            else:
                return "Unknown"
        except Exception as e:
            print(f"장비 식별 오류: {e}")
            return "Unknown"

    def show_realtime_current(self):
        visa_address = self.visa_combobox.currentText()
        
        self.device_model = self.get_device_model(visa_address)

        if self.device_model not in ["2461", "2410", "2400"]:
            QMessageBox.critical(self, "오류", "지원되지 않는 장비입니다.")
            return
    
        if self.realtime_window:
            self.realtime_window.close()  # 창 닫기 호출
            self.realtime_window.deleteLater()  # Qt 이벤트 루프에서 제거
            self.realtime_window = None

        self.realtime_window = RealtimeCurrentWindow(visa_address, self.device_model)
        self.realtime_window.show()

        if self.sweep_window:
            self.sweep_window.close()
        if self.mosfet_window:
            self.mosfet_window.close()
        if self.compare_window:
            self.compare_window.close()

    def show_sweep_voltage(self):
        visa_address = self.visa_combobox.currentText()

        self.device_model = self.get_device_model(visa_address)

        if self.device_model not in ["2461", "2410", "2400"]:
            QMessageBox.critical(self, "오류", "지원되지 않는 장비입니다.")
            return
        
        if self.sweep_window:
            self.sweep_window.close()
            self.sweep_window.deleteLater()
            self.sweep_window = None
        
        self.sweep_window = SweepVoltageWindow(visa_address, self.device_model)
        self.sweep_window.show()

        if self.realtime_window:
            self.realtime_window.close()
        if self.compare_window:
            self.compare_window.close()
        if self.mosfet_window:
            self.mosfet_window.close()

    def show_mosfet_sweep(self):
        # 게이트/드레인 VISA 주소를 선택받아야 하므로, 예시로 두 개 선택창을 띄운다고 가정
        visa_addresses = [self.visa_combobox.itemText(i) for i in range(self.visa_combobox.count())]
        if len(visa_addresses) < 2:
            QMessageBox.critical(self, "오류", "MOSFET 측정에는 두 개의 장비가 필요합니다.")
            return

        # 두 장비의 모델명을 확인
        model_map = {}
        for addr in visa_addresses[:2]:  # 콤보박스에서 2개만 사용한다고 가정
            model = self.get_device_model(addr)
            model_map[model] = addr

        try:
            gate_visa = model_map["2400"]
            drain_visa = model_map["2410"]
        except KeyError:
            QMessageBox.critical(self, "오류", "2400(게이트), 2410(드레인) 장비가 모두 연결되어 있어야 합니다.")
            return

        # 이미 창이 열려 있으면 닫기
        if hasattr(self, 'mosfet_window') and self.mosfet_window:
            self.mosfet_window.close()
            self.mosfet_window.deleteLater()
            self.mosfet_window = None

        self.mosfet_window = MosfetSweepWindow(gate_visa, drain_visa)
        self.mosfet_window.show()

        # 다른 창 닫기 (옵션)
        if self.realtime_window:
            self.realtime_window.close()
        if self.sweep_window:
            self.sweep_window.close()
        if self.compare_window:
            self.compare_window.close()

    def show_compare_mode(self):
        if self.compare_window is None:
            self.compare_window = CompareWindow()
        self.compare_window.show()
        if self.realtime_window is not None:
            self.realtime_window.close()
        if self.sweep_window is not None:
            self.sweep_window.close()
        if self.mosfet_window:
            self.mosfet_window.close()

def get_connected_devices():
    """PyVISA를 사용해 연결된 장비 검색"""
    rm = pyvisa.ResourceManager()
    return rm.list_resources()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())
