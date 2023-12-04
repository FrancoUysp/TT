import datetime
import xgboost as xgb
from ..base_strategy import BaseStrategy


class WaveModel(BaseStrategy):
    def __init__(self, model_01, model_23, params, server):
        super().__init__(model_01, params)
        self.model_23 = model_23
        self.model_01 = model_01
        self.server = server

        self.initial_capital = params.get("initial_capital", 16000)
        self.capital_over_time = [self.initial_capital]
        self.trade_price = 0

        self.LOOKBACK = params.get("LOOKBACK", 180)
        self.LONG_TIMER = params.get("LONG_TIMER", 1)
        self.SHORT_EXIT = params.get("SHORT_EXIT", 1)
        self.SHORT_TIMER = params.get("SHORT_TIMER", 1)
        self.LONG_EXIT = params.get("LONG_EXIT", 1)
        self.LONG_DIFF = params.get("LONG_DIFF", 40)
        self.SHORT_DIFF = params.get("SHORT_DIFF", 20)
        self.name = params.get("name", "Wave Model")

        self.previous_high = -float("inf")
        self.previous_low = float("inf")

        self.type = "Wave Model"
        self.units = 1
        self.trade_history = []
        self.rois = dict()
        self.rois["daily"] = 0
        self.rois["monthly"] = 0
        self.rois["all_time"] = 0

        self.latest_date = None
        self.current_price = 0

        self.wait_count_for_short = 0
        self.wait_count_for_long = 0
        self.short_exit_timer = 0
        self.long_exit_timer = 0

        self.in_short_trade = False
        self.in_long_trade = False

    def execute(self, data, latest_datetime):
        # Get the latest minute data
        self.latest_date = latest_datetime

        latest_minute_data = data.iloc[-1:]
        current_price = latest_minute_data["close"].item()
        self.current_price = current_price

        current_low = latest_minute_data["low"].item()
        current_high = latest_minute_data["high"].item()

        # Calculate high and low from the lookback period
        lookback_data = data.iloc[-self.LOOKBACK :]
        lookback_high = lookback_data["high"].max()
        lookback_low = lookback_data["low"].min()

        # Determine the long and short signals based on model predictions
        dval_01 = xgb.DMatrix(latest_minute_data)
        dval_23 = xgb.DMatrix(latest_minute_data)
        prob_01 = self.model_01.predict(dval_01)[0]
        prob_23 = self.model_23.predict(dval_23)[0]
        print(f"prob long: {prob_01}\t prob short: {prob_23}")
        max_prob = max(prob_01, prob_23)
        sug_long = prob_01 > prob_23
        sug_short = not sug_long

        if not self.in_long_trade and not self.in_short_trade:
            if (
                lookback_high > self.previous_high
                and (lookback_high - self.previous_low) >= self.SHORT_DIFF
            ):
                self.wait_count_for_short = self.SHORT_TIMER
            elif self.wait_count_for_short > 0:
                self.wait_count_for_short -= 1
                if self.wait_count_for_short <= 0 and sug_short and max_prob > 0.5:
                    print("short entry")
                    self.handle_short_entry(current_price, latest_datetime)
        elif self.in_short_trade:
            if current_low <= lookback_low:
                self.short_exit_timer = self.SHORT_EXIT
            elif self.short_exit_timer > 0:
                self.short_exit_timer -= 1
                if self.short_exit_timer <= 0:
                    self.handle_short_exit(current_price, latest_datetime)

        # Execute trading logic for LONG trades
        if not self.in_long_trade and not self.in_short_trade:
            if (
                lookback_low < self.previous_low
                and (self.previous_high - lookback_low) >= self.LONG_DIFF
            ):
                self.wait_count_for_long = self.LONG_TIMER
            elif self.wait_count_for_long > 0:
                self.wait_count_for_long -= 1
                if self.wait_count_for_long <= 0 and sug_long and max_prob > 0.5:
                    self.handle_long_entry(current_price, latest_datetime)
        elif self.in_long_trade:
            # Check for LONG exit condition
            if current_high >= lookback_high:
                self.long_exit_timer = self.LONG_EXIT
            elif self.long_exit_timer > 0:
                self.long_exit_timer -= 1
                if self.long_exit_timer <= 0:
                    self.handle_long_exit(current_price, latest_datetime)

        self.previous_high = lookback_high
        self.previous_low = lookback_low


    def exit_trade(self):
        if self.in_long_trade:
            self.handle_long_exit(self.current_price, self.latest_date)
        elif self.in_short_trade:
            self.handle_short_exit(self.current_price, self.latest_date)

    def is_in_trade(self):
        return self.in_long_trade or self.in_short_trade

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
            "units": self.units,
        }
        return params

    def set_params(self, params):
        if self.is_in_trade() == False:
            self.LOOKBACK = params.get("LOOKBACK", self.LOOKBACK)
            self.LONG_TIMER = params.get("LONG_TIMER", self.LONG_TIMER)
            self.SHORT_EXIT = params.get("SHORT_EXIT", self.SHORT_EXIT)
            self.SHORT_TIMER = params.get("SHORT_TIMER", self.SHORT_TIMER)
            self.LONG_EXIT = params.get("LONG_EXIT", self.LONG_EXIT)
            self.LONG_DIFF = params.get("LONG_DIFF", self.LONG_DIFF)
            self.SHORT_DIFF = params.get("SHORT_DIFF", self.SHORT_DIFF)
            self.name = params.get("name", self.name)
            self.units = params.get("units", self.units)

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
        units: {self.units}
        """
        print(print_string)

    def calculate_roi(self):
        daily_roi = {}
        monthly_roi = {}
        total_profit = 0
        total_investment = 0

        for i in range(len(self.trade_history)):
            trade = self.trade_history[i]
            date = trade["date"].date()
            month = trade["date"].strftime("%Y-%m")

            if "short_entry_price" in trade and i + 1 < len(self.trade_history):
                exit_trade = self.trade_history[i + 1]
                if "short_exit_price" in exit_trade:
                    investment = trade["short_entry_price"] * abs(trade["units"])
                    profit = (trade["short_entry_price"] - exit_trade["short_exit_price"]) * abs(trade["units"])
                    total_profit += profit
                    total_investment += investment

            elif "long_entry_price" in trade and i + 1 < len(self.trade_history):
                exit_trade = self.trade_history[i + 1]
                if "long_exit_price" in exit_trade:
                    investment = trade["long_entry_price"] * abs(trade["units"])
                    profit = (exit_trade["long_exit_price"] - trade["long_entry_price"]) * trade["units"]
                    total_profit += profit
                    total_investment += investment

            else:
                continue  

            daily_roi[date] = (daily_roi.get(date, 0) + profit) / investment * 100
            monthly_roi[month] = (monthly_roi.get(month, 0) + profit) / investment * 100

        alltime_roi = (total_profit / total_investment) * 100 if total_investment > 0 else 0
        return daily_roi, monthly_roi, alltime_roi

    def get_roi(self):
        return self.rois

    def get_labels(self):
        labels = {"type": self.type, "alltime_roi": self.rois["all_time"]}
        return labels

    def get_trade_history(self):
        return self.trade_history

    def handle_long_entry(self, current_price, latest_datetime):
        self.server.place_long(name = self.name, quantity = self.units)
        self.in_long_trade = True
        self.trade_price = current_price
        self.trade_history.append(
            {
                "long_entry_price": current_price,
                "units": self.units,
                "date": latest_datetime,
            }
        )

    def handle_long_exit(self, current_price, latest_datetime):
        self.server.exit_long(name = self.name)
        self.in_long_trade = False
        self.trade_history.append(
            {
                "long_exit_price": current_price,
                "units": -self.units,
                "date": latest_datetime,
            }
        )
        roi_tuple = self.calculate_roi()
        self.rois["daily"] = roi_tuple[0]
        self.rois["monthly"] = roi_tuple[1]
        self.rois["all_time"] = roi_tuple[2]

    def handle_short_entry(self, current_price, latest_datetime):
        self.server.place_short(name = self.name, quantity = self.units)
        self.in_short_trade = True
        self.trade_price = current_price
        self.trade_history.append(
            {
                "short_entry_price": current_price,
                "units": -self.units,
                "date": latest_datetime,
            }
        )

    def handle_short_exit(self, current_price, latest_datetime):
        self.server.exit_short(name = self.name)
        self.in_short_trade = False
        self.trade_history.append(
            {
            "short_exit_price": current_price,
            "units": self.units,
            "date": latest_datetime,
            }
        )
        roi_tuple = self.calculate_roi()
        self.rois["daily"] = roi_tuple[0]
        self.rois["monthly"] = roi_tuple[1]
        self.rois["all_time"] = roi_tuple[2]
        
