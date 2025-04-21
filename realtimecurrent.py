import sys
import pyvisa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QLabel, QLineEdit, QPushButton)
from datetime import datetime, timedelta
import csv

class MainWindow(QMainWindow):
    def __init__(self, visa_address, device_model):
        super().__init__()
        self.device_model = device_model
        # Initialize Keithley and create canvas
        self.visa_address = visa_address
        self.keithley = None
        self.init_keithley()

        self.setWindowTitle("Keithley Realtime Curr")
        self.setGeometry(500, 100, 1500, 1200)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create control panel
        control_panel = QHBoxLayout()

        # Voltage control widgets
        voltage_layout = QVBoxLayout()
        voltage_label = QLabel("Source Voltage (V):")
        self.voltage_input = QLineEdit("0")
        self.source_voltage = 0.0
        self.voltage_input.setMaximumWidth(100)
        
        # Current limit control widgets
        current_limit_layout = QVBoxLayout()
        current_limit_label = QLabel("Current Limit (A):")
        self.current_limit_input = QLineEdit("1")
        self.current_limit = 1.0
        self.current_limit_input.setMaximumWidth(100)
        
        # Set buttons
        self.set_voltage_button = QPushButton("Set Voltage")
        self.set_voltage_button.clicked.connect(self.set_voltage)
        self.set_current_button = QPushButton("Set Current Limit")
        self.set_current_button.clicked.connect(self.set_current_limit)
        
        # Add voltage controls to layout
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(self.voltage_input)
        voltage_layout.addWidget(self.set_voltage_button)
        control_panel.addLayout(voltage_layout)
        
        # Add current limit controls to layout
        current_limit_layout.addWidget(current_limit_label)
        current_limit_layout.addWidget(self.current_limit_input)
        current_limit_layout.addWidget(self.set_current_button)
        control_panel.addLayout(current_limit_layout)
        
        # Add start and stop record buttons
        self.start_record_button = QPushButton("Start Record")
        self.start_record_button.clicked.connect(self.start_record)
        control_panel.addWidget(self.start_record_button)

        self.stop_record_button = QPushButton("Stop Record")
        self.stop_record_button.clicked.connect(self.stop_record)
        self.stop_record_button.setEnabled(False)  # Initially disabled
        control_panel.addWidget(self.stop_record_button)

        # Add control panel to main layout
        layout.addLayout(control_panel)
        
        self.voltage_display = QLabel("Voltage: 0.0 V")
        self.current_display = QLabel("Current: 0.0 A")
        self.voltage_display.setStyleSheet("font-size: 25px; color: blue;")
        self.current_display.setStyleSheet("font-size: 25px; color: green;")
        layout.addWidget(self.voltage_display)
        layout.addWidget(self.current_display)

        self.canvas = MplCanvas(self)
        layout.addWidget(self.canvas)
        
        # Start animation for real-time updates
        self.start_animation()

        # Initialize recording state
        self.is_recording = False
        self.recording_file = None  # File object for the CSV file
        self.csv_writer = None      # CSV writer object
        
    def init_keithley(self):
        """Initialize the Keithley SourceMeter"""
        try:
            if self.keithley:  # 기존 연결이 있으면 해제
                self.keithley.close()

            rm = pyvisa.ResourceManager()
            self.keithley = rm.open_resource(self.visa_address)
            self.keithley.write("*RST")
            self.keithley.write(":SENS:FUNC 'CURR'")

            if self.device_model == "2461":
                self.keithley.write(":SENS:CURR:RANG:AUTO ON")
            else:
                self.keithley.write(":FORMat:ELEMents CURR")

            self.keithley.write(":FORM:DATA ASC")
            self.keithley.write(":SOUR:FUNC VOLT")

            if self.device_model == "2461":
                self.keithley.write(":SOUR:VOLT:RANG 105")
            elif self.device_model == "2400":
                self.keithley.write(":SOUR:VOLT:RANG 200")
            elif self.device_model == "2410":
                self.keithley.write(":SOUR:VOLT:RANG 1100")

            self.keithley.write(":SOUR:VOLT 0")
            self.keithley.write(":OUTP ON")
        except Exception as e:
            print(f"장비 연결 오류: {e}")
            self.keithley = None

    def set_voltage(self):
        """Set the source voltage"""
        # 장비별 전압 범위 딕셔너리 정의
        VOLTAGE_RANGES = {
            "2410": (-10, 1100),
            "2400": (-10, 200),
            "2461": (-10, 105)
        }
        # 장비별 안내 메시지 딕셔너리 정의
        VOLTAGE_MESSAGES = {
            "2410": "keithley 2410의 전압범위는 -10[V] ~ 1100[V]로 설정돼있습니다.",
            "2400": "keithley 2400의 전압범위는 -10[V] ~ 200[V]로 설정돼있습니다.",
            "2461": "keithley 2461의 전압범위는 -10[V] ~ 105[V]로 설정돼있습니다."
        }

        min_v, max_v = VOLTAGE_RANGES[self.device_model]
        message = VOLTAGE_MESSAGES[self.device_model]

        try:
            voltage = float(self.voltage_input.text())
            if min_v <= voltage <= max_v:
                self.keithley.write(f":SOUR:VOLT {voltage}")
                self.source_voltage = voltage  # Update global variable
            else:
                print(message)

        except ValueError as e:
            print(f"Invalid voltage value: {e}")

    def set_current_limit(self):
        """Set the current limit"""
        try:
            current_limit_value = float(self.current_limit_input.text())
            if 0 < current_limit_value <= 1.0:
                if self.device_model == "2461":
                    self.keithley.write(f":SOURce:VOLTage:ILIMit {current_limit_value}")
                else:
                    self.keithley.write(f"SENS:CURR:PROT {current_limit_value}")

                self.current_limit = current_limit_value
            else:
                print("전류제한 범위를 벗어났습니다! (10[pA] ~ 1[A]로 설정돼있습니다.)")
        except ValueError as e:
            print(f"Invalid current limit value: {e}")

    def start_record(self):
        """Start recording data to a CSV file."""
        try:
            # Open a new CSV file for writing
            self.recording_file = open(f"C:/Users/LG/Desktop/2461_SourceMeter/실시간_전류_측정기록/current_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mode='w', newline='')
            self.csv_writer = csv.writer(self.recording_file)
            
            # Write headers
            self.csv_writer.writerow(["Timestamp", "Source Voltage (V)", "Current Limit (A)", "Current (A)"])
            
            # Update recording state
            self.is_recording = True
            print("Recording started.")
            
            # Enable/Disable buttons
            self.start_record_button.setEnabled(False)
            self.stop_record_button.setEnabled(True)
        except Exception as e:
            print(f"Error starting recording: {e}")

    def stop_record(self):
        """Stop recording data."""
        try:
            if self.is_recording:
                # Close the CSV file
                self.recording_file.close()
                self.is_recording = False
                print("Recording stopped.")
                
                # Enable/Disable buttons
                self.start_record_button.setEnabled(True)
                self.stop_record_button.setEnabled(False)
        except Exception as e:
            print(f"Error stopping recording: {e}")

    def update_graph(self, frame):
        try:
            # Read current value from Keithley
            if self.device_model == "2461":
                current = float(self.keithley.query(":READ?"))
            else:
                response = self.keithley.query(":READ?")
                current_str = response.strip().split(',')[0]
                current = float(current_str)

            time_stamps.append(datetime.now())
            current_values.append(current)

            # Update QLabel with the latest voltage and current values
            self.voltage_display.setText(f"Voltage: {self.source_voltage:.2f} V")
            self.current_display.setText(f"Current: {current:.6f} A")

            # Limit data to the last 20 points for display
            time_stamps_limited = time_stamps[-20:]
            current_values_limited = current_values[-20:]

            # Clear and redraw the plot
            self.canvas.ax.clear()
            self.canvas.ax.plot(time_stamps_limited, current_values_limited, 
                                marker='o', linestyle='-', color='b')

            # Update axis properties
            self.canvas.ax.set_title("Real-Time Current Measurement")
            self.canvas.ax.set_xlabel("Time")
            self.canvas.ax.set_ylabel("Current (A)")
            
            # Dynamically adjust x-axis limits
            if len(time_stamps_limited) > 1:
                self.canvas.ax.set_xlim(time_stamps_limited[0], time_stamps_limited[-1])
            else:
                single_time = time_stamps_limited[0]
                self.canvas.ax.set_xlim(single_time, single_time + timedelta(seconds=1))

            # Format x-axis for HH:MM:SS only
            self.canvas.ax.xaxis.set_major_locator(mdates.SecondLocator(interval=1))  # Show ticks every second
            self.canvas.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # Exclude milliseconds
            
            # Rotate x-axis tick labels for better readability
            self.canvas.ax.tick_params(axis='x', rotation=45)
            
            # Redraw canvas to reflect updates
            self.canvas.draw()

            # Append data to CSV if recording is active
            if self.is_recording:
                self.csv_writer.writerow([
                    time_stamps[-1].strftime('%Y-%m-%d %H:%M:%S.%f'), 
                    self.source_voltage, 
                    self.current_limit, 
                    current
                ])
        
        except Exception as e:
            print(f"Error updating graph: {e}")

    def start_animation(self):
        """애니메이션 새로 시작"""
        if hasattr(self, 'ani') and self.ani.event_source:
            self.ani.event_source.stop()  # 기존 애니메이션 중지

        self.ani = FuncAnimation(
            self.canvas.fig,
            self.update_graph,
            interval=100,
            cache_frame_data=False
        )

    def closeEvent(self, event):
        """창 닫을 때 리소스 정리"""
        try:
            if hasattr(self, 'ani') and self.ani.event_source:
                self.ani.event_source.stop()
                
            # 장비 연결 상태 확인 후 정리
            if self.keithley is not None:
                try:
                    self.keithley.write(":OUTP OFF")
                except pyvisa.errors.InvalidSession:
                    pass  # 이미 종료된 세션은 무시
                finally:
                    self.keithley.close()
                    self.keithley = None
        except Exception as e:
            print(f"리소스 정리 오류: {e}")
        finally:
            event.accept()
            
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        # Set figure size (width=10 inches, height=6 inches)
        self.fig, self.ax = plt.subplots(figsize=(20, 15))  # Adjust these values as needed
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax.set_title("Real-Time Current Measurement")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Current (A)")
        self.ax.grid(True)


# Global variables
rm = pyvisa.ResourceManager()
time_stamps = []
current_values = []

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
