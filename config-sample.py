rh = {
    "username": "",
    "password": "",
}

config = {
    "tradesEnabled": False,
    "buyBelowMA": 0.0075,
    "sellAboveBuyPrice": 0.01,
    "movingAverageWindows": 24,  # 4 hours * 6 samples per hour
    "minSecondsBetweenUpdates": 120,
    "maxSecondsBetweenUpdates": 480,
    "coinList": [ 'ETH' ],
    "rsiWindow": 24,
    "rsiOversold": 39.5,
    "cashReserve": 50.0,
    "stopLoss": 0.2   # sell if the price drops at least 30% below the purchase price 
}
