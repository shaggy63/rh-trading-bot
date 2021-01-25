#!/usr/bin/python3 -u

# Crypto Trading Bot
# Version: 0.9.5
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
    price = 0.0
    quantity = 0.0
    order_id = ''

    def __init__( self, name='' ):
        print( 'Creating coin ' + name )
        self.price = 0.0
        self.quantity = 0.0
        self.order_id = ''

class moneyBot:
    default_config = {
        'username': '',
        'password': '',
        'trades_enabled': False,
        'debug_enabled': False,
        'ticker_list': [],
        'buy_below_moving_average': 0.0075,
        'sell_above_buy_price': 0.01,
        'moving_average_periods': [ 20, 100, 24, 70, 15 ],
        'rsi_period': 20,
        'rsi_buy_threshold': 39.5,
        'min_seconds_between_updates': 120,
        'min_seconds_between_updates': 300,
        'reserve': 0.0,
        'stop_loss_threshold': 0.2
    }
    data = pd.DataFrame()
    portfolio = {}
    
    min_share_increments = {}  #the smallest increment of a coin you can buy/sell
    min_price_increments = {}   #the smallest fraction of a dollar you can buy/sell a coin with
    min_consecutive_samples = 0
    
    available_cash = 0
    nextMinute = 0
    tradingLocked = False # used to determine if we have had a break in our incoming price data and hold buys if so

    def __init__( self ):
        # Set Pandas to output all columns in the dataframe
        pd.set_option( 'display.max_columns', None )
        pd.set_option( 'display.width', 300 )

        print( '-- Configuration ------------------------' )
        for c in self.default_config:
            isDefined = config.get( c )
            if ( not isDefined ):
                config[ c ] = self.default_config[ c ]

        if ( not config[ 'username' ] or not config[ 'password' ] ):
            print( 'RobinHood credentials not found in config file. Aborting.' )
            exit()

        if ( config[ 'rsi_period' ] > config[ 'moving_average_periods' ][ 0 ] ):
            self.min_consecutive_samples = config[ 'rsi_period' ]
        else:
            self.min_consecutive_samples = config[ 'moving_average_periods' ][ 0 ]
        
        for k, v in config.items():
            if ( k == 'username' or k == 'password' ):
                continue

            print( k.replace( '_', ' ' ).capitalize(), ': ', v, sep='' )

        print( '-- End Configuration --------------------' )

        if path.exists( 'portfolio.pickle' ):
            # Load state
            print( 'Loading previously saved state' )
            with open( 'portfolio.pickle', 'rb' ) as f:
                self.portfolio = pickle.load( f )
        else:
            # Start from scratch
            print( 'No state saved, starting from scratch' )
            for ticker in config[ 'ticker_list' ]:
                self.portfolio[ ticker ] = coin( ticker )

        # Load data points
        if ( path.exists( 'dataframe.pickle' ) ):
            self.data = pd.read_pickle( 'dataframe.pickle' )
        else:
            column_names = [ 'timestamp' ]

            for ticker in config[ 'ticker_list' ]:
                column_names.append( ticker )

            self.data = pd.DataFrame( columns = column_names )

        # Connect to RobinHood
        if ( not config[ 'debug_enabled' ] ):
            try:
                rhResponse = r.login( config[ 'username' ], config[ 'password' ] )
            except:
                print( 'Got exception while attempting to log into RobinHood.' )
                exit()

        # Download RobinHood parameters
        for ticker in config[ 'ticker_list' ]:
            if ( not config[ 'debug_enabled' ] ):
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

            self.min_share_increments.update( { ticker: float( s_inc ) } )
            self.min_price_increments.update( { ticker: float( p_inc ) } )

        print( '-- Bot Ready ----------------------------' )

        # Schedule the bot
        self.nextMinute = datetime.now().minute
        return

    def getHoldings( self, ticker ):
        quantity = 0.0

        if ( not config[ 'debug_enabled' ] ):
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
        if ( timediff.seconds > config[ 'max_seconds_between_updates' ] * 2 ):
            return False

        # Check for break in sequence of samples to minimum consecutive sample number
        position = len( self.data ) - 1
        if ( position >= self.min_consecutive_samples ):
            for x in range( 0, self.min_consecutive_samples ):
                timediff = datetime.strptime( self.data.iloc[ position - x ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) - datetime.strptime( self.data.iloc[ position - ( x + 1 ) ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) 

                if ( timediff.seconds > config[ 'max_seconds_between_updates' ] * 2 ):
                    print( 'Interruption found in price data, holding buys until sufficient samples are collected.' )
                    return False

        return True

    def updateDataPoints( self, now ):
        newRow = {}

        self.tradingLocked = False
        newRow[ 'timestamp' ] = now.strftime( "%Y-%m-%d %H:%M" )

        # Calculate moving averages and RSI values
        for ticker in config[ 'ticker_list' ]:
            if ( not config[ 'debug_enabled' ] ):
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
                self.data[ ticker + '_SMA_F' ] = self.data[ ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 0 ] ).mean()
                self.data[ ticker + '_SMA_S' ] = self.data[ ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 1 ] ).mean()
                self.data[ ticker + '_RSI' ] = talib.RSI( self.data[ ticker ].values, timeperiod = config[ 'rsi_period' ] )
                self.data[ ticker + '_MACD' ], self.data[ ticker + '_MACD_S' ], macd_hist = talib.MACD( self.data[ ticker ].values, fastperiod = config[ 'moving_average_periods' ][ 2 ], slowperiod = config[ 'moving_average_periods' ][ 3 ], signalperiod = config[ 'moving_average_periods' ][ 4 ] )

        return self.data

    def cancelOrder( self, order_id ):
        print( 'Swing and miss, cancelling order ' + order_id )
        
        if ( not config[ 'debug_enabled' ] ):
            try:
                cancelResult = r.cancel_crypto_order( order_id )
            except:
                print( 'Got exception canceling order, will try again.' )
                return False

        return True

    def sell( self, ticker, price ):
        # Sell only what previously bought
        availableCoin = self.portfolio[ ticker ].quantity

        if ( availableCoin > 0.0 ):
            # Price needs to be specified to no more precision than listed in min_price_increments. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            price = round( math.floor( price / self.min_price_increments[ ticker ] ) * self.min_price_increments[ ticker ], 7 )  
            profit = ( availableCoin * price ) - ( availableCoin * self.portfolio[ ticker ].price )

            print( 'Selling ' + str( ticker ) + ' ' + str( availableCoin ) + ' for $' + str( price ) + ' (profit: $' + str( round( profit, 2 ) ) + ')' )

            if ( config[ 'trades_enabled' ] ):
                if ( not config[ 'debug_enabled' ] ):
                    try:
                        sell_info = r.order_sell_crypto_limit( str( ticker ), availableCoin, price )
                    except:
                        print( 'Got exception trying to sell, aborting.' )
                        return

                self.portfolio[ ticker ].price = 0.0
                self.portfolio[ ticker ].quantity = 0.0
                self.portfolio[ ticker ].order_id = sell_info[ 'id' ]

        return

    def buy( self, ticker, price ):
        # If we are already in the process of a buy, don't submit another
        if ( self.available_cash < 1 ):
            print( 'Previous buy incomplete.' )
            return

        # Values need to be specified to no more precision than listed in min_price_increments. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
        price = round( math.floor( price / self.min_price_increments[ ticker ] ) * self.min_price_increments[ ticker ], 7 )
        quantity = ( self.available_cash - 0.25 ) / price
        quantity = round( math.floor( quantity / self.min_share_increments[ ticker ] ) * self.min_share_increments[ ticker ], 7 )
        print( 'Buying ' + str( ticker ) + ' ' + str( quantity ) + ' at $' + str( price ) )

        if ( config[ 'trades_enabled' ] ):
            if ( not config[ 'debug_enabled' ] ):
                try:
                    buy_info = r.order_buy_crypto_limit( str( ticker ), quantity, price )
                except:
                    print( 'Got exception trying to buy, aborting.' )
                    return

            self.portfolio[ ticker ].price = price
            self.portfolio[ ticker ].quantity = quantity
            self.portfolio[ ticker ].order_id = buy_info[ 'id' ]

        return

    def runBot( self ):
        while ( True ):
            now = datetime.now()

            # Is it time to spring into action?
            if ( now.minute == self.nextMinute ):
                self.data = self.updateDataPoints( now )

                # Determine when to run next
                futureTime = now + timedelta( 0, random.randint( config[ 'min_seconds_between_updates' ], config[ 'max_seconds_between_updates' ] - 1 ) )
                self.nextMinute = futureTime.minute

                # Refresh the cash amount available for trading
                if ( not config[ 'debug_enabled' ] ):
                    try:
                        me = r.account.load_phoenix_account( info=None )
                        self.available_cash = float( me[ 'crypto_buying_power' ][ 'amount' ] ) - config[ 'reserve' ]
                    except:
                        print( 'An exception occurred while reading available cash amount.' )
                        self.available_cash = -1.0
                else:
                    self.available_cash = random.randint( 1000, 5000 ) + config[ 'reserve' ]

                # Print state
                print( '-- ' + str( datetime.now().strftime( '%Y-%m-%d %H:%M' ) ) + ' ---------------------' )
                print( self.data.tail() )
                print( '-- Bot Status ---------------------------' )
                print( 'Next Run (minute): ' + str( self.nextMinute ).zfill( 2 ) )
                print( '$' + str( self.available_cash ) + ' available for trading' )
                print( 'Trading Locked: ' + str( self.tradingLocked ) )
                
                try:
                    open_orders = r.get_all_open_crypto_orders()
                except:
                    print( 'An exception occurred while retrieving list of open orders.' )
                    open_orders = []

                for ticker, coin_data in self.portfolio.items():
                    # Check if any of the open orders on Robinhood are ours (swing/miss)
                    for order in open_orders:
                        if ( order[ 'id' ] == coin_data.order_id and self.cancelOrder( coin_data.order_id ) ):
                            print( 'Order #' + str( coin_data.order_id ) + ' was not filled. Cancelled.' )
                            self.available_cash += order[ 'price' ] * order[ 'quantity' ]
                            self.portfolio[ ticker ].price = 0.0
                            self.portfolio[ ticker ].quantity = 0.0
                            self.portfolio[ ticker ].order_id = ''

                    print( str( ticker ) + ': ' + str( coin_data.quantity ), end = '' )
            
                    if ( coin_data.quantity > 0.0 ):
                        cost = coin_data.quantity * coin_data.price
                        sell_at = round( cost + ( cost * config[ 'sell_above_buy_price' ] ), 3 )
                        print( ' | Cost: $' + str( round( cost, 3 ) ) + ' | Current value: $' + str( round( self.data.iloc[ -1 ][ ticker ] * coin_data.quantity, 3 ) ) + ' | Selling at $' + str( sell_at ) )
                    else:
                        print( "\n" )

                # Save state
                with open( 'portfolio.pickle', 'wb' ) as f:
                    pickle.dump( self.portfolio, f )

                self.data.to_pickle( 'dataframe.pickle' )

                # We don't have enough consecutive data points to decide what to do
                if ( not self.checkConsecutive( now ) ):
                    time.sleep( 30 )
                    continue

                for ticker in config[ 'ticker_list' ]:
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
                                self.portfolio[ ticker ].quantity == 0.0 and
                                price < MAFast - ( MAFast * config[ 'buy_below_moving_average' ] ) and
                                RSI <= config[ 'rsi_buy_threshold' ]
                            ):
                            self.buy( ticker, price )

                        # Sell?
                        if ( (
                                self.portfolio[ ticker ].quantity > 0.0 and
                                price > self.portfolio[ ticker ].price + ( self.portfolio[ ticker ].price * config[ 'sell_above_buy_price' ] )
                                
                            ) or 
                            # Stop-loss
                            (
                                price < self.portfolio[ ticker ].price - ( self.portfolio[ ticker ].price * config[ 'stop_loss_threshold' ] )
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
