#!/usr/bin/python3 -u

# Crypto Trading Bot
# Version: 0.9
# Credits: https://github.com/JasonRBowling/cryptoTradingBot/

from config import config
from datetime import datetime, timedelta
import math
import numpy as np
import os.path as path
import pandas as pd
import pickle
import random
import robin_stocks as r
import sys
import talib
import time

class coin:
    purchasedPrice = 0.0
    numBought = 0.0
    lastBuyOrder = ''
    timeBought = ''

    def __init__( self, name='' ):
        print( 'Creating coin ' + name )
        self.purchasedPrice = 0.0
        self.numBought = 0.0
        self.lastBuyOrderID = ''
        self.timeBought = ''

class moneyBot:
    defaultConfig = {
        'username': '',
        'password': '',
        'tradesEnabled': False,
        'debugEnabled': False,
        'tickerList': [],
        'buyBelowMA': 0.0075,
        'sellAboveBuyPrice': 0.01,
        'movingAveragePeriods': [ 20, 100, 24, 70, 15 ],
        'rsiPeriod': 20,
        'rsiOversold': 39.5,
        'minSecondsBetweenUpdates': 120,
        'maxSecondsBetweenUpdates': 300,
        'cashReserve': 0.0,
        'stopLoss': 0.2
    }
    data = pd.DataFrame()
    coinState = {}
    
    minShareIncrements = {}  #the smallest increment of a coin you can buy/sell
    minPriceIncrements = {}   #the smallest fraction of a dollar you can buy/sell a coin with
    minConsecutiveSamples = 0
    
    availableCash = 0
    nextMinute = 0
    tradingLocked = False # used to determine if we have had a break in our incoming price data and hold buys if so

    def __init__( self ):
        # Set Pandas to output all columns in the dataframe
        pd.set_option( 'display.max_columns', None )
        pd.set_option( 'display.width', 300 )

        print( '-- Configuration ------------------------' )
        for c in self.defaultConfig:
            isDefined = config.get( c )
            if ( not isDefined ):
                config[ c ] = self.defaultConfig[ c ]

        if ( not config[ 'username' ] or not config[ 'password' ] ):
            print( 'RobinHood credentials not found in config file. Aborting.' )
            exit()

        if ( config[ 'rsiPeriod' ] > config[ 'movingAveragePeriods' ][ 0 ] ):
            self.minConsecutiveSamples = config[ 'rsiPeriod' ]
        else:
            self.minConsecutiveSamples = config[ 'movingAveragePeriods' ][ 0 ]
        
        for k, v in config.items():
            if ( k == 'username' or k == 'password' ):
                continue

            print( k, ': ', v, sep='' )

        print( '-- End Configuration --------------------' )

        if path.exists( 'state.pickle' ):
            # Load state
            print( 'Loading previously saved state' )
            with open( 'state.pickle', 'rb' ) as f:
                self.coinState = pickle.load( f )
        else:
            # Start from scratch
            print( 'No state saved, starting from scratch' )
            for c in config[ 'tickerList' ]:
                self.coinState[ c ] = coin( c )

        # Load data points
        if ( path.exists( 'dataframe.pickle' ) ):
            self.data = pd.read_pickle( 'dataframe.pickle' )
        else:
            column_names = [ 'timestamp' ]

            for c in config[ 'tickerList' ]:
                column_names.append( c )

            self.data = pd.DataFrame( columns = column_names )

        # Connect to RobinHood
        if ( not config[ 'debugEnabled' ] ):
            try:
                rhResponse = r.login( config[ 'username' ], config[ 'password' ] )
            except:
                print( 'Got exception while attempting to log into RobinHood.' )
                exit()

        # Download RobinHood parameters
        for ticker in config[ 'tickerList' ]:
            if ( not config[ 'debugEnabled' ] ):
                try:
                    result = r.get_crypto_info( ticker )
                    s_inc = result[ 'min_order_quantity_increment' ]
                    p_inc = result[ 'min_order_price_increment' ]
                except:
                    print( 'Failed to get increments from RobinHood.' )
                    exit()
            else:
                s_inc = 0.0001
                p_inc = 0.0001

            self.minShareIncrements.update( { ticker: float( s_inc ) } )
            self.minPriceIncrements.update( { ticker: float( p_inc ) } )

        print( '-- Bot Ready ----------------------------' )

        # Schedule the bot
        self.nextMinute = datetime.now().minute
        return

    def getHoldings( self, ticker ):
        quantity = 0.0

        if ( not config[ 'debugEnabled' ] ):
            try:
                result = r.get_crypto_positions()
                for t in result:
                    symbol = t[ 'currency' ][ 'code' ]
                    if ( symbol == ticker ):
                        quantity = t[ 'quantity' ]
            except:
                print( 'Got exception while getting holdings from RobinHood.' )
                quantity = -1.0
        else:
            quantity = random.randint( 5, 60 )

        return float( quantity )

    def checkConsecutive( self, now ):
        if ( self.data.shape[ 0 ] <= 1 ):
            return False
        
        # Check for break between now and last sample
        timediff = now - datetime.strptime( self.data.iloc[ -1 ][ 'timestamp' ], '%Y-%m-%d %H:%M' )

        # Not enough data points available or it's been too long since we recorded any data
        if ( timediff.seconds > config[ 'maxSecondsBetweenUpdates' ] * 2 ):
            return False

        # Check for break in sequence of samples to minimum consecutive sample number
        position = len( self.data ) - 1
        if ( position >= self.minConsecutiveSamples ):
            for x in range( 0, self.minConsecutiveSamples ):
                timediff = datetime.strptime( self.data.iloc[ position - x ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) - datetime.strptime( self.data.iloc[ position - ( x + 1 ) ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) 

                if ( timediff.seconds > config[ 'maxSecondsBetweenUpdates' ] * 2 ):
                    print( 'Interruption found in price data, holding buys until sufficient samples are collected.' )
                    return False

        return True

    def updateDataPoints( self, now ):
        newRow = {}

        self.tradingLocked = False
        newRow[ 'timestamp' ] = now.strftime( "%Y-%m-%d %H:%M" )

        # Calculate moving averages and RSI values
        for ticker in config[ 'tickerList' ]:
            if ( not config[ 'debugEnabled' ] ):
                try:
                    result = r.get_crypto_quote( ticker )
                    newRow[ ticker ] = round( float( result[ 'mark_price' ] ), 3 )
                
                except:
                    print( 'An exception occurred retrieving prices.' )
                    self.tradingLocked = True
                    return self.data
            else:
                newRow[ ticker ] = round( float( random.randint( 10, 100 ) ), 3 )

            self.data = self.data.append( newRow, ignore_index = True )

            if ( self.data.shape[ 0 ] > 0 ):
                self.data[ ticker + '_SMA_F' ] = self.data[ ticker ].shift( 1 ).rolling( window = config[ 'movingAveragePeriods' ][ 0 ] ).mean()
                self.data[ ticker + '_SMA_S' ] = self.data[ ticker ].shift( 1 ).rolling( window = config[ 'movingAveragePeriods' ][ 1 ] ).mean()
                self.data[ ticker + '_RSI' ] = talib.RSI( self.data[ ticker ].values, timeperiod = config[ 'rsiPeriod' ] )
                self.data[ ticker + '_MACD' ], self.data[ ticker + '_MACD_S' ], macd_hist = talib.MACD( self.data[ ticker ].values, fastperiod = config[ 'movingAveragePeriods' ][ 2 ], slowperiod = config[ 'movingAveragePeriods' ][ 3 ], signalperiod = config[ 'movingAveragePeriods' ][ 4 ] )

        return self.data

    def cancelOrder( self, orderID ):
        print( 'Swing and miss, cancelling order ' + orderID )
        
        if ( not config[ 'debugEnabled' ] ):
            try:
                cancelResult = r.cancel_crypto_order( orderID )
            except:
                print( 'Got exception canceling order, will try again.' )
                return False

        return True

    def sell( self, ticker, price ):
        # Sell only what previously bought
        availableCoin = self.coinState[ ticker ].numBought

        if ( availableCoin > 0.0 ):
            # Price needs to be specified to no more precision than listed in minPriceIncrement. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            price = round( math.floor( price / self.minPriceIncrements[ ticker ] ) * self.minPriceIncrements[ ticker ], 7 )  
            profit = ( availableCoin * price ) - ( availableCoin * self.coinState[ ticker ].purchasedPrice )

            print( 'Selling ' + str( ticker ) + ' ' + str( availableCoin ) + ' for $' + str( price ) + ' (profit: $' + str( round( profit, 2 ) ) + ')' )

            if ( config[ 'tradesEnabled' ] ):
                if ( not config[ 'debugEnabled' ] ):
                    try:
                        sellResult = r.order_sell_crypto_limit( str( ticker ), availableCoin, price )
                        self.coinState[ ticker ].lastSellOrder = sellResult[ 'id' ]
                    except:
                        print( 'Got exception trying to sell, cancelling trade.' )
                        return

                self.coinState[ ticker ].purchasedPrice = 0.0
                self.coinState[ ticker ].numBought = 0.0
                self.coinState[ ticker ].lastBuyOrderID = ''
                self.coinState[ ticker ].timeBought = ''

        return

    def buy( self, ticker, price ):
        # If we are already in the process of a buy, don't submit another
        if ( self.availableCash < 1 ):
            print( 'Previous buy incomplete.' )
            return

        # Values need to be specified to no more precision than listed in minPriceIncrement. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
        price = round( math.floor( price / self.minPriceIncrements[ ticker ] ) * self.minPriceIncrements[ ticker ], 7 )
        shares = ( self.availableCash - 0.25 ) / price
        shares = round( math.floor( shares / self.minShareIncrements[ ticker ] ) * self.minShareIncrements[ ticker ], 8 )
        print( 'Buying ' + str( ticker ) + ' ' + str( shares ) + ' at $' + str( price ) )

        if ( config[ 'tradesEnabled' ] ):
            if ( not config[ 'debugEnabled' ] ):
                try:
                    buyResult = r.order_buy_crypto_limit( str( ticker ), shares, price )
                    self.coinState[ ticker ].lastBuyOrderID = buyResult[ 'id' ]
                except:
                    print( 'Got exception trying to buy, cancelling.' )
                    return

            self.coinState[ ticker ].purchasedPrice = price
            self.coinState[ ticker ].timeBought = str( datetime.now() )
            self.coinState[ ticker ].numBought = shares

        return

    def runBot( self ):
        while ( True ):
            now = datetime.now()

            # Is it time to spring into action?
            if ( now.minute == self.nextMinute ):
                self.data = self.updateDataPoints( now )

                # Determine when to run next
                futureTime = now + timedelta( 0, random.randint( config[ 'minSecondsBetweenUpdates' ], config[ 'maxSecondsBetweenUpdates' ] - 1 ) )
                self.nextMinute = futureTime.minute

                # Refresh the cash amount available for trading
                if ( not config[ 'debugEnabled' ] ):
                    try:
                        me = r.account.load_phoenix_account( info=None )
                        self.availableCash = float( me[ 'crypto_buying_power' ][ 'amount' ] ) - config[ 'cashReserve' ]
                    except:
                        print( 'An exception occurred getting cash amount.' )
                        self.availableCash = -1.0
                else:
                    self.availableCash = random.randint( 1000, 5000 ) + config[ 'cashReserve' ]

                # Print state
                print( '-- ' + str( datetime.now().strftime( '%Y-%m-%d %H:%M' ) ) + ' ---------------------' )
                print( self.data.tail() )
                print( '-- Bot Status ---------------------------' )
                print( 'Next Run (minute): ' + str( self.nextMinute ).zfill( 2 ) )
                print( '$' + str( self.availableCash ) + ' available for trading' )
                print( 'Trading Locked: ' + str( self.tradingLocked ) )

                for ticker, state in self.coinState.items():
                    # Check for swing/miss on each coin here
                    if ( self.availableCash < 1 and state.timeBought != '' ):
                        timeDiffBuyOrder = now - datetime.strptime( state.timeBought, '%Y-%m-%d %H:%M:%S.%f' )
                        availableCoin = self.getHoldings( ticker )
                        if availableCoin == -1:
                            print( 'Error trying to get holdings while checking for swing/miss, cancelling.' )
                        elif ( availableCoin < state.numBought and self.cancelOrder( state.lastBuyOrderID ) ):
                            self.availableCash = self.coinState[ ticker ].purchasedPrice * self.coinState[ ticker ].numBought
                            self.coinState[ ticker ].purchasedPrice = 0.0
                            self.coinState[ ticker ].numBought = 0.0
                            self.coinState[ ticker ].lastBuyOrderID = ''
                            self.coinState[ ticker ].timeBought = ''

                    print( str( ticker ) + ': ' + str( state.numBought ), end = '' )
            
                    if ( state.numBought > 0.0 ):
                        coinCost = state.numBought * state.purchasedPrice
                        targetProfit = coinCost * config[ 'sellAboveBuyPrice' ]
                        print( ' | Cost: $' + str( round( coinCost, 3 ) ) + ' | Current value: $' + str( round( self.data.iloc[ -1 ][ ticker ] * state.numBought, 3 ) ) + ' | Selling at $' + str( round( coinCost + targetProfit, 3 ) ) )
                    else:
                        print( "\n" )

                # Save state
                with open( 'state.pickle', 'wb' ) as f:
                    pickle.dump( self.coinState, f )

                self.data.to_pickle( 'dataframe.pickle' )

                # We don't have enough consecutive data points to decide what to do
                if ( not self.checkConsecutive( now ) ):
                    time.sleep(30)
                    continue

                for ticker in config[ 'tickerList' ]:
                    # Look at values in last row
                    price = self.data.iloc[ -1 ][ ticker ]
                    MAFast = self.data.iloc[ -1 ][ ticker + '_SMA_F' ]
                    MASlow = self.data.iloc[ -1 ][ ticker + '_SMA_S' ]
                    RSI = self.data.iloc[ -1 ][ ticker + '_RSI' ]
                    MACD = self.data.iloc[ -1 ][ ticker + '_MACD' ]
                    MACD_SIG = self.data.iloc[ -1 ][ ticker + '_MACD_S' ]

                    if ( not math.isnan( MAFast ) and not math.isnan( RSI ) and not self.tradingLocked ):
                        # Buy?
                        if (
                                self.coinState[ ticker ].numBought == 0.0 and
                                price < MAFast - ( MAFast * config[ 'buyBelowMA' ] ) and
                                RSI <= config[ 'rsiOversold' ]
                            ):
                            self.buy( ticker, price )

                        # Sell?
                        if ( (
                                self.coinState[ ticker ].numBought > 0.0 and
                                price > self.coinState[ ticker ].purchasedPrice + ( self.coinState[ ticker ].purchasedPrice * config[ 'sellAboveBuyPrice' ] )
                                
                            ) or 
                            # Stop-loss
                            (
                                price < self.coinState[ ticker ].purchasedPrice - ( self.coinState[ ticker ].purchasedPrice * config[ 'stopLoss' ] )
                            ) ):
                            self.sell( ticker, price )

                # Take a break, you deserve it
                time.sleep( 60 )

        time.sleep( 30 )

def main():
    m = moneyBot()
    m.runBot()

if __name__ == "__main__":
    main()
