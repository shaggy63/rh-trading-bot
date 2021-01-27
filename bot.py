#!/usr/bin/python3 -u

# Crypto Trading Bot
# Version: 1.0
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
import threading

class asset:
    ticker = ''
    quantity = 0.0
    price = 0.0
    order_id = ''

    def __init__( self, ticker = '', quantity = 0.0, price = 0.0, order_id = '' ):
        self.ticker = ticker
        self.quantity = float( quantity )
        self.price = float( price )
        self.order_id = order_id

class bot:
    default_config = {
        'username': '',
        'password': '',
        'trades_enabled': False,
        'debug_enabled': False,
        'ticker_list': [],
        'trade_strategies': {
            'buy': 'rsi_sma',
            'sell': 'above_buy'
        },
        'buy_below_moving_average': 0.0075,
        'sell_above_buy_price': 0.01,
        'buy_amount_per_trade': 0,
        'moving_average_periods': {
            'sma_fast': 40,
            'sma_slow': 200,
            'macd_fast': 40,
            'macd_slow': 120,
            'macd_signal': 25
        },
        'rsi_period': 20,
        'rsi_buy_threshold': 39.5,
        'min_seconds_between_updates': 120,
        'min_seconds_between_updates': 300,
        'reserve': 0.0,
        'stop_loss_threshold': 0.2
    }
    data = pd.DataFrame()
    orders = {}

    min_share_increments = {}  #the smallest increment of a coin you can buy/sell
    min_price_increments = {}   #the smallest fraction of a dollar you can buy/sell a coin with
    min_consecutive_samples = 0
    
    available_cash = 0
    next_minute = 0
    is_trading_locked = False # used to determine if we have had a break in our incoming price data and hold buys if so

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

        if ( config[ 'rsi_period' ] > config[ 'moving_average_periods' ][ 'sma_fast' ] ):
            self.min_consecutive_samples = config[ 'rsi_period' ]
        else:
            self.min_consecutive_samples = config[ 'moving_average_periods' ][ 'sma_fast' ]
        
        for a_key, a_value in config.items():
            if ( a_key == 'username' or a_key == 'password' ):
                continue

            print( a_key.replace( '_', ' ' ).capitalize(), ': ', a_value, sep='' )

        print( '-- End Configuration --------------------' )

        if path.exists( 'orders.pickle' ):
            # Load state
            print( 'Loading previously saved state' )
            with open( 'orders.pickle', 'rb' ) as f:
                self.orders = pickle.load( f )
        else:
            # Start from scratch
            print( 'No state saved, starting from scratch' )

        # Load data points
        if ( path.exists( 'dataframe.pickle' ) ):
            self.data = pd.read_pickle( 'dataframe.pickle' )
        else:
            column_names = [ 'timestamp' ]

            for a_ticker in config[ 'ticker_list' ]:
                column_names.append( a_ticker )

            self.data = pd.DataFrame( columns = column_names )

        # Connect to RobinHood
        if ( not config[ 'debug_enabled' ] ):
            try:
                rh_response = r.login( config[ 'username' ], config[ 'password' ] )
            except:
                print( 'Got exception while attempting to log into RobinHood.' )
                exit()

        # Download RobinHood parameters
        for a_ticker in config[ 'ticker_list' ]:
            if ( not config[ 'debug_enabled' ] ):
                try:
                    result = r.get_crypto_info( a_ticker )
                    s_inc = result[ 'min_order_quantity_increment' ]
                    p_inc = result[ 'min_order_price_increment' ]
                except:
                    print( 'Failed to get increments from RobinHood.' )
                    exit()
            else:
                s_inc = 0.0001
                p_inc = 0.0001

            self.min_share_increments.update( { a_ticker: float( s_inc ) } )
            self.min_price_increments.update( { a_ticker: float( p_inc ) } )

        print( '-- Bot Ready ----------------------------' )

        return

    def is_data_integrity( self, now ):
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
                    print( 'Holding trades: interruption found in price data.' )
                    return False

        return True

    def get_new_data( self, now ):
        new_row = {}

        self.is_trading_locked = False
        new_row[ 'timestamp' ] = now.strftime( "%Y-%m-%d %H:%M" )

        # Calculate moving averages and RSI values
        for a_ticker in config[ 'ticker_list' ]:
            if ( not config[ 'debug_enabled' ] ):
                try:
                    result = r.get_crypto_quote( a_ticker )
                    new_row[ a_ticker ] = round( float( result[ 'mark_price' ] ), 3 )
                
                except:
                    print( 'An exception occurred retrieving prices.' )
                    self.is_trading_locked = True
                    return self.data
            else:
                new_row[ a_ticker ] = round( float( random.randint( 10, 100 ) ), 3 )

            self.data = self.data.append( new_row, ignore_index = True )

            if ( self.data.shape[ 0 ] > 0 ):
                self.data[ a_ticker + '_SMA_F' ] = self.data[ a_ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 'sma_fast' ] ).mean()
                self.data[ a_ticker + '_SMA_S' ] = self.data[ a_ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 'sma_slow' ] ).mean()
                self.data[ a_ticker + '_RSI' ] = talib.RSI( self.data[ a_ticker ].values, timeperiod = config[ 'rsi_period' ] )
                self.data[ a_ticker + '_MACD' ], self.data[ a_ticker + '_MACD_S' ], macd_hist = talib.MACD( self.data[ a_ticker ].values, fastperiod = config[ 'moving_average_periods' ][ 'macd_fast' ], slowperiod = config[ 'moving_average_periods' ][ 'macd_slow' ], signalperiod = config[ 'moving_average_periods' ][ 'macd_signal' ] )

        return self.data

    def cancel_order( self, order_id ):
        if ( not config[ 'debug_enabled' ] ):
            try:
                cancelResult = r.cancel_crypto_order( order_id )
            except:
                print( 'Got exception canceling order, will try again.' )
                return False

        return True

    # The two methods here below (conditional_buy, conditional_sell) implement various trading strategies
    def conditional_buy( self, ticker ):
        if ( self.available_cash < config[ 'buy_amount_per_trade' ] or self.is_trading_locked ):
            return False

        # MASlow = self.data.iloc[ -1 ][ ticker + '_SMA_S' ]
        # MACD = self.data.iloc[ -1 ][ ticker + '_MACD' ]
        # MACD_SIG = self.data.iloc[ -1 ][ ticker + '_MACD_S' ]

        # faster MA over slower MA in an uptrend, slower MA over faster MA in a downtrend
        # https://www.babypips.com/learn/forex/moving-average-crossover-trading

        if (
            ( 
                # Simple Fast-SMA and RSI 
                # Buy when price is below Fast-SMA and RSI is below threshold
                config[ 'trade_strategies' ][ 'buy' ] == 'rsi_sma' and

                # Make sure the data is valid
                not math.isnan( self.data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
                not math.isnan( self.data.iloc[ -1 ][ ticker + '_RSI' ] ) and

                # Is the current price below the Fast-SMA by the percentage defined in the config file?
                self.data.iloc[ -1 ][ ticker ] <= self.data.iloc[ -1 ][ ticker + '_SMA_F' ] - ( self.data.iloc[ -1 ][ ticker + '_SMA_F' ] * config[ 'buy_below_moving_average' ] ) and

                # RSI below the threshold
                self.data.iloc[ -1 ][ ticker + '_RSI' ] <= config[ 'rsi_buy_threshold' ] 
            )
            or
            (
                # Fast-SMA and RSI - Credits: https://medium.com/mudrex/rsi-trading-strategy-with-20-sma-on-mudrex-a26bd2ac039b
                # Buy when price crosses down Fast-SMA, RSI is above 50
                config[ 'trade_strategies' ][ 'buy' ] == 'rsi_sma_50' and
                
                # Make sure the data is valid
                not math.isnan( self.data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
                not math.isnan( self.data.iloc[ -2 ][ ticker + '_SMA_F' ] ) and
                not math.isnan( self.data.iloc[ -1 ][ ticker + '_RSI' ] ) and

                # Price crosses down Fast-SMA (i.e., it was greater than Fast-SMA before, and it went below in the last reading)
                self.data.iloc[ -1 ][ ticker ] > self.data.iloc[ -2 ][ ticker + '_SMA_F' ]  and
                self.data.iloc[ -1 ][ ticker ] <= self.data.iloc[ -1 ][ ticker + '_SMA_F' ] - ( self.data.iloc[ -1 ][ ticker + '_SMA_F' ] * config[ 'buy_below_moving_average' ] ) and
                
                # RSI above 50
                self.data.iloc[ -1 ][ ticker + '_RSI' ] > 50
            )
        ):
            # Values need to be specified to no more precision than listed in min_price_increments.
            # Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            price = round( math.floor( self.data.iloc[ -1 ][ ticker ] / self.min_price_increments[ ticker ] ) * self.min_price_increments[ ticker ], 7 )
            
            # How much to buy depends on the configuration
            quantity = ( self.available_cash if ( config[ 'buy_amount_per_trade' ] == 0 ) else config[ 'buy_amount_per_trade' ] ) / price
            quantity = round( math.floor( quantity / self.min_share_increments[ ticker ] ) * self.min_share_increments[ ticker ], 7 )
    
            print( 'Buying ' + str( ticker ) + ' ' + str( quantity ) + ' at $' + str( price ) )

            if ( config[ 'trades_enabled' ] and not config[ 'debug_enabled' ] ):
                try:
                    buy_info = r.order_buy_crypto_limit( str( ticker ), quantity, price )

                    # Add this new asset to our orders
                    self.orders[ buy_info[ 'id' ] ] = asset( ticker, quantity, price, buy_info[ 'id' ] )
                except:
                    print( 'Got exception trying to buy, aborting.' )
                    return False

            return True
        return False

    def conditional_sell( self, asset ):
        # Do we have enough of this asset to sell?
        if ( asset.quantity <= 0.0 or self.is_trading_locked ):
            return False

        if (
            (
                # Simple percentage
                config[ 'trade_strategies' ][ 'sell' ] == 'above_buy' and

                # Is the current price above the purchase price by the percentage set in the config file?
                self.data.iloc[ -1 ][ asset.ticker ] > asset.price + ( asset.price * config[ 'sell_above_buy_price' ] )
            )
            or
            (
                # Fast-SMA and RSI - Credits: https://medium.com/mudrex/rsi-trading-strategy-with-20-sma-on-mudrex-a26bd2ac039b
                # Sell when price crosses up Fast-SMA, RSI is below 60
                config[ 'trade_strategies' ][ 'sell' ] == 'rsi_sma_60' and

                # Make sure the data is valid
                not math.isnan( self.data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] ) and
                not math.isnan( self.data.iloc[ -2 ][ asset.ticker + '_SMA_F' ] ) and
                not math.isnan( self.data.iloc[ -1 ][ asset.ticker + '_RSI' ] ) and

                # Price crosses up Fast-SMA (i.e., it was less than Fast-SMA before, and it went above in the last reading)
                self.data.iloc[ -1 ][ asset.ticker ] < self.data.iloc[ -2 ][ asset.ticker + '_SMA_F' ]  and
                self.data.iloc[ -1 ][ asset.ticker ] >= self.data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] + ( self.data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] * config[ 'sell_above_buy_price' ] ) and
                
                # RSI below 50
                self.data.iloc[ -1 ][ asset.ticker + '_RSI' ] < 60 and

                # Price is greater than purchase price
                self.data.iloc[ -1 ][ asset.ticker ] > asset.price
            )
            or 
            (
                # Stop-loss: is the current price below the purchase price by the percentage defined in the config file?
                self.data.iloc[ -1 ][ asset.ticker ] < asset.price - ( asset.price * config[ 'stop_loss_threshold' ] )
            )
        ):   
            # Values needs to be specified to no more precision than listed in min_price_increments. 
            # Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            price = round( math.floor( self.data.iloc[ -1 ][ ticker ] / self.min_price_increments[ ticker ] ) * self.min_price_increments[ ticker ], 7 )
            profit = round( ( asset.quantity * price ) - ( asset.quantity * asset.price ), 3 )

            print( 'Selling ' + str( asset.ticker ) + ' ' + str( asset.quantity ) + ' for $' + str( price ) + ' (profit: $' + str( profit ) + ')' )

            if ( config[ 'trades_enabled' ] and not config[ 'debug_enabled' ] ):
                try:
                    sell_info = r.order_sell_crypto_limit( str( asset.ticker ), asset.quantity, price )

                    # Mark this asset as sold, the garbage collector (see 'run' method) will remove it from our orders at the next iteration
                    self.orders[ asset.order_id ].quantity = 0
                except:
                    print( 'Got exception trying to sell, aborting.' )
                    return False

            return True
        return False

    def run( self ):
        now = datetime.now()
        self.data = self.get_new_data( now )

        # Determine when to run next
        next_run = random.randint( config[ 'min_seconds_between_updates' ], config[ 'max_seconds_between_updates' ] )
        next_time = now + timedelta( 0, next_run )
        threading.Timer( next_run, self.run ).start()

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
        print( 'Next run (minute): ' + str( next_time.minute ).zfill( 2 ) )
        print( 'Buying power available: $' + str( self.available_cash ) )

        # We don't have enough consecutive data points to decide what to do
        self.is_trading_locked = not self.is_data_integrity( now )

        if ( len( self.orders ) > 0 ):
            # Do we have any open orders on the platform? (swing/miss)
            try:
                open_orders = r.get_all_open_crypto_orders()
            except:
                print( 'An exception occurred while retrieving list of open orders.' )
                open_orders = []

            print( '-- Orders -------------------------------' )

            for a_asset in list( self.orders.values() ):
                # Check if any of these open orders on Robinhood are ours
                is_asset_deleted = False
                for a_order in open_orders:
                    if ( a_order[ 'id' ] == a_asset.order_id and self.cancel_order( a_order[ 'id' ] ) ):
                        print( 'Order #' + str( a_order[ 'id' ] ) + ' (' + a_order[ 'side' ] + ' ' + a_asset.ticker + ') was not filled. Cancelled and removed from orders.' )
                        
                        # If this was a buy order, update the amount of available cash freed by the cancelled transaction
                        if ( a_order[ 'side' ] == 'buy' ):
                            self.available_cash += a_asset.price * a_asset.quantity

                        self.orders.pop( a_asset.order_id )
                        is_asset_deleted = True

                if ( not is_asset_deleted ):
                    # Print a summary of all our assets
                    print( str( a_asset.ticker ) + ': ' + str( a_asset.quantity ), end = '' )
            
                    if ( a_asset.quantity > 0.0 ):
                        cost = a_asset.quantity * a_asset.price
                        print( ' | Price: $' + str( round( a_asset.price, 3 ) ) + ' | Cost: $' + str( round( cost, 3 ) ) + ' | Current value: $' + str( round( self.data.iloc[ -1 ][ a_asset.ticker ] * a_asset.quantity, 3 ) ) )
                    else:
                        print( "\n" )

                    # Is it time to sell any of them?
                    self.conditional_sell( a_asset )

        # Buy?
        for a_ticker in config[ 'ticker_list' ]:
            self.conditional_buy( a_ticker )

        # Save state
        with open( 'orders.pickle', 'wb' ) as f:
            pickle.dump( self.orders, f )

        self.data.to_pickle( 'dataframe.pickle' )

if __name__ == "__main__":
    b = bot()
    b.run()