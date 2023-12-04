import pandas as pd
import sys
import os
from .utils import read_df
import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timedelta

class Server:

    BUFFER_SIZE = 1320 
    SYMBOL = 'NAS100'
    TIMEFRAME = mt5.TIMEFRAME_M1

    SERVER = "Pepperstone-Demo"
    PASSWORD = "duCf7yzn:h"
    LOGIN = 61202587
    
    def __init__(self):
        self.update_main()
        self.last_processed_data = None  # New attribute to track the last processed data
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
        and update the main.csv file. Then, read the last rows of main.csv as the buffer.
        """
        self.connect()

        server_time = datetime.now() + timedelta(hours=2)
        server_time = server_time.replace(microsecond=0, second=0) - timedelta(minutes=1)

        rates = mt5.copy_rates_from(self.SYMBOL, self.TIMEFRAME, int(server_time.timestamp()), 1)

        if rates is None or len(rates) == 0:
            print("Error fetching new data from MT5:", mt5.last_error())
            self.close_connection()
            return self.buffer_df

        new_data = pd.DataFrame(rates)
        new_data['datetime'] = pd.to_datetime(new_data['time'], unit='s')
        new_data = new_data[['datetime', 'open', 'high', 'low', 'close']]

        # Check if new_data is the same as the last processed data
        if self.last_processed_data is not None and new_data.equals(self.last_processed_data):
            self.close_connection()
            return self.buffer_df

        # Update last_processed_data

        file = os.path.join("data", "main.csv")
        main_df = pd.read_csv(file, parse_dates=['datetime'])

        if new_data['datetime'].iloc[0] > main_df['datetime'].iloc[-1]:
            # Append new data to main.csv
            new_data.to_csv(file, mode='a', header=False, index=False)
            self.last_processed_data = new_data

        # Read the last BUFFER_SIZE rows from main.csv to update the buffer
        buffer_df = pd.read_csv(file, parse_dates=['datetime']).tail(self.BUFFER_SIZE)

        self.close_connection()
        return buffer_df



    def update_main(self):

        self.connect()
        file = os.path.join("data", "main.csv")  
        main_df = read_df(file)

        last_entry_time = main_df['datetime'].iloc[-1]

        symbol = "NAS100"
        timeframe = mt5.TIMEFRAME_M1  

        server_time = (datetime.now() + timedelta(hours=2)).replace(microsecond=0) - timedelta(minutes=1)

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

        columns = ['time', 'open', 'high', 'low', 'close', "s", "s2", "s3"]
        df = pd.DataFrame(all_data, columns=columns)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df[['datetime', 'open', 'high', 'low', 'close']]
        df = df[df['datetime'] > last_entry_time]

        df.to_csv(file, mode='a', header=False, index=False)
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

    def place_long(self, name, quantity, symbol=SYMBOL):
        self.connect()
        if name not in self.positions:
            self.positions[name] = []

        if not any(pos['type'] == 'long' for pos in self.positions[name]):
            # Fetch account information to check for sufficient margin
            account_info = mt5.account_info()
            if not account_info:
                print("Failed to get account information")
                return

            # Check if there is enough free margin to place the order
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                print(f"Symbol info could not be retrieved for {symbol}")
                return

            cost_of_one_lot = symbol_info.trade_contract_size * mt5.symbol_info_tick(symbol).ask
            if account_info.margin_free < cost_of_one_lot * quantity:
                print("Insufficient margin to place long order")
                return

            self.positions[name].append({'symbol': symbol, 'quantity': quantity, 'type': 'long'})
            
            # MT5 API Call to Place a Long Order
            filling_type = self.find_filling_mode(symbol, "BUY")
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 20,
                "magic": 0,
                "comment": f"Long order by {name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type
            }

            result = mt5.order_send(trade_request)
            print(result)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"Failed to place long order: {result.comment}")
            else:
                print(f"Long order placed successfully for {name}")
        self.close_connection()

    def exit_long(self, name, symbol=SYMBOL):

        self.connect()
        if name in self.positions:
            long_positions = [pos for pos in self.positions[name] if pos['symbol'] == symbol and pos['type'] == 'long']
            if not long_positions:
                print(f"No long positions found for {name} on {symbol}")
                return

            # Assuming you want to close the first long position found
            position_to_close = long_positions[0]

            filling_type = self.find_filling_mode(symbol, "BUY")
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position_to_close['quantity'],
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "magic": 0,
                "comment": f"Exiting long for {name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type
            }

            result = mt5.order_send(trade_request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"Failed to exit long position: {result.comment}")
            else:
                print(f"Exited long position for {name}")
                self.positions[name].remove(position_to_close)
        self.close_connection()

    def place_short(self, name, quantity, symbol):
        self.connect()

        if name not in self.positions:
            self.positions[name] = []

        if not any(pos['type'] == 'short' and pos['symbol'] == symbol for pos in self.positions[name]):
            account_info = mt5.account_info()
            if not account_info:
                print("Failed to get account information")
                self.close_connection()
                return

            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                print(f"Symbol info could not be retrieved for {symbol}")
                self.close_connection()
                return

            cost_of_one_lot = symbol_info.trade_contract_size * mt5.symbol_info_tick(symbol).bid
            if account_info.margin_free < cost_of_one_lot * quantity:
                print("Insufficient margin to place short order")
                self.close_connection()
                return

            filling_type = self.find_filling_mode(symbol, "SELL")

            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": quantity,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "comment": f"Short order by {name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type
            }

            result = mt5.order_send(trade_request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_message = "Failed to place short order"
                if result:
                    error_message += f": {result.comment}"
                print(error_message)
            else:
                print(f"Short order placed successfully for {name}")
                self.positions[name].append({'symbol': symbol, 'quantity': quantity, 'type': 'short'})

        self.close_connection()

    def exit_short(self, name, symbol): 
        self.connect()

        if name in self.positions:
            # Filter for short positions of the specified symbol
            short_positions = [pos for pos in self.positions[name] if pos['symbol'] == symbol and pos['type'] == 'short']
            if not short_positions:
                print(f"No short positions found for {name} on {symbol}")
                self.close_connection()
                return

            # Assuming closing the first short position found
            position_to_close = short_positions[0]

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"Symbol info could not be retrieved for {symbol}")
                self.close_connection()
                return

            filling_type = self.find_filling_mode(symbol, "SELL")

            # MT5 API Call to Close a Short Position
            trade_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position_to_close['quantity'],
                "type": mt5.ORDER_TYPE_BUY,  # Buying back the short position
                "price": mt5.symbol_info_tick(symbol).ask,  # Current ask price
                "deviation": 20,
                "comment": f"Exiting short for {name}",
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": filling_type,  # Filling type based on symbol settings
            }

            result = mt5.order_send(trade_request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error_message = "Failed to exit short position"
                if result:
                    error_message += f": {result.comment}"
                print(error_message)
            else:
                print(f"Exited short position for {name}")
                # Removing the position from the list
                self.positions[name].remove(position_to_close)

        self.close_connection()

    def find_filling_mode(self, symbol=SYMBOL, order_type="BUY"):
        if order_type == "BUY":
            price = mt5.symbol_info_tick(symbol).ask
            order = mt5.ORDER_TYPE_BUY
        elif order_type == "SELL":
            price = mt5.symbol_info_tick(symbol).bid
            order = mt5.ORDER_TYPE_SELL
        else: return -1

        for i in range(2):
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": mt5.symbol_info(symbol).volume_min,
            "type": order,  
            "price": price,
            "type_filling": i,
            "type_time": mt5.ORDER_TIME_GTC}

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

