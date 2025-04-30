import sys
import pyvisa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QLineEdit, QPushButton, QMessageBox
)
from datetime import datetime, timedelta
import csv

class MOSFETWindow(QMainWindow):
    def __init__(self, gate_visa, drain_visa):
        super().__init__()

        # Initialize devices
        self.gate_keithley = None
        self.drain_keithley = None
        self.init_gate_device(gate_visa)
        self.init_drain_device(drain_visa)

        self.setWindowTitle("MOSFET Real-Time Measurement")
        self.setGeometry(500, 100, 1500, 1200)

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Control panel
        control_panel = QHBoxLayout()

        # Gate voltage controls
        gate_layout = QVBoxLayout()
        gate_label = QLabel("Gate Voltage (V):")
        self.gate_voltage_input = QLineEdit("0")
        self.set_gate_button = QPushButton("Set Gate Voltage")
        self.set_gate_button.clicked.connect(self.set_gate_voltage)
        gate_layout.addWidget(gate_label)
        gate_layout.addWidget(self.gate_voltage_input)
        gate_layout.addWidget(self.set_gate_button)

        # Drain voltage controls
        drain_layout = QVBoxLayout()
        drain_label = QLabel("Drain Voltage (V):")
        self.drain_voltage_input = QLineEdit("0")
        self.set_drain_button = QPushButton("Set Drain Voltage")
        self.set_drain_button.clicked.connect(self.set_drain_voltage)
        drain_layout.addWidget(drain_label)
        drain_layout.addWidget(self.drain_voltage_input)
        drain_layout.addWidget(self.set_drain_button)

        # Current limit controls (for drain)
        current_limit_layout = QVBoxLayout()
        current_limit_label = QLabel("Drain Current Limit (A):")
        self.current_limit_input = QLineEdit("1")
        self.current_limit = 1.0
        self.set_current_button = QPushButton("Set Current Limit")
        self.set_current_button.clicked.connect(self.set_current_limit)
        current_limit_layout.addWidget(current_limit_label)
        current_limit_layout.addWidget(self.current_limit_input)
        current_limit_layout.addWidget(self.set_current_button)

        # Recording controls
        self.start_record_button = QPushButton("Start Record")
        self.start_record_button.clicked.connect(self.start_record)
        self.stop_record_button = QPushButton("Stop Record")
        self.stop_record_button.clicked.connect(self.stop_record)
        self.stop_record_button.setEnabled(False)

        # Add to control panel
        control_panel.addLayout(gate_layout)
        control_panel.addLayout(drain_layout)
        control_panel.addLayout(current_limit_layout)
        control_panel.addWidget(self.start_record_button)
        control_panel.addWidget(self.stop_record_button)

        layout.addLayout(control_panel)

        # Displays
        self.gate_voltage_display = QLabel("Gate Voltage: 0.0 V")
        self.drain_voltage_display = QLabel("Drain Voltage: 0.0 V")
        self.current_display = QLabel("Drain Current: 0.0 A")
        self.gate_voltage_display.setStyleSheet("font-size: 16px; color: blue;")
        self.gate_voltage_display.setFixedHeight(25)

        self.drain_voltage_display.setStyleSheet("font-size: 16px; color: purple;")
        self.drain_voltage_display.setFixedHeight(25)

        self.current_display.setStyleSheet("font-size: 18px; color: green;")
        self.current_display.setFixedHeight(36)

        layout.addWidget(self.gate_voltage_display)
        layout.addWidget(self.drain_voltage_display)
        layout.addWidget(self.current_display)

        # Plot
        self.canvas = MplCanvas(self)
        layout.addWidget(self.canvas)

        # Data
        self.time_stamps = []
        self.gate_currents = []
        self.drain_currents = []
        self.gate_voltages = []
        self.drain_voltages = []

        # Recording
        self.is_recording = False
        self.recording_file = None
        self.csv_writer = None

        # Animation
        self.start_animation()

    def init_gate_device(self, visa_address):
        try:
            rm = pyvisa.ResourceManager()
            self.gate_keithley = rm.open_resource(visa_address)
            self.gate_keithley.write("*RST")
            self.gate_keithley.write(":SOUR:FUNC VOLT")  # Voltage source
            self.gate_keithley.write(":SENS:FUNC 'CURR'")  # Current 측정 활성화 
            self.gate_keithley.write(":SENS:CURR:RANGE:AUTO ON")  # Auto range
            self.gate_keithley.write(":SOUR:VOLT:RANG 200")
            self.gate_keithley.write(":OUTP ON")
        except Exception as e:
            QMessageBox.critical(self, "Gate Device Error", f"게이트 장비 연결 실패: {e}")

    def init_drain_device(self, visa_address):
        try:
            rm = pyvisa.ResourceManager()
            self.drain_keithley = rm.open_resource(visa_address)
            self.drain_keithley.write("*RST")
            self.drain_keithley.write(":SOUR:FUNC VOLT")
            self.drain_keithley.write(":SOUR:VOLT:RANG 1100")  # 2410 spec
            self.drain_keithley.write(":OUTP ON")
        except Exception as e:
            QMessageBox.critical(self, "Drain Device Error", f"Drain device connection failed: {e}")

    def set_gate_voltage(self):
        try:
            voltage = float(self.gate_voltage_input.text())
            if -10 <= voltage <= 200:
                self.gate_keithley.write(f":SOUR:VOLT {voltage}")
                self.gate_voltage_display.setText(f"Gate Voltage: {voltage:.2f} V")
            else:
                QMessageBox.warning(self, "Warning", "Gate voltage out of range (-10V ~ 200V)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid gate voltage: {e}")

    def set_drain_voltage(self):
        try:
            voltage = float(self.drain_voltage_input.text())
            if -10 <= voltage <= 1100:
                self.drain_keithley.write(f":SOUR:VOLT {voltage}")
                self.drain_voltage_display.setText(f"Drain Voltage: {voltage:.2f} V")
            else:
                QMessageBox.warning(self, "Warning", "Drain voltage out of range (-10V ~ 1100V)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid drain voltage: {e}")

    def set_current_limit(self):
        try:
            current_limit_value = float(self.current_limit_input.text())
            if 0 < current_limit_value <= 1.0:
                self.drain_keithley.write(f"SENS:CURR:PROT {current_limit_value}")
                self.current_limit = current_limit_value
            else:
                QMessageBox.warning(self, "Warning", "Current limit out of range (0 < I ≤ 1.0 A)")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid current limit: {e}")

    def start_record(self):
        try:
            self.recording_file = open(
                f"C:/Users/LG/Desktop/2461_SourceMeter/mosfet_realtime_record/current_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mode='w', newline=''
            )
            self.csv_writer = csv.writer(self.recording_file)
            self.csv_writer.writerow([
                "Timestamp", "Gate Voltage (V)", "Drain Voltage (V)",
                "Gate Current (A)", "Drain Current (A)", "Current Limit (A)"
            ])
            self.is_recording = True
            self.start_record_button.setEnabled(False)
            self.stop_record_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting recording: {e}")

    def stop_record(self):
        try:
            if self.is_recording:
                self.recording_file.close()
                self.is_recording = False
                self.start_record_button.setEnabled(True)
                self.stop_record_button.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error stopping recording: {e}")

    # update_graph 함수 수정
    def update_graph(self, frame):
        try:
            # 게이트 측정
            gate_response = self.gate_keithley.query(":READ?")
            gate_data = gate_response.strip().split(',')
            gate_current = float(gate_data[1])  # 2400: [current, voltage, ...]
            gate_voltage = float(gate_data[0])

            # 드레인 측정 (drain_data[1]이 전류)
            drain_response = self.drain_keithley.query(":READ?")
            drain_data = drain_response.strip().split(',')
            drain_current = float(drain_data[1])  # [voltage, current, ...]라면
            drain_voltage = float(drain_data[0])

            # 데이터 저장
            now = datetime.now()
            self.time_stamps.append(now)
            self.gate_currents.append(gate_current)
            self.drain_currents.append(drain_current)
            self.gate_voltages.append(gate_voltage)
            self.drain_voltages.append(drain_voltage)

            # UI 업데이트
            self.gate_voltage_display.setText(f"Gate Voltage: {gate_voltage:.2f} V")
            self.drain_voltage_display.setText(f"Drain Voltage: {drain_voltage:.2f} V")
            self.current_display.setText(
                f"Gate Current: {gate_current:.3e} A\n"
                f"Drain Current: {drain_current:.3e} A"
            )

            # 최근 20개 포인트만 사용
            ts = self.time_stamps[-20:]
            gate_curr = self.gate_currents[-20:]
            drain_curr = self.drain_currents[-20:]

            # 두 개 subplot에 각각 그리기
            self.canvas.ax_gate.clear()
            self.canvas.ax_gate.plot(ts, gate_curr, 'r-', marker='o', label='Gate Current')
            self.canvas.ax_gate.set_ylabel("Current (A)")
            self.canvas.ax_gate.set_title("Gate Current")
            self.canvas.ax_gate.grid(True)
            self.canvas.ax_gate.legend(loc='upper right')

            self.canvas.ax_drain.clear()
            self.canvas.ax_drain.plot(ts, drain_curr, 'b-', marker='s', label='Drain Current')
            self.canvas.ax_drain.set_xlabel("Time")
            self.canvas.ax_drain.set_ylabel("Current (A)")
            self.canvas.ax_drain.set_title("Drain Current")
            self.canvas.ax_drain.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.canvas.ax_drain.tick_params(axis='x', rotation=45)
            self.canvas.ax_drain.grid(True)
            self.canvas.ax_drain.legend(loc='upper right')

            self.canvas.draw()

            # 데이터 기록
            if self.is_recording:
                self.csv_writer.writerow([
                    now.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    gate_voltage,
                    drain_voltage,
                    gate_current,
                    drain_current,
                    self.current_limit
                ])

        except pyvisa.errors.VisaIOError as e:
            QMessageBox.critical(self, "측정 오류", f"장비 통신 오류: {str(e)}")
            self.close()
        except Exception as e:
            print(f"Graph update error: {str(e)}")

    def start_animation(self):
        self.ani = FuncAnimation(
            self.canvas.fig,
            self.update_graph,
            interval=200,
            cache_frame_data=False
        )

    def closeEvent(self, event):
        try:
            if hasattr(self, 'ani') and self.ani.event_source:
                self.ani.event_source.stop()
            if self.gate_keithley is not None:
                try:
                    self.gate_keithley.write(":OUTP OFF")
                except pyvisa.errors.InvalidSession:
                    pass
                finally:
                    self.gate_keithley.close()
                    self.gate_keithley = None
            if self.drain_keithley is not None:
                try:
                    self.drain_keithley.write(":OUTP OFF")
                except pyvisa.errors.InvalidSession:
                    pass
                finally:
                    self.drain_keithley.close()
                    self.drain_keithley = None
            if self.recording_file:
                self.recording_file.close()
        except Exception as e:
            print(f"Resource cleanup error: {e}")
        finally:
            event.accept()

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, (self.ax_gate, self.ax_drain) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax_gate.set_title("Gate Current")
        self.ax_gate.set_ylabel("Current (A)")
        self.ax_gate.grid(True)
        self.ax_drain.set_title("Drain Current")
        self.ax_drain.set_xlabel("Time")
        self.ax_drain.set_ylabel("Current (A)")
        self.ax_drain.grid(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MOSFETWindow()
    main_window.show()
    sys.exit(app.exec_())
