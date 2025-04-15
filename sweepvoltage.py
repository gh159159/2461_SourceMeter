import sys
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime

# Keithley 2461 Configuration (SCPI Commands)
rm = pyvisa.ResourceManager()
instrument = None


class VoltageSweepApp(QMainWindow):
    def __init__(self, visa_address, device_model):
        super().__init__()
        self.setWindowTitle("Keithley Sweep Voltage")
        self.setGeometry(500, 100, 1500, 1200)

        self.device_model = device_model

        if device_model not in ["2461", "2410", "2400"]:
            raise ValueError(f"Unsupported device: {device_model}")
    
        self.visa_address = visa_address
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Input fields for voltage sweep parameters
        input_layout = QHBoxLayout()
        self.start_voltage_label = QLabel("Start Voltage (V):")
        self.start_voltage_input = QLineEdit("0")
        self.end_voltage_label = QLabel("End Voltage (V):")
        self.end_voltage_input = QLineEdit("5")
        self.step_voltage_label = QLabel("Step Voltage (V):")
        self.step_voltage_input = QLineEdit("0.1")

        # ILIMit (Current Limit) 입력 필드 추가
        self.ilimit_label = QLabel("Current Limit (A):")
        self.ilimit_input = QLineEdit("0.01")  # 기본값 10 mA
        
        input_layout.addWidget(self.start_voltage_label)
        input_layout.addWidget(self.start_voltage_input)
        input_layout.addWidget(self.end_voltage_label)
        input_layout.addWidget(self.end_voltage_input)
        input_layout.addWidget(self.step_voltage_label)
        input_layout.addWidget(self.step_voltage_input)
        input_layout.addWidget(self.ilimit_label)
        input_layout.addWidget(self.ilimit_input)

        layout.addLayout(input_layout)

        # Start button
        self.start_button = QPushButton("Start Sweep")
        self.start_button.clicked.connect(self.start_sweep)

        # Reset button
        self.reset_button = QPushButton("Reset")  
        self.reset_button.clicked.connect(self.reset_inputs)

        # Record 버튼 추가
        self.record_button = QPushButton("Record")
        self.record_button.clicked.connect(self.record_data)
        
        button_layout = QHBoxLayout()  # 버튼 레이아웃 생성
        button_layout.addWidget(self.start_button)  # Start 버튼 추가
        button_layout.addWidget(self.reset_button)  # Reset 버튼 추가
        button_layout.addWidget(self.record_button)  # 버튼 레이아웃에 추가
        layout.addLayout(button_layout)  # 버튼 레이아웃을 메인 레이아웃에 추가

        # Matplotlib canvas for plotting
        self.canvas = FigureCanvas(Figure())
        layout.addWidget(self.canvas)

    def reset_inputs(self):
        """Reset input fields, clear the plot, and reset the instrument state."""
        global instrument

        # 입력 필드를 기본값으로 초기화
        self.start_voltage_input.setText("0")
        self.end_voltage_input.setText("5")
        self.step_voltage_input.setText("0.1")

        # 플롯 초기화 (Figure 전체 삭제)
        self.canvas.figure.clf()  # Figure 전체 초기화
        self.canvas.draw()  # 캔버스 업데이트

        # Keithley 장비 상태 초기화
        if instrument is not None:
            try:
                instrument.write(":OUTPut OFF")  # 출력 비활성화
                instrument.close()  # 연결 종료
            except Exception as e:
                print(f"Error resetting instrument: {e}")
            finally:
                instrument = None  # 장비 객체 초기화

    def start_sweep(self):
        """Perform the voltage sweep and plot the I-V curve."""
        try:
            # 입력 값 가져오기 및 검증
            start_voltage = float(self.start_voltage_input.text())
            end_voltage = float(self.end_voltage_input.text())
            step_voltage = float(self.step_voltage_input.text())
            current_limit = float(self.ilimit_input.text())  # ILIMit 값 가져오기

            if start_voltage >= end_voltage or step_voltage <= 0:
                raise ValueError("Invalid voltage range or step size.")
            if current_limit <= 0:
                raise ValueError("Current limit must be greater than zero.")

            # 데이터 측정
            self.voltages, self.currents = perform_voltage_sweep(self, start_voltage, end_voltage, step_voltage, current_limit)

            # 기존 그래프 초기화
            self.canvas.figure.clf()  # Figure 전체 초기화
            ax = self.canvas.figure.add_subplot(111)  # 단일 축 생성

            # 데이터 플롯
            ax.plot(self.voltages, self.currents, marker='o', linestyle='-', color='b', label="I-V Curve")
            ax.set_title("Diode I-V Characteristics", fontsize=16)
            ax.set_xlabel("Voltage (V)", fontsize=14)
            ax.set_ylabel("Current (A)", fontsize=14)
            ax.grid(True)
            ax.legend(fontsize=12)

            # 캔버스 업데이트
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def record_data(self):
        """Save the graph as an image and the data as a CSV file."""
        try:
            # 현재 시간 가져오기
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")  # 형식: YYYY-MM-DD_HH-MM-SS

            # 파일 이름 설정 (시간 추가)
            image_filename = f"C:/Users/LG/Desktop/2461_SourceMeter/I-V특성_측정기록/graph_{timestamp}.png"
            csv_filename = f"C:/Users/LG/Desktop/2461_SourceMeter/I-V특성_측정기록/data_{timestamp}.csv"

            # 그래프를 이미지로 저장 (DPI=300)
            self.canvas.figure.savefig(image_filename, dpi=300)
            print(f"Graph saved as {image_filename}")

            # 데이터가 존재하는지 확인
            if not hasattr(self, 'voltages') or not hasattr(self, 'currents'):
                raise ValueError("No data to save. Perform a sweep first.")

            # 데이터를 CSV로 저장
            data = np.column_stack((self.voltages, self.currents))
            np.savetxt(csv_filename, data, delimiter=",", header="Voltage (V), Current (A)", comments="")
            print(f"Data saved as {csv_filename}")

            # 성공 메시지 표시
            QMessageBox.information(self, "Success", f"Graph saved as {image_filename} and data saved as {csv_filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving: {e}")


def perform_voltage_sweep(self, start_v, end_v, step_v, current_limit):
    """Perform the voltage sweep using Keithley 2461."""
    global instrument

    try:
        # Connect to Keithley instrument if not already connected
        if instrument is None:
            instrument = rm.open_resource(self.visa_address) 
            instrument.timeout = 10000  # 10-second timeout
            instrument.write_termination = '\n'
            instrument.read_termination = '\n'

            # Initialize and configure the instrument
            instrument.write("*RST")  # Reset the device
            instrument.write("*CLS")  # Clear status
            instrument.write(":SOURce:FUNCtion VOLTage")          # Voltage source mode
            instrument.write(":SENSe:FUNCtion 'CURRent'")         # Current measurement mode
            
            if self.device_model == "2461":
                instrument.write(":SOURce:VOLTage:RANGe:AUTO ON")
                instrument.write(":SENSe:CURRent:RANGe:AUTO ON")
                instrument.write(f":SOURce:VOLTage:ILIMit {current_limit}")
                
            else:
                instrument.write(":FORMat:ELEMents CURR")
                instrument.write(f"SENS:CURR:PROT {current_limit}")

            instrument.write(":OUTPut ON")                       # Enable output

        voltages = np.arange(start_v, end_v + step_v, step_v)  # Voltage range array
        currents = []

        for voltage in voltages:
            try:
                instrument.write(f":SOURce:VOLTage {voltage}")   # Set voltage
                instrument.query("*OPC?")                       # Wait for operation completion
                
                if self.device_model == "2461":
                    current = float(instrument.query(":MEASure:CURRent?"))
                else:
                    response = instrument.query(":READ?")
                    current = float(response.strip().split(',')[0])

                currents.append(current)
                print(f"Voltage: {voltage}, Current: {current}")  # Debugging output

            except Exception as e:
                print(f"Error reading current at voltage {voltage}: {e}")
                currents.append(0)  # Append zero on error

    finally:
        if instrument is not None:
            instrument.write(":OUTPut OFF")  # Disable output

    return voltages, currents


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoltageSweepApp()
    window.show()
    sys.exit(app.exec_())
