import dash
from dash import dcc, html
import plotly.graph_objs as go
from dash.dependencies import Output, Input
from apiv2 import *
from preprocess import *
from utils import *
from preprocess import DataPreprocessor
from model import LightGBMModel 


class DashApp:

    def __init__(self):
        self.processor = DataPreprocessor()
        self.model = LightGBMModel()
        self.app = dash.Dash(__name__)

        self.previous_predictions = None

        update_main()
        self.buffer_data = create_buffer_queue()
        
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
                interval=5*1000,  
                n_intervals=0
            )
        ])

    def _set_callback(self):

        self.buffer_data = append_to_buffer_and_update_main(self.buffer_data)
        buffer_data = self.buffer_data
        preprocessed_data = self.processor.transform_for_pred(self.buffer_data.copy())
        predictions = self.model.pred_t(df=preprocessed_data, thresh=0.5)
        dates = buffer_data.iloc[-preprocessed_data.shape[0]:]["datetime"]
        self.previous_predictions = predictions 

        @self.app.callback(
            Output('live-plot', 'figure'),
            Input('interval-component', 'n_intervals')
        )

        def update_figure(n): 
            str_dates = dates.astype(str).tolist()
            figure = go.Figure()
            
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

            predicted_buy_indices = np.where(predictions== 1)[0]
            predicted_sell_indices = np.where(predictions== -1)[0]

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
        self.app.run_server(host = "0.0.0.0", debug=False)


if __name__ == '__main__':
    app = DashApp()
    app.run()
