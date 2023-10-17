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

    data['date'] = pd.to_datetime(data['date'], format='%Y.%m.%d').dt.strftime('%Y-%m-%d')

    for col in ["open", "high", "low", "close"]:  # Lowercase column names
        data[col] = data[col].str.replace(",", ".").astype(float)

    # Create 'datetime' column by combining 'date' and 'time' columns
    data["datetime"] = data.apply(
        lambda row: datetime.datetime.strptime(  # Adjusted reference to strptime method
            f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M:%S"
        ),
        axis=1,
    )

    # Drop 'date' and 'time' columns
    data = data.drop(columns=['date', 'time'])

    data = data.sort_values(by=["datetime"])  # Lowercase column name
    return data  # Don't forget to return the data

