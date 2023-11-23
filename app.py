from flask import Flask, jsonify, request, render_template
import os
import json
import threading
from src.server_connect import append_to_buffer_and_update_main, create_buffer_queue, update_main
from src.utils import *
import time
from threading import Lock
from flask_cors import CORS

HOST_IP = '0.0.0.0'
HOST_PORT = 8000
UPDATE_INTERVAL = 3 

app = Flask(__name__)
CORS(app)

data_lock = Lock()
buffer_df = None

class MainServer():
    def __init__(self):
        global buffer_df
        buffer_df = create_buffer_queue()
        self.models = self.load_models()  # Load or initialize your models here
        self.update_thread = threading.Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()

    def load_models(self):
        models = {}
        return models
    def update_data(self):
        global buffer_df
        while True:
            try:
                with data_lock:
                    buffer_df = append_to_buffer_and_update_main(buffer_df)
                    if self.models:
                        for model_name, model in self.models.items():
                            decision = model.process_new_data(buffer_df)

            except Exception as e:
                print(f"An error occurred: {e}")

            time.sleep(UPDATE_INTERVAL)

@app.route('/get_data', methods=['GET'])
def get_data():
    with data_lock:
        if buffer_df is not None:
            data = buffer_df[['datetime', 'open', 'high', 'low', 'close']].to_dict('records')
            return jsonify(data)
        else:
            return jsonify({"error": "Data not available"}), 503

@app.route('/get_models', methods=['GET'])
def get_models():
    models_dir = 'models'  
    models_info = []
    for model_name in os.listdir(models_dir):
        model_path = os.path.join(models_dir, model_name)
        if os.path.isdir(model_path):
            params_file_path = os.path.join(model_path, 'parameters.json')
            try:
                with open(params_file_path, 'r') as params_file:
                    params = json.load(params_file)
                    # Only append strategy_params to the models_info
                    strategy_params = params.get('strategy_params', {})  # Get strategy_params or empty dict if not found
                    models_info.append({'name': model_name, 'params': strategy_params})
            except FileNotFoundError:
                print(f"parameters.json not found for model {model_name}")
                continue
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for model {model_name}: {e}")
                continue

    print(models_info)
    return jsonify(models_info)

@app.route('/add_model', methods=['POST'])
def add_model():
    # Retrieve the model parameters from the request
    model_params = request.json
    # Logic to add the model goes here
    print('Received model to add:', model_params)
    # After adding the model, return success
    return jsonify({"success": True, "message": "Model added successfully"})

@app.route('/set_params', methods=['POST'])
def set_params():
    # Retrieve and set parameters for your model
    params = request.json
    print('Received parameters:', params)  # This line will print the parameters to the console
    # Placeholder for setting parameters
    # Here you would add your logic to actually set the parameters in your system
    
    return jsonify({"success": True, "message": "Parameters set"})
@app.route('/sell_all', methods=['POST'])
def sell_all():
    # Implement the logic to sell all
    # Placeholder response
    return jsonify({"success": True, "message": "Sold all positions"})

@app.route('/opt_out', methods=['POST'])
def opt_out():
    # Implement the logic for opting out
    # Placeholder response
    return jsonify({"success": True, "message": "Opted out successfully"})

@app.route('/get_roi_day', methods=['GET'])
def get_roi_day():
    # Placeholder for daily ROI retrieval logic
    daily_roi = "5.2%"
    return jsonify({"daily_roi": daily_roi})

@app.route('/get_roi_month', methods=['GET'])
def get_roi_month():
    # Placeholder for monthly ROI retrieval logic
    monthly_roi = "10.4%"
    return jsonify({"monthly_roi": monthly_roi})

@app.route('/get_roi_all_time', methods=['GET'])
def get_roi_all_time():
    # Placeholder for all-time ROI retrieval logic
    all_time_roi = "150%"
    return jsonify({"all_time_roi": all_time_roi})

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    update_main()
    main_server = MainServer()
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)
