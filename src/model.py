import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from imblearn.over_sampling import RandomOverSampler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from preprocess import *


class NeuralNetworkModel:
    def __init__(self, split_perc=0.95):
        self.model = None

        self.split_perc = split_perc

    def predict(self, df):
        """
        Predict using the trained model on the provided dataframe.
        
        Args:
        - df (pandas.DataFrame): Input data for prediction.
        
        Returns:
        - np.array: Predicted values in binary (1 or 0).
        """
        # Preprocess input data (assuming similar preprocessing is required)
        X = df.apply(pd.to_numeric, errors="coerce").dropna()
        # Feature scaling
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Predict
        y_pred = self.model.predict(X_scaled)

        # Convert to binary
        y_pred_binary = np.array([1 if p >= 0.5 else 0 for p in y_pred.ravel()])

        return y_pred_binary
    def set_data(self, data):
        self.data = data
        self.data = data.apply(pd.to_numeric, errors="coerce").dropna()

        self.params = {
            "learning_rate": 0.001,
            "epochs": 10,
            "batch_size": 32,
            "input_dim": self.data.shape[1] - 1,  # excluding target column
        }

    def preprocess_data(self):
        self.split_idx = int(len(self.data) * self.split_perc)
        self.train_data = self.data.iloc[: self.split_idx]
        
        # Note: Assuming that "target" can be -1, 0, or 1 and you want to exclude 0.
        self.train_data = self.train_data[self.train_data["target"] != 0]
        
        self.X_train = self.train_data.drop(columns=["target"])
        self.y_train = self.train_data["target"].apply(lambda x: 1 if x == 1 else 0)  # Ensuring binary encoding
        
        self.X_test = self.data.iloc[self.split_idx:].drop(columns=["target"])
        self.y_test = self.data.iloc[self.split_idx:]["target"].apply(lambda x: 1 if x == 1 else 0)  
        
        ros = RandomOverSampler()
        self.X_train, self.y_train = ros.fit_resample(self.X_train, self.y_train)

        # Feature scaling
        scaler = StandardScaler()
        self.X_train = scaler.fit_transform(self.X_train)
        self.X_test = scaler.transform(self.X_test)

    def train(self):
        self.model = Sequential()
        self.model.add(Dense(128, input_dim=self.params["input_dim"], activation='relu'))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(1, activation='sigmoid'))  # Binary classification
        
        self.model.compile(loss='binary_crossentropy',
                           optimizer=Adam(lr=self.params["learning_rate"]),
                           metrics=['accuracy'])
        
        self.model.fit(self.X_train, self.y_train, 
                       epochs=self.params["epochs"],
                       batch_size=self.params["batch_size"])
        
    def backtest(self):
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        self.y_pred = self.model.predict(self.X_test)
        self.y_pred_binary = [1 if p >= 0.5 else 0 for p in self.y_pred.ravel()]
        report = classification_report(self.y_test, self.y_pred_binary, zero_division=0)
        print(report)

    def save_model(self, filename):
        if not os.path.exists(filename):
            os.makedirs(filename)
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        self.model.save(filename + "/nn_model.h5")

    def load_model(self, filename):
        self.model = load_model(filename + "/nn_model.h5")
        return self.model

    def plot_candlestick_with_predictions(
        self,
        output_dir="../output/plots",
    ):
        data=self.data[self.split_idx :]
        predictions=self.y_pred_binary
        # Ensure the directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        fig = go.Figure()

        # Candlestick trace
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                name="Candlesticks",
            )
        )

        # Predicted Buy/Sell/Hold signal trace
        predictions = np.array(predictions)
        predicted_buy_signals = np.where(predictions == 1)[0]
        predicted_sell_signals = np.where(predictions == 0)[0]

        fig.add_trace(
            go.Scatter(
                x=data.index[predicted_buy_signals],
                y=data["close"].iloc[predicted_buy_signals],
                mode="markers",
                name="Predicted Buy Signals",
                marker=dict(color="lime", size=12, symbol="circle"),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data.index[predicted_sell_signals],
                y=data["close"].iloc[predicted_sell_signals],
                mode="markers",
                name="Predicted Sell Signals",
                marker=dict(color="magenta", size=12, symbol="circle"),
            )
        )
        # Layout adjustments
        fig.update_layout(
            title="Candlestick Chart with Predicted Buy/Sell/Hold Signals",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
        )

        fig.show()

        # Save the figure to the desired directory
        fig.write_html(os.path.join(output_dir, "candlestick_with_predictions.html"))

if __name__ == "__main__":
    preprocessor = DataPreprocessor(n=100000)
    preprocessor.label_sharp_changes()
    preprocessor.add_time_features()
    preprocessor.add_technical_indicators()
    preprocessor.handle_missing_values()

    data = preprocessor.data

    model = NeuralNetworkModel(split_perc=0.9)
    model.set_data(data)
    model.preprocess_data()
    model.train()
    model.backtest()
    model.plot_candlestick_with_predictions()
    model.save_model("../plots")
