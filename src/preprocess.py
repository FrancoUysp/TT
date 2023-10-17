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

    def label_sharp_changes(self, look_ahead_window=20, price_increase_threshold=(1+0.00075), price_decrease_threshold=(1-0.0005)):
        """
        Label optimal buy/sell signals based on significant price changes in a look-ahead window.

        Parameters:
        - look_ahead_window (int): The number of periods to look ahead to find significant price changes.
        - price_increase_threshold (float): The threshold for a significant price increase.
        - price_decrease_threshold (float): The threshold for a significant price decrease.

        Returns:
        - data (pd.DataFrame): Original DataFrame with an additional 'target' column.
        """
        self.data['target'] = 0  # Initialize a new column 'target' with zeros
        
        # Rolling maximum and minimum prices in the look-ahead window
        roll_max = self.data['close'].shift(-look_ahead_window).rolling(look_ahead_window, min_periods=1).mean()
        roll_min = self.data['close'].shift(-look_ahead_window).rolling(look_ahead_window, min_periods=1).mean()
        
        # Identify buy and sell signals based on significant price changes
        buy_signals = (roll_max >= self.data['close'] * price_increase_threshold)
        sell_signals = (roll_min <= self.data['close'] * price_decrease_threshold)
        
        # Label the signals in the 'target' column
        self.data.loc[buy_signals, 'target'] = 1
        self.data.loc[sell_signals, 'target'] = -1

        return self.data

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

        self.data.drop(columns=['datetime'], inplace=True)

    def handle_missing_values(self):
        self.data = self.data.dropna()

    def transform_for_pred(self, data):
        self.data = data
        print("hello")
        self.add_time_features()
        print("hello")
        self.add_technical_indicators()
        print("hello")
        self.handle_missing_values()
        print("hello")
        return self.data

    def transform_for_training(self, n = None):
        self.data = read_df(DATA_PATH, n) 
        self.label_sharp_changes()
        self.add_time_features()
        self.add_technical_indicators()
        self.handle_missing_values()
        return self.data

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.transform_for_training(n=10000)
    preprocessor.plot_candlestick_with_signals()
    print(preprocessor.data.head())
