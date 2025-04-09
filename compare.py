import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel,
    QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class DiodeComparisonApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diode Comparison")
        self.setGeometry(500, 100, 1500, 1200)  # 창 크기 조정

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # 메인 레이아웃 (수평)

        # Left panel for controls (라벨과 버튼)
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(10, 10, 10, 10)  # 여백 설정

        # Load button
        self.load_button = QPushButton("Load CSV Files")
        self.load_button.setFixedSize(150, 40)  # 버튼 크기 조정
        self.load_button.clicked.connect(self.load_csv_files)
        left_panel.addWidget(self.load_button)

        # Zoom 버튼
        self.zoom_button = QPushButton("Zoom In")
        self.zoom_button.setFixedSize(150, 40)
        self.zoom_button.clicked.connect(self.enable_zoom)
        left_panel.addWidget(self.zoom_button)

        # Reset 버튼
        self.reset_button = QPushButton("Reset View")
        self.reset_button.setFixedSize(150, 40)
        self.reset_button.clicked.connect(self.reset_view)
        left_panel.addWidget(self.reset_button)

        # Pan 버튼
        self.pan_button = QPushButton("Pan")
        self.pan_button.setFixedSize(150, 40)
        self.pan_button.clicked.connect(self.enable_pan)
        left_panel.addWidget(self.pan_button)

        # Add spacer to push controls to the top
        left_panel.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Add left panel to the main layout
        main_layout.addLayout(left_panel)

        # Right panel for the graph (그래프 부분)
        self.canvas = FigureCanvas(plt.figure(figsize=(12, 8)))  # 그래프 크기 설정 (12x8 inches)
        main_layout.addWidget(self.canvas)

        # Data storage for loaded files
        self.loaded_files = []

    def load_csv_files(self):
        """Load up to 6 CSV files and plot their data."""
        try:
            # Open file dialog to select CSV files
            file_dialog = QFileDialog()
            file_paths, _ = file_dialog.getOpenFileNames(
                self, "Select up to 6 CSV Files", "", "CSV Files (*.csv)"
            )

            if len(file_paths) == 0:
                QMessageBox.warning(self, "No File Selected", "No files were selected.")
                return

            if len(file_paths) > 6:
                QMessageBox.warning(self, "Too Many Files", "Please select up to 6 files.")
                return

            # Clear previous data and plot
            self.loaded_files = []
            self.canvas.figure.clf()
            ax = self.canvas.figure.add_subplot(111)

            # Load and plot each file
            colors = ['b', 'g', 'r', 'c', 'm', 'y']  # Colors for up to 6 diodes
            for i, file_path in enumerate(file_paths):
                data = np.loadtxt(file_path, delimiter=",", skiprows=1)  # Skip header row
                voltages = data[:, 0]
                currents = data[:, 1]
                label = os.path.basename(file_path).replace(".csv", "")  # Use filename as label

                # Plot data
                ax.plot(voltages, currents, marker='o', linestyle='-', color=colors[i % len(colors)], label=label)

                # Store loaded data for future use (optional)
                self.loaded_files.append((file_path, voltages, currents))
                # Save original axes limits for reset functionality
                self.original_xlim = ax.get_xlim()
                self.original_ylim = ax.get_ylim()


            # Configure plot appearance
            ax.set_title("Diode I-V Characteristics Comparison", fontsize=18)
            ax.set_xlabel("Voltage (V)", fontsize=14)
            ax.set_ylabel("Current (A)", fontsize=14)
            ax.grid(True)
            ax.legend(fontsize=12)

            # Update canvas
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def enable_zoom(self):
        """Enable zoom functionality."""
        QMessageBox.information(self, "Zoom Mode", "Use your mouse wheel to zoom in/out.")

        def on_scroll(event):
            """Handle mouse scroll event for zooming."""
            ax = self.canvas.figure.gca()  # Get current axes

            # Zoom in or out based on scroll direction
            if event.button == 'up':  # Zoom in
                scale_factor = 0.9
            elif event.button == 'down':  # Zoom out
                scale_factor = 1.1
            else:
                return

            # Get current axis limits
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()

            # Calculate new limits based on scale factor
            x_center = (xlim[0] + xlim[1]) / 2
            y_center = (ylim[0] + ylim[1]) / 2

            new_xlim = [x_center + (x - x_center) * scale_factor for x in xlim]
            new_ylim = [y_center + (y - y_center) * scale_factor for y in ylim]

            # Apply new limits and redraw the canvas
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.canvas.draw()

        # Connect the scroll event to the zoom function
        self.canvas.mpl_connect('scroll_event', on_scroll)

    def reset_view(self):
        """Reset the graph view to the original limits."""
        if self.original_xlim is None or self.original_ylim is None:
            QMessageBox.warning(self, "No Data", "No data to reset. Please load and plot data first.")
            return

        # Reset axes to original limits
        ax = self.canvas.figure.gca()
        ax.set_xlim(self.original_xlim)
        ax.set_ylim(self.original_ylim)

        # Redraw the canvas
        self.canvas.draw()

    def enable_pan(self):
        """Enable pan functionality to move the graph."""
        QMessageBox.information(self, "Pan Mode", "Click and drag the graph to pan.")

        # Variables to store the initial mouse position
        self.panning = False
        self.pan_start = None

        def on_press(event):
            """Handle mouse press event to start panning."""
            if event.button == 1:  # Left mouse button
                self.panning = True
                self.pan_start = (event.xdata, event.ydata)  # Store starting position

        def on_release(event):
            """Handle mouse release event to stop panning."""
            if event.button == 1:  # Left mouse button
                self.panning = False
                self.pan_start = None

        def on_motion(event):
            """Handle mouse motion event to perform panning."""
            if not self.panning or self.pan_start is None:
                return
            
            # Check if event.xdata or event.ydata is None
            if event.xdata is None or event.ydata is None:
                return

            ax = self.canvas.figure.gca()  # Get current axes

            # Calculate the shift based on mouse movement
            dx = self.pan_start[0] - event.xdata
            dy = self.pan_start[1] - event.ydata

            # Update axis limits
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            ax.set_xlim([x + dx for x in xlim])
            ax.set_ylim([y + dy for y in ylim])

            # Redraw the canvas
            self.canvas.draw()

        # Connect the events to the handlers
        self.canvas.mpl_connect('button_press_event', on_press)
        self.canvas.mpl_connect('button_release_event', on_release)
        self.canvas.mpl_connect('motion_notify_event', on_motion)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiodeComparisonApp()
    window.show()
    sys.exit(app.exec_())
