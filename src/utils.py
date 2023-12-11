import pandas as pd

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
