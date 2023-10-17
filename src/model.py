import os
import lightgbm as lgb
import numpy as np
import pickle
import pandas as pd
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from imblearn.over_sampling import RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler 
from preprocess import *
from sklearn.model_selection import train_test_split

class LightGBMModel:
    def __init__(self, split_perc=0.95):
        self.model = None
        self.split_perc = split_perc

    def predict(self, df, thresh=0.6):
        X = df.apply(pd.to_numeric, errors="coerce").dropna()
        y_pred_proba = self.model.predict(X, num_iteration=self.model.best_iteration)  # Get predicted probabilities
        
        # Convert probabilities to class labels based on the threshold
        y_pred = np.where(
            y_pred_proba > thresh, 1,  # probability of class 1 > 0.6 => label 1
            np.where(
                (1 - y_pred_proba) > thresh, -1,
                0  
            )
        )
        return y_pred

    def set_data(self, data):
        self.data = data
        self.data = data.apply(pd.to_numeric, errors="coerce").dropna()

    def preprocess_data(self):
        self.split_idx = int(len(self.data) * self.split_perc)
        self.train_data = self.data.iloc[: self.split_idx]
        self.train_data = self.train_data[self.train_data["target"] != 0]

        # Print the count of unique values for the target variable in self.train_data
        print("Unique value counts in training data target variable:\n", self.train_data["target"].value_counts())

        self.X_train = self.train_data.drop(columns=["target"])
        self.y_train = self.train_data["target"]

        self.X_test = self.data.iloc[self.split_idx:].drop(columns=["target"])
        self.y_test = self.data.iloc[self.split_idx:]["target"]  
        print("Unique value counts in testing data target variable:\n", self.y_test.value_counts())

        ros = RandomUnderSampler()
        self.X_train, self.y_train = ros.fit_resample(self.X_train, self.y_train)


    def train(self):

        def pnl_metric(preds, train_data):
            labels = train_data.get_label()
            indices = train_data.get_data().index
            buy_sell_signals = np.where(preds > 0.5, 1, -1)  # assuming binary classification
            prices = self.data['close'].iloc[indices]
            shifted_signals = np.roll(buy_sell_signals, -20)  # Shift signals to align with future price changes
            pnl = np.sum(shifted_signals[1:] * prices.diff().iloc[1:])  # calculate PnL
            return 'Profit and Loss', pnl, True  # higher PnL is better

        # Splitting some of your training data into a validation set
        X_train_split, X_val_split, y_train_split, y_val_split = train_test_split(
            self.X_train, self.y_train, test_size=0.2, random_state=42, stratify=self.y_train
        )

        d_train = lgb.Dataset(X_train_split, label=y_train_split, free_raw_data=False)
        d_valid = lgb.Dataset(X_val_split, label=y_val_split, free_raw_data=False)

        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'dart',
        }
        
        # Setting up the early stopping rounds parameter
        self.model = lgb.train(
            params,
            d_train,
            valid_sets=[d_valid],  # Validation data used for early stopping
            callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=True)],  # Stop after 50 rounds of no improvement
            num_boost_round=2000,  # Maximum number of boosting rounds
            feval=pnl_metric,
        )

        # This will print the optimal number of boosting rounds (trees)
        print(f'Optimal number of trees: {self.model.best_iteration}')


    def backtest(self):
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        self.y_pred = self.predict(self.X_test, 0.75)  # Use your predict method
        report = classification_report(np.array(self.y_test), self.y_pred)  # Compare with y_test
        print(report)

    def save_model(self, filename):
        if not os.path.exists(filename):
            os.makedirs(filename)
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        pickle.dump(self.model, open(filename + '/lgb_model.pkl', 'wb'))

    def load_model(self, filename):
        self.model = pickle.load(open(filename + '/lgb_model.pkl', 'rb'))
        return self.model
    def plot_candlestick_with_predictions(
        self,
        output_dir="../output/plots",
    ):
        data=self.data[self.split_idx:]
        predictions=self.y_pred
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
        predicted_sell_signals = np.where(predictions == -1)[0]

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
    preprocessor = DataPreprocessor()
    preprocessor.transform_for_training(n=450000)
    data = preprocessor.data


    model = LightGBMModel(split_perc=0.99)
    model.set_data(data)
    model.preprocess_data()
    model.train()
    model.backtest()
    model.plot_candlestick_with_predictions()
    model.save_model("../models")
