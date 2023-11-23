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
                    # if self.models:
                    #     for model_name, model in self.models.items():
                    #         decision = model.process_new_data(buffer_df)

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

    # print(models_info)
    return jsonify(models_info)

@app.route('/add_model', methods=['POST'])
def add_model():
    model_params = request.json
    model_name = model_params.get("name")  # Assuming a 'name' key in your JSON
    if not model_name:
        return jsonify({"success": False, "message": "Model name is required"}), 400
    
    with data_lock:
        if model_name in main_server.models:
            return jsonify({"success": False, "message": "Model already exists"}), 400
        else:
            # Store the model parameters under the model name
            main_server.models[model_name] = model_params
            # You might want to create an actual model instance here and store it
            # instead of just the parameters, depending on your application's requirements
            return jsonify({"success": True, "message": "Model added successfully"})

@app.route('/get_active_models', methods=['GET'])
def get_active_models():
    with data_lock:
        # Return a list of model dictionaries with names and parameters
        active_models = [{"name": name, "params": params} for name, params in main_server.models.items()]
        return jsonify(active_models)

@app.route('/update_model', methods=['POST'])
def update_model():
    with data_lock:
        model_params = request.json
        old_name = model_params.get("old_name")
        new_name = model_params.get("name")

        if old_name in main_server.models:
            if new_name != old_name:
                if new_name not in main_server.models:
                    main_server.models.pop(old_name)
                    main_server.models[new_name] = model_params
                    main_server.models[new_name]['name'] = new_name
                else:
                    return jsonify({"success": False, "message": "New model name already exists"}), 400
            else:
                main_server.models[old_name] = model_params
                main_server.models[old_name]['name'] = old_name

            if 'old_name' in model_params:
                del model_params['old_name']

            print(main_server.models)
            return jsonify({"success": True, "message": "Model updated successfully"})

        else:
            return jsonify({"success": False, "message": "Old model not found"}), 404

@app.route('/delete_model', methods=['POST'])
def delete_model():
    with data_lock:
        model_name = request.json.get("name")
        if model_name and model_name in main_server.models:
            # Delete the model
            del main_server.models[model_name]
            return jsonify({"success": True, "message": "Model deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Model not found"}), 404

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    update_main()
    main_server = MainServer()
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)
