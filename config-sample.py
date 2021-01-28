config = {
    'username': "", # Robinhood credentials
    'password': "",
    'trades_enabled': False, # if False, just collect data
    'debug_enabled': False, # if enabled, just pretend to connect to Robinhood
    'ticker_list': { # list of coin ticker pairs Kraken/Robinhood (XETHZUSD/ETH, etc) - https://api.kraken.com/0/public/AssetPairs
        'XETHZUSD': 'ETH'
    }, 
    'trade_strategies': { # select which strategies would you like the bot to use (buy, sell); see documentation for more info
        'buy': 'sma_rsi_threshold',
        'sell': 'above_buy'
    },
    'buy_below_moving_average': 0.0075, # buy if price drops below Fast_MA by this percentage (0.75%)
    'profit_percentage': 0.01, # sell if price raises above purchase price by this percentage (1%)
    'buy_amount_per_trade': 0, # if greater than zero, buy this amount of coin, otherwise use all the cash in the account
    'moving_average_periods': { # data points needed to calculate SMA fast, SMA slow, MACD fast, MACD slow, MACD signal
        'sma_fast': 48, # 12 data points per hour, 4 hours worth of data
        'sma_slow': 192,
        'macd_fast': 48,
        'macd_slow': 104, # MACD 12/26 -> 48/104
        'macd_signal': 28
    },
    'rsi_period': 48, # data points for RSI
    'rsi_threshold': { # RSI thresholds to trigger a buy or a sell order
        'buy': 39.5,
        'sell': 60
    },
    'reserve': 0.0, # tell the bot if you don't want it to use all of the available cash in your account
    'stop_loss_threshold': 0.3,   # sell if the price drops at least 30% below the purchase price
    'minutes_between_updates': 5, # 1 (default), 5, 15, 30, 60, 240, 1440, 10080, 21600
    'max_data_rows': 10000
}
