import numpy as np
import pandas as pd
import ta
from tqdm import tqdm
import warnings

warnings.simplefilter("ignore")

DATA_PATH = '../data/BTC_USDT.csv'

class DataPreprocessor:
    def __init__(self, path = DATA_PATH, n = None):
        self.path = path
        self.data = self._load_data(n)

    def _load_data(self, n):
        column_names = ['Date', 'open', 'high', 'low', 'close', 'volume']
        data = pd.read_csv(self.path, delimiter=',', names=column_names, header=0) # Using header=0 to utilize the first row as headers
        if n is not None:
            data = data.iloc[:n] 
        data[['open', 'high', 'low', 'close', 'volume']] = data[['open', 'high', 'low', 'close', 'volume']].astype(float)
        data['Date'] = pd.to_datetime(data['Date'], format='%Y-%m-%d %H:%M:%S')
        return data

    def label_sharp_changes(self, window_size=30, price_diff_threshold=20):
        """
        Label sharp changes in closing price within a specified window size.

        Parameters:
        - data (pd.DataFrame): DataFrame with a 'Close' column containing closing prices.
        - window_size (int): Size of the rolling window.
        - price_diff_threshold (float): Threshold for detecting a sharp price change.

        Returns:
        - data (pd.DataFrame): Original DataFrame with an additional 'target' column.
        """
        # Calculate rolling minimum and maximum
        rolling_min = self.data['close'].rolling(window_size).min()
        rolling_max = self.data['close'].rolling(window_size).max()

        # Calculate price difference within the window
        price_diff = rolling_max - rolling_min

        # Identify indices with sharp price changes
        sharp_changes_idx = np.where(price_diff >= price_diff_threshold)[0]

        # Refine sharp change indices to avoid out-of-bounds error
        sharp_changes_idx = sharp_changes_idx[sharp_changes_idx < len(self.data) - window_size + 1]

        # Initialize a new column 'target' with zeros
        self.data['target'] = 0
        
         # Loop through each sharp change index
        for idx in sharp_changes_idx:
             # Find where the sharp change started (min or max within the window)
            min_price = rolling_min.iloc[idx]
            max_price = rolling_max.iloc[idx]
            actual_price = self.data['close'].iloc[idx]
            
             # Check whether the change is an increase or decrease
            if np.abs(actual_price - min_price) > np.abs(max_price - actual_price):
                change_start_idx = self.data['close'].iloc[idx-window_size+1:idx+1].idxmin()
                # Label the points where the sharp change occurred with 1
                self.data['target'].iloc[change_start_idx:idx+1] = 1
            else:
                change_start_idx = self.data['close'].iloc[idx-window_size+1:idx+1].idxmax()
                # Label the points where the sharp change occurred with -1
                self.data['target'].iloc[change_start_idx:idx+1] = -1

    def add_time_features(self):
        self.data['Year'] = self.data['Date'].dt.year
        self.data['Month'] = self.data['Date'].dt.month
        self.data['Day'] = self.data['Date'].dt.day
        self.data['Hour'] = self.data['Date'].dt.hour
        self.data['Minute'] = self.data['Date'].dt.minute
        self.data['Day_of_Week'] = self.data['Date'].dt.dayofweek
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



        # On-Balance Volume (OBV)
        self.data['OBV'] = ta.volume.OnBalanceVolumeIndicator(self.data['close'], self.data['volume']).on_balance_volume()

        # Accumulation/Distribution Index
        self.data['Accum/Dist'] = ta.volume.AccDistIndexIndicator(self.data['high'], self.data['low'], self.data['close'], self.data['volume']).acc_dist_index()

        # Chaikin Money Flow (CMF)
        self.data['CMF'] = ta.volume.ChaikinMoneyFlowIndicator(self.data['high'], self.data['low'], self.data['close'], self.data['volume']).chaikin_money_flow()

        # Force Index
        self.data['Force_Index'] = ta.volume.ForceIndexIndicator(self.data['close'], self.data['volume']).force_index()

        # Ease of Movement (EoM)
        self.data['EoM'] = ta.volume.EaseOfMovementIndicator(self.data['high'], self.data['low'], self.data['close'], self.data['volume']).ease_of_movement()
        self.data['EoM_SMA'] = self.data['EoM'].rolling(window=14).mean()  # You can add a Simple Moving Average to the EoM

        # Volume Price Trend
        self.data['VPT'] = ta.volume.VolumePriceTrendIndicator(self.data['close'], self.data['volume']).volume_price_trend()

        # Negative Volume Index (NVI)
        self.data['NVI'] = ta.volume.NegativeVolumeIndexIndicator(self.data['close'], self.data['volume']).negative_volume_index()

        # KST Oscillator
        kst = ta.trend.KSTIndicator(self.data['close'])
        self.data['KST'] = kst.kst()
        self.data['KST_Signal'] = kst.kst_sig()

        # TRIX - a momentum oscillator showing the percent rate of change of a triple exponentially smoothed moving average
        self.data['TRIX'] = ta.trend.TRIXIndicator(self.data['close']).trix()


        self.data.drop(columns=['Date'], inplace=True)

    def handle_missing_values(self):
        self.data = self.data.dropna()

    def save_to_csv(self, filename):
        self.data.to_csv(filename, index=False)

    def transform(self, data):
        data[['open', 'high', 'low', 'close', 'volume']] = data[['open', 'high', 'low', 'close', 'volume']].astype(float)
        data['Date'] = pd.to_datetime(data['Date'], format='%Y-%m-%d %H:%M:%S')
        self.data = data
        self.add_time_features()
        self.add_technical_indicators()
        self.handle_missing_values()
        return self.data

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.label_sharp_changes()
    preprocessor.add_time_features()
    preprocessor.add_technical_indicators()
    preprocessor.handle_missing_values()
    print(preprocessor.data.head())
    # preprocessor.save_to_csv("preprocessed_data.csv")
