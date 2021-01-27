config = {
    'username': "", # Robinhood credentials
    'password': "",
    'trades_enabled': False, # if False, just collect data
    'debug_enabled': False, # if enabled, just pretend to connect to Robinhood
    'ticker_list': [ 'ETH' ], # list of coin tickers (BTC, ETH, etc)
    'trade_strategies': { # select which strategies would you like the bot to use (buy, sell); see documentation for more info
        'buy': 'rsi_sma',
        'sell': 'above_buy'
    },
    'buy_below_moving_average': 0.0075, # buy if price drops below Fast_MA by this percentage (0.75%)
    'profit_percentage': 0.01, # sell if price raises above purchase price by this percentage (1%)
    'buy_amount_per_trade': 0, # if greater than zero, buy this amount of coin, otherwise use all the cash in the account
    'moving_average_periods': { # data points to calculate SMA fast, SMA slow, MACD fast, MACD slow, MACD signal
        'sma_fast': 40,
        'sma_slow': 200,
        'macd_fast': 40,
        'macd_slow': 120,
        'macd_signal': 25
    },
    'rsi_period': 20, # data points for RSI
    'rsi_buy_threshold': 39.5, # threshold to trigger a buy
    'reserve': 0.0, # tell the bot if you don't want it to use all of the available cash in your account
    'stop_loss_threshold': 0.3,   # sell if the price drops at least 30% below the purchase price
    'min_seconds_between_updates': 120,
    'max_seconds_between_updates': 300,
    'max_data_rows': 10000
}
