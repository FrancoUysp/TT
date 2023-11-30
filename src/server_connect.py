import pandas as pd

import os
from .utils import read_df

class Server:
    BUFFER_SIZE = 2640
    def __init__(self):
        self.buffer_df_mock_api = pd.DataFrame()
        self.buffer_df = self.create_buffer_queue()

    def update_main(self):
        # Method to update main data, if necessary
        pass

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

    def place_long(self, name, quantity):
        """
        This method is meant to place a long order with the brokerage
        """
        pass

    def exit_long(self, name):
        """
        This method is meant to exit a long order with the brokerage
        """
        pass
    def place_short(self, name, quantity):
        """
        This method is meant to place a short order with the brokerage
        """
        pass
    def exit_short(self, name):
        """
        This method is meant to exit a short order with the brokerage
        """
        pass

# Example usage:
if __name__ == "__main__":
    server = Server()

