# RobinHood Crypto Trading Bot
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

Once you have all the dependencies in place, copy `config-sample.py` to `config.py` and enter at least your RobinHood username and password there. You can also customize the script's behavior through the other parameters:
* (string) `username` and `password`: Your Robinhood credentials
* (bool) `tradesEnabled`:  Run the bot in test mode and just collect data, or allow it to submit orders
* (bool) `debugEnabled`: Simulate interactions with Robinhood (via random values)
* (list) `tickerList`: List of coin tickers you want to trade (BTC, ETH, etc)
* (float) `buyBelowMA`: If the price dips below the MA by this percentage, and if the RSI is below the oversold threshold (see below), it will try to buy
* (float) `sellAboveBuyPrice`: Once the price rises above the Buy price by this percentage, it will try to sell
* (int) `movingAveragePeriods`: Number of MA observations to wait before sprinting into action, for each measure (SMA fast, SMA slow, MACD fast, MACD slow, MACD signal)
* (int) `rsiPeriod`: Length of the observation window for calculating the RSI
* (float) `rsiOversold`: Threshold below which the bot will try to buy
* (int) `minSecondsBetweenUpdates` and `maxSecondsBetweenUpdates`: This bot will pick a random wait time in between readings; use these values to define that range
* (float) `cashReserve`: By default, the bot will try to use all the funds available in your account to buy crypto; use this value if you want to set aside a given amount that the bot should not spend
* (float) `stopLoss`: Threshold below which the bot will sell its holdings, regardless of any gains

## Running the bot
If you want to keep the bot running even when you're not logged into your server, I recommend using the [nohup](https://linuxize.com/post/linux-nohup-command/) command in Linux. It will save all the output in a file called `nohup.out`, where you can see what the bot is thinking. Information about the bot's state is also saved in three pickle files, so that if you stop and restart it, it will continue from where it left off:

> `nohup ./bot.py &`

The overall flow looks like this:
* Initialize or load a previously saved state
* Load the configuration
* Determine when to run next
* If it's time to spring into action, download the current price data from RobinHood
* Compute [moving average](https://www.investopedia.com/terms/m/movingaverage.asp) and [RSI](https://www.investopedia.com/terms/r/rsi.asp), making sure that there haven't been any interruptions in the data sequence
* Append this information to a pickle data file
* Check if the conditions to buy or sell are met, depending on the local wallet being empty or not
* Submit the order and check that it went through
* Loop again

## Additional Notes
This code is *far* from perfect and can certainly be improved. Waking up and finding that the bot has made money for you while you were sleeping can be cool. Watching the price continue to plunge after the bot buys, not so much. Remember, there's no logic to try and locate the bottom of a dip. And that's, in a way, why I decided to publish these experiments here on Github: if you feel like lending a hand, submit a pull request, don't be shy!
