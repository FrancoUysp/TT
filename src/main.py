import dash
from dash import dcc, html
import plotly.graph_objs as go
from dash.dependencies import Output, Input
import threading
import time
from apiv2 import *
from preprocess import *
from utils import *
from preprocess import DataPreprocessor
from model import LightGBMModel
import catboost

class DashApp:

    def __init__(self):
        self.processor = DataPreprocessor()
        self.model = LightGBMModel()
        self.model.load_model(os.path.join("..", "models"))
        self.app = dash.Dash(__name__)
        self.previous_predictions = None
        update_main()
        self.buffer_data = create_buffer_queue()
        self._set_layout()
        self._set_callback()
        self.predictions = []


        # Initialize threading
        self.stop_event = threading.Event()
        self.bg_thread = threading.Thread(target=self.update_predictions, args=(self.stop_event,))

    def update_predictions(self, stop_event):
        while not stop_event.is_set():
            self.buffer_data = append_to_buffer_and_update_main(self.buffer_data)
            self.preprocessed_data = self.processor.transform_for_pred(self.buffer_data.copy())
            self.predictions = self.model.pred_t(df=self.preprocessed_data, thresh=0.5)
            self.previous_predictions = self.predictions
            time.sleep(5)

    def _set_layout(self):
        self.app.layout = html.Div(style={
            'backgroundColor': '#111111',
            'width': '100vw',
            'height': '100vh',
            'margin': '0'
        }, children=[
            dcc.Graph(
                id='live-plot',
                config={'displayModeBar': False},
                style={'height': '100%'}
            ),
            dcc.Interval(
                id='interval-component',
                interval=5 * 1000,
                n_intervals=0
            )
        ])

    def _set_callback(self):
        @self.app.callback(
            Output('live-plot', 'figure'),
            Input('interval-component', 'n_intervals')
        )

        def update_figure(n): 
            self.dates = self.buffer_data.iloc[-self.preprocessed_data.shape[0]:]["datetime"]
            str_dates = self.dates.astype(str).tolist()
            figure = go.Figure()
            
            figure.add_trace(
                go.Candlestick(
                    x=str_dates,
                    open=self.preprocessed_data['open'],
                    high=self.preprocessed_data['high'],
                    low=self.preprocessed_data['low'],
                    close=self.preprocessed_data['close'],
                    name="Candlesticks"
                )
            )

            predicted_buy_indices = np.where(self.predictions== 1)[0]
            predicted_sell_indices = np.where(self.predictions== -1)[0]

            predicted_buy_dates = [str_dates[i] for i in predicted_buy_indices]
            predicted_sell_dates = [str_dates[i] for i in predicted_sell_indices]

            predicted_buy_close_values =self.preprocessed_data['close'].iloc[predicted_buy_indices]
            predicted_sell_close_values = self.preprocessed_data['close'].iloc[predicted_sell_indices]

            figure.add_trace(
                go.Scatter(
                    x=predicted_buy_dates,
                    y=predicted_buy_close_values,
                    mode="markers",
                    name="Predicted Buy Signals",
                    marker=dict(color="lime", size=12, symbol="circle"),
                )
            )

            figure.add_trace(
                go.Scatter(
                    x=predicted_sell_dates,
                    y=predicted_sell_close_values,
                    mode="markers",
                    name="Predicted Sell Signals",
                    marker=dict(color="magenta", size=12, symbol="circle"),
                )
            )
            figure.update_layout(
                title="Candlestick Chart with Predicted Buy/Sell Signals",
                xaxis_title="Date",
                yaxis_title="Price",

                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                xaxis=dict(type="category")  
            )

            return figure

    def run(self):
        # Start background thread
        self.bg_thread.start()
        self.app.run_server(host="0.0.0.0", debug=False)

    def stop(self):
        # Stop the background thread
        self.stop_event.set()
        self.bg_thread.join()

if __name__ == '__main__':
    app = DashApp()
    try:
        app.run()
    finally:
        app.stop()

if __name__ == '__main__':
    app = DashApp()
    app.run()
