import pandas as pd 
import numpy as np 
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import MetaTrader5 as mt5
import datetime
import time
from datetime import timedelta

SERVER = "Pepperstone-Demo"
PASSWORD = "duCf7yzn:h"
LOGIN = 61202587
SYMBOLS = ["XAUUSD", "NAS100"] 
EMAIL_LIST = ["peter@trollopegroup.co.za", "francouysp@gmail.com", "marcoleroux7@gmail.com"]  # Define your email list
last_email_sent_date = None  # To keep track of the last email sent date

def send_email(subject, body, to_email):
    '''
    send_email(
        subject="Automation test",
        body="This is a test email sent from a Python script.",
        to_email="peter@trollopegroup.co.za "
    )
    '''
    gmail_user = 'francouysaiden@gmail.com'  # replace with your gmail address
    gmail_password = 'fany feqy qhlx eaoc'

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(gmail_user, gmail_password)
        text = msg.as_string()
        server.sendmail(gmail_user, to_email, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

def connect():
    mt5.initialize()
    authorized = mt5.login(LOGIN, password=PASSWORD, server=SERVER)

    if authorized:
        print(f"Connected: Connecting to MT5 Client at {SERVER}")
    else:
        print("Failed to connect, error code: {}".format(mt5.last_error()))

def close_connection():
    """
    This method is meant to close the connection with the brokerage.
    """
    try:
        mt5.shutdown()
    except Exception as e:
        print(e)

def find_filling_mode(symbol, order_type="BUY"):
    if not mt5.symbol_info_tick(symbol):
        print(f"Failed to get symbol info for {symbol}")
        return -1  # Or any other error handling

    if order_type == "BUY":
        price = mt5.symbol_info_tick(symbol).ask
        order = mt5.ORDER_TYPE_BUY
    elif order_type == "SELL":
        price = mt5.symbol_info_tick(symbol).bid
        order = mt5.ORDER_TYPE_SELL
    else:
        return -1  # Invalid order type

    for i in range(2):
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": mt5.symbol_info(symbol).volume_min,
            "type": order,
            "price": price,
            "type_filling": i,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = mt5.order_check(request)

        if result and result.comment == "Done":
            return i  

    return -1  

def place_trade(id:int, quantity:float, symbol, buy=False, sell=False, pct_tp=0, pct_sl=0, comment="NA", id_position=None):
    connect()
    quantity = float(quantity)
    cost_of_one_lot = None
    trade_request = None

    if buy == True:
        filling_mode = find_filling_mode(symbol, "BUY")
    else:
        filling_mode = find_filling_mode(symbol, "SELL")

    if filling_mode == -1:
        print("Error finding filling mode")
        return

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"{symbol} not found, cannot place order")
        close_connection()
        return

    if not symbol_info.visible:
        print(f"{symbol} is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print(f"symbol_select({symbol}) failed, cannot place order")
            close_connection()
            return

    # obtain account info
    account_info = mt5.account_info()
    if not account_info:
        print("Failed to get account information")
        close_connection()
        return

    # calculate the margin required to place the order
    if buy:
        cost_of_one_lot = symbol_info.trade_contract_size * symbol_info.ask
        if symbol == "XAUUSD":
            cost_of_one_lot /= 100
    if sell:
        cost_of_one_lot = symbol_info.trade_contract_size * symbol_info.bid
        if symbol == "XAUUSD":
            cost_of_one_lot /= 100

    if (
        cost_of_one_lot != None
        and account_info.margin_free < cost_of_one_lot * quantity
    ):
        print("Insufficient margin to place order")
        close_connection()
        return

    print(id_position)
    # enter a long
    if buy and id_position == None:
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": quantity,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "deviation": 20,
            "magic": 112009,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

    # here we exit a buy position
    if sell and id_position != None:
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": quantity,
            "type": mt5.ORDER_TYPE_SELL,
            "position": id_position,
            "price": mt5.symbol_info_tick(symbol).bid,
            "deviation": 20,
            "magic": 112009,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

    # here we enter a short
    if sell and id_position == None:
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": quantity,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "deviation": 20,
            "magic": 112009,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

    # here we exit a short
    if buy and id_position != None:
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": quantity,
            "type": mt5.ORDER_TYPE_BUY,
            "position": id_position,
            "price": mt5.symbol_info_tick(symbol).ask,
            "deviation": 20,
            "magic": 112009,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

    if trade_request != None:
        result = mt5.order_send(trade_request)
        if result is None:
            print("order_send failed, error code:", mt5.last_error())
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(
                f"Trade request executed successfully, position id={result.order}"
            )
            close_connection()
            return result.order

    close_connection()

def find_units(proportion, symbol, buy):
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return 0

    account_info = mt5.account_info()
    if account_info is None:
        print("Failed to access account information")
        mt5.shutdown()
        return 0

    # Calculate the amount of capital to be used based on free margin
    capital = account_info.margin_free * proportion

    # Get the current price of the symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
        mt5.shutdown()
        return 0

    # You can choose between the bid or ask price depending on your needs
    # For example, use the ask price for buy orders and the bid price for sell orders
    symbol_price  = symbol_info.ask if buy else symbol_info.bid

    # Calculate the number of units that can be bought
    if symbol_price == 0:
        print("Symbol price is 0, unable to calculate units")
        mt5.shutdown()
        return 0

    units = math.floor(capital / symbol_price)

    # Adjust the units according to the minimum volume step
    units = units - (units % symbol_info.volume_step)

    mt5.shutdown()
    return units

def get_latest_min(symbol, server_time_offset_hours):
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return None

    # Ensure the symbol is watched
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to watch symbol {symbol}")
        mt5.shutdown()
        return None

    # Adjust for server time difference
    server_time = datetime.datetime.now() + timedelta(hours=server_time_offset_hours)
    server_time = server_time.replace(microsecond=0, second=0) - timedelta(minutes=1)

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, int(server_time.timestamp()), 1)

    # You can stop watching the symbol if you don't need it after fetching data
    # mt5.symbol_select(symbol, False)

    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print(f"No data for {symbol}, Error: {mt5.last_error()}")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df = df[["datetime", "open", "high", "low", "close"]]

    return df.iloc[0]

def get_trade_information(sym):
    if not mt5.initialize():
        return "Failed to initialize MT5"

    # Define the time range for trade history
    from_date = datetime.datetime.now() - datetime.timedelta(days=30)
    to_date = datetime.datetime.now()

    trades = mt5.history_deals_get(from_date, to_date)
    if trades is None or len(trades) == 0:
        mt5.shutdown()
        return f"No trade history found for {sym}"

    # Filter trades by symbol and specific comment pattern
    filtered_trades = [trade for trade in trades if trade.symbol == sym and 'unique identifier' in trade.comment]

    # Analyze the filtered trades
    trade_info = []
    for trade in filtered_trades:
        trade_time = datetime.datetime.fromtimestamp(trade.time)
        trade_type = "Buy" if trade.type == mt5.ORDER_TYPE_BUY else "Sell"
        profit = trade.profit
        # Additional information can be added here
        trade_info.append(f"Time: {trade_time}, Type: {trade_type}, Profit: {profit}")

    mt5.shutdown()

    return "\n".join(trade_info) if trade_info else f"No trades found for {sym} with specified criteria."

class TrendFollower():
    def __init__(self, proportion, L_thresh_prop, S_thresh_prop, symbol):
        self.L_thresh_prop = L_thresh_prop
        self.S_thresh_prop = S_thresh_prop 

        self.units = 0
        self.proportion= proportion
        self.symbol = symbol
        
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
        
        self.current_price = latest_minute_data["close"].item()
        if self.prev_price == 0:
            self.prev_price = self.current_price
            return
        price_change = self.current_price - self.prev_price
        
        self.L_thresh = self.current_price * self.L_thresh_prop
        self.S_thresh = self.current_price * self.S_thresh_prop
        
        self.prev_price = self.current_price
        self.prev_neg = self.accumulative_sum_neg
        self.prev_pos = self.accumulative_sum_pos

        if price_change > 0:
            self.accumulative_sum_pos += price_change
            self.accumulative_sum_neg = 0
        elif price_change < 0:
            self.accumulative_sum_neg += price_change
            self.accumulative_sum_pos = 0

        self.sum_bull = self.prev_pos if (self.prev_pos > 0 and self.accumulative_sum_pos == 0) else 0
        self.sum_bear = self.prev_neg if (self.prev_neg < 0 and self.accumulative_sum_neg == 0) else 0
       
        # if self.sum_bull > self.L_thresh:
        if self.in_trade and self.trade_type == 0:  
            comment = f"{self.symbol}"
            place_trade(id=None, quantity=self.units, buy=True, id_position=self.trade_id, symbol=self.symbol, comment=comment)
            self.in_trade = False
            self.trade_id = None
            # print("###############################exit short", self.trade_id)
        if not self.in_trade:  
            self.units = find_units(self.proportion, self.symbol, buy = True)
            comment = f"{self.symbol}"
            self.trade_id = place_trade(id=None, quantity=self.units, buy=True, symbol=self.symbol, comment=comment)
            # print("###############################placed long", self.trade_id)
            self.trade_type = 1
            self.in_trade = True
            return

        # elif self.sum_bear < self.S_thresh:
        if self.in_trade and self.trade_type == 1:  
            comment = f"{self.symbol}"
            place_trade(id=None, quantity=self.units, sell=True, id_position=self.trade_id, symbol=self.symbol, comment=comment)
            self.in_trade = False
            # print("###############################exit long", self.trade_id)
            self.trade_id = None
        if not self.in_trade:  
            # Enter short trade use place trade to do this
            comment = f"{self.symbol}"
            self.units = find_units(self.proportion, self.symbol, buy = False)
            self.trade_id = place_trade(id=None, quantity=self.units, sell=True, symbol=self.symbol, comment=comment)
            # print("###############################placed short", self.trade_id)
            self.trade_type = 0
            self.in_trade = True
            return


def send_daily_emails():
    subject = "Daily Update"
    body = "This is the daily update sent from the Python script.\n\n"

    # Gather trade information for each symbol
    for sym in SYMBOLS:
        trade_info = get_trade_information(sym)
        body += f"Trade Information for {sym}:\n{trade_info}\n\n"

    for email in EMAIL_LIST:
        send_email(subject, body, email)

    print("Daily emails sent to all in the list.")

def init_models():
    models = {}
    for sym in SYMBOLS:
        proportion = 0.5  # Example proportion value

        if sym == "XAUUSD":
            L_thresh_prop = 0.005 
            S_thresh_prop = -0.002 
        else:
            L_thresh_prop = 0.003     # Example threshold values
            S_thresh_prop = -0.004

        models[sym] = TrendFollower(proportion, L_thresh_prop, S_thresh_prop, sym)
    
    return models

def main():

    latest_data = {}
    server_time_offset_hours = 2  # Adjust this based on your server's time difference
    global last_email_sent_date
    models = init_models()
    last_minute = datetime.datetime.now().minute

    while True:
        current_time = datetime.datetime.now()
        current_minute = current_time.minute
        
        # Email sending check
        if current_time.hour == 18 and current_time.minute == 0 and (last_email_sent_date != current_time.date()):
            send_daily_emails()
            last_email_sent_date = current_time.date()


        if last_minute != current_minute:
            last_minute = current_minute  
            print("Fetching new minute data...")
            for sym in SYMBOLS:
                trade_info = get_trade_information(sym)
                print(trade_info)
                # Fetch the latest minute interval data for each symbol
                latest_minute_data = get_latest_min(sym, server_time_offset_hours)
                latest_data[sym] = latest_minute_data
                print(f"Latest data for {sym}: {latest_data[sym]}")

                # Execute the model for the symbol if data is available
                if latest_minute_data is not None:
                    models[sym].execute(latest_minute_data, current_time)
            
        # Calculate sleep time
        time_to_sleep = 60.1 - (datetime.datetime.now().second + datetime.datetime.now().microsecond/1000000.0)
        time.sleep(time_to_sleep)

if __name__ == "__main__":
    main()
