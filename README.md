# CryptocurrencyTradingBot
a cryptocurrency bot that trades on large coin-specific dips relative to the rest of the market, complete with a backtesting module for the optimization of input parameters.

This bot looks for large relative falls in the price of a specific cryptocurrency based on the rest of the market movements, and triggers buy orders depending on whether a certain threshold is met for the movement, which is based on the standard deviation of each movement in the tracked currencies. To start, set the parameters in the top section of the main_fin.py, with the starting parameters set as:

threshold_for_loss_pct = -5 #i.e. 5 percent

pct_of_mvt_as_pct = 90 #sell when the price has made a 90% recovery

max_bid_ask_spread_as_pct = 0.3 #just eliminating currencies where the bid ask spread is too great

devs = float(-2.1) #How many standard deviations below the mean we're setting our "fall threshold" to be

Then update the private and public keys in ConnectToBinanceAPINonUS.py, or run it in simuluation mode by removing the references to Binance in the main_fin.py file.
The backtesting modules are designed to optimize the input parameters.
