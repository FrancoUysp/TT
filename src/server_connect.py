import pandas as pd
import os
from .utils import read_df
# import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timedelta

class Server:

    BUFFER_SIZE = 1320 
    SYMBOL = 'NAS100.a'
    # TIMEFRAME = mt5.TIMEFRAME_M1

    SERVER = "MetaQuotes-Demo"
    PASSWORD = ""
    LOGIN = 0
    

    def __init__(self):
        self.buffer_df_mock_api = pd.DataFrame()
        self.buffer_df = self.create_buffer_queue()
        self.positions = {}  # Stores the state of positions for each model
        # self.init_connection()

    def create_buffer_queue(self):
        """
        This method will create the current queue that is
        in memory and will be used to process and make decisions.
        """
        file = os.path.join("data", "main.csv")
        main_df = read_df(file)
        self.buffer_df_mock_api = main_df.tail(2 * self.BUFFER_SIZE)
        self.buffer_df = self.buffer_df_mock_api.head(self.BUFFER_SIZE)
        self.buffer_df_mock_api = self.buffer_df_mock_api.tail(self.BUFFER_SIZE)
        return self.buffer_df

    def append_to_buffer_and_update_main(self):
        """
        this method is meant to fetch the last minute from the brokerage
        and append it to the buffer queue. It also removes the last element
        in the buffer queue (the oldest)
        """
        self.buffer_df = self.buffer_df.iloc[1:]
        self.buffer_df = pd.concat([self.buffer_df, self.buffer_df_mock_api.head(1)], ignore_index=True)
        self.buffer_df_mock_api = self.buffer_df_mock_api.iloc[1:]
        return self.buffer_df

    def update_main(self):
        # file = os.path.join("data", "main.csv")
        # main_df = read_df(file)
        # last_entry_time = main_df['datetime'].iloc[-1]

        # symbol = "NAS100.a"
        # timeframe = mt5.TIMEFRAME_M1

        # server_time = datetime.now() + timedelta(hours=3)
        # server_time = server_time.replace(microsecond=0, second=0, minute=server_time.minute)

        # last_entry_unix = int(last_entry_time.timestamp())
        # server_time_unix = int(server_time.timestamp())

        # MAX_DURATION = 30000 * 60
        # total_duration = server_time_unix - last_entry_unix
        # num_chunks = (total_duration + MAX_DURATION - 1) // MAX_DURATION

        # all_data = []

        # for i in range(num_chunks):
        #     start_time = last_entry_unix + i * MAX_DURATION
        #     end_time = min(last_entry_unix + (i + 1) * MAX_DURATION, server_time_unix)

        #     segment_data = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
        #     if segment_data is not None and len(segment_data) > 0:
        #         all_data.extend(segment_data)
        #     else:
        #         print(f"Error fetching data for chunk {i+1}. Checking error...")
        #         error = mt5.last_error()
        #         print("Error in MT5:", error)

        # if all_data:
        #     columns = ['time', 'open', 'high', 'low', 'close']
        #     df = pd.DataFrame(all_data, columns=columns)
        #     df['datetime'] = pd.to_datetime(df['time'], unit='s')
        #     df = df[['datetime', 'open', 'high', 'low', 'close']]
        #     df = df[df['datetime'] > last_entry_time]

        #     df.to_csv(file, mode='a', header=False, index=False)
        #     print("Main.csv updated successfully!")
        pass

    # def init_connection(self):
    #     """
    #     This method is meant to initialize the connection with the brokerage.
    #     """
    #     try:
    #         if not mt5.initialize():
    #             print("Error initializing MetaTrader 5")
    #             return False
    #         return True
    #     except Exception as e:
    #         print(e)
    #         return False

    # def close_connection(self):
    #     """
    #     This method is meant to close the connection with the brokerage.
    #     """
    #     try:
    #         mt5.shutdown()
    #     except Exception as e:
    #         print(e)

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

