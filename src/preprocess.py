import numpy as np
import pandas as pd
import ta
from tqdm import tqdm
import warnings
import plotly.graph_objects as go

from utils import read_df

warnings.simplefilter("ignore")

DATA_PATH = '../data/L.csv'

class DataPreprocessor:
    def __init__(self, path = DATA_PATH):
        self.path = path
    def plot_candlestick_with_signals(self, output_file=None):
        fig = go.Figure()

        # Create the candlestick trace
        fig.add_trace(go.Candlestick(x=self.data.index,
                open=self.data['open'],
                high=self.data['high'],
                low=self.data['low'],
                close=self.data['close'],
                name='Candlesticks'))

        # Create traces for buy and sell signals
        buy_signals = self.data[self.data['target'] == 1]
        sell_signals = self.data[self.data['target'] == -1]

        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['close'],
                                 mode='markers', name='Buy Signals',
                                 marker=dict(color='green', size=10, symbol='triangle-up')))

        fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['close'],
                                 mode='markers', name='Sell Signals',
                                 marker=dict(color='red', size=10, symbol='triangle-down')))

        # Update layout
        fig.update_layout(
            title='Candlestick Chart with Buy/Sell Signals',
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_dark',
            xaxis_rangeslider_visible=False
        )

        if output_file:
            fig.write_html(output_file)  # Save to file
        else:
            fig.show()  # Show the plot

    def add_time_features(self):
        self.data['Year'] = self.data['datetime'].dt.year
        self.data['Month'] = self.data['datetime'].dt.month
        self.data['Day'] = self.data['datetime'].dt.day
        self.data['Hour'] = self.data['datetime'].dt.hour
        self.data['Minute'] = self.data['datetime'].dt.minute
        self.data['Day_of_Week'] = self.data['datetime'].dt.dayofweek
        self.data['Day_Sin'] = np.sin((self.data['Day'] - 1) * (2. * np.pi / 30))
        self.data['Day_Cos'] = np.cos((self.data['Day'] - 1) * (2. * np.pi / 30))
        self.data['Hour_Sin'] = np.sin(self.data['Hour'] * (2. * np.pi / 24))
        self.data['Hour_Cos'] = np.cos(self.data['Hour'] * (2. * np.pi / 24))
        self.data['Minute_Sin'] = np.sin(self.data['Minute'] * (2. * np.pi / 60))
        self.data['Minute_Cos'] = np.cos(self.data['Minute'] * (2. * np.pi / 60))

    def add_technical_indicators(self):
        self.data['SMA_10'] = ta.trend.sma_indicator(self.data['close'], window=10)
        self.data['EMA_10'] = ta.trend.ema_indicator(self.data['close'], window=10)
        self.data['RSI'] = ta.momentum.RSIIndicator(self.data['close'], window=14).rsi()

        macd = ta.trend.MACD(self.data['close'])
        self.data['MACD'] = macd.macd()
        self.data['MACD_signal'] = macd.macd_signal()
        self.data['MACD_diff'] = macd.macd_diff()

        stoch = ta.momentum.StochasticOscillator(self.data['high'], self.data['low'], self.data['close'])
        self.data['Stoch_%K'] = stoch.stoch()
        self.data['Stoch_%D'] = stoch.stoch_signal()

        self.data['ATR'] = ta.volatility.AverageTrueRange(self.data['high'], self.data['low'], self.data['close']).average_true_range()

        bollinger = ta.volatility.BollingerBands(self.data['close'])
        self.data['Bollinger_hband'] = bollinger.bollinger_hband()
        self.data['Bollinger_lband'] = bollinger.bollinger_lband()
        self.data['Bollinger_mavg'] = bollinger.bollinger_mavg()

        self.data['ROC'] = ta.momentum.ROCIndicator(self.data['close']).roc()
        self.data['PPO'] = ta.momentum.PercentagePriceOscillator(self.data['close']).ppo()

        # Ichimoku Cloud
        self.data['Ichimoku_Conversion'] = (self.data['high'].rolling(window=9).max() + self.data['low'].rolling(window=9).min()) / 2
        self.data['Ichimoku_Base'] = (self.data['high'].rolling(window=26).max() + self.data['low'].rolling(window=26).min()) / 2
        self.data['Ichimoku_Leading_A'] = (self.data['Ichimoku_Conversion'] + self.data['Ichimoku_Base']) / 2
        self.data['Ichimoku_Leading_B'] = (self.data['high'].rolling(window=52).max() + self.data['low'].rolling(window=52).min()) / 2
        self.data['Ichimoku_Lagging'] = self.data['close'].shift(26)
        
        self.data['Pct_Change_1min'] = self.data['close'].pct_change(1)
        self.data['Pct_Change_5min'] = self.data['close'].pct_change(5)
        self.data['Pct_Change_10min'] = self.data['close'].pct_change(10)
        self.data['Pct_Change_30min'] = self.data['close'].pct_change(30)

        # Volatility Indicators
        self.data['ATRP'] = ta.volatility.AverageTrueRange(self.data['high'], self.data['low'], self.data['close']).average_true_range()

        # Other Indicators
        self.data['Historical_Volatility'] = self.data['close'].rolling(window=10).std() * (252**0.5)  # Annualized volatility
        self.data['Price_Oscillator'] = self.data['close'].diff(4)  # Difference between the current price and the price 4 periods ago
        self.data['Standard_Deviation'] = self.data['close'].rolling(window=14).std()

        # Commodity Channel Index (CCI)
        self.data['CCI'] = ta.trend.CCIIndicator(self.data['high'], self.data['low'], self.data['close']).cci()

        # Donchian Channels
        donchian = ta.volatility.DonchianChannel(self.data['high'], self.data['low'], self.data['close'])
        self.data['Donchian_Channel_hband'] = donchian.donchian_channel_hband()
        self.data['Donchian_Channel_lband'] = donchian.donchian_channel_lband()
        self.data['Donchian_Channel_mband'] = donchian.donchian_channel_mband()

        self.data['DPO'] = ta.trend.DPOIndicator(self.data['close']).dpo()

        # Keltner Channel (KC)
        typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3
        self.data['MFI'] = ta.volume.MFIIndicator(high=self.data['high'], low=self.data['low'], close=self.data['close'], volume=typical_price).money_flow_index()

        # Trix
        self.data['Trix'] = ta.trend.TRIXIndicator(self.data['close']).trix()

        self.data.drop(columns=['datetime'], inplace=True)

    def handle_missing_values(self):
        self.data.dropna(axis=0, inplace=True)

    def transform_for_pred(self, data):
        self.data = data
        self.add_time_features()
        self.add_technical_indicators()
        self.handle_missing_values()
        return self.data

    def analyze_sharp_changes(self, data, window_size=30, price_diff_threshold=50, tolerance=1):
        """
        Analyze the data for sharp changes, compute related products, and assign buy/sell/hold signals.
        
        Parameters:
        - data (pd.DataFrame): DataFrame with a 'Close' column containing closing prices.
        - window_size (int): Size of the rolling window.
        - price_diff_threshold (float): Threshold for detecting a sharp price change.
        - tolerance (float): Threshold for proximity to sharp changes for buy/sell/hold signals.

        Returns:
        - data (pd.DataFrame): DataFrame with the new columns.
        """
        
        rolling_min = data['close'].rolling(window_size).min()
        rolling_max = data['close'].rolling(window_size).max()
        
        price_diff = rolling_max - rolling_min
        sharp_changes_idx = np.where(price_diff >= price_diff_threshold)[0]
        sharp_changes_idx = sharp_changes_idx[sharp_changes_idx < len(data) - window_size + 1]
        sharp_changes_info = []
        for idx in sharp_changes_idx:
            min_price = rolling_min.iloc[idx]
            max_price = rolling_max.iloc[idx]
            actual_price = data['close'].iloc[idx]
            if np.abs(actual_price - min_price) > np.abs(max_price - actual_price):
                change_start_price = min_price
                change_magnitude = actual_price - min_price
            else:
                change_start_price = max_price
                change_magnitude = max_price - actual_price
            
            if not any(np.abs(change_start_price - prev_price) < window_size for prev_price, _ in sharp_changes_info):
                sharp_changes_info.append((change_start_price, change_magnitude))
        
        # Sort the changes by magnitude in descending order, extract the prices, and then sort by price
        lines = sorted([price for price, _ in sorted(sharp_changes_info, key=lambda x: x[1], reverse=True)])
        data = data[data['close'] >= (10000 - 20)]

        close_prices = data['close'].values[:, np.newaxis]
        lines = np.array(lines)
        lines_reshaped = lines[np.newaxis, :]

        diffs = lines_reshaped - close_prices
        partitioned_indices = np.argpartition(np.abs(diffs), 4, axis=1)[:, :4]
        closest_diffs = np.take_along_axis(diffs, partitioned_indices, axis=1)
        closest_rs_values = np.take_along_axis(lines_reshaped, partitioned_indices, axis=1)
        # product_values = closest_diffs * closest_rs_values

        # data['SL_1'] = product_values[:, 0]
        # data['SL_2'] = product_values[:, 1]
        # data['SL_3'] = product_values[:, 2]
        # data['SL_4'] = product_values[:, 3]

        data['target'] = np.nan
        tolerance = 1
        close_prices = data['close'].values[:, np.newaxis]
        diffs = np.abs(lines_reshaped - close_prices)
        within_tolerance_indices = np.where(diffs <= tolerance)

        data = data.reset_index(drop=True)

        # Ensure valid indices before assignment
        valid_indices = set(data.index)
        filtered_indices = [idx for idx in within_tolerance_indices[0] if idx in valid_indices]

        data.loc[filtered_indices, 'target'] = lines_reshaped[0, within_tolerance_indices[1]]

        data.loc[within_tolerance_indices[0], 'target'] = lines_reshaped[0, within_tolerance_indices[1]]
        data['target'].fillna(method='bfill', inplace=True)
        data.dropna(subset=['target'], inplace=True)
        diffs = data['target'] - data['close']
        data['target'] = np.where(diffs > 0, 1, np.where(diffs < 0, -1, 0))
        
        return data 
                    

    def transform_for_training(self, n = None):
        self.data = read_df(DATA_PATH, n) 
        self.data = self.analyze_sharp_changes(self.data)
        self.add_time_features()
        self.add_technical_indicators()
        self.handle_missing_values()
        return self.data

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.transform_for_training()
    preprocessor.plot_candlestick_with_signals()
    print(preprocessor.data.head())
