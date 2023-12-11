import pandas as pd
import os
from .utils import *
import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timedelta


class Server:
    BUFFER_SIZE = 1320
    SYMBOL = "NAS100"
    TIMEFRAME = mt5.TIMEFRAME_M1

    SERVER = "Pepperstone-Demo"
    PASSWORD = "duCf7yzn:h"
    LOGIN = 61202587

    def __init__(self):
        self.update_main()
        self.last_processed_data = (
            None  # New attribute to track the last processed data
        )
        self.buffer_df = self.create_buffer_queue()
        self.positions = {}

    def create_buffer_queue(self):
        """
        This method will create the current queue that is in memory and will be used to process and make decisions.
        """
        file_path = os.path.join("data", "main.csv")
        if os.path.exists(file_path):
            main_df = read_df(file_path)
            buffer_df = main_df.tail(self.BUFFER_SIZE)
            return buffer_df
        else:
            print("File not found:", file_path)
            return pd.DataFrame()

    def append_to_buffer_and_update_main(self):
        """
        Fetch the data from the previous minute from the brokerage
        and update the buffer_df in memory. Also append this new data to the main.csv file.
        """
        self.connect()

        server_time = datetime.now() + timedelta(hours=2)
        server_time = server_time.replace(microsecond=0, second=0) - timedelta(
            minutes=1
        )

        rates = mt5.copy_rates_from(
            self.SYMBOL, self.TIMEFRAME, int(server_time.timestamp()), 1
        )

        if rates is None or len(rates) == 0:
            print("Error fetching new data from MT5:", mt5.last_error())
            self.close_connection()
            return self.buffer_df

        new_data = pd.DataFrame(rates)
        new_data["datetime"] = pd.to_datetime(new_data["time"], unit="s")
        new_data = new_data[["datetime", "open", "high", "low", "close"]]

        # Check if buffer_df is initialized and if new data is different from last processed data
        if self.buffer_df is not None and not new_data.equals(self.last_processed_data):
            # Append new data to the buffer and keep the last BUFFER_SIZE rows
            self.buffer_df = pd.concat([self.buffer_df, new_data]).tail(
                self.BUFFER_SIZE
            )

            # Append new data to main.csv file
            file_path = os.path.join("data", "main.csv")
            new_data.to_csv(file_path, mode="a", header=False, index=False)

            self.last_processed_data = new_data

        self.close_connection()
        return self.buffer_df

    def update_main(self):
        self.connect()
        file = os.path.join("data", "main.csv")
        main_df = read_df(file)

        last_entry_time = main_df["datetime"].iloc[-1]

        symbol = "NAS100"
        timeframe = mt5.TIMEFRAME_M1

        server_time = (datetime.now() + timedelta(hours=2)).replace(
            microsecond=0
        ) - timedelta(minutes=1)

        last_entry_unix = int(last_entry_time.timestamp())
        server_time_unix = int(server_time.timestamp())

        MAX_DURATION = 30000 * 60

        total_duration = server_time_unix - last_entry_unix
        num_chunks = (total_duration + MAX_DURATION - 1) // MAX_DURATION

        all_data = []

        for i in range(num_chunks):
            start_time = last_entry_unix + i * MAX_DURATION
            end_time = min(last_entry_unix + (i + 1) * MAX_DURATION, server_time_unix)

            segment_data = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
            if segment_data.size > 0:
                all_data.extend(segment_data)
            else:
                print(f"Error fetching data for chunk {i+1}. Checking error...")
                error = mt5.last_error()
                print("Error in MT5:", error)

        all_data = np.array(all_data)

        columns = ["time", "open", "high", "low", "close", "s", "s2", "s3"]
        df = pd.DataFrame(all_data, columns=columns)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df = df[["datetime", "open", "high", "low", "close"]]
        df = df[df["datetime"] > last_entry_time]

        df.to_csv(file, mode="a", header=False, index=False)
        self.close_connection()
        print("Main.csv updated successfully!")

    def close_connection(self):
        """
        This method is meant to close the connection with the brokerage.
        """
        try:
            mt5.shutdown()
        except Exception as e:
            print(e)

    def place_trade(
        self,
        id:int,
        quantity:float,
        buy=False,
        sell=False,
        pct_tp=0,
        pct_sl=0,
        comment="NA",
        id_position=None,
        symbol=SYMBOL,
    ):
        self.connect()
        cost_of_one_lot = None
        trade_request = None

        if buy == True:
            filling_mode = self.find_filling_mode(symbol, "BUY")
        else:
            filling_mode = self.find_filling_mode(symbol, "SELL")

        if filling_mode == -1:
            print("Error finding filling mode")
            return

        if id not in self.positions:
            self.positions[id] = []

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"{symbol} not found, cannot place order")
            self.close_connection()
            return

        if not symbol_info.visible:
            print(f"{symbol} is not visible, trying to switch on")
            if not mt5.symbol_select(symbol, True):
                print(f"symbol_select({symbol}) failed, cannot place order")
                self.close_connection()
                return

        # just ensuring on active trade per model
        for pos in self.positions[id]:
            if pos["type"] == "long" and pos["symbol"] == symbol:
                print(f"Long position for {symbol} by {id} already exists.")
                self.close_connection()
                return

        # obtain account info
        account_info = mt5.account_info()
        if not account_info:
            print("Failed to get account information")
            self.close_connection()
            return

        # calculate the margin required to place the order
        if buy:
            cost_of_one_lot = symbol_info.trade_contract_size * symbol_info.ask
        if sell:
            cost_of_one_lot = symbol_info.trade_contract_size * symbol_info.bid

        if (
            cost_of_one_lot != None
            and account_info.margin_free < cost_of_one_lot * quantity
        ):
            print("Insufficient margin to place order")
            self.close_connection()
            return

        # enter a long
        if buy and id_position == None:
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 20,
                "magic": 112009,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

        # here we exit a buy position
        if buy and id_position != None:
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_SELL,
                "position": id_position,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "magic": 112009,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

        # here we enter a short
        if sell and id_position == None:
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "magic": 112009,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

        # here we exit a short
        if sell and id_position != None:
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_BUY,
                "position": id_position,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 20,
                "magic": 112009,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

        if trade_request != None:
            result = mt5.order_send(trade_request)
            if result is None:
                print("order_send failed, error code:", mt5.last_error())
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(
                    f"Trade request executed successfully, position id={result.order}"
                )
                self.positions[id].append(
                    {
                        "type": "long" if buy else "short",
                        "symbol": symbol,
                        "position": result.order,
                    }
                )
                self.close_connection()
                return result.order

        self.close_connection()


    def find_filling_mode(self, symbol=SYMBOL, order_type="BUY"):
        if order_type == "BUY":
            price = mt5.symbol_info_tick(symbol).ask
            order = mt5.ORDER_TYPE_BUY
        elif order_type == "SELL":
            price = mt5.symbol_info_tick(symbol).bid
            order = mt5.ORDER_TYPE_SELL
        else:
            return -1

        for i in range(2):
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": mt5.symbol_info(symbol).volume_min,
                "type": order,
                "price": price,
                "type_filling": i,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_check(request)

            if result.comment == "Done":
                break
        return i

    def connect(self):
        mt5.initialize()
        authorized = mt5.login(self.LOGIN, password=self.PASSWORD, server=self.SERVER)

        if authorized:
            print(f"Connected: Connecting to MT5 Client at {self.SERVER}")
        else:
            print("Failed to connect, error code: {}".format(mt5.last_error()))


if __name__ == "__main__":
    server = Server()
