import pandas as pd
import os 
import MetaTrader5 as mt5
import numpy as np
from datetime import datetime as dt, timedelta
import time

BUFFER_SIZE = 60

def read_df(file_loc, n=None):
    "Used to read main.csv etc"
    if n is None:
        data = pd.read_csv(file_loc)
    else:
        data = pd.read_csv(file_loc, nrows=n)

    data['datetime'] = pd.to_datetime(data['datetime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    
    data.dropna(inplace=True, axis=0)

    data = data.sort_values(by=["datetime"])  

    return data  

def update_main():
    file = os.path.join("..", "data", "main.csv")  
    main_df = read_df(file)

    last_entry_time = main_df['datetime'].iloc[-1]

    if not mt5.initialize():
        print("Error initializing MetaTrader 5")
        return

    symbol = "NAS100.a"
    timeframe = mt5.TIMEFRAME_M1  

    server_time = (dt.now() + timedelta(hours=3)).replace(microsecond=0) - timedelta(minutes=1)
    print(last_entry_time, server_time)

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
    mt5.shutdown()
    print("Main.csv updated successfully!")

def create_buffer_queue():
    file = os.path.join("..", "data", "main.csv")
    main_df = read_df(file)
    buffer_df = main_df.tail(BUFFER_SIZE)
    return buffer_df

def append_to_buffer_and_update_main(buffer_df):
    file = os.path.join("..", "data", "main.csv")
    
    latest_buffer_time = buffer_df['datetime'].iloc[-1]
    
    end_time = dt.now() + timedelta(hours=3) - timedelta(minutes=1)  
    end_time = end_time.replace(microsecond=0).replace(second=0) 
    
    print(latest_buffer_time, end_time)
    if latest_buffer_time == end_time:
        return buffer_df
    
    if not mt5.initialize():
        print("Error initializing MetaTrader 5")
        return buffer_df

    symbol = "NAS100.a"
    timeframe = mt5.TIMEFRAME_M1

    # Calculate the start time for fetching a single minute's worth of data
    start_time = latest_buffer_time + timedelta(minutes=1)
    
    segment_data = mt5.copy_rates_range(symbol, timeframe, int(start_time.timestamp()), int(end_time.timestamp()))
    if segment_data.size == 0:
        print("Error fetching data. Checking error...")
        error = mt5.last_error()
        print("Error in MT5:", error)
        mt5.shutdown()
        return buffer_df


    columns = ['time', 'open', 'high', 'low', 'close']
    df = pd.DataFrame(segment_data, columns=columns)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df = df[['datetime', 'open', 'high', 'low', 'close']]
    
    buffer_df = pd.concat([buffer_df.iloc[1:], df], ignore_index=True)
    
    entry_to_append = buffer_df.iloc[-1]
    main_df_all = read_df(file)
    main_df_all = main_df_all.iloc[:-1]
    last_entry_in_main = pd.to_datetime(main_df_all['datetime'].iloc[-1])
    
    if pd.to_datetime(last_entry_in_main) <= entry_to_append['datetime']:
        entry_to_append.to_frame().T.to_csv(file, mode='a', header=False, index=False)


    mt5.shutdown()
    return buffer_df

if __name__ == "__main__":
    update_main()
    buffer_df = create_buffer_queue()

    while True:
        buffer_df = append_to_buffer_and_update_main(buffer_df)
        time.sleep(5)  # waits for 5 seconds before calling the function again
