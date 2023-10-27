from logging import debug
import dash
from dash import dcc, html
import plotly.graph_objs as go
from dash.dependencies import Output, Input
import asyncio
from apiv2 import *
from preprocess import *
import threading
from utils import *

from model import LightGBMModel 


class DashApp:

    def __init__(self):
        # Initialize the app
        self.threads = 0
        self.app = dash.Dash(__name__)

        self.previous_predictions = None

        update_main()
        self.buffer_data = create_buffer_queue()
        
        self.api = PolygonClient()  # Assuming APIKEY is defined
        self._set_layout()
        self._set_callback()

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
                interval=1*1000,
                n_intervals=0
            )
        ])

    def _set_callback(self):
        @self.app.callback(
            Output('live-plot', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_graph(n_intervals):
#######################################################################################################
            preprocessed_data, dates, predictions = self.api.get_agg_dat()  # Changed to get_agg_dat
            if np.array_equal(self.previous_predictions, predictions):
                raise dash.exceptions.PreventUpdate

            if preprocessed_data is None or dates is None or predictions is None or preprocessed_data.empty:
                return go.Figure()  

            self.previous_predictions = predictions
            str_dates = dates.astype(str).tolist()

            # Create a new figure
            figure = go.Figure()
            
            # Candlestick trace
            figure.add_trace(
                go.Candlestick(
                    x=str_dates,
                    open=preprocessed_data['open'],
                    high=preprocessed_data['high'],
                    low=preprocessed_data['low'],
                    close=preprocessed_data['close'],
                    name="Candlesticks"
                )
            )

            # Predicted Buy/Sell signal trace
            predicted_buy_indices = np.where(predictions == 1)[0]
            predicted_sell_indices = np.where(predictions == -1)[0]

            predicted_buy_dates = [str_dates[i] for i in predicted_buy_indices]
            predicted_sell_dates = [str_dates[i] for i in predicted_sell_indices]

            predicted_buy_close_values = preprocessed_data['close'].iloc[predicted_buy_indices]
            predicted_sell_close_values = preprocessed_data['close'].iloc[predicted_sell_indices]

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
            # Layout adjustments
            figure.update_layout(
                title="Candlestick Chart with Predicted Buy/Sell Signals",
                xaxis_title="Date",
                yaxis_title="Price",
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                xaxis=dict(type="category")  # Here's the change to force the xaxis to be categorical
            )

            return figure
####################################################################################################
    def run_websocket(self):
        self.api.connect()

    def run(self):
        if self.threads == 0:
            self.threads = 1
            ws_thread = threading.Thread(target=self.run_websocket)
            ws_thread.start()
            print("WebSocket thread started")

        if self.threads == 1:
            print("Starting the Dash app")
            self.app.run_server(host = "0.0.0.0", debug=False)


if __name__ == '__main__':
    app = DashApp()
    app.run()
