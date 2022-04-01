from datetime import datetime, date
from GoogleSheets import main
import time as t
from datetime import datetime, time
import alpaca_trade_api as tradeapi
import urllib
import json
import pandas as pd
import numpy as np
import re
try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+
from urllib.request import urlretrieve
import urllib
import time
from ConnectToBinanceAPINonUS import *
import sys
import os
import traceback
from collections import defaultdict
import smtplib
import subprocess, platform
import math

#print(math.floor(12.75))

### PARAMETERS TO SET
threshold_for_loss_pct = -5
pct_of_mvt_as_pct = 90
max_bid_ask_spread_as_pct = 0.3
devs = float(-2.1)
### 2 months worth of backtesting: [-0.1  0.4 -3. ], 


threshold_for_fall_as_pct = -1

initial_investment = 0.0181  # in btc 0.01760862

#starting_bnb = 0.09162331 #in btc
cumulative_investment = 0 
cumulative_profit = 0

threshold_for_sale_pct = 0.65
threshold_for_sale = (threshold_for_sale_pct / 100)

threshold_for_loss = (threshold_for_loss_pct / 100)

wait_time_to_sell_in_min = 48*60

#for correction function
#wait_time_to_buy_in_min = 15

check_enabled = False
threshold_for_check_as_pct = 0.05
time_to_check_in_seconds = 30

pct_of_mvt = pct_of_mvt_as_pct/100

scenario = str(threshold_for_sale_pct)+ str(max_bid_ask_spread_as_pct) + str(threshold_for_check_as_pct) + str(threshold_for_loss_pct)+ str(time_to_check_in_seconds) + str(devs) + str(pct_of_mvt_as_pct)

def SendEmail(Subject, Body):
    fromaddr = ''
    toaddrs = ''
    msg = 'Subject: {}\n\n{}'.format(Subject, Body)
    username = ''
    password = ''
    server = smtplib.SMTP('smtp.gmail.com:587')
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(username, password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

def BuyAndCheckPosition(symbol,A, symbol_ask_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs):
    
    BuyOnBinance(symbol, symbol_ask_price, qty_to_purchase)

    position_qty = 0

    t.sleep(2.5)

    counter = 0
    start_buy = time.time()
    while (int(position_qty) < int(qty_to_purchase)):
        #print("Position Not Filled Yet")
        t.sleep(2.5)

        try:
            position_qty = GetBalanceOnBinance(symbol)
            print("Position qty:" + str(position_qty))
            print("Position hypothetical:" + str(qty_to_purchase))

        except Exception as e:
            print(e)
            position_qty = 0
            counter = counter + 1

        end_buy = time.time()
        elapsed_time_buy = ((end_buy - start_buy) / 60)

        if ((elapsed_time_buy > 5) & (position_qty == 0)):
            
            CancelAllOpenOrders(symbol)

            symbol, symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs = ReturnOpportunity(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct, "opportunities_curr.csv", "opportunities_all.csv",check_enabled,devs)
            
            Purchase(symbol,symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)
            
        # else:
        #     symbol, symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs = ReturnOpportunity(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct, "opportunities_curr.csv", "opportunities_all.csv",check_enabled,devs)
        #     Purchase(symbol,symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)

    if (int(position_qty) == int(qty_to_purchase)):
        main("All!A:E", rows=[
        [symbol, str(datetime.datetime.now()), "Buy", symbol_ask_price, qty_to_purchase]])
        hold_and_sell(symbol,A, symbol_ask_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)
    else:
        print("Didn't purchase the correct amount - something went wrong")

def SellAndCheckPosition(symbol, new_symbol_price, qty_to_purchase):
    SellOnBinance(symbol, new_symbol_price, qty_to_purchase)

    open_orders = True
    while (open_orders == True):
        open_orders = AnyOpenOrders(symbol)
        t.sleep(2.5)

def Purchase(symbol, symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs):
    A = True
    global cumulative_investment
    cumulative_investment = initial_investment + cumulative_profit
    
    print(cumulative_investment)

    if ((symbol == 'BCH-BTC')|(symbol == 'DASH-BTC')|(symbol == 'ETH-BTC')|(symbol == 'XMR-BTC')):
        qty_v0 = cumulative_investment / symbol_ask_price
        qty_to_purchase = (math.floor(qty_v0*1000)/1000)
    
    elif ((symbol == 'BNB-BTC')|(symbol == 'FIL-BTC')|(symbol == 'LTC-BTC')|(symbol == 'ATOM-BTC')):
        qty_v0 = cumulative_investment / symbol_ask_price
        qty_to_purchase = (math.floor(qty_v0*100)/100)
    elif ((symbol == 'LINK-BTC')|(symbol == 'DOT-BTC')|(symbol == 'UNI-BTC')):
        qty_v0 = cumulative_investment / symbol_ask_price
        qty_to_purchase = (math.floor(qty_v0*10)/10)
    else:
        qty_to_purchase = math.floor((cumulative_investment / symbol_ask_price))
    

    #BuyAndCheckPosition(symbol,A, symbol_ask_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)
    
    main("All!A:E", rows=[
            [symbol, str(datetime.datetime.now()), "Buy", symbol_ask_price, qty_to_purchase]])

    hold_and_sell(symbol,A, symbol_ask_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)

def hold_and_sell(symbol, A, symbol_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs):
        new_symbol_price = 0
        print("bought " + symbol +"...")
        global cumulative_profit
        start = time.time()
        end = 0
        elapsed_time = 0
        prices = []
        prices_non_pct = []
        while (A == True):
            try:
               
                new_symbol_price = float(GetBidPriceOnBinanceOB(symbol))
                percent_change = (new_symbol_price -
                                    symbol_price) / symbol_price
                          
                prices.append(percent_change)
                prices_non_pct.append(new_symbol_price)


            except Exception as e:
                traceback.print_exc()     
                t.sleep(60)
                hold_and_sell(symbol, A, symbol_price, qty_to_purchase,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)

            #print(symbol + "Current stock price: " + str(new_symbol_price))
            
            print(symbol + " Percent Change: " + str(round(percent_change * 100, 2)))

            #subprocess.Popen("cls", shell=True).communicate()
            
                
            if (((percent_change >= pct_of_mvt*(abs(act_pct_from_mvg)/100)) & (new_symbol_price >= symbol_price))| ((percent_change <= threshold_for_loss)&(new_symbol_price>0))): # | (new_symbol_price <= 0.95*min_ask_price)

                try:

                    # SellAndCheckPosition(symbol, new_symbol_price, qty_to_purchase)
                    main("All!A:E", rows=[
                        [symbol, str(datetime.datetime.now()), "Sell", new_symbol_price, qty_to_purchase]])

                    purchase_value = qty_to_purchase * symbol_price
                    sale_value = qty_to_purchase*new_symbol_price

                    Fees = ((0.075)/100)*purchase_value + ((0.075)/100)*sale_value    

                    Profit = (sale_value - purchase_value) - Fees
                   
                    profit_pct = Profit/(qty_to_purchase * symbol_price)

                    cumulative_profit = cumulative_profit + Profit

                    SendEmail("Trade Position Closed: BTC " +
                              str(round(Profit, 8)) + "", "")

                    end = time.time()
                    elapsed_time = (end - start) / 60   

                    #Record in google sheets
                    main("Sheet14!A:I", rows=[[symbol, str(datetime.datetime.now()), qty_to_purchase,purchase_value,symbol_price, sale_value,new_symbol_price, Profit,elapsed_time,profit_pct,min(prices),max(prices),Average(prices),threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,threshold_for_sale_pct,threshold_for_loss_pct,threshold_for_check_as_pct,time_to_check_in_seconds,pct_of_mvt_as_pct,devs,scenario,act_pct_from_mvg ,act_bid_ask_spread,act_devs]])


                    symbol, symbol_ask_price, min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs = ReturnOpportunity(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct,"opportunities_curr.csv", "opportunities_all.csv",check_enabled,devs)
                    
                    Purchase(symbol,symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)
                except Exception as e:
                    traceback.print_exc()     
                    t.sleep(2.5)
            else:
                t.sleep(0.05)

A = True

# hold_and_sell('XRP-BTC', A, 0.00002809, 9, 0.00, -2.46993416, -0.07119972, -3.10532112
# )

# hold_and_sell('XMR-BTC', True, 0.007158, 2,0,-1.5,0,-2.25)

symbol, symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs = ReturnOpportunity(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct, "opportunities_curr.csv", "opportunities_all.csv",check_enabled,devs)

Purchase(symbol,symbol_ask_price,min_ask_price,act_pct_from_mvg,act_bid_ask_spread,act_devs)
