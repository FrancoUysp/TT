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
from tqdm import tqdm
from sklearn.model_selection import train_test_split

class LightGBMModel:
    def __init__(self, split_perc=0.95):
        self.model = None
        self.split_perc = split_perc
        self.processor = DataPreprocessor()

    def pred_t(self, df, thresh=0.6):
        X = df.apply(pd.to_numeric, errors="coerce").dropna()
        y_pred_proba = self.model.predict_proba(X)[:, 1]  # Get probability of class 1
        y_pred = np.where(
            y_pred_proba > thresh, 1,  # If probability of class 1 > 0.6, predict 1
            np.where(
                (1 - y_pred_proba) > thresh, -1,  # If probability of class 0 > 0.6, predict -1
                0  # Otherwise, predict 0
            )
        )
        return y_pred

    def set_data(self, data):
        self.data = data
        self.data = data.apply(pd.to_numeric, errors="coerce").dropna()

    def plot_feature_importances(self):
        if self.model is None:
            raise ValueError("Model is not trained yet.")
            
        # Extract feature names and their importance scores
        features = self.X_train.columns.tolist()
        importances = self.model.feature_importance(importance_type="gain")
        
        # Sorting the features based on importance
        sorted_idx = np.argsort(importances)[::-1]
        
        # Creating the bar chart
        fig = go.Figure([go.Bar(
            x=np.array(features)[sorted_idx],
            y=importances[sorted_idx],
            orientation='v'
        )])
        
        fig.update_layout(
            title="Feature Importance",
            xaxis_title="Features",
            yaxis_title="Importance",
            template="plotly_dark",
        )
        
        fig.show()

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

        ros = RandomOverSampler()
        self.X_train, self.y_train = ros.fit_resample(self.X_train, self.y_train)

    def train(self):
        d_train = lgb.Dataset(self.X_train, label=self.y_train, free_raw_data=False)

        params = {
            'objective': "binary",
            'metric': 'binary_error', 
            'boosting_type': 'dart',   # This is the correction for the 'dart' entry
            'is_unbalance': True,
        }

        def tqdm_callback():
            pbar = tqdm(total=500, desc="Training Progress")  
            
            def callback(env):
                if env.iteration % 10 == 0:
                    pbar.update(10)
                if env.iteration >= 500:  # or you can use pbar.total
                    pbar.close()  # Ensure the progress bar is closed at the end

            return callback

        self.model = lgb.train(
            params,
            d_train,
            callbacks=[tqdm_callback()],
            num_boost_round=500,
        )


    def backtest(self):
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        self.y_pred = self.pred_t(self.X_test, 0.5)  # Use your predict method
        report = classification_report(np.array(self.y_test), self.y_pred)  # Compare with y_test
        print(report)

    def save_model(self, filename):
        directory = os.path.dirname(filename)  # Get the directory of the filename
        if not os.path.exists(directory):
            os.makedirs(directory)
        if self.model is None:
            raise ValueError("Model is not trained yet.")
        with open(os.path.join(filename, 'lgb_model.pkl'), 'wb') as f:
            pickle.dump(self.model, f)

    def load_model(self, filename):
        with open(os.path.join(filename, 'trained_catboost_model.pkl'), 'rb') as f:
            self.model = pickle.load(f)
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
    preprocessor.transform_for_training()
    data = preprocessor.data


    model = LightGBMModel(split_perc=0.97)
    model.set_data(data)
    model.preprocess_data()
    model.train()
    model.plot_feature_importances()
    model.backtest()
    model.plot_candlestick_with_predictions()
    model.save_model(os.path.join("..", "models"))
