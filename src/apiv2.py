import json
from websocket import WebSocketApp
from datetime import datetime, timedelta
import pandas as pd
from preprocess import *
from model import *
import os
from utils import *

LIVE_DATA_PATH = "../data/live.csv"
APIKEY = "iAfvumytfgq4EvTak20t8uuxCxVETG7v"


class PolygonClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.processed_df, self.dates, self.predictions = (None, None, None)
        self.ws = None
        self.live_df = None
        self.processor = DataPreprocessor()
        self.model = LightGBMModel()

    def on_message(self, ws, message):
        data = json.loads(message)

        for event in data:
            if event.get("ev") == "AM" and event.get("sym") == "I:NDX":
                dt_obj = datetime.utcfromtimestamp(
                    event.get("s", 0) / 1000
                ) + timedelta(hours=2)
                date = dt_obj.strftime("%Y.%m.%d")  # changed the format to match the CSV
                time = dt_obj.strftime("%H:%M:%S")

                open_value = str(event.get("o", "")).replace(",", ".")
                high_value = str(event.get("h", "")).replace(",", ".")
                low_value = str(event.get("l", "")).replace(",", ".")
                close_value = str(event.get("c", "")).replace(",", ".")

                new_row = [date, time, open_value, high_value, low_value, close_value]

                # Check if file exists to determine whether header is needed
                file_exists = os.path.isfile(LIVE_DATA_PATH)

                # Open file in append mode
                with open(LIVE_DATA_PATH, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    if not file_exists:
                        writer.writerow(["date", "time", "open", "high", "low", "close"])  # header
                    writer.writerow(new_row)  # data row

                self.live_df = self.read_df(LIVE_DATA_PATH)
                self.dates = self.live_df["date"]
                self.processed_df = self.processor.transform_for_training()
                self.predictions = self.model.predict(self.processed_df)
                self.dates = self.dates[len(self.processed_df.shape[0]):]


    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(
        self, ws, *args, **kwargs
    ):  # Modified to accept any additional arguments
        print("### closed ###", args, kwargs)  # Print all arguments

    def on_open(self, ws):
        print("### opened ###")
        ws.send(json.dumps({"action": "auth", "params": self.api_key}))
        # Subscribing to aggregate minute data for all stocks in NASDAQ100
        ws.send(json.dumps({"action": "subscribe", "params": "AM.I:NDX"}))

    def connect(self):
        self.ws = WebSocketApp(
            "wss://socket.polygon.io/indices",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )
        self.ws.run_forever()

    def get_agg_dat(self):
        return self.processed_df, self.dates, self.predictions
    def read_df(self, file_loc):
        "Used to read main.csv etc"
        data = pd.read_csv(
            file_loc,
            names=["date", "time", "open", "high", "low", "close"],  # Lowercase column names
            delimiter=";",
        )
        for col in ["open", "high", "low", "close"]:  # Lowercase column names
            data[col] = data[col].str.replace(",", ".").astype(float)
        data["datetime"] = data.apply(
            lambda row: datetime.strptime(
                f"{row['date']} {row['time']}", "%Y.%m.%d %H:%M:%S"
            ),
            axis=1,
        )
        data = data.sort_values(by=["datetime"])  # Lowercase column name
        return data


