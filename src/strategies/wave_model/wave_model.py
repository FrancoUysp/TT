import datetime
import xgboost as xgb
from ..base_strategy import BaseStrategy


class WaveModel(BaseStrategy):
    def __init__(self, model_01, model_23, params):
        super().__init__(model_01, params)
        self.model_23 = model_23
        self.model_01 = model_01
        
        self.initial_capital = params.get('initial_capital', 16000)
        self.capital_over_time = [self.initial_capital]
        self.trade_price = 0

        self.LOOKBACK = params.get('LOOKBACK', 180)
        self.LONG_TIMER = params.get('LONG_TIMER', 1)
        self.SHORT_EXIT = params.get('SHORT_EXIT', 1)
        self.SHORT_TIMER = params.get('SHORT_TIMER', 1)
        self.LONG_EXIT = params.get('LONG_EXIT', 1)
        self.LONG_DIFF = params.get('LONG_DIFF', 40)
        self.SHORT_DIFF = params.get('SHORT_DIFF', 20)
        self.name= params.get('name', 'Wave Model')

        self.previous_high = -float("inf")
        self.previous_low = float("inf")

        self.type = "wave_model"
        self.units = 0

        self.wait_count_for_short = 0
        self.wait_count_for_long = 0
        self.short_exit_timer = 0
        self.long_exit_timer = 0

        self.in_short_trade = False
        self.in_long_trade = False

    def execute(self, data):

        # Get the latest minute data
        latest_minute_data = data.iloc[-1:]
        current_price = latest_minute_data['close'].item()
        current_low = latest_minute_data['low'].item()
        current_high = latest_minute_data['high'].item()

        # Calculate high and low from the lookback period
        lookback_data = data.iloc[-self.LOOKBACK:]
        lookback_high = lookback_data['high'].max()
        lookback_low = lookback_data['low'].min()

        # Determine the long and short signals based on model predictions
        dval_01 = xgb.DMatrix(latest_minute_data)
        dval_23 = xgb.DMatrix(latest_minute_data)
        prob_01 = self.model_01.predict(dval_01)[0]
        prob_23 = self.model_23.predict(dval_23)[0]
        max_prob = max(prob_01, prob_23)
        sug_long = prob_01 > prob_23
        sug_short = not sug_long

        if not self.in_long_trade and not self.in_short_trade:
            if lookback_high > self.previous_high and (lookback_high - self.previous_low) >= self.SHORT_DIFF:
                self.wait_count_for_short = self.SHORT_TIMER
            elif self.wait_count_for_short > 0:
                self.wait_count_for_short -= 1
                if self.wait_count_for_short <= 0 and sug_short and max_prob > 0.5:
                    self.in_short_trade = True
                    self.trade_price = current_price
                    print(f"Short trade opened at {current_price}")
        elif self.in_short_trade:
            if current_low <= lookback_low:
                print("Short trade closed at stop loss")
                self.short_exit_timer = self.SHORT_EXIT
            elif self.short_exit_timer > 0:
                self.short_exit_timer -= 1
                if self.short_exit_timer <= 0:
                    self.in_short_trade = False
                    print(f"Short trade closed at {current_price}")

        # Execute trading logic for LONG trades
        if not self.in_long_trade and not self.in_short_trade:
            if lookback_low < self.previous_low and (self.previous_high - lookback_low) >= self.LONG_DIFF:
                self.wait_count_for_long = self.LONG_TIMER
            elif self.wait_count_for_long > 0:
                self.wait_count_for_long -= 1
                if self.wait_count_for_long <= 0 and sug_long and max_prob > 0.5:
                    # Execute long trade
                    self.in_long_trade = True
                    self.trade_price = current_price
                    print(f"Long trade opened at {current_price}")
        elif self.in_long_trade:
            # Check for LONG exit condition
            if current_high >= lookback_high:
                self.long_exit_timer = self.LONG_EXIT
            elif self.long_exit_timer > 0:
                self.long_exit_timer -= 1
                if self.long_exit_timer <= 0:
                    self.in_long_trade = False
                    print(f"Long trade closed at {current_price}")

        self.previous_high = lookback_high
        self.previous_low = lookback_low
    
    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_type(self):
        return self.type
    
    def set_type(self, type):
        self.type = type

    def get_params(self):
        params = {
            "LOOKBACK": self.LOOKBACK,
            "LONG_TIMER": self.LONG_TIMER,
            "SHORT_EXIT": self.SHORT_EXIT,
            "SHORT_TIMER": self.SHORT_TIMER,
            "LONG_EXIT": self.LONG_EXIT,
            "LONG_DIFF": self.LONG_DIFF,
            "SHORT_DIFF": self.SHORT_DIFF,
            "name": self.name,
        }
        return params

    def set_params(self, params):
        self.LOOKBACK = params.get('LOOKBACK', self.LOOKBACK)
        self.LONG_TIMER = params.get('LONG_TIMER', self.LONG_TIMER)
        self.SHORT_EXIT = params.get('SHORT_EXIT', self.SHORT_EXIT)
        self.SHORT_TIMER = params.get('SHORT_TIMER', self.SHORT_TIMER)
        self.LONG_EXIT = params.get('LONG_EXIT', self.LONG_EXIT)
        self.LONG_DIFF = params.get('LONG_DIFF', self.LONG_DIFF)
        self.SHORT_DIFF = params.get('SHORT_DIFF', self.SHORT_DIFF)
        self.name = params.get('name', self.name)

    def print_params(self):
        print_string = f"""
        LOOKBACK: {self.LOOKBACK}
        LONG_TIMER: {self.LONG_TIMER}   
        SHORT_EXIT: {self.SHORT_EXIT}
        SHORT_TIMER: {self.SHORT_TIMER}
        LONG_EXIT: {self.LONG_EXIT}
        LONG_DIFF: {self.LONG_DIFF}
        SHORT_DIFF: {self.SHORT_DIFF}
        name: {self.name}
        """
        print(print_string)

    def get_units(self):
        return self.units

    def set_units(self, units):
        self.units = units
