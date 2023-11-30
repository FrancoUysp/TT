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
        self.buffer_df = self.create_buffer_queue()
        self.positions = {}  
        self.init_connection()

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
        This method is meant to fetch the last minute from the brokerage
        and append it to the buffer queue. It also removes the last element
        in the buffer queue (the oldest).
        """
        if not self.init_connection():
            print("Error initializing MetaTrader 5")
            return self.buffer_df

        latest_buffer_time = self.buffer_df['datetime'].iloc[-1]
        
        # Calculate the current server time with a 3-hour offset
        server_time = datetime.now() + timedelta(hours=3)
        server_time = server_time.replace(microsecond=0, second=0, minute=server_time.minute)

        # Check if latest buffer time is up to date
        if latest_buffer_time >= server_time - timedelta(minutes=1):
            self.close_connection()
            return self.buffer_df

        # Fetch the next minute's data
        next_time = latest_buffer_time + timedelta(minutes=1)
        rates = mt5.copy_rates_from(self.SYMBOL, self.TIMEFRAME, int(next_time.timestamp()), 1)

        if rates is None or len(rates) == 0:
            print("Error fetching new data from MT5:", mt5.last_error())
            self.close_connection()
            return self.buffer_df

        new_data = pd.DataFrame(rates)
        new_data['datetime'] = pd.to_datetime(new_data['time'], unit='s')
        new_data = new_data[['datetime', 'open', 'high', 'low', 'close']]

        # Append the new data to the buffer and remove the oldest entry
        self.buffer_df = pd.concat([self.buffer_df.iloc[1:], new_data], ignore_index=True)

        file = os.path.join("data", "main.csv")
        new_data.to_csv(file, mode='a', header=False, index=False)

        self.close_connection()
        return self.buffer_df

    def update_main(self):
        file = os.path.join("data", "main.csv")  
        main_df = read_df(file)

        last_entry_time = main_df['datetime'].iloc[-1]


        symbol = "NAS100"
        timeframe = mt5.TIMEFRAME_M1  

        server_time = (datetime.now() + timedelta(hours=3)).replace(microsecond=0) - timedelta(minutes=1)

        last_entry_unix = int(last_entry_time.timestamp())
        server_time_unix = int(server_time.timestamp())

        MAX_DURATION = 30000 * 60  

        total_duration = server_time_unix - last_entry_unix
        num_chunks = (total_duration + MAX_DURATION - 1) // MAX_DURATION

        all_data = []  

        for i in range(num_chunks):
            start_time = last_entry_unix + i * MAX_DURATION
            end_time = min(last_entry_unix + (i + 1) * MAX_DURATION, server_time_unix)

            print(f"symbol: {symbol}, timeframe: {timeframe}, start_time: {start_time}, end_time:{end_time}")
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
        print("Main.csv updated successfully!")

    def init_connection(self):
        """
        Initialize the connection with the brokerage using the predefined credentials.
        """
        try:
            if not mt5.initialize(login=self.LOGIN, password=self.PASSWORD, server=self.SERVER):
                print("Error initializing MetaTrader 5: ", mt5.last_error())
                return False
            print("MT5 Initialized successfully.")
            return True
        except Exception as e:
            print("Exception occurred during MT5 initialization: ", e)
            return False

    def close_connection(self):
        """
        This method is meant to close the connection with the brokerage.
        """
        try:
            mt5.shutdown()
        except Exception as e:
            print(e)

    def place_long(self, name, quantity, symbol=SYMBOL):
        """
        This method is meant to place a long order with the brokerage.
        """
        if name not in self.positions:
            self.positions[name] = []

        # Ensure no existing long position for this model before placing a new one
        if not any(pos['type'] == 'long' for pos in self.positions[name]):
            self.positions[name].append({'symbol': symbol, 'quantity': quantity, 'type': 'long'})
            # TODO: Add the MT5 API call to place a long order here

    def exit_long(self, name, symbol=SYMBOL):
        """
        This method is meant to exit a long order with the brokerage.
        """
        # Remove the long position for this model
        if name in self.positions:
            self.positions[name] = [pos for pos in self.positions[name] if not (pos['symbol'] == symbol and pos['type'] == 'long')]
            # TODO: Add the MT5 API call to exit a long order here

    def place_short(self, name, quantity,symbol=SYMBOL):
        """
        This method is meant to place a short order with the brokerage.
        """
        if name not in self.positions:
            self.positions[name] = []

        # Ensure no existing short position for this model before placing a new one
        if not any(pos['type'] == 'short' for pos in self.positions[name]):
            self.positions[name].append({'symbol': symbol, 'quantity': quantity, 'type': 'short'})
            # TODO: Add the MT5 API call to place a short order here

    def exit_short(self, name, symbol=SYMBOL):
        """
        This method is meant to exit a short order with the brokerage.
        """
        # Remove the short position for this model
        if name in self.positions:
            self.positions[name] = [pos for pos in self.positions[name] if not (pos['symbol'] == symbol and pos['type'] == 'short')]
            # TODO: Add the MT5 API call to exit a short order here
if __name__ == "__main__":
    server = Server()

