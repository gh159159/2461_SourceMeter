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
    def __init__(self, visa_address):
        super().__init__()
        
        # Initialize Keithley and create canvas
        self.visa_address = visa_address
        self.init_keithley()

        self.setWindowTitle("Keithley 2461 Control Panel")
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
        self.voltage_input.setMaximumWidth(100)
        
        # Current limit control widgets
        current_limit_layout = QVBoxLayout()
        current_limit_label = QLabel("Current Limit (A):")
        self.current_limit_input = QLineEdit("1")
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
        self.ani = FuncAnimation(self.canvas.fig, self.update_graph, interval=100, cache_frame_data=False)

        # Initialize recording state
        self.is_recording = False
        self.recording_file = None  # File object for the CSV file
        self.csv_writer = None      # CSV writer object

    def init_keithley(self):
        """Initialize the Keithley SourceMeter"""
        global keithley
        keithley = rm.open_resource(self.visa_address) 
        keithley.write("*RST")
        keithley.write(":SENS:FUNC 'CURR'")
        keithley.write(":SENS:CURR:RANG:AUTO ON")
        keithley.write(":FORM:DATA ASC")
        keithley.write(":SOUR:FUNC VOLT")
        keithley.write(":SOUR:VOLT:RANG 20")
        keithley.write(":SOUR:VOLT 0")
        keithley.write(":OUTP ON")

    def set_voltage(self):
        """Set the source voltage"""
        global source_voltage
        try:
            voltage = float(self.voltage_input.text())
            if -10 <= voltage <= 20:
                keithley.write(f":SOUR:VOLT {voltage}")
                source_voltage = voltage  # Update global variable
            else:
                print("전압제한 범위를 벗어났습니다! (-10[V] ~ 20[V]로 설정돼있습니다.)")
        except ValueError as e:
            print(f"Invalid voltage value: {e}")

    def set_current_limit(self):
        """Set the current limit"""
        global current_limit
        try:
            current_limit_value = float(self.current_limit_input.text())
            if -1.0 < current_limit_value <= 2.0:
                keithley.write(f":SOUR:VOLT:ILIM {current_limit_value}")
                current_limit = current_limit_value
            else:
                print("전류제한 범위를 벗어났습니다! (-1[A] ~ 2[A]로 설정돼있습니다.)")
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
            current = float(keithley.query(":READ?"))
            time_stamps.append(datetime.now())
            current_values.append(current)

            # Update QLabel with the latest voltage and current values
            self.voltage_display.setText(f"Voltage: {source_voltage:.2f} V")
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
                    source_voltage, 
                    current_limit, 
                    current
                ])
        
        except Exception as e:
            print(f"Error updating graph: {e}")

    def closeEvent(self, event):
        """창 닫을 때 애니메이션 및 리소스 정리"""
        self.ani.event_source.stop()  # 애니메이션 중지
        keithley.write(":OUTP OFF")   # 장비 출력 종료
        keithley.close()              # 장비 연결 해제
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
source_voltage = 0.0  # Default source voltage
current_limit = 1  # Default current limit

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
