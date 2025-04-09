from flask import jsonify, request, Blueprint
import pyvisa
import pandas as pd
import numpy as np

measure_route = Blueprint("measure_route", __name__)

rm = pyvisa.ResourceManager()

try:
    instrument = rm.open_resource('USB0::0x05E6::0x2461::04628945::INSTR')
    instrument.write_termination = '\n'
    instrument.read_termination = '\n'
    instrument.write("*RST")
    instrument.write("*CLS")
    instrument_connected = True
except Exception as e:
    instrument_connected = False
    instrument = None

@measure_route.route("/measure", methods=["POST"])
def measure():
    if not instrument_connected:
        return jsonify({"error": "Instrument not connected"})

    try:
        start_voltage = float(request.form.get("start_voltage", 0))
        end_voltage = float(request.form.get("end_voltage", 5))
        step_voltage = float(request.form.get("step_voltage", 0.1))

        instrument.write(":SOURce:FUNCtion VOLTage")          # 전압 소스 모드 설정
        instrument.write(":SENSe:FUNCtion 'CURRent'")         # 전류 측정 모드 활성화
        instrument.write(":SOURce:VOLTage:RANGe:AUTO ON")     # 자동 전압 범위 활성화
        instrument.write(":SENSe:CURRent:RANGe:AUTO ON")      # 자동 전류 범위 활성화
        instrument.write(":SOURce:VOLTage:ILIMit 0.02")       # 최대 전류 제한 (20mA)
        instrument.write("OUTP ON")

        voltages = np.arange(start_voltage, end_voltage + step_voltage, step_voltage)
        currents = []

        for voltage in voltages:
            try:
                instrument.write(f"SOUR:VOLT {voltage}")
                instrument.query("*OPC?")
                current = float(instrument.query("MEAS:CURR?").strip())
                currents.append(current)
            except Exception as e:
                currents.append(0)

        return jsonify({"voltages": voltages.tolist(), "currents": currents})

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        instrument.write("OUTP OFF")

@measure_route.route('/save_data', methods=['POST'])
def save_data():
    data = {
        'Voltage (V)': request.json['voltages'],
        'Current (A)': request.json['currents']
    }
    df = pd.DataFrame(data)
    
    filename = request.json.get('filename', 'measurement_results.csv')
    df.to_csv(filename, index=False)
    return jsonify({'message': f'Data saved to {filename}'})
