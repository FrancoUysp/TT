import requests
from binance import Client, BinanceSocketManager
import pandas as pd
import asyncio
import websockets
from model import *
from preprocess import *
import json 
import os
from datetime import datetime, timedelta

class BinanceDataRetriever:
    def __init__(self, base_url="https://api.binance.com/api/v3"):
        self.base_url = base_url
        self.all_columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'num_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
        self.df_columns = ['Date', 'open', 'high', 'low', 'close', 'volume']  # Added 'volume' here
        self.max_records = 10000  # Maximum records before saving to file
        self.ws_url = "wss://stream.binance.com:9443/ws/"
        self.current_minute = None
        self.aggregate_volume = 0
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.message_count= 0
        self.aggregate_data = pd.DataFrame(columns=["Date", "open", "high", "low", "close", "volume"])

        self.model = NeuralNetworkModel()
        self.processor = DataPreprocessor()
        self.preprocessed_data, self.dates, self.predictions = (None, None, None)
        self.historical_data = None
        self.model.load_model("../plots")

    def get_historical_price(self, symbol, currency, start_dt, end_dt, interval):
        start_timestamp = round(start_dt.timestamp())*1000
        end_timestamp = round(end_dt.timestamp())*1000 - 1

        r = requests.get(f'{self.base_url}/klines?symbol={symbol}{currency}&interval={interval}&startTime={start_timestamp}&endTime={end_timestamp}&limit=1000')
        content = r.json()

        if len(content) > 0:
            df = pd.DataFrame.from_records(content, columns=self.all_columns)
            df['Date'] = df['open_time'].apply(lambda ts: datetime.fromtimestamp(int(ts)/1000))
            return df[self.df_columns].sort_values('Date', ascending=False)
        else:
            return None

    def retrieve_data(self, symbols, currency='USDT', start_dt=None, end_dt=None):
        for symbol in symbols:
            print(f'[START] Retrieving data for {symbol}/{currency}')
            end_dt_midnight = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)

            all_data = []
            current_start_dt = start_dt
            while current_start_dt <= end_dt_midnight:
                df = self.get_historical_price(symbol, currency, current_start_dt, end_dt_midnight, "1m")
                
                if df is not None and not df.empty:
                    all_data.append(df)
                    current_start_dt += timedelta(minutes=len(df))  # Advance start date by the number of records received
                    total_records = sum([len(d) for d in all_data])

                    if total_records >= self.max_records:
                        concatenated_df = pd.concat(all_data, ignore_index=True)
                        filename = f'../data/{symbol}_{currency}.csv'
                        concatenated_df = concatenated_df.sort_values('Date', ascending=True)
                        concatenated_df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
                        print(f'[APPENDED] {filename} with {self.max_records} records')
                        all_data = []
                else:
                    break

            # Save any remaining records if less than self.max_records
            if all_data:
                concatenated_df = pd.concat(all_data, ignore_index=True)
                filename = f'../data/{symbol}_{currency}.csv'
                concatenated_df = concatenated_df.sort_values('Date', ascending=True)
                concatenated_df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
                print(f'[APPENDED] {filename} with remaining records')

    async def subscribe(self, symbol, interval):
        async with websockets.connect(f"{self.ws_url}{symbol.lower()}@kline_{interval}") as ws:
            async for msg in ws:
                self.process_message(msg)

    def process_message(self, msg):
        data = json.loads(msg)
        kline = data['k']
        minute = datetime.fromtimestamp(kline['t'] / 1000).replace(second=0, microsecond=0)
        volume = float(kline['v'])
        if self.current_minute is None:
            self.current_minute = minute
            self.open = kline['o']
            self.high = kline['h']
            self.low = kline['l']
        else:
            if minute != self.current_minute:
                self.close = kline['c']
                self.process_aggregate_volume()
                self.reset_aggregate_volume(minute, kline)
            else:
                self.high = max(self.high, kline['h'])
                self.low = min(self.low, kline['l'])
        self.aggregate_volume += volume

    def process_aggregate_volume(self):
        formatted_date = self.current_minute.strftime('%Y-%m-%d %H:%M:%S')
        new_data = {
            "Date": [formatted_date],
            "open": [self.open],
            "high": [self.high],
            "low": [self.low],
            "close": [self.close],
            "volume": [self.aggregate_volume]
        }

        # Appending new data to aggregate data
        self.aggregate_data = pd.concat([self.aggregate_data, pd.DataFrame(new_data)], ignore_index=True)

        current_length = len(self.aggregate_data)

        # Load historical data if needed
        if current_length < 100:
            if self.historical_data is None:
                self.historical_data = pd.read_csv('../data/BTC_USDT.csv')

            rows_needed = 100 - current_length
            self.aggregate_data = pd.concat([self.historical_data.tail(rows_needed), self.aggregate_data], ignore_index=True)
        elif current_length > 100:
            self.aggregate_data = self.aggregate_data.tail(100)

        # Preprocess data and make predictions
        self.dates = self.aggregate_data["Date"]
        self.preprocessed_data = self.processor.transform(self.aggregate_data)
        self.dates = self.dates[100-self.preprocessed_data.shape[0]:]
        self.predictions = self.model.predict(self.preprocessed_data)

        print(self.preprocessed_data.shape, len(self.dates), len(self.predictions))


    def reset_aggregate_volume(self, new_minute, kline):
        self.current_minute = new_minute
        self.aggregate_volume = 0
        self.open = kline['o']
        self.high = kline['h']
        self.low = kline['l']
        self.close = None  # Reset close as we do not have close price for the new minute yet

    def start_minute_data_stream(self, symbol):
        asyncio.get_event_loop().run_until_complete(self.subscribe(symbol, '1m'))
    def get_aggregate_data(self):
        return self.preprocessed_data, self.dates, self.predictions
    
if __name__ == "__main__":
    retriever = BinanceDataRetriever()
    symbols_input = input("Enter the tokens you want to retrieve, separated by comma (e.g., BTC,ETH): ").split(',')
    symbols = [symbol.strip().upper() for symbol in symbols_input]

    start_date_str = input("Enter the start date in YYYY-MM-DD format: ")
    end_date_str = input("Enter the end date in YYYY-MM-DD format: ")

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    retriever.retrieve_data(symbols, start_dt=start_date, end_dt=end_date)

    # retriever = BinanceDataRetriever()
    # retriever.start_minute_data_stream('BTCUSDT')
