from base_strategy import BaseStrategy
import datetime
import xgboost as xgb


class WaveModel(BaseStrategy):
    def __init__(self, model_01, model_23, data, execution_handler, params):
        super().__init__(model_01, data, execution_handler, params)
        self.model_23 = model_23
        self.model_01 = model_01
        
        # Assign parameters from the `params` dictionary
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

        self.previous_high = -float("inf")
        self.previous_low = float("inf")

        self.wait_count_for_short = 0
        self.wait_count_for_long = 0
        self.short_exit_timer = 0
        self.long_exit_timer = 0

        self.in_short_trade = False
        self.in_long_trade = False


    def execute(self, data):

        dval_01 = xgb.DMatrix(data)  
        dval_23 = xgb.DMatrix(data)  
        predictions_01 = self.model_01.predict(dval_01)  
        predictions_23 = self.model_23.predict(dval_23)  

        for i in range(len(data)):

            window = data.iloc[-self.LOOKBACK:]
            current_high = max(window["high"])
            current_low = min(window["low"])
            current_price = data.iloc[i]["close"]
            sug_long = False 
            sug_short = False

            prob_23 = predictions_23[i]
            prob_01 = predictions_01[i]

            if prob_01  > prob_23:
                sug_long = True
            else: 
                sug_short = True

            p = max(prob_01, prob_23)

            # SHORT logic
            if current_high > self.previous_high and (current_high - self.previous_low) > self.SHORT_DIFF and not (self.in_long_trade or self.in_short_trade):
                self.wait_count_for_short = self.SHORT_TIMER
            elif self.wait_count_for_short > 0 and sug_short:
                self.wait_count_for_short -= 1
                if self.wait_count_for_short == 0 and p > 0.5 and i == len(data) - 1:
                    self.in_short_trade = True
                    trade_price = current_price
                    print(f"Short trade opened at {current_price} and at time {datetime.datetime.now()}")

            # LONG logic
            if current_low < self.previous_low and (self.previous_high - current_low) > self.LONG_DIFF and not (self.in_long_trade or self.in_short_trade):
                self.wait_count_for_long = self.LONG_TIMER
            elif self.wait_count_for_long > 0 and sug_long:
                self.wait_count_for_long -= 1
                if self.wait_count_for_long == 0 and p > 0.5 and i == len(data) - 1:
                    self.in_long_trade = True
                    trade_price = current_price
                    print(f"Long trade opened at {current_price} and at time {datetime.datetime.now()}")

            #exit logic for short
            if self.in_short_trade:
                if current_price < current_low:
                    self.short_exit_timer = self.SHORT_EXIT
                if self.short_exit_timer > 0:
                    self.short_exit_timer -= 1
                    if self.short_exit_timer == 0:
                        self.in_short_trade = False
                        print(f"Short trade closed at {current_price} and at time {datetime.datetime.now()}")

            #exit logic for long
            if self.in_long_trade:
                if current_price > current_high:
                    self.long_exit_timer = self.LONG_EXIT
                if self.long_exit_timer > 0:
                    self.long_exit_timer -= 1
                    if self.long_exit_timer == 0:
                        self.in_long_trade = False
                        print(f"Long trade closed at {current_price} and at time {datetime.datetime.now()}")

            self.previous_high = current_high
            self.previous_low = current_low
