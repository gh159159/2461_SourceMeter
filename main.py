import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit
from realtimecurrent import MainWindow as RealtimeCurrentWindow
from sweepvoltage import VoltageSweepApp as SweepVoltageWindow
from compare import DiodeComparisonApp as CompareWindow

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley 2461 Control Panel")
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

        self.visa_label = QLabel("장비 VISA 주소 입력:")
        self.visa_input = QLineEdit("USB0::0x05E6::0x2461::04628945::INSTR")  # Default address

        # Buttons to switch modes
        self.realtime_button = QPushButton("실시간 전류")
        self.realtime_button.clicked.connect(self.show_realtime_current)

        self.sweep_button = QPushButton("전압 스윕")
        self.sweep_button.clicked.connect(self.show_sweep_voltage)

        self.compare_button = QPushButton("그래프 비교하기")
        self.compare_button.clicked.connect(self.show_compare_mode)

        layout.addWidget(self.visa_label)
        layout.addWidget(self.visa_input)
        layout.addWidget(self.realtime_button)
        layout.addWidget(self.sweep_button)
        layout.addWidget(self.compare_button)

        # Placeholder for the mode windows
        self.realtime_window = None
        self.sweep_window = None
        self.compare_window = None

    def show_realtime_current(self):
        visa_address = self.visa_input.text()
        if self.realtime_window is None:
            self.realtime_window = RealtimeCurrentWindow(visa_address)
        self.realtime_window.show()
        if self.sweep_window is not None:
            self.sweep_window.close()
        if self.compare_window is not None:
            self.compare_window.close()

    def show_sweep_voltage(self):
        visa_address = self.visa_input.text()
        if self.sweep_window is None:
            self.sweep_window = SweepVoltageWindow(visa_address)
        self.sweep_window.show()
        if self.realtime_window is not None:
            self.realtime_window.close()
        if self.compare_window is not None:
            self.compare_window.close()

    def show_compare_mode(self):
        visa_address = self.visa_input.text()
        if self.compare_window is None:
            self.compare_window = CompareWindow()
        self.compare_window.show()
        if self.realtime_window is not None:
            self.realtime_window.close()
        if self.sweep_window is not None:
            self.sweep_window.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())
