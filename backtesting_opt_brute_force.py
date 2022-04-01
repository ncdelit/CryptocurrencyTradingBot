from datetime import datetime, date
from GoogleSheets import main
import time as t
import datetime
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
import sys
import os
import traceback
from collections import defaultdict
import smtplib
from concurrent.futures import ThreadPoolExecutor
import subprocess, platform
from multiprocessing import pool
import math
from ConnectToBinanceAPINonUS import *
import scipy.optimize as optimize
import optuna

pd.options.mode.chained_assignment = None  # default='warn'

act_devs_all = []
act_pct_from_mvg_all = []

all_ask_price_min = []

reg_data = []
trade_data = []

def process(params):
    #global a
    trade_counter = 0
    loss_counter = 0
    global no_of_trades
    global cumulative_profit
    global elp_time
    pct_chg_all = []

    # elp_time = 178.4500381

    initial_investment = 1000 # in btc
    #init_investment_in_usd = initial_investment*58865
    cumulative_investment = 0
    cumulative_profit = 0
    
    times = []
   
    a = True

    threshold_for_loss = params[0]
    pct_of_mvt = params[1]
    devs = params[2]
    window = int(params[3])

    max_elapsed = 0

    elp_time =  ddf['date'].min() + datetime.timedelta(minutes = window)
    
    # ddf['ask_price_mvg'] = ddf.groupby('symbol')['open'].transform(lambda x: x.rolling(window, 1).mean().shift().bfill())
    start_check = time.time()
    ddf['ask_price_mvg'] = ddf.groupby('symbol')['open'].transform(lambda x: x.ewm(span=window).mean().shift().bfill())

    ddf['pct_from_mvg'] = ((ddf['open'] - ddf['ask_price_mvg'])/ddf['ask_price_mvg'])*100

    ddf['avg_pct_from_mvg'] = ddf.groupby('date')['pct_from_mvg'].transform('mean')

    ddf['std_dev'] = ddf.groupby('date')['pct_from_mvg'].transform('std')

    # ddf['ask_price_min'] = ddf.groupby('symbol')['open'].transform(lambda x: x.rolling(window, 1,closed="left").min())

    ddf['ask_price_min'] = ddf.groupby('symbol')['open'].transform(lambda x: x.rolling(window, 1).min().shift().bfill())

    ddf['pct_from_min'] = (ddf['open'] - ddf['ask_price_min'])/ddf['ask_price_min']

    ddf['no_of_std_devs'] = (ddf['pct_from_mvg'] - ddf['avg_pct_from_mvg'])/ddf['std_dev']
    end_check = time.time()
    elapsed_check = end_check - start_check
    # print(elapsed_check/60)
    #ddf.to_csv('alldownloaded.csv', index=False, mode='w+')
    #ddf.to_csv('test_new_v3.csv', index=False, mode='w+')
    falls = []
    trade_data = []
    while (a == True):
        #print(a)
        #print(threshold_for_loss)
        
        ddf_filtered = ddf[(ddf['no_of_std_devs'].values <= devs) & (ddf['date'].values > elp_time)&(ddf['pct_from_mvg'].values*-1*pct_of_mvt > 0.2)] #&(ddf['avg_pct_from_mvg'] > -5)&(ddf['no_of_std_devs'] > -3.3)

       
        try:
            symbol_to_return = str(ddf_filtered.iloc[0]['symbol'])
            
            purchase_price = float(ddf_filtered.iloc[0]['open'])
            pct_from_min = float(ddf_filtered.iloc[0]['pct_from_min'])
            date = ddf_filtered.iloc[0]['date']
            #print("bought @" + str(date))
            act_pct_from_mvg = float(ddf_filtered.iloc[0]['pct_from_mvg']) / 100
            falls.append(act_pct_from_mvg)
            act_devs = float(ddf_filtered.iloc[0]['no_of_std_devs'])

            cumulative_investment = initial_investment + cumulative_profit
            #cumulative_investment = initial_investment

            if ((symbol_to_return == 'BCH-BTC')|(symbol_to_return == 'DASH-BTC')|(symbol_to_return == 'ETH-BTC')|(symbol_to_return == 'XMR-BTC')):
                qty_v0 = cumulative_investment / purchase_price
                bought_qty = (math.floor(qty_v0*1000)/1000)
    
            elif ((symbol_to_return == 'BNB-BTC')|(symbol_to_return == 'FIL-BTC')|(symbol_to_return == 'LTC-BTC')|(symbol_to_return == 'ATOM-BTC')):
                qty_v0 = cumulative_investment / purchase_price
                bought_qty = (math.floor(qty_v0*100)/100)
            elif ((symbol_to_return == 'LINK-BTC')|(symbol_to_return == 'DOT-BTC')|(symbol_to_return == 'UNI-BTC')):
                qty_v0 = cumulative_investment / purchase_price
                bought_qty = (math.floor(qty_v0*10)/10)
            else:
                qty_v0 = cumulative_investment / purchase_price
                bought_qty = (math.floor(qty_v0*1000)/1000)

            #print(bought_qty)
            bought = bought_qty * purchase_price
            
            ddf_filtred_for_purchase = ddf[(ddf['symbol'].values == symbol_to_return) & (ddf['date'].values > date)]
        
            #date_v2 = float(ddf_filtred_for_purchase.iloc[0]['date']) 

            ddf_filtred_for_purchase['pct_chg_frm_prch'] =  (ddf_filtred_for_purchase['open'] - purchase_price)/purchase_price

            ddf_filtered_for_price_change = ddf_filtred_for_purchase[(ddf_filtred_for_purchase['pct_chg_frm_prch'].values >= pct_of_mvt * (abs(act_pct_from_mvg)))] 

            #|((ddf_filtred_for_purchase['date'] - date) >12*60)

            ddf_filtered_for_price_change_loss = ddf_filtred_for_purchase[(ddf_filtred_for_purchase['pct_chg_frm_prch'].values <= threshold_for_loss)]

            #print(ddf_filtered_for_price_change_loss)

            if not ddf_filtered_for_price_change.empty:
                date_gain = ddf_filtered_for_price_change.iloc[0]['date']

                if not ddf_filtered_for_price_change_loss.empty: #i .e. there is a movement which exceeds loss threshold
                    date_loss = ddf_filtered_for_price_change_loss.iloc[0]['date']

                    if (date_gain < date_loss): #i.e. there is a gain eventually, and that gain is before a loss
                        #print("gain before loss")
                        date_fin = date_gain
                    else:
                        #print("loss before gain")
                        date_fin = date_loss
                else: #i.e. there is no loss movement which exceeds loss threshold
                    #print("no loss movement that exceeds loss threshold")
                    date_fin = date_gain
            else:
                if not ddf_filtered_for_price_change_loss.empty: #i.e. there is no gain movement above threshhold, and there is a loss movement which exceeds threshold
                    date_loss = ddf_filtered_for_price_change_loss.iloc[0]['date']
                    #print("there is a loss and no gain")
                    date_fin = date_loss
                else:
                    #print("No loss or no gain at all")
                    #print(max(ddf_filtred_for_purchase['date']))
                    #print("unsold at end of simulation")
                    date_fin = max(ddf_filtred_for_purchase['date'])
            
                #print(date_fin)

            #print(purchase_price)

            # print(ddf_filtered.head(1))
            # print(ddf_filtred_for_purchase.head(1))
            # print(ddf_filtered_for_price_change.head(1))

            #if not ddf_filtered_for_price_change.empty:
            elaps_max = max_elapsed*60
            
            # if (((date_fin - date) > elaps_max)):
            #     time_chk = ddf[(ddf['date'] >= date + elaps_max)]
            #     date_fin = time_chk.iloc[0]['date']
            
            #if (((date_fin - date) > elaps_max)&((pct_of_mvt * (abs(act_pct_from_mvg)) < 0.025)))

            ddf_fin = ddf_filtred_for_purchase[(ddf_filtred_for_purchase['date'].values == date_fin)]
            #print(ddf_fin.iloc[0])
            #print(ddf_fin)
            #print(ddf_fin)
            #no_of_trades = no_of_trades + 1
            symbol_to_return = str(ddf_fin.iloc[0]['symbol'])
            #print(symbol_to_return)
            #date_v3 = float(ddf_fin.iloc[0]['date'])

            df_betw = ddf[(ddf['date'].values <= date_fin) & (ddf['date'].values >= date)&(ddf['symbol'].values== symbol_to_return)]

            all_prices = ((df_betw['open'] - purchase_price) / purchase_price) * 100

            all_prices_non_pct = df_betw['open']

            sale_price = float(ddf_fin.iloc[0]['open'])
            #print(sale_price)
            sold = sale_price * bought_qty
            fees = ((0.075)/100)*bought + ((0.075)/100)*sold   
            profit = (sold - bought) - fees
            # print(sale_price)
            # print(purchase_price)
            pct_chg = (profit / bought)
            #pct_changes.append(pct_chg)
            cumulative_profit = cumulative_profit + profit
            date_sold = (ddf_fin.iloc[0]['date'])
            #date = (date_fin - date) / 60
            times.append(date)
            #print(pct_chg*100)
            
            # print("")
            # print("Coin: " + symbol_to_return)
            # print("pct_from_min: " + str(float(pct_from_min)))
            # print("Buy Price: " + str(purchase_price))
            # print("Bought: " + str(bought))
            # print("Bought: " + str(bought_qty))
            # print("Sold: " + str(sold))
            # print("Sold Price: " + str(sale_price))
            # print("pct chg: " + str(pct_chg*100))
            # print("Total Profit: $" + str(round(cumulative_profit, 4)))
            # #print("date: " + str(date))
            # print("Min price: " + str(min(round(all_prices, 2))) + str("%"))
            # print("Profit: " + str(profit))
            # print("Date :" + str(date))
            # print("Act devs :" + str(act_devs))
            # print("Bought_date :" + str(date))
            # print("Sold_date :" + str(date_fin))

            # print("Buy Price: " + str(purchase_price))
            # print("Bought: " + str(bought))
            # print("Bought: " + str(bought_qty))
            # print("Sold: " + str(sold))
            # print("Sold Price: " + str(sale_price))
            # print("pct chg: " + str(pct_chg*100))
            # print("Total Profit: $" + str(round(cumulative_profit, 4)))
            # no_of_days = date/(24*60)
            # no_of_trades_per_day = (no_of_trades / no_of_days)
            # no_of_trades_per_month = no_of_trades_per_day * 30
            # avg_prof = Average(pct_changes)
            # profit_per_day = cumulative_profit / no_of_days
            # profit_per_month = profit_per_day * 30
            # bal_end = init_investment_in_usd*math.pow(((1 + avg_prof)),no_of_trades_per_month)
            trade_data.append(
                {
                'symbol': symbol_to_return,
                'pct_from_min': pct_from_min,
                'profit_pct':  pct_chg,
                'date': date,
                'month_year': str(date.month) +"-"+ str(date.year),
                'week_year': str(date.isocalendar()[1]) +"-"+ str(date.year),
                'act_fall_from_pct': act_pct_from_mvg,
                'act_devs': act_devs,
                'pct_from_min': pct_from_min,
                'pnl':profit

                }
            )

            df2 = pd.DataFrame(trade_data)
            pivoted_trade_data_w = df2.groupby('week_year')['pnl'].agg(['sum'])
            pivoted_trade_data_m = df2.groupby('month_year')['pnl'].agg(['sum'])
            #df2.to_csv('in_sample_trades_sept_oct.csv', index=False, mode='w+')
            #pivoted_trade_data = df2.groupby('symbol')['date'].agg(['count'])
            #pivoted_trade_data = df2.groupby('symbol')['pnl'].agg(['sum'])

            # print("Coin: " + symbol_to_return)
            # print("Buy Price: " + str(purchase_price))
            # print("Bought: " + str(bought))
            # print("Sold: " + str(sold))
            # print("Sold Price: " + str(sale_price))
            # print("pct chg: " + str(pct_chg*100))
            # print("Total Profit: $" + str(round(cumulative_profit, 4)))
            # print("Total number of trades per day: " + str(round(no_of_trades_per_day, 2)))
            # print("Project profit per month: $"+str(round((bal_end - init_investment_in_usd),4)))
            # print("date:" + str(date_fin))
            # print("")
            # act_devs_all.append(act_devs)
            # act_pct_from_mvg_all.append(act_pct_from_mvg)
            pct_chg_all.append(pct_chg)
            #all_ask_price_min.append(min_price)
            #print(act_pct_from_mvg)
            
            #print(date_fin)
            elp_time = date_fin
            trade_counter = trade_counter + 1
            if (pct_chg < 0):
                loss_counter = loss_counter + 1
            
            # if (cumulative_profit <= -0.5*initial_investment):
            #     print("safety kicks in")
            #     break

        except Exception as e:
            a = False
            
            #traceback.print_exc() 
            #traceback.print_exc()
    print(pivoted_trade_data_m)
    print("")
    print(str(cumulative_profit) + " " + str(threshold_for_loss)+ " " + str(pct_of_mvt)+ " " + str(devs)+ " " + str(window))
    print(str(Average(times)) + " = average hours")
    print(str(max(times)) + " = max hours")
    print("no. of trades: " + str(trade_counter))
    print("no. of losses: " + str(loss_counter))
    print("Avg profit: " + str(round(Average(pct_chg_all)*100,2)))
    print("Avg falls: " + str(round(Average(falls)*100,2)))
    
    SQN = (math.sqrt(df2['date'].count())*df2['pnl'].mean())/df2['pnl'].std()


    reg_data.append(
        {
            'Return': cumulative_profit,
            'threshold_for_loss': threshold_for_loss,
            'pct_of_mvt':  pct_of_mvt,
            'devs': devs,
            'window':window,
            'average_trade_dur': Average(times),
            'no_of_trades': trade_counter,
            'no_of_losses': loss_counter,
            'avg_profit': Average(pct_chg_all),
            'hours_max': max_elapsed,
            'SQN':SQN,
            'min_weekly':pivoted_trade_data_w['sum'].min(), 
            'min_monthly': pivoted_trade_data_m['sum'].min()
        }
    )
    
    df = pd.DataFrame(reg_data)
    df.to_csv('params_'+str(t0)+".csv", index=False, mode='w+')
    # end_check = time.time()
    # elapsed_check = end_check - start_check
    print(elapsed_check/60)
    return -cumulative_profit
 
ddf = pd.read_csv("more_historic_data_v2.csv")
ddf['date'] = pd.to_datetime(ddf['date'], infer_datetime_format=True)

#OS 1
# ddf = ddf[((pd.DatetimeIndex(ddf['date']).month ==9)|(pd.DatetimeIndex(ddf['date']).month ==10)|(pd.DatetimeIndex(ddf['date']).month ==11))&(pd.DatetimeIndex(ddf['date']).year ==2020)]

#OS 2
# ddf = ddf[(((pd.DatetimeIndex(ddf['date']).month ==12))&(pd.DatetimeIndex(ddf['date']).year ==2020))|(((pd.DatetimeIndex(ddf['date']).month ==1)|(pd.DatetimeIndex(ddf['date']).month ==2))&(pd.DatetimeIndex(ddf['date']).year ==2021))]

ddf = ddf.astype({"symbol": 'category'})

# IS 1
# ddf = ddf[(((pd.DatetimeIndex(ddf['date']).month ==3)|(pd.DatetimeIndex(ddf['date']).month ==4)|(pd.DatetimeIndex(ddf['date']).month ==5)|(pd.DatetimeIndex(ddf['date']).month ==6)|(pd.DatetimeIndex(ddf['date']).month ==7)|(pd.DatetimeIndex(ddf['date']).month ==8))&(pd.DatetimeIndex(ddf['date']).year ==2020))]

# IS 2
# ddf = ddf[(((pd.DatetimeIndex(ddf['date']).month ==6)|(pd.DatetimeIndex(ddf['date']).month ==7)|(pd.DatetimeIndex(ddf['date']).month ==8)|(pd.DatetimeIndex(ddf['date']).month ==9)|(pd.DatetimeIndex(ddf['date']).month ==10)|(pd.DatetimeIndex(ddf['date']).month ==11))&(pd.DatetimeIndex(ddf['date']).year ==2020))]

# IS 3
ddf = ddf[(((pd.DatetimeIndex(ddf['date']).month ==9)|(pd.DatetimeIndex(ddf['date']).month ==10)|(pd.DatetimeIndex(ddf['date']).month ==11)|(pd.DatetimeIndex(ddf['date']).month ==12))&(pd.DatetimeIndex(ddf['date']).year ==2020))|((((pd.DatetimeIndex(ddf['date']).month ==1)|(pd.DatetimeIndex(ddf['date']).month ==2))&(pd.DatetimeIndex(ddf['date']).year ==2021)))]

# PLO
# ddf = ddf[(((pd.DatetimeIndex(ddf['date']).month ==12))&(pd.DatetimeIndex(ddf['date']).year ==2020))|
# (((pd.DatetimeIndex(ddf['date']).month ==1)|(pd.DatetimeIndex(ddf['date']).month == 2)|(pd.DatetimeIndex(ddf['date']).month ==3)|(pd.DatetimeIndex(ddf['date']).month ==4)|(pd.DatetimeIndex(ddf['date']).month ==5))&(pd.DatetimeIndex(ddf['date']).year ==2021))]


ddf = ddf[(ddf['open'] > 0)]

ddf = ddf.sort_values(by=['date'])

del ddf['unix']
del ddf['high']
del ddf['low']
del ddf['close']
del ddf['Volume ADA']
del ddf['Volume USDT']
del ddf['tradecount']
del ddf['Volume BNB']
del ddf['Volume BTC']
del ddf['Volume BTT']
del ddf['Volume DASH']
del ddf['Volume EOS']
del ddf['Volume ETC']
del ddf['Volume ETH']
del ddf['Volume LINK']
del ddf['Volume LTC']
del ddf['Volume NEO']
del ddf['Volume TRX']
del ddf['Volume XLM']
del ddf['Volume XRP']
del ddf['Volume ZEC']
del ddf['Volume QTUM']
del ddf['Volume XMR']
#-0.15 0.6000000000000001 -2.9 120
#print(ddf)
t0 = str(time.time())

loss_as_pct_low = -4
loss_as_pct_high = -2.5
loss_incr_as_pct = 1

loss_as_low = loss_as_pct_low/100
loss_as_pct_high = loss_as_pct_high/100
loss_incr_as_pct = loss_incr_as_pct/100

pct_of_mvg_as_pct_low = 40
pct_of_mvg_as_pct_high = 100
pct_of_mvg_as_pct_incr = 10

pct_of_mvg_as_low = pct_of_mvg_as_pct_low/100
pct_of_mvg_as_high = pct_of_mvg_as_pct_high/100
pct_of_mvg_as_incr = pct_of_mvg_as_pct_incr / 100

low_devs = -3
high_devs = -2
incr_devs = .1

low_window = 60
high_window = 300
incr_window = 60

low_elaps = 24*13
high_elaps = 24*14
incr_elaps = 24

rranges = (slice(loss_as_low,loss_as_pct_high,loss_incr_as_pct),slice(pct_of_mvg_as_low,pct_of_mvg_as_high,pct_of_mvg_as_incr),slice(low_devs, high_devs, incr_devs),slice(low_window,high_window,incr_window),)

resbrute = optimize.brute(process, ranges=rranges,full_output=True,finish=None)
print(resbrute[0])
print(resbrute[1])

