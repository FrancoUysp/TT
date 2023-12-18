from flask import Flask, jsonify, request, render_template
import datetime
import sys
import pickle
import os
import json
import threading
from src.preprocess import DataPreprocessor
from src.strategies.trend_follower.trend_follower import TrendFollower
from src.strategies.wave_model.wave_model import WaveModel
from src.utils import *
import time
from threading import Lock
from flask_cors import CORS
from src.server_connect import Server

HOST_IP = "0.0.0.0"
HOST_PORT = 8000

app = Flask(__name__)
CORS(app)
data_lock = Lock()

# Assuming the Server class is in the src.server_connect module


class MainServer:
    def __init__(self):
        """
        This class is the main server that runs in the background and updates the data.
        """
        self.server = Server()
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
        last_minute = datetime.datetime.now().minute
        i = 0
        while True:
            current_time = datetime.datetime.now()
            current_minute = current_time.minute

            if last_minute != current_minute:
                last_minute = current_minute  # Update the last_minute to the current
                print("Fetching new minute data...")

                try:
                    with data_lock:
                        self.server.append_to_buffer_and_update_main()
                        processed_data = self.preprocessor.transform_for_pred(
                            self.server.buffer_df.copy()
                        )
                        if self.models:
                            for model in self.models.values():
                                # model.execute(
                                #     processed_data, self.server.buffer_df["datetime"].iloc[-1]
                                # )
                                if i == 0:
                                    model.handle_long_entry(
                                        self.server.buffer_df["close"].iloc[-1],
                                        self.server.buffer_df["datetime"].iloc[-1],
                                    )
                                    print(f"model: {model.get_name()} entered a long")
                                if i == 1:
                                    model.handle_long_exit(
                                        self.server.buffer_df["close"].iloc[-1],
                                        self.server.buffer_df["datetime"].iloc[-1],
                                    )
                                    print(f"model: {model.get_name()} exited a long")
                                if i == 2:
                                    model.handle_short_entry(
                                        self.server.buffer_df["close"].iloc[-1],
                                        self.server.buffer_df["datetime"].iloc[-1],
                                    )
                                    print(f"model: {model.get_name()} entered a short")
                                if i == 3:
                                    model.handle_short_exit(
                                        self.server.buffer_df["close"].iloc[-1],
                                        self.server.buffer_df["datetime"].iloc[-1],
                                    )
                                    print(f"model: {model.get_name()} exited a short")
                                i += 1
                except Exception as e:
                    print(f"An error occurred: {e}")

            time_to_sleep = 60.5 - datetime.datetime.now().second
            time.sleep(time_to_sleep)


main_server = MainServer()


@app.route("/get_data", methods=["GET"])
def get_data():
    with data_lock:
        model_name = request.args.get("name")
        response_data = {"candle_data": [], "trade_history": []}
        if main_server.server.buffer_df is not None:
            response_data["candle_data"] = main_server.server.buffer_df[
                ["datetime", "open", "high", "low", "close"]
            ].to_dict("records")

        if model_name and model_name in main_server.models:
            model = main_server.models[model_name]
            trade_hist = model.get_trade_history()
            print(trade_hist)
            response_data["trade_history"] = trade_hist

        return jsonify(response_data)


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
                    print(models_info)
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
    This method should add a new model to the system that is currently training.
    """
    model_params = request.json
    model_name = model_params.get("name")
    if not model_name:
        return jsonify({"success": False, "message": "Model name is required"}), 400

    with data_lock:
        if model_name in main_server.models:
            return jsonify({"success": False, "message": "Model already exists"}), 400
        else:
            # Here, we assume the model files are pickled and stored in a directory named "models/wave_model/"
            try:
                if model_name == "wave_model":
                    model_1_path = os.path.join("models", "wave_model", "m1.pickle.dat")
                    model_2_path = os.path.join("models", "wave_model", "m2.pickle.dat")

                    # Make sure to handle the case where the files might not exist.
                    if not os.path.exists(model_1_path) or not os.path.exists(
                        model_2_path
                    ):
                        return (
                            jsonify(
                                {"success": False, "message": "Model files not found"}
                            ),
                            400,
                        )

                    with open(model_1_path, "rb") as f1, open(model_2_path, "rb") as f2:
                        model_1 = pickle.load(f1)
                        model_2 = pickle.load(f2)

                    new_model = WaveModel(
                        model_1, model_2, model_params, main_server.server
                    )

                elif model_name == "trend_follower":
                    new_model = TrendFollower(model_params, main_server.server)

                else:
                    return (
                        jsonify({"error": False, "message": "Model not found"}),
                        404,
                    )

                main_server.models[model_name] = new_model
                return jsonify({"success": True, "message": "Model added successfully"})
            except Exception as e:
                # Catch any other exceptions and return an error message.
                return jsonify({"success": False, "message": str(e)}), 500


# The MainServer class and server instance should be defined as per your previous structure.


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
            model = main_server.models[model_name]
            if model.is_in_trade() == True:
                return jsonify(
                    {
                        "success": False,
                        "message": "Cannot remove model that is in trade",
                    }
                )
            else:
                del main_server.models[model_name]
                return jsonify(
                    {"success": True, "message": "Model deleted successfully"}
                )
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


@app.route("/get_model_labels", methods=["GET"])
def get_model_labels():
    try:
        with data_lock:
            model_name = request.args.get("name")
            if model_name and model_name in main_server.models:
                model = main_server.models[model_name]
                model_labels = model.get_labels()  # Get labels from the model
                return jsonify({"success": True, "labels": model_labels})
            else:
                return jsonify({"success": False, "message": "Model not found"}), 404
    except Exception as e:
        print(str(e))
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/is_model_in_trade", methods=["GET"])
def is_model_in_trade():
    try:
        model_name = request.args.get("name")
        if model_name and model_name in main_server.models:
            model = main_server.models[model_name]
            is_in_trade = model.is_in_trade()
            return jsonify({"status": "success", "is_in_trade": is_in_trade}), 200
        else:
            return jsonify({"status": "error", "message": "Model not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/exit_trade", methods=["GET"])
def exit_trade():
    try:
        with data_lock:
            model_name = request.args.get("name")
            if model_name and model_name in main_server.models:
                model = main_server.models[model_name]
                if model.is_in_trade() == False:
                    return (
                        jsonify({"status": "error", "message": "Model not in trade"}),
                        404,
                    )
                exit_status = model.exit_trade()
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": "Trade exit executed",
                            "exit_status": exit_status,
                        }
                    ),
                    200,
                )
            else:
                return jsonify({"status": "error", "message": "Model not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/")
def index():
    """
    renders the index.html file
    """
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host=HOST_IP, port=HOST_PORT)
