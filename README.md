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

Once you have all the dependencies in place, copy `config-sample.py` to `config.py` and enter at least your Robinhood username and password there. You can also customize the script's behavior through the other parameters:
* (string) `username` and `password`: Robinhood credentials
* (bool) `trades_enabled`:  If False, run in test mode and just collect data, otherwise submit orders
* (bool) `debug_enabled`: Simulate interactions with Robinhood (via random values)
* (list) `ticker_list`: List of coin tickers you want to trade (BTC, ETH, etc)
* (dict) `trade_strategies`: Select which strategies would you like the bot to use (buy, sell)
* (float) `buy_below_moving_average`: If the price dips below the MA by this percentage, and if the RSI is below the oversold threshold (see below), it will try to buy
* (float) `sell_above_buy_price`: Once the price rises above the Buy price by this percentage, it will try to sell
* (float) `buy_amount_per_trade`: If greater than zero, buy this amount of coin, otherwise use all the cash in the account
* (dict) `moving_average_periods`: Number of MA observations to wait before sprinting into action, for each measure (SMA fast, SMA slow, MACD fast, MACD slow, MACD signal)
* (int) `rsi_period`: Length of the observation window for calculating the RSI
* (float) `rsi_buy_threshold`: Threshold below which the bot will try to buy
* (int) `min_seconds_between_updates` and `max_seconds_between_updates`: This bot will pick a random wait time in between readings; use these values to define that range
* (float) `reserve`: By default, the bot will try to use all the funds available in your account to buy crypto; use this value if you want to set aside a given amount that the bot should not spend
* (float) `stop_loss_threshold`: Threshold below which the bot will sell its holdings, regardless of any gains

## Running the bot
If you want to keep the bot running even when you're not logged into your server, I recommend using the [nohup](https://linuxize.com/post/linux-nohup-command/) command in Linux. It will save all the output in a file called `nohup.out`, where you can see what the bot is thinking. Information about the bot's state is also saved in three pickle files, so that if you stop and restart it, it will continue from where it left off:

> `nohup ./bot.py &`

The overall flow looks like this:
* Initialize or load a previously saved state
* Load the configuration
* Determine when to run next
* If it's time to spring into action, download the current price data from Robinhood
* Compute [moving average](https://www.investopedia.com/terms/m/movingaverage.asp) and [RSI](https://www.investopedia.com/terms/r/rsi.asp), making sure that there haven't been any interruptions in the data sequence
* Append this information to a pickle data file
* Check if the conditions to buy or sell are met
* If they are, submit the corresponding order and check if it went through
* Loop again

## Technical Analysis

### Relative Strength Index and Simple Moving Average
The RSI trading indicator is a measure of the relative strength of the market (compared to its history), a momentum oscillator and is often used as an overbought and oversold technical indicator. The RSI is displayed as a line graph that moves between two extremes from 0 to 100. Traditional interpretation and usage of the RSI are that values of 70 or above indicate that a security is becoming overvalued and the price of the security is likely to go down in the future (bearish), while the RSI reading of 30 or below indicates an oversold or undervalued condition and the price of the security is likely to go up in the future (bullish). Our bot uses this information to determine when it's *time to buy*, by checking if the current RSI is below the threshold set in the config file (39.5 by default). It also checks that the current price is below the SMA by the percentage configured in the settings. If those two conditions are met, it will submit a buy using all the available cash in the account (minus the reserve).

The simple strategy outlined here above can be expanded [in many ways](https://medium.com/mudrex/rsi-trading-strategy-with-20-sma-on-mudrex-a26bd2ac039b). To that end, this bot keeps track of a few indicators that can be used to [determine if it's time to buy or sell](https://towardsdatascience.com/algorithmic-trading-with-macd-and-python-fef3d013e9f3): SMA fast, SMA slow, RSI, MACD, MACD Signal. Future versions will include ways to select which approach you would like to use. 

### Backtesting
Backtesting is the process of testing a trading or investment strategy using data from the past to see how it would have performed. For example, let's say your trading strategy is to buy Bitcoin when it falls 3% in a day, your backtest software will check Bitcoin's prices in the past and fire a trade when it fell 3% in a day. The backtest results will show if the trades were profitable. At this time, this bot doesn't offer an easy way to ingest past data and run simulations, but it's something I have on my wishlist for sure.

## Additional Notes
This code is *far* from perfect and can certainly be improved. Waking up and finding that the bot has made money for you while you were sleeping can be cool. Watching the price continue to plunge after the bot buys, not so much. Remember, there's no logic to try and locate the bottom of a dip. And that's, in a way, why I decided to publish these experiments here on Github: if you feel like lending a hand, submit a pull request, don't be shy!
