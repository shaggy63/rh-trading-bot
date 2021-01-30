# Robinhood Crypto Trading Bot
A simple Python crypto algotrader 

## Introduction
I've been wanting to play around with algotraders for a while now. After some initial research, I stumbled upon [Jason Bowling's article](https://medium.com/swlh/a-full-crypto-trading-bot-in-python-aafba122bc4e), in which he describes the mechanics of his rudimentary Python bot. His code tickled my curiosity, so I started tinkering with it. In the spirit of open source, I created this public repository to share my experiments with anyone interested in such esoteric stuff.

## Disclaimer
To use Jason's words: cryptocurrency investing is *risky*! Doing it using a computer program is even riskier. Doing it with code you didn’t write is a _terrible_ idea. What you do with this code is entirely up to you, and any risks you take are your own. It’s intended to be educational and comes with absolutely no guarantee of anything at all. You could lose all your money. Seriously.

## Installation
You'll need access to a working Python3 interpreter. For the sake of simplicity, I am going to assume that you know your way around a Linux shell, and that you have [pip3](https://linuxize.com/post/how-to-install-pip-on-ubuntu-18.04/#installing-pip-for-python-3) on your machine. Install the following dependencies:
* [Robin-Stock](http://www.robin-stocks.com/en/latest/quickstart.html): `pip3 install robin_stocks`
* [Pandas](https://pandas.pydata.org/pandas-docs/stable/index.html): `pip3 install pandas`
* [TA-Lib](https://www.ta-lib.org/): download their tarball and compile it

Once you have all the dependencies in place, copy `config-sample.py` to `config.py` and enter at least your Robinhood username and password. You can also use the following parameters to customize the bot's behavior:
* (string) `username` and `password`: Robinhood credentials
* (bool) `trades_enabled`:  If False, run in test mode and just collect data, otherwise submit orders
* (bool) `debug_enabled`: Simulate interactions with Robinhood (via random values)
* (list) `ticker_list`: List of coin ticker pairs Kraken/Robinhood (XETHZUSD/ETH, etc); see [here](https://api.kraken.com/0/public/AssetPairs) for a complete list of available tickers on Kraken
* (dict) `trade_strategies`: Select which strategies would you like the bot to use (buy, sell)
* (float) `buy_below_moving_average`: If the price dips below the MA by this percentage, and if the RSI is below the oversold threshold (see below), it will try to buy
* (float) `sell_above_buy_price`: Once the price rises above the Buy price by this percentage, it will try to sell
* (float) `buy_amount_per_trade`: If greater than zero, buy this amount of coin, otherwise use all the cash in the account
* (dict) `moving_average_periods`: Number of MA observations to wait before sprinting into action, for each measure (SMA fast, SMA slow, MACD fast, MACD slow, MACD signal)
* (int) `rsi_period`: Length of the observation window for calculating the RSI
* (float) `rsi_buy_threshold`: Threshold below which the bot will try to buy
* (float) `reserve`: By default, the bot will try to use all the funds available in your account to buy crypto; use this value if you want to set aside a given amount that the bot should not spend
* (float) `stop_loss_threshold`: Threshold below which the bot will sell its holdings, regardless of any gains
* (int) `minutes_between_updates`: How often should the bot spring into action (1 (default), 5, 15, 30, 60, 240, 1440, 10080, 21600)
* (bool) `save_charts`: Enable this feature to have the bot save SMA charts for each coin it's handling
* (int) `max_data_rows`: Max number of data points to store in the Pickle file (if you have issues with memory limits on your machine). 1k rows = 70kB

## Running the bot
If you want to keep the bot running even when you're not logged into your server, I recommend using the [nohup](https://linuxize.com/post/linux-nohup-command/) command in Linux. It will save its output in a file called `nohup.out`, where you can see what the bot is thinking. Information about the bot's state is also saved in three pickle files, so that if you stop and restart it, it will continue from where it left off:

> `nohup ./bot.py &`

The overall flow looks like this:
* Load the configuration and initialize or load a previously saved state
* Load saved data points or download new ones from Kraken
* Every 5 minutes (you can customize this in the settings), download the latest price info from Kraken for each coin
* Compute [moving averages](https://www.investopedia.com/terms/m/movingaverage.asp) and [RSI](https://www.investopedia.com/terms/r/rsi.asp), making sure that there haven't been any interruptions in the data sequence
* If the conditions to buy or sell are met, submit the corresponding order
* Rinse and repeat

The bot maintains a list of purchased assets (saved as `orders.pickle`) and at each iteration, it determines if the conditions to sell any of them are met. It also handles swing and miss orders, by checking if any of the orders placed during the previous iteration are still pending (not filled), and cancels them.

## Indicators
### Relative Strength Index
The RSI trading indicator is a measure of the relative strength of the market (compared to its history), a momentum oscillator and is often used as an overbought and oversold technical indicator. The RSI is displayed as a line graph that moves between two extremes from 0 to 100. Traditional interpretation and usage of the RSI are that values of 70 or above indicate that a security is becoming overvalued and the price of the security is likely to go down in the future (bearish), while the RSI reading of 30 or below indicates an oversold or undervalued condition and the price of the security is likely to go up in the future (bullish).

### Moving Average Convergence/Divergence
Moving average convergence divergence (MACD) is a trend-following momentum indicator that shows the relationship between two moving averages of a security’s price. The MACD is calculated by subtracting the 26-period [exponential moving average](https://www.investopedia.com/terms/e/ema.asp) (EMA) from the 12-period EMA. The result of that calculation is the MACD line. A nine-day EMA of the MACD called the "signal line," is then plotted on top of the MACD line, which can function as a trigger for buy and sell signals. Traders may buy the security when the MACD crosses above its signal line and sell—or short—the security when the MACD crosses below the signal line. Moving average convergence divergence (MACD) indicators can be interpreted in several ways, but the more common methods are crossovers, divergences, and rapid rises/falls.

## Technical Analysis
This bot can implement any technical analysis as a series of conditions on the indicators it collects. Some of them are built into the algorithm, to give you a starting point to create your own. For example, Jason's approach is to buy when the price drops below the Fast-SMA by the percentage configured in the settings, and the RSI is below the threshold specified in the config file. By looking at multiple data points, you can also determine if a crossover happened, and act accordingly. The simple strategy outlined here above can be expanded [in many ways](https://medium.com/mudrex/rsi-trading-strategy-with-20-sma-on-mudrex-a26bd2ac039b). To that end, this bot keeps track of a few indicators that can be used to [determine if it's time to buy or sell](https://towardsdatascience.com/algorithmic-trading-with-macd-and-python-fef3d013e9f3): SMA fast, SMA slow, RSI, MACD, MACD Signal. Future versions will include ways to select which approach you would like to use. 

## Backtesting
Backtesting is the process of testing a trading or investment strategy using data from the past to see how it would have performed. For example, let's say your trading strategy is to buy Bitcoin when it falls 3% in a day, your backtest software will check Bitcoin's prices in the past and fire a trade when it fell 3% in a day. The backtest results will show if the trades were profitable. At this time, this bot doesn't offer an easy way to ingest past data and run simulations, but it's something I have on my wishlist for sure.

## Additional Notes
This code is *far* from perfect and can certainly be improved. Waking up and finding that the bot has made money for you while you were sleeping can be cool. Watching the price continue to plunge after the bot buys, not so much. Remember, there's no logic to try and locate the bottom of a dip. And that's, in a way, why I decided to publish these experiments here on Github: if you feel like lending a hand, submit a pull request, don't be shy!
