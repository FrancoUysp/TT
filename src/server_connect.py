import pandas as pd
import os
import numpy as np
from datetime import datetime as dt, timedelta
import time
from .utils import read_df

global buffer_df_mock_api
buffer_df_mock_api = pd.DataFrame()
BUFFER_SIZE = 1320 


def update_main():
    pass

def create_buffer_queue():
    """
    This method will create the current queue that is
    in memory and will be used to process and make decisions
    """
    global buffer_df_mock_api
    file = os.path.join("data", "main.csv")
    main_df = read_df(file)
    buffer_df_mock_api = main_df.tail(2 * BUFFER_SIZE)
    buffer_df = buffer_df_mock_api.head(BUFFER_SIZE)
    buffer_df_mock_api = buffer_df_mock_api.tail(BUFFER_SIZE)
    return buffer_df


def append_to_buffer_and_update_main(buffer_df):
    """
    this method is meant to fetch the last minute from the brokerage
    and aappend it to the buffer queue. It also removes the last element
    in the buffer queue (the oldest)
    """
    global buffer_df_mock_api
    buffer_df = buffer_df.iloc[1:]
    buffer_df = pd.concat([buffer_df, buffer_df_mock_api.head(1)], ignore_index=True)
    buffer_df_mock_api = buffer_df_mock_api.iloc[1:]
    return buffer_df


if __name__ == "__main__":
    # update_main()
    buffer_df = create_buffer_queue()

    # while True:
    #     buffer_df = append_to_buffer_and_update_main(buffer_df)
    #     time.sleep(5)  # waits for 5 seconds before calling the function again
