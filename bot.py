#!/usr/bin/python3 -u

# Crypto Trading Bot
# Version: 0.8
# Credits: https://github.com/JasonRBowling/cryptoTradingBot/

import config as cfg
from datetime import datetime, timedelta
import math
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
    name = ''
    lastBuyOrder = ''
    timeBought = ''

    def __init__( self, name='' ):
        print( 'Creating coin ' + name )
        self.name = name
        self.purchasedPrice = 0.0
        self.numBought = 0.0
        self.lastBuyOrderID = ''
        self.timeBought = ''

class moneyBot:

    # See config.py ---------
    tradesEnabled = False
    buyBelowMA = 0.00
    sellAboveBuyPrice = 0.00
    movingAverageWindows = 0
    minSecondsBetweenUpdates = 0
    maxSecondsBetweenUpdates = 0
    coinList = []
    rsiWindow = 0
    rsiOversold = 0
    cashReserve = 0.0
    stopLoss = 0.0
    # -----------------------

    coinState = []
    minIncrements = {}  #the smallest increment of a coin you can buy/sell
    minPriceIncrements = {}   #the smallest fraction of a dollar you can buy/sell a coin with

    data = pd.DataFrame()
    boughtIn = False
    nextMinute = 0

    # used to determine if we have had a break in our incoming price data and hold buys if so
    buysLockedCounter = 0
    minConsecutiveSamples = 0
    pricesGood = False

    def __init__( self ):
        self.loadConfig()

        if path.exists( 'state.pickle' ):
            # Load state
            print( 'Loading previously saved state.' )
            with open( 'state.pickle', 'rb' ) as f:
                self.coinState = pickle.load( f )
        else:
            # Start from scratch
            print( 'No state saved, starting from scratch.' )
            self.coinState = []
            for c in self.coinList:
                self.coinState.append( coin( c ) )

        if path.exists( 'boughtIn.pickle' ):
            with open( 'boughtIn.pickle', 'rb' ) as f:
                self.boughtIn = pickle.load( f )

        # Load data points
        self.data = self.loadDataframe()

        # Connect to RobinHood
        try:
            r.login( self.rh_user, self.rh_pw )
        except:
            print( 'Got exception while attempting to log into RobinHood.' )
            exit()

        # Download RobinHood parameters
        for c in range(0, len(self.coinList)):

            try:
                result = r.get_crypto_info( self.coinList[ c ] )
                inc = result[ 'min_order_quantity_increment' ]
                p_inc = result[ 'min_order_price_increment' ]
            except:
                print( 'Failed to get increments from RobinHood.' )
                exit()

            self.minIncrements.update( {self.coinList[ c ]: float( inc )} )
            self.minPriceIncrements.update( {self.coinList[ c ]: float( p_inc )} )

        print( '--------------------------------------' )
        return

    def loadConfig( self ):
        print( 'Configuration ------------------------' )
        self.rh_user = cfg.rh[ 'username' ]
        self.rh_pw = cfg.rh[ 'password' ]

        self.buyBelowMA = float( cfg.config[ 'buyBelowMA' ] )
        print( 'Buy Limit: ' + str( self.buyBelowMA * 100) + '%' )

        self.sellAboveBuyPrice = float( cfg.config[ "sellAboveBuyPrice" ] )
        print( 'Sell Limit: ' + str( self.sellAboveBuyPrice * 100 ) + '%' )

        self.minSecondsBetweenUpdates = cfg.config[ 'minSecondsBetweenUpdates' ]
        self.maxSecondsBetweenUpdates = cfg.config[ 'maxSecondsBetweenUpdates' ]
        self.coinList = cfg.config[ 'coinList' ]
        self.rsiWindow = cfg.config[ 'rsiWindow' ]
        self.rsiOversold = cfg.config[ 'rsiOversold' ]
        self.movingAverageWindows = cfg.config[ 'movingAverageWindows' ]

        # When to run next (random minute)
        futureTime = datetime.now() + timedelta( 0, random.randint( self.minSecondsBetweenUpdates, self.maxSecondsBetweenUpdates - 1 ) )
        self.nextMinute = futureTime.minute
        print( 'Next Run (minute): ' + str( self.nextMinute ) )

        self.tradesEnabled = cfg.config[ 'tradesEnabled' ]
        print( 'Trades enabled: ' + str( self.tradesEnabled ) )

        if ( self.rsiWindow > self.movingAverageWindows ):
            self.minConsecutiveSamples = self.rsiWindow
        else:
            self.minConsecutiveSamples = self.movingAverageWindows
        print( 'Consecutive prices required: ' + str( self.minConsecutiveSamples ) )

        self.cashReserve = cfg.config[ 'cashReserve' ]
        print( 'Cash Reserve: ' + str( self.cashReserve ) )

        self.stopLoss = cfg.config[ 'stopLoss' ]
        print( 'Stop-Loss: ' + str( self.stopLoss * 100 ) + '%' )

        print( '--------------------------------------' )
        return

    def getPrices( self ):
        prices = {}

        for c in self.coinList:
            try:
                result = r.get_crypto_quote( c )
                price = result[ 'mark_price' ]
            except:
                print( 'An exception occurred retrieving prices.' )
                return {}

            prices.update( {c: float( price )} )

        return prices

    def saveState( self ):
        with open( 'state.pickle', 'wb' ) as f:
            pickle.dump( self.coinState, f )

        with open( 'boughtIn.pickle', 'wb' ) as f:
            pickle.dump( self.boughtIn, f )

        self.data.to_pickle( 'dataframe.pickle' )

    def getHoldings( self, ticker ):
        quantity = 0.0
        try:
            result = r.get_crypto_positions()
            for t in range( 0, len( result ) ):
                symbol = result[ t ][ 'currency' ][ 'code' ]
                if ( symbol == ticker ):
                    quantity = result[ t ][ 'quantity' ]
        except:
            print( 'Got exception while getting holdings from RobinHood.' )
            quantity = -1.0

        return float( quantity )

    def getCash( self ):
        try:
            me = r.account.load_phoenix_account( info=None )
            cash = float( me[ 'crypto_buying_power' ][ 'amount' ] )
        except:
            print( 'An exception occurred getting cash amount.' )
            return -1.0

        if cash - self.cashReserve < 0.0:
            return 0.0
        else:
            return cash

    def checkConsecutive( self, now ):
        # Check for break between now and last sample
        timediff = now - self.data.iloc[ -1 ][ 'exec_time' ]

        if ( timediff.seconds > self.maxSecondsBetweenUpdates ):
            print( 'It has been too long since last price point gathered, holding buys.' )
            return False

        if ( self.data.shape[ 0 ] <= 1 ):
            return True

        # Check for break in sequence of samples to minimum consecutive sample number
        position = len( self.data ) - 1
        if ( position >= self.minConsecutiveSamples ):
            for x in range( 0, self.minConsecutiveSamples ):
                timediff = self.data.iloc[position - x]['exec_time'] - self.data.iloc[position - (x + 1)]['exec_time']

                if ( timediff.seconds > self.maxSecondsBetweenUpdates ):
                    print( 'Interruption found in price data, holding buys until sufficient samples are collected.' )
                    return False

        return True

    def updateDataframe( self, now ):
        # We check this each time, so we don't need to lock for more than two cycles. It will set back to two if it fails on the next pass.
        if ( self.data.shape[ 0 ] > 0 and self.checkConsecutive( now ) == False ):
            self.buysLockedCounter = 2

        # Tick down towards being able to buy again, if not there already.
        if ( self.buysLockedCounter > 0 ):
            self.buysLockedCounter -= 1

        rowdata = {}

        currentPrices = self.getPrices()
        if ( len( currentPrices ) == 0 ):
            print( 'Exception received getting prices: ignoring data, locking buys' )
            self.buysLockedCounter = 2
            self.pricesGood = False
            return self.data

        self.pricesGood = True
        rowdata.update( {'exec_time': now} )

        for c in self.coinList:
            rowdata.update( {c: currentPrices[ c ]} )

        self.data = self.data.append( rowdata, ignore_index=True )

        # Calculate moving averages and RSI values
        for c in self.coinList:
            self.data[ str( c + '-MA' ) ] = self.data[ c ].shift( 1 ).rolling( window = self.movingAverageWindows ).mean()
            self.data[ str( c + '-RSI' )] = talib.RSI( self.data[ c ].values, timeperiod = self.rsiWindow )

        return self.data

    def loadDataframe( self ):
        if ( path.exists( 'dataframe.pickle' ) ):
            self.data = pd.read_pickle( 'dataframe.pickle' )
        else:
            column_names = ['exec_time']

            for c in self.coinList:
                column_names.append(c)

            self.data = pd.DataFrame( columns=column_names )

        return self.data        

    def roundDown( self, x, a ):
        return math.floor( x/a ) * a

    def printState( self ):
        availableCash = self.getCash() - self.cashReserve
        print( str( datetime.now()) + ' ---------------------------------------' )
        print( self.data.tail() )
        print( '$' + str( availableCash ) + ' available for trading (' + str( availableCash + self.cashReserve ) + ' - ' + str( self.cashReserve ) + ' reserve)' )
        print( 'Buys Locked: ' + str( self.buysLockedCounter > 0 ) )
        print( 'Next Run (minute): ' + str( self.nextMinute ) )

        for c in self.coinState:
            print( str( c.name ) + ': ' + str( c.numBought ) )
            
            if ( c.numBought > 0.0 ):
                print( 'Cost: $' + str( c.numBought * c.purchasedPrice ) )
                print( 'Current value: $' + str( round( self.data.iloc[ -1 ][ c.name ] * c.numBought, 2 ) ) )

    def cancelOrder(self, orderID):
        print( 'Swing and miss, cancelling order ' + orderID )
        try:
            cancelResult = r.cancel_crypto_order( orderID )
            print( str( cancelResult ) )
        except:
            print( 'Got exception canceling order, will try again.' )
            return False

        return True

    def sell( self, c, price ):
        if ( self.boughtIn == False ):
            # A previous sell has not completed. We are marked as not in the market but still holding coin, abort sale.
            print( 'Previous sale incomplete.' )
            return

        # Sell only what previously bought
        coinHeld = self.coinState[ c ].numBought

        if ( coinHeld > 0.0 ):
            # Price needs to be specified to no more precision than listed in minPriceIncrement. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            minPriceIncrement = self.minPriceIncrements[ self.coinState[ c ].name ]
            price = round( self.roundDown( price, minPriceIncrement ), 7 )
            profit = ( coinHeld * price ) - ( coinHeld * self.coinState[ c ].purchasedPrice )

            print( 'Selling ' + str( self.coinState[ c ].name ) + ' ' + str( coinHeld ) + ' for $' + str( price ) + ' (profit: $' + str( round( profit, 2 ) ) + ')' )

            if ( self.tradesEnabled == True ):
                try:
                    sellResult = r.order_sell_crypto_limit( str( self.coinList[ c ] ), coinHeld, price )
                    self.coinState[c].lastSellOrder = sellResult[ 'id' ]
                except:
                    print( 'Got exception trying to sell, cancelling.' )
                    return

                self.coinState[c].purchasedPrice = 0.0
                self.coinState[c].numBought = 0.0
                self.coinState[c].lastBuyOrderID = ""
                self.coinState[c].timeBought = ""
                self.boughtIn = False

        return

    def buy(self, c, price):

        #we are already in the process of a buy, don't submit another
        if self.boughtIn == True:
            print("Previous buy incomplete.")
            return

        availableCash = self.getCash()
        if availableCash == -1:
            print("Got an exception checking for available cash, canceling buy.")
            return

        # Deduct the reserve
        availableCash -= self.cashReserve

        print("$" + str(availableCash) + "  available for trading")

        if (availableCash > 1.0):
            minPriceIncrement = self.minPriceIncrements[self.coinState[c].name]
            #price needs to be specified to no more precision than listed in minPriceIncrement. Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
            price = round(self.roundDown(price, minPriceIncrement), 7)
            shares = (availableCash - .25)/price
            minShareIncrement = self.minIncrements[self.coinState[c].name]
            shares = round(self.roundDown(shares, minShareIncrement), 8)
            sellAt = price + (price * self.sellAboveBuyPrice)
            print("Buying " + str(shares) + " shares of " + self.coinList[c] + " at " + str(price) + " selling at " + str(round(sellAt, 2)))

            if self.tradesEnabled == True:
                try:
                    buyResult = r.order_buy_crypto_limit(str(self.coinList[c]), shares, price)
                    self.coinState[c].lastBuyOrderID = buyResult['id']
                except:
                    print("Got exception trying to buy, cancelling.")
                    return

                print("Bought " + str(shares) + " shares of " + self.coinList[c] + " at " + str(price) + " selling at " + str(round(sellAt, 2)))
                self.coinState[c].purchasedPrice = price
                self.coinState[c].timeBought = str( datetime.now() )
                self.coinState[c].numBought = shares
                self.boughtIn = True

        return


    def runBot( self ):
        while ( True ):
            now = datetime.now()

            # Is it time to spring into action?
            if ( now.minute == self.nextMinute ):
                self.data = self.updateDataframe( now )

                # Determine when to run next
                futureTime = datetime.now() + timedelta( 0, random.randint( self.minSecondsBetweenUpdates, self.maxSecondsBetweenUpdates - 1 ) )
                self.nextMinute = futureTime.minute

                # Check for swing/miss on each coin here
                if self.boughtIn == True:
                    for c in self.coinState:
                        if ( c.timeBought != '' ):
                            dt_timeBought = datetime.strptime( c.timeBought, '%Y-%m-%d %H:%M:%S.%f' )
                            timeDiffBuyOrder = now - dt_timeBought
                            coinHeld = self.getHoldings( c.name )
                            if coinHeld == -1:
                                print( 'Error trying to get holdings while checking for swing/miss, cancelling.' )
                            elif ( timeDiffBuyOrder.total_seconds() > 3600 and coinHeld < c.numBought ):
                                cancelled = self.cancelOrder( c.lastBuyOrderID )
                                if ( cancelled == True ):
                                    c.purchasedPrice = 0.0
                                    c.numBought = 0.0
                                    c.lastBuyOrderID = ""
                                    c.timeBought = ""
                                    self.boughtIn = False

                for c in range( 0, len( self.coinList ) ):
                    # Look at values in last row only
                    price = self.data.iloc[ -1 ][ self.coinList[ c ] ]
                    movingAverage = self.data.iloc[ -1 ][ str( self.coinList[ c ] ) + '-MA' ]
                    RSI = self.data.iloc[ -1 ][ str( self.coinList[ c ] ) + '-RSI' ]

                    if ( math.isnan( movingAverage ) == False and math.isnan( RSI ) == False and self.pricesGood == True ):
                        # Buy?
                        if (
                                self.buysLockedCounter == 0 and
                                price < movingAverage - (movingAverage * self.buyBelowMA) and
                                self.coinState[c].numBought == 0.0 and
                                RSI <= self.rsiOversold
                            ):
                            self.buy( c, price )

                        # Sell?
                        if ( (
                                price > self.coinState[c].purchasedPrice + (self.coinState[c].purchasedPrice * self.sellAboveBuyPrice) and
                                self.coinState[c].numBought > 0.0
                            ) or 
                            (
                                price < self.coinState[ c ].purchasedPrice - ( self.coinState[ c ].purchasedPrice * self.stopLoss )
                            ) ):
                            self.sell( c, price )

                self.printState()
                self.saveState()
                time.sleep(60)

        time.sleep(30)

def main():
    m = moneyBot()
    m.runBot()

if __name__ == "__main__":
    main()
