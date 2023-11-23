import numpy as np
from pandas.io.xml import preprocess_data
from sklearn.decomposition import PCA
from sklearn.decomposition import FastICA
from sklearn.preprocessing import StandardScaler
import pandas as pd
import ta
import warnings
import plotly.graph_objects as go
import os

from .utils import read_df

warnings.simplefilter("ignore")

DATA_PATH = os.path.join('..', 'data', 'main.csv')
TOL = 1

class DataPreprocessor:
    def __init__(self, path = DATA_PATH, n = 50000):
        if isinstance(path, str):
            self.data = read_df(path, n)
        elif isinstance(path, pd.DataFrame):
            self.data = path 
        else:
            raise TypeError("path_or_df must be a string or a pandas DataFrame")

    def label_target_wave(self, data):
        highs = data['high'].values
        lows = data['low'].values
        prices = data['close'].values
        labels = [0] * len(data)

        wait_count_for_long = 0
        wait_count_for_short = 0
        short_exit_timer = 0
        long_exit_timer = 0
        LOOKBACK = 180
        LONG_TIMER = SHORT_EXIT = 1
        SHORT_TIMER = LONG_EXIT = 1
        LONG_DIFF = 40
        SHORT_DIFF = 20

        ongoing_trade = None

        for i in range(LOOKBACK, len(data)):
            high_window = highs[i-LOOKBACK:i]
            low_window = lows[i-LOOKBACK:i]
            current_high = highs[i]
            current_low = lows[i]
            current_price = prices[i]

            previous_high = max(high_window)
            previous_low = min(low_window)

            # SHORT logic
            if current_high > previous_high and (current_high - previous_low) > SHORT_DIFF:
                wait_count_for_short = SHORT_TIMER
            elif wait_count_for_short > 0:
                wait_count_for_short -= 1
                if wait_count_for_short == 0 and not ongoing_trade:
                    ongoing_trade = {"idx": i, "type": "short", "entry_price": current_price}

            # Exit condition for short trade
            if ongoing_trade and ongoing_trade["type"] == "short":
                if current_low < previous_low:
                    short_exit_timer = SHORT_EXIT
                if short_exit_timer > 0:
                    short_exit_timer -= 1
                    if short_exit_timer == 0:
                        profit_pct = (ongoing_trade["entry_price"] - current_price) / ongoing_trade["entry_price"]
                        label = 3 if profit_pct >= 0.00 else 2
                        for j in range(ongoing_trade["idx"], i):
                            labels[j] = label
                        ongoing_trade = None

            if current_low < previous_low and (previous_high - current_low) > LONG_DIFF:
                wait_count_for_long = LONG_TIMER
            elif wait_count_for_long > 0:
                wait_count_for_long -= 1
                if wait_count_for_long == 0 and not ongoing_trade:
                    ongoing_trade = {"idx": i, "type": "long", "entry_price": current_price}

            if ongoing_trade and ongoing_trade["type"] == "long":
                if current_high > previous_high:
                    long_exit_timer = LONG_EXIT
                if long_exit_timer > 0:
                    long_exit_timer -= 1
                    if long_exit_timer == 0:
                        profit_pct = (current_price - ongoing_trade["entry_price"]) / ongoing_trade["entry_price"]
                        label = 1 if profit_pct >= 0.00 else 0
                       
                        for j in range(ongoing_trade["idx"], i):
                            labels[j] = label
                        ongoing_trade = None

        data['target'] = labels
        return data

    def label_strong_target(self, data, window_size=30, price_diff_threshold=20, tolerance=1, pred = False):

        rs_lines = pd.read_csv("data/stronglines.csv")
        lines = rs_lines.values.flatten()

        close_prices = data['close'].values[:, np.newaxis]
        lines = np.array(lines)
        lines_reshaped = lines[np.newaxis, :]

        diffs = lines_reshaped - close_prices
        partitioned_indices = np.argpartition(np.abs(diffs), 4, axis=1)[:, :4]
        closest_diffs = np.take_along_axis(diffs, partitioned_indices, axis=1)
        closest_rs_values = np.take_along_axis(lines_reshaped, partitioned_indices, axis=1)

        data['SL_1'] = closest_diffs[:, 0]
        data['SL_2'] = closest_diffs[:, 1]
        data['SL_3'] = closest_diffs[:, 2]
        data['SL_4'] = closest_diffs[:, 3]
        if not pred:
            data['target'] = np.nan
            tolerance = TOL
            close_prices = data['close'].values[:, np.newaxis]
            diffs = np.abs(lines_reshaped - close_prices)
            within_tolerance_indices = np.where(diffs <= tolerance)

            data = data.reset_index(drop=True)

            valid_indices = set(data.index)
            filtered_indices = [idx for idx in within_tolerance_indices[0] if idx in valid_indices]

            data.loc[filtered_indices, 'target'] = lines_reshaped[0, within_tolerance_indices[1]]

            data.loc[within_tolerance_indices[0], 'target'] = lines_reshaped[0, within_tolerance_indices[1]]
            data['target'].fillna(method='bfill', inplace=True)
            data.dropna(subset=['target'], inplace=True)
            diffs = data['target'] - data['close']
            data['target'] = np.where(diffs > 0, 1, np.where(diffs < 0, -1, 0))

        return data 

    def add_time_features(self):
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
        windows = {
            "long": 180,
            "medium": 180 // 2,
            "short": 180 // 6
        }

        for name, size in windows.items():
            # SMA, EMA, RSI
            self.data[f'SMA_{name}'] = ta.trend.sma_indicator(self.data['close'], window=size)
            self.data[f'EMA_{name}'] = ta.trend.ema_indicator(self.data['close'], window=size)
            self.data[f'RSI_{name}'] = ta.momentum.RSIIndicator(self.data['close'], window=size).rsi()

            # MACD (only for the default values as it uses multiple windows)
            if name == "medium":
                macd = ta.trend.MACD(self.data['close'])
                self.data['MACD'] = macd.macd()
                self.data['MACD_signal'] = macd.macd_signal()
                self.data['MACD_diff'] = macd.macd_diff()

            # Stochastic Oscillator
            stoch = ta.momentum.StochasticOscillator(self.data['high'], self.data['low'], self.data['close'], window=size)
            self.data[f'Stoch_%K_{name}'] = stoch.stoch()
            self.data[f'Stoch_%D_{name}'] = stoch.stoch_signal()

            # Donchian
            donchian = ta.volatility.DonchianChannel(self.data['high'], self.data['low'], self.data['close'], window=size)
            self.data[f'Donchian_{name}_hband'] = donchian.donchian_channel_hband()
            self.data[f'Donchian_{name}_lband'] = donchian.donchian_channel_lband()
            self.data[f'Donchian_{name}_mband'] = donchian.donchian_channel_mband()

            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(self.data['close'], window=size)
            self.data[f'Bollinger_{name}_hband'] = bollinger.bollinger_hband()
            self.data[f'Bollinger_{name}_lband'] = bollinger.bollinger_lband()
            self.data[f'Bollinger_{name}_mavg'] = bollinger.bollinger_mavg()

            # Percentage Change
            self.data[f'Pct_Change_{name}'] = self.data['close'].pct_change(size)

            # Historical Volatility
            self.data[f'Historical_Volatility_{name}'] = self.data['close'].rolling(window=size).std() * (252**0.5)

            # CCI
            self.data[f'CCI_{name}'] = ta.trend.CCIIndicator(self.data['high'], self.data['low'], self.data['close'], window=size).cci()

            # Standard Deviation
            self.data[f'Standard_Deviation_{name}'] = self.data['close'].rolling(window=size).std()

            # TRIX
            self.data[f'TRIX_{name}'] = ta.trend.TRIXIndicator(self.data['close'], window=size).trix()

        self.data['Parabolic_SAR'] = ta.trend.PSARIndicator(self.data['high'], self.data['low'], self.data['close']).psar()
        self.data['ATR'] = ta.volatility.AverageTrueRange(self.data['high'], self.data['low'], self.data['close']).average_true_range()
        self.data['ROC'] = ta.momentum.ROCIndicator(self.data['close']).roc()
        self.data['PPO'] = ta.momentum.PercentagePriceOscillator(self.data['close']).ppo()

        self.data['Ichimoku_Conversion'] = (self.data['high'].rolling(window=9).max() + self.data['low'].rolling(window=9).min()) / 2
        self.data['Ichimoku_Base'] = (self.data['high'].rolling(window=26).max() + self.data['low'].rolling(window=26).min()) / 2
        self.data['Ichimoku_Leading_A'] = (self.data['Ichimoku_Conversion'] + self.data['Ichimoku_Base']) / 2
        self.data['Ichimoku_Leading_B'] = (self.data['high'].rolling(window=52).max() + self.data['low'].rolling(window=52).min()) / 2
        self.data['Ichimoku_Lagging'] = self.data['close'].shift(26)

        self.data['ATRP'] = ta.volatility.AverageTrueRange(self.data['high'], self.data['low'], self.data['close']).average_true_range()
        self.data['Price_Oscillator'] = self.data['close'].diff(4)

        self.data.drop(columns=['datetime'], inplace=True)


    def handle_missing_values(self):
        self.data = self.data.dropna()

            
    def transform_for_pred(self, data):
        preprocessor = DataPreprocessor(path=data)
        preprocessor.add_time_features()
        preprocessor.add_technical_indicators()
        preprocessor.data = preprocessor.label_strong_target(preprocessor.data, pred = True)
        preprocessor.handle_missing_values()
        return self.data

    def transform_for_train(self, data):
        preprocessor = DataPreprocessor(path=data)
        preprocessor.add_time_features()
        preprocessor.add_technical_indicators()
        preprocessor.data = preprocessor.label_target_wave(preprocessor.data)
        preprocessor.data = preprocessor.label_strong_target(preprocessor.data, pred = True)
        preprocessor.handle_missing_values()
        return self.data

