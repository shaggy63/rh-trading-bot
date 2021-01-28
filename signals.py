from config import config
from math import isnan

# Signals are defined in alphabetical order
class signals:
    def buy_sma_crossover_rsi( self, ticker, data ):
        # Moving Average Crossover with RSI Filter
        # Credits: https://trader.autochartist.com/moving-average-crossover-with-rsi-filter/
        # Buy when Fast-SMA crosses Slow-SMA fro below, and stays above for 3 consecutive readings, and RSI > buy threshold (50 suggested)

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -3 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -4 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -3 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -4 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_RSI' ] ) and

            # Fast-SMA crossed Slow-SMA and stays above
            data.iloc[ -1 ][ ticker + '_SMA_F' ] >= data.iloc[ -1 ][ ticker + '_SMA_S' ]  and
            data.iloc[ -2 ][ ticker + '_SMA_F' ] >= data.iloc[ -2 ][ ticker + '_SMA_S' ]  and
            data.iloc[ -3 ][ ticker + '_SMA_F' ] >= data.iloc[ -3 ][ ticker + '_SMA_S' ]  and
            data.iloc[ -4 ][ ticker + '_SMA_F' ] < data.iloc[ -4 ][ ticker + '_SMA_S' ]  and
            
            # ... and they diverge
            data.iloc[ -1 ][ ticker + '_SMA_F' ] - data.iloc[ -1 ][ ticker + '_SMA_S' ] >= data.iloc[ -2 ][ ticker + '_SMA_F' ] - data.iloc[ -2 ][ ticker + '_SMA_S' ] and
            
            # RSI above threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] > config[ 'rsi_threshold' ][ 'buy' ]
        )

    def buy_sma_rsi_threshold( self, ticker, data ):
        # Simple Fast-SMA and RSI 
        # Buy when price is below Fast-SMA and RSI is below threshold
        return (
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_RSI' ] ) and

            # Is the current price below the Fast-SMA by the percentage defined in the config file?
            data.iloc[ -1 ][ ticker ] <= data.iloc[ -1 ][ ticker + '_SMA_F' ] - ( data.iloc[ -1 ][ ticker + '_SMA_F' ] * config[ 'buy_below_moving_average' ] ) and

            # RSI below the threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] <= config[ 'rsi_threshold' ][ 'buy' ]
        )

    def sell_above_buy( self, asset, data ):
        # Simple percentage
        return (
            data.iloc[ -1 ][ asset.ticker ] > asset.price + ( asset.price * config[ 'profit_percentage' ] )
        )

    def sell_sma_crossover_rsi( self, asset, data ):
        # Moving Average Crossover with RSI Filter
        # Credits: https://trader.autochartist.com/moving-average-crossover-with-rsi-filter/

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -3 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -4 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -3 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -4 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_RSI' ] ) and

            # Fast-SMA crossed Slow-SMA and stays above
            data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] <= data.iloc[ -1 ][ asset.ticker + '_SMA_S' ]  and
            data.iloc[ -2 ][ asset.ticker + '_SMA_F' ] <= data.iloc[ -2 ][ asset.ticker + '_SMA_S' ]  and
            data.iloc[ -3 ][ asset.ticker + '_SMA_F' ] <= data.iloc[ -3 ][ asset.ticker + '_SMA_S' ]  and
            data.iloc[ -4 ][ asset.ticker + '_SMA_F' ] > data.iloc[ -4 ][ asset.ticker + '_SMA_S' ]  and
            
            # ... and they diverge
            data.iloc[ -1 ][ ticker + '_SMA_S' ] - data.iloc[ -1 ][ ticker + '_SMA_F' ] >= data.iloc[ -2 ][ ticker + '_SMA_S' ] - data.iloc[ -2 ][ ticker + '_SMA_F' ] and
            
            # RSI below threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] <= config[ 'rsi_threshold' ][ 'sell' ] and

            # Price is greater than purchase price by at least profit percentage
            data.iloc[ -1 ][ asset.ticker ] >= asset.price + (  asset.price * config[ 'profit_percentage' ] )
        )