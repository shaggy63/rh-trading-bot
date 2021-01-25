config = {
    'username': "", # Robinhood credentials
    'password': "",
    'trades_enabled': False, # if False, the bot will just collect data
    'debug_enabled': False, # if enabled, the bot will just pretend to connect to Robinhood
    'ticker_list': [ 'ETH' ], # list of coin tickers (BTC, ETH, etc)
    'buy_below_moving_average': 0.0075, # buy if price drops below Fast_MA by this percentage (0.75%)
    'sell_above_buy_price': 0.01, # sell if price raises above purchase price by this percentage (1%)
    'moving_average_periods': [ 20, 100, 12, 26 ], # data points to calculate SMA fast, SMA slow, MACD fast, MACD slow, MACD signal
    'rsi_period': 20, # data points for RSI
    'rsi_buy_threshold': 39.5, # threshold to trigger a buy
    'min_seconds_between_updates': 120,
    'max_seconds_between_updates': 300,
    'reserve': 0.0, # tell the bot if you don't want it to use all of the available cash in your account
    'stop_loss_threshold': 0.3   # sell if the price drops at least 30% below the purchase price 
}
