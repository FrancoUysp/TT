from flask import Flask, jsonify, request, render_template
import pickle
import os
import json
import threading
from src.preprocess import DataPreprocessor
from src.server_connect import (
    append_to_buffer_and_update_main,
    create_buffer_queue,
    update_main,
)
from src.strategies.wave_model.wave_model import WaveModel
from src.utils import *
import time
from threading import Lock
from flask_cors import CORS

HOST_IP = "0.0.0.0"
HOST_PORT = 8000
UPDATE_INTERVAL = 1

app = Flask(__name__)
CORS(app)

data_lock = Lock()
buffer_df = None


class MainServer:
    def __init__(self):
        """
        This class is the main server that runs in the background and updates the data.
        """
        global buffer_df
        buffer_df = create_buffer_queue()
        self.models = self.load_models()  # Load or initialize your models here
        self.update_thread = threading.Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()
        self.preprocessor = DataPreprocessor()

    def load_models(self):
        """
        This method should load your models from disk and return them in a dictionary.
        """
        models = {}
        return models

    def update_data(self):
        """
        This method should be run in a separate thread and should update the data
        """
        global buffer_df
        while True:
            try:
                with data_lock:
                    buffer_df = append_to_buffer_and_update_main(buffer_df)
                    if self.models:
                        for model in self.models.values():
                            processed_data = self.preprocessor.transform_for_pred(
                                buffer_df.copy()
                            )
                            model.execute(processed_data)

            except Exception as e:
                print(f"An error occurred: {e}")

            time.sleep(UPDATE_INTERVAL)


@app.route("/get_data", methods=["GET"])
def get_data():
    """
    This method should return the candle data in JSON format.
    """
    with data_lock:
        if buffer_df is not None:
            data = buffer_df[["datetime", "open", "high", "low", "close"]].to_dict(
                "records"
            )
            return jsonify(data)
        else:
            return jsonify({"error": "Data not available"}), 503


@app.route("/get_models", methods=["GET"])
def get_models():
    """
    This method should return the list of models that the system supports and their parameters.
    """
    models_dir = "models"
    models_info = []
    for model_name in os.listdir(models_dir):
        model_path = os.path.join(models_dir, model_name)
        if os.path.isdir(model_path):
            params_file_path = os.path.join(model_path, "parameters.json")
            try:
                with open(params_file_path, "r") as params_file:
                    params = json.load(params_file)
                    strategy_params = params.get("strategy_params", {})
                    models_info.append({"name": model_name, "params": strategy_params})
            except FileNotFoundError:
                print(f"parameters.json not found for model {model_name}")
                continue
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for model {model_name}: {e}")
                continue

    return jsonify(models_info)


@app.route("/add_model", methods=["POST"])
def add_model():
    """
    This method should add a new model to the system. that is currently training.
    """
    model_params = request.json
    model_name = model_params.get("name")
    if not model_name:
        return jsonify({"success": False, "message": "Model name is required"}), 400
    with data_lock:
        if model_name in main_server.models:
            return jsonify({"success": False, "message": "Model already exists"}), 400
        else:
            model_1 = pickle.load(open("models/wave_model/m1.pickle.dat", "rb"))
            model_2 = pickle.load(open("models/wave_model/m2.pickle.dat", "rb"))
            new_model = WaveModel(model_1, model_2, model_params)
            main_server.models[model_name] = new_model
            return jsonify({"success": True, "message": "Model added successfully"})


@app.route("/get_active_models", methods=["GET"])
def get_active_models():
    """
    This method should return the list of models that are currently running.
    """
    with data_lock:
        active_models = [
            {
                "name": model.get_name(),
                "params": model.get_params(),
                "type": model.get_type(),
            }
            for model in main_server.models.values()
        ]
        return jsonify(active_models)


@app.route("/update_model", methods=["POST"])
def update_model():
    """
    This method should update the parameters of a model that is currently running.
    """
    with data_lock:
        model_params = request.json
        old_name = model_params.get("old_name")
        new_name = model_params.get("name")

        if old_name in main_server.models:
            model_to_update = main_server.models[old_name]
            model_to_update.set_params(model_params)
            if new_name and new_name != old_name:
                if new_name in main_server.models:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "New model name already exists",
                            }
                        ),
                        400,
                    )
                model_to_update.set_name(new_name)
                main_server.models[new_name] = model_to_update
                del main_server.models[old_name]
            else:
                main_server.models[old_name] = model_to_update

            return jsonify({"success": True, "message": "Model updated successfully"})

        else:
            return jsonify({"success": False, "message": "Old model not found"}), 404


@app.route("/delete_model", methods=["POST"])
def delete_model():
    """
    this method should delete a model that is currently running.
    """
    with data_lock:
        model_name = request.json.get("name")
        if model_name and model_name in main_server.models:
            del main_server.models[model_name]
            return jsonify({"success": True, "message": "Model deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Model not found"}), 404


@app.route("/get_model_params", methods=["GET"])
def get_model_params():
    """
    this method should return the parameters of a model that is currently running.
    """
    with data_lock:
        model_name = request.args.get("name")
        if model_name and model_name in main_server.models:
            model = main_server.models[model_name]
            model_params = (
                model.get_params()
            )  # Here we assume get_params() returns a dictionary
            return jsonify({"success": True, "params": model_params})
        else:
            return jsonify({"success": False, "message": "Model not found"}), 404


@app.route("/")
def index():
    """
    renders the index.html file
    """
    return render_template("index.html")


if __name__ == "__main__":
    update_main()
    main_server = MainServer()
    app.run(host=HOST_IP, port=HOST_PORT, debug=True)
