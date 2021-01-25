config = {
    'username': "", # Robinhood credentials
    'password': "",
    'tradesEnabled': False, # if False, the bot will just collect data
    'debugEnabled': False, # if enabled, the bot will just pretend to connect to Robinhood
    'tickerList': [ 'ETH' ], # list of coin tickers (BTC, ETH, etc)
    'buyBelowMA': 0.0075, # buy if price drops below Fast_MA by this percentage (0.75%)
    'sellAboveBuyPrice': 0.01, # sell if price raises above purchase price by this percentage (1%)
    'movingAveragePeriods': [ 20, 100, 12, 26 ], # data points to calculate SMA fast, SMA slow, MACD fast, MACD slow, MACD signal
    'rsiPeriod': 20, # data points for RSI
    'rsiOversold': 39.5, # threshold to trigger a buy
    'minSecondsBetweenUpdates': 120,
    'maxSecondsBetweenUpdates': 300,
    'cashReserve': 0.0, # tell the bot if you don't want it to use all of your funds
    'stopLoss': 0.3   # sell if the price drops at least 30% below the purchase price 
}
