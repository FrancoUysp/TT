import datetime
import xgboost as xgb
import uuid


class TrendFollower():
    def __init__(self, params, server):
        self.server = server

        self.SHORT_THRESHOLD = params.get("SHORT_THRESHOLD", -83)
        self.LONG_THRESHOLD = params.get("LONG_THRESHOLD", 41)

        self.name = params.get("name", "Trend Follower")

        self.type = "Trend Follower"
        self.units = 1
        self.trade_history = []
        self.rois = dict()
        self.rois["daily"] = 0
        self.rois["monthly"] = 0
        self.rois["all_time"] = 0
        self.id = str(uuid.uuid4())
        self.trade_id = None

        self.latest_date = None
        self.current_price = 0

        self.trade_price = 0
        self.in_trade = False
        self.trade_type = None 
        self.sum_bull = 0
        self.sum_bear = 0
        self.accumulative_sum_pos = 0
        self.accumulative_sum_neg = 0
        self.prev_pos = 0
        self.prev_neg = 0
        self.prev_price = 0

    def execute(self, data, latest_datetime):
        self.latest_date = latest_datetime
        latest_minute_data = data.iloc[-1:]
        current_price = latest_minute_data["close"].item()

        if self.prev_price == 0:
            self.prev_price = current_price
            return

        self.current_price = current_price

        price_change = current_price - self.prev_price
        self.prev_neg = self.accumulative_sum_neg
        self.prev_pos = self.accumulative_sum_pos

        if price_change > 0:
            self.accumulative_sum_pos += price_change
            self.accumulative_sum_neg = 0
        elif price_change < 0:
            self.accumulative_sum_neg += price_change
            self.accumulative_sum_pos = 0

        if self.prev_pos > 0 and self.accumulative_sum_pos == 0:
            self.sum_bull = self.prev_pos
        else:
            self.sum_bull = 0
            
        if self.prev_neg < 0 and self.accumulative_sum_neg == 0:
            self.sum_bear = self.prev_neg
        else: 
            self.sum_bear = 0

        if self.sum_bull > self.LONG_THRESHOLD:
            if self.in_trade and self.trade_type == 0:  # Exit short trade
                self.handle_short_exit(current_price, latest_datetime)
            if not self.in_trade:  # Enter long trade
                self.handle_long_entry(current_price, latest_datetime)

        elif self.sum_bear < self.SHORT_THRESHOLD:
            if self.in_trade and self.trade_type == 1:  # Exit long trade
                self.handle_long_exit(current_price, latest_datetime)
            if not self.in_trade:  # Enter short trade
                self.handle_short_entry(current_price, latest_datetime)

        self.prev_price = current_price

    def exit_trade(self):
        if self.in_trade == False:
            return
        if self.trade_type == 0:
            self.handle_short_exit(self.current_price, self.latest_date)
            return
        if self.trade_type == 1:
            self.handle_long_exit(self.current_price, self.latest_date)
            return

    def is_in_trade(self):
        return self.in_trade

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
            "SHORT_THRESHOLD": self.SHORT_THRESHOLD,
            "LONG_THRESHOLD": self.LONG_THRESHOLD,
            "name": self.name,
            "units": self.units,
        }
        return params

    def set_params(self, params):
        if self.is_in_trade() == False:
            self.SHORT_THRESHOLD = params.get("SHORT_THRESHOLD", self.SHORT_THRESHOLD)
            self.LONG_THRESHOLD = params.get("LONG_THRESHOLD", self.LONG_THRESHOLD)
            self.name = params.get("name", self.name)
            self.units = params.get("units", self.units)

    def print_params(self):
        print_string = f"""
        SHORT_THRESHOLD: {self.SHORT_THRESHOLD}
        LONG_THRESHOLD: {self.LONG_THRESHOLD}
        name: {self.name}
        units: {self.units}
        """
        print(print_string)

    def calculate_roi(self):
        daily_roi = {}
        monthly_roi = {}
        total_profit = 0
        total_investment = 0
        profit = 0
        investment = 0

        for i in range(len(self.trade_history)):
            trade = self.trade_history[i]
            date = trade["date"].date()
            month = trade["date"].strftime("%Y-%m")

            if "short_entry_price" in trade and i + 1 < len(self.trade_history):
                exit_trade = self.trade_history[i + 1]
                if "short_exit_price" in exit_trade:
                    investment = trade["short_entry_price"] * abs(trade["units"])
                    profit = (
                        trade["short_entry_price"] - exit_trade["short_exit_price"]
                    ) * abs(trade["units"])
                    total_profit += profit
                    total_investment += investment

            elif "long_entry_price" in trade and i + 1 < len(self.trade_history):
                exit_trade = self.trade_history[i + 1]
                if "long_exit_price" in exit_trade:
                    investment = trade["long_entry_price"] * abs(trade["units"])
                    profit = (
                        exit_trade["long_exit_price"] - trade["long_entry_price"]
                    ) * trade["units"]
                    total_profit += profit
                    total_investment += investment

            else:
                continue

            daily_roi[date] = (daily_roi.get(date, 0) + profit) / investment * 100
            monthly_roi[month] = (monthly_roi.get(month, 0) + profit) / investment * 100

        alltime_roi = (
            (total_profit / total_investment) * 100 if total_investment > 0 else 0
        )
        return daily_roi, monthly_roi, alltime_roi

    def get_roi(self):
        return self.rois

    def get_labels(self):
        labels = {"type": self.type, "alltime_roi": self.rois["all_time"]}
        return labels

    def get_trade_history(self):
        return self.trade_history

    def handle_long_entry(self, current_price, latest_datetime):
        self.trade_id = self.server.place_trade(
            id=self.id,
            quantity=self.units,
            buy=True,
            sell=False,
        )
        self.trade_type = 1
        self.trade_price = current_price
        self.in_trade = True
        self.trade_history.append(
            {
                "long_entry_price": current_price,
                "units": self.units,
                "date": latest_datetime,
            }
        )

    def handle_long_exit(self, current_price, latest_datetime):
        self.server.place_trade(
            id=self.id,
            quantity=self.units,
            buy=False,
            sell=True,
            id_position=self.trade_id,
        )
        self.in_trade = False
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
        self.trade_id = self.server.place_trade(
            id=self.id,
            quantity=self.units,
            buy=False,
            sell=True,
        )
        self.trade_type = 0
        self.trade_price = current_price
        self.in_trade = True
        self.trade_history.append(
            {
                "short_entry_price": current_price,
                "units": -self.units,
                "date": latest_datetime,
            }
        )

    def handle_short_exit(self, current_price, latest_datetime):
        self.server.place_trade(
            id=self.id,
            quantity=self.units,
            buy=True,
            sell=False,
            id_position=self.trade_id,
        )
        self.in_trade = False
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

    def get_id(self):
        return self.id

