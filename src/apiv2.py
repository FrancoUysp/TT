import json
import csv
from websocket import WebSocketApp
import datetime

import pandas as pd
from preprocess import *
from model import *
import os
from utils import *

LIVE_DATA_PATH = "../data/live.csv"
APIKEY = "iAfvumytfgq4EvTak20t8uuxCxVETG7v"


class PolygonClient:
    def __init__(self):
        self.api_key = APIKEY 
        self.processed_df, self.dates, self.predictions = (None, None, None)
        self.ws = None
        self.live_df = None
        self.processor = DataPreprocessor()
        self.model = LightGBMModel()
        self.model.load_model("../models")

    def on_message(self, ws, message):
        data = json.loads(message)

        for event in data:
            if event.get("ev") == "AM" and event.get("sym") == "I:NDX":
                dt_obj = datetime.datetime.utcfromtimestamp(
                    event.get("s", 0) / 1000
                ) + datetime.timedelta(hours=2)
                date = dt_obj.strftime("%Y.%m.%d")  # changed the format to match the CSV
                time = dt_obj.strftime("%H:%M:%S")

                open_value = str(event.get("o", "")).replace(".", ",")
                high_value = str(event.get("h", "")).replace(".", ",")
                low_value = str(event.get("l", "")).replace(".", ",")
                close_value = str(event.get("c", "")).replace(".", ",")

                new_row = [date, time, open_value, high_value, low_value, close_value]

                # Check if file exists to determine whether header is needed
                file_exists = os.path.isfile(LIVE_DATA_PATH)

                # Open file in append mode
                with open(LIVE_DATA_PATH, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    if not file_exists:
                        writer.writerow(["date", "time", "open", "high", "low", "close"])  
                    writer.writerow(new_row)  

                self.live_df = read_df(LIVE_DATA_PATH)
                self.dates = self.live_df["datetime"]
                if (self.live_df.shape[0]>60):
                    self.processed_df = self.processor.transform_for_pred(self.live_df)
                    if self.processed_df.empty:
                        self.dates = None
                        self.predictions = None
                    else:
                        self.predictions = self.model.predict(self.processed_df, 0.5)
                        self.dates = self.dates[self.processed_df.shape[0]:]

                print(self.live_df)

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


