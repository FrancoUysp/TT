import pandas as pd
import datetime 

def read_df(file_loc, n=None):
    "Used to read main.csv etc"
    if n is None:
        data = pd.read_csv(
            file_loc,
            names=["date", "time", "open", "high", "low", "close"],  # Lowercase column names
            delimiter=";",
        )
    else:
        data = pd.read_csv(
            file_loc,
            names=["date", "time", "open", "high", "low", "close"],  # Lowercase column names
            delimiter=";",
            nrows=n
        )


    for col in ["open", "high", "low", "close"]:
        data[col] = pd.to_numeric(data[col].str.replace(",", "."), errors='coerce')

    # Create 'datetime' column by combining 'date' and 'time' columns
    data['datetime'] = pd.to_datetime(data['date'] + ' ' + data['time'], format='%Y.%m.%d %H:%M:%S', errors='coerce')
    data.dropna(inplace=True, axis=0)


    # Drop 'date' and 'time' columns
    data = data.drop(columns=['date', 'time'])

    data = data.sort_values(by=["datetime"])  # Lowercase column name
    return data  # Don't forget to return the data

