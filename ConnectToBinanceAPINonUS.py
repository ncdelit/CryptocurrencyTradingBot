from datetime import datetime, date
#from GoogleSheets import main
import time as t
import datetime
#import alpaca_trade_api as tradeapi
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
#from TradingData import *
import hashlib
import hmac
import requests

def ReadCSV(name):
    
    err = True
    while (err == True):
        try:
            err = False
            df = pd.read_csv(name)
            try:
                if (df != None):
                    return df
            except Exception as e:
                return df
        except Exception as e:
            traceback.print_exc()     
            time.sleep(0.5)
    
def Average(lst):
    try: 
        return sum(lst) / len(lst) 
    except Exception as e:
        return 0

def CorrectionWriteCSV(wait_time_to_buy_in_min,freq,period_in_seconds):
    
    # find your own number of partitions    start = time.time()
    symbols = ['ADA-BTC', 'ETH-BTC', 'DOT-BTC', 'LTC-BTC', 'LINK-BTC', 'UNI-BTC', 'XRP-BTC', 'BCH-BTC',
    'XEM-BTC', 'BNB-BTC','FIL-BTC','ATOM-BTC','LUNA-BTC','XMR-BTC','DASH-BTC','ENJ-BTC','BAT-BTC']
    
    price_data = pd.DataFrame({'symbol': symbols})
    
    ddf = price_data
    
    name_of_ddf_csv_curr = "opportunities_curr.csv"
    name_of_ddf_csv_all = "opportunities_all.csv"

    ddf['ask_price'] = 0
    ddf['bid_price'] = 0
    ddf['bid_price_cumul'] = 0
    ddf['ask_price_cumul'] = 0
    ddf['ask_price_mvg'] = 0
    ddf['bid_price_mvg'] = 0
    ddf['min_ask_price'] = 0
    ddf['ask_price_cumul_shadow'] = 0
    ddf['ask_price_emvg'] = 0
    counter = 1
    counter_shadow = 1

    emva_smoothing = 2
    
    start = time.time()
    start_freq = time.time()
    
    ddf_overall = ddf

    while True:

        ddf = ddf.fillna(0)
        end_freq = time.time()
        elapsed_time_freq = (end_freq - start_freq) / 60

        if (elapsed_time_freq > freq):
            ddf['ask_price_cumul'] = ddf['ask_price_cumul_shadow']
            ddf['ask_price_cumul_shadow'] = 0
            start_freq = time.time()
            counter = counter_shadow
            counter_shadow = 1
            #os.remove(name_of_ddf_csv_curr)
            #os.remove(name_of_ddf_csv_all)

        # start = time.time()
        # price_data['bid_price'] = price_data['symbol'].apply(
        # GetBidPriceOnBinanceOB)
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf.head())

        new_bid_prices = []
        new_ask_prices = []
        start_ch = time.time()
        for symbol in symbols:
            new_bid_prices.append(GetBidPriceOnBinanceOB(symbol))
            new_ask_prices.append(GetAskPriceOnBinanceOB(symbol))
            #t.sleep(0.001)
        
        # with ThreadPoolExecutor(max_workers=10000) as pool:
        #         try:
        #             ddf['bid_price'] = list(pool.map(GetBidPriceOnBinanceOB, ddf['symbol']))

        #             ddf['ask_price'] = list(pool.map(GetAskPriceOnBinanceOB, ddf['symbol']))
        #         except Exception as e:
        #             print("ERROR!!!!")
        
        end_ch = time.time()
        elapsed_time_ch = (end_ch - start_ch)
        
        print(elapsed_time_ch)

        # ddf['bid_price'] = ddf.symbol.map(
        #     lambda x: float(GetBidPriceOnBinanceOB(x)), meta=('symbol', float))

        ddf['bid_price'] = new_bid_prices
        ddf['ask_price'] = new_ask_prices

        ddf['pct_from_mvg'] = ((ddf['ask_price'] - ddf['ask_price_emvg']) / ddf['ask_price_emvg']) * 100

        
        ddf['pct_from_mvg_abs'] = abs(ddf['pct_from_mvg'])                         
            
        ddf['bid_price_cumul'] = (ddf['bid_price_cumul'] + ddf['bid_price'])
        
        ddf['bid_price_mvg'] = (ddf['bid_price_cumul']) / counter
        
        ddf['ask_price_emvg'] = (ddf['ask_price']*(emva_smoothing/(1+counter))) + (ddf['ask_price_emvg']*(1-(emva_smoothing/(1+counter))))

        ddf['ask_price_cumul'] = (ddf['ask_price_cumul'] + ddf['ask_price'])
     
        ddf['ask_price_mvg'] = (ddf['ask_price_cumul']) / counter
        
        ddf['bid_ask_spread'] = ((ddf['bid_price'] - ddf['ask_price']) / ddf['ask_price']) * 100

        end = time.time()
        elapsed_time = (end - start) / 60

        ddf['elapsed_time'] = elapsed_time
        
        ddf_overall = ddf_overall.append(ddf)

        if (elapsed_time_freq >= 0.75 * freq):
            ddf['ask_price_cumul_shadow'] = ddf['ask_price_cumul_shadow'] + ddf['ask_price']
            counter_shadow = counter_shadow + 1
 
        if (elapsed_time >= wait_time_to_buy_in_min):

            WriteCSV(ddf, name_of_ddf_csv_curr)
            WriteCSV(ddf_overall,name_of_ddf_csv_all)
            print("csv's generated")

        counter = counter + 1        
        time.sleep(period_in_seconds)

    # print(price_data)
 
def ReturnOpportunityAlt(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct,csv_curr, csv_all,check_enabled,devs,pct_of_mvt):
    
    error_generating = True
    
    while (error_generating == True):
        error = True
        while (error == True):
            try:
                ddf = ReadCSV(csv_curr)
                ddf_overall = ReadCSV(csv_all)
                try:
                    if (ddf != None):
                        error = False
                except Exception as e:
                    error = False
            except Exception as e:
                traceback.print_exc()     
        
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf)
        #subprocess.Popen("cls", shell=True).communicate()
        #print(ddf_filtered)
        
        start_check = time.time()
        end_check = time.time()
        elapsed_check = end_check - start_check
        new_prices_pct = []
   
        with pd.option_context('display.float_format', '{:0.8f}'.format):
            print(ddf)
        
        # if (devs < 0):
        ddf_filtered = ddf[(ddf['pct_from_monitor_price']<=-15)]
        # else:
        #     ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -max_bid_ask_spread_as_pct) & (ddf['no_of_std_devs'] >= devs)]
            
        try:

            min_pct_from_avg = ddf_filtered[ddf_filtered['no_of_std_devs'] == ddf_filtered['no_of_std_devs'].max()]

            symbol_to_return = str(min_pct_from_avg.iloc[0]['symbol'])
            price_to_return = str(min_pct_from_avg.iloc[0]['ask_price'])
            bid_ask_spread = str(min_pct_from_avg.iloc[0]['bid_ask_spread'])
            pct_from_mvg = str(min_pct_from_avg.iloc[0]['pct_from_mvg'])
            elapsed_time = str(min_pct_from_avg.iloc[0]['elapsed_time'])
            
            devs = str(min_pct_from_avg.iloc[0]['no_of_std_devs'])

            ddf_overall = ddf_overall[(ddf_overall['ask_price'] != 0) & (ddf_overall['symbol'] ==symbol_to_return)]

            min_ask_price = ddf_overall['ask_price'].min()

            if (check_enabled == True):
                while (elapsed_check <= time_to_check_in_seconds):
    
                    new_symbol_price = float(GetBidPriceOnBinanceOB(symbol_to_return))
                    
                    percent_change = ((new_symbol_price -
                                        float(price_to_return)) / float(price_to_return))*100

                    new_prices_pct.append(percent_change)

                    print("checking..." +str(percent_change))
                
            
                    end_check = time.time()
                    elapsed_check = end_check - start_check

                if(Average(new_prices_pct) >= threshold_for_check_as_pct):
                    main("Detail!A:F", rows=[
                    [symbol_to_return, str(datetime.datetime.now()), price_to_return, bid_ask_spread, pct_from_mvg,elapsed_time]])

                    error_generating = False
            else:
                error_generating = False 

        except Exception as e:
            # traceback.print_exc()   
            print(e)       
            time.sleep(0.5)            
            #subprocess.Popen("cls", shell=True).communicate()
            # if (elapsed_time > 5):
            #     print("Resetting")
            #     Correction()
            #pass
    
    ddf.to_csv("assets_bought.csv", index=False, mode='w+')
    return symbol_to_return, float(price_to_return),float(min_ask_price),float(pct_from_mvg),float(bid_ask_spread),float(devs)

def ReturnOpportunity(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct,csv_curr, csv_all,check_enabled,devs,pct_of_mvt):
    
    error_generating = True
    
    while (error_generating == True):
        error = True
        while (error == True):
            try:
                ddf = ReadCSV(csv_curr)
                ddf_overall = ReadCSV(csv_all)
                try:
                    if (ddf != None):
                        error = False
                except Exception as e:
                    error = False
            except Exception as e:
                traceback.print_exc()     
        
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf)
        #subprocess.Popen("cls", shell=True).communicate()
        #print(ddf_filtered)
        
        start_check = time.time()
        end_check = time.time()
        elapsed_check = end_check - start_check
        new_prices_pct = []
   
        with pd.option_context('display.float_format', '{:0.8f}'.format):
            print(ddf)
        
        # if (devs < 0):
        ddf_filtered = ddf[((ddf['bid_ask_spread'] >= -max_bid_ask_spread_as_pct) & (ddf['no_of_std_devs'] <= devs)&(ddf['pct_from_mvg'].values*-1*pct_of_mvt > 0.2))] #|(ddf['pct_from_monitor_price']<=-2.5)
        # else:
        #     ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -max_bid_ask_spread_as_pct) & (ddf['no_of_std_devs'] >= devs)]
            
        try:

            min_pct_from_avg = ddf_filtered[ddf_filtered['no_of_std_devs'] == ddf_filtered['no_of_std_devs'].max()]

            symbol_to_return = str(min_pct_from_avg.iloc[0]['symbol'])
            price_to_return = str(min_pct_from_avg.iloc[0]['ask_price'])
            bid_ask_spread = str(min_pct_from_avg.iloc[0]['bid_ask_spread'])
            pct_from_mvg = str(min_pct_from_avg.iloc[0]['pct_from_mvg'])
            elapsed_time = str(min_pct_from_avg.iloc[0]['elapsed_time'])
            
            devs = str(min_pct_from_avg.iloc[0]['no_of_std_devs'])

            ddf_overall = ddf_overall[(ddf_overall['ask_price'] != 0) & (ddf_overall['symbol'] ==symbol_to_return)]

            min_ask_price = ddf_overall['ask_price'].min()

            if (check_enabled == True):
                while (elapsed_check <= time_to_check_in_seconds):
    
                    new_symbol_price = float(GetBidPriceOnBinanceOB(symbol_to_return))
                    
                    percent_change = ((new_symbol_price -
                                        float(price_to_return)) / float(price_to_return))*100

                    new_prices_pct.append(percent_change)

                    print("checking..." +str(percent_change))
                
            
                    end_check = time.time()
                    elapsed_check = end_check - start_check

                if(Average(new_prices_pct) >= threshold_for_check_as_pct):
                    main("Detail!A:F", rows=[
                    [symbol_to_return, str(datetime.datetime.now()), price_to_return, bid_ask_spread, pct_from_mvg,elapsed_time]])

                    error_generating = False
            else:
                error_generating = False 

        except Exception as e:
            # traceback.print_exc()   
            print(e)       
            time.sleep(0.5)            
            #subprocess.Popen("cls", shell=True).communicate()
            # if (elapsed_time > 5):
            #     print("Resetting")
            #     Correction()
            #pass
    
    ddf.to_csv("assets_bought.csv", index=False, mode='w+')
    return symbol_to_return, float(price_to_return),float(min_ask_price),float(pct_from_mvg),float(bid_ask_spread),float(devs)

def ReturnOpportunityAlt2(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct,csv_curr, csv_all,check_enabled,devs,pct_of_mvt):
    
    error_generating = True
    
    while (error_generating == True):
        error = True
        while (error == True):
            try:
                ddf = ReadCSV(csv_curr)
                ddf_overall = ReadCSV(csv_all)
                try:
                    if (ddf != None):
                        error = False
                except Exception as e:
                    error = False
            except Exception as e:
                traceback.print_exc()     
        
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf)
        #subprocess.Popen("cls", shell=True).communicate()
        #print(ddf_filtered)
        
        start_check = time.time()
        end_check = time.time()
        elapsed_check = end_check - start_check
        new_prices_pct = []

        print("true")
        with pd.option_context('display.float_format', '{:0.8f}'.format):
            print(ddf)
        
        # if (devs < 0):
        ddf_filtered = ddf[(ddf['median_pct_from_mvg']<=-2)]
        print(ddf_filtered)
        # else:
        #     ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -max_bid_ask_spread_as_pct) & (ddf['no_of_std_devs'] >= devs)]
            
        try:
            
            test = str(ddf_filtered.iloc[0]['symbol'])


            symbol_to_return = "all"
            price_to_return = ddf_filtered['ask_price'].sum()
            bid_ask_spread = ddf_filtered['bid_ask_spread'].mean()
            pct_from_mvg = ddf_filtered['pct_from_mvg'].mean()
            elapsed_time = ddf_filtered['elapsed_time'].max()
            
            devs = ddf_filtered['no_of_std_devs'].mean()

            min_ask_price = ddf_filtered['pct_from_mvg'].min()

            error_generating = False
            
        except Exception as e:
            traceback.print_exc()
            #print("true")   
            print(e)       
            time.sleep(0.5)            
            #subprocess.Popen("cls", shell=True).communicate()
            # if (elapsed_time > 5):
            #     print("Resetting")
            #     Correction()
            #pass
    
   
    ddf.to_csv("assets_bought.csv", index=False, mode='w+')
    return symbol_to_return, float(price_to_return),float(min_ask_price),float(pct_from_mvg),float(bid_ask_spread),float(devs)

def ReturnOpportunityETH(threshold_for_fall_as_pct,max_bid_ask_spread_as_pct,time_to_check_in_seconds,threshold_for_check_as_pct,csv_curr, csv_all,check_enabled,devs,pct_of_mvt):
    
    error_generating = True
    
    while (error_generating == True):
        error = True
        while (error == True):
            try:
                ddf = ReadCSV(csv_curr)
                ddf_overall = ReadCSV(csv_all)
                try:
                    if (ddf != None):
                        error = False
                except Exception as e:
                    error = False
            except Exception as e:
                traceback.print_exc()     
        
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf)
        #subprocess.Popen("cls", shell=True).communicate()
        #print(ddf_filtered)
        
        start_check = time.time()
        end_check = time.time()
        elapsed_check = end_check - start_check
        new_prices_pct = []
   
        with pd.option_context('display.float_format', '{:0.8f}'.format):
            print(ddf)
        
        # if (devs < 0):
        ddf_filtered = ddf[(((ddf['symbol'] == 'ETH-BTC')|(ddf['symbol'] == 'BNB-BTC')) & (ddf['median_pct_from_mvg'] > 0)&(ddf['pct_from_mvg'].values < 0)&(ddf['pct_from_mvg'].values*-1*pct_of_mvt > 0.2))] #|(ddf['pct_from_monitor_price']<=-2.5)
        # else:
        #     ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -max_bid_ask_spread_as_pct) & (ddf['no_of_std_devs'] >= devs)]
            
        try:

            min_pct_from_avg = ddf_filtered[ddf_filtered['no_of_std_devs'] == ddf_filtered['no_of_std_devs'].max()]

            symbol_to_return = str(min_pct_from_avg.iloc[0]['symbol'])
            price_to_return = str(min_pct_from_avg.iloc[0]['ask_price'])
            bid_ask_spread = str(min_pct_from_avg.iloc[0]['bid_ask_spread'])
            pct_from_mvg = str(min_pct_from_avg.iloc[0]['pct_from_mvg'])
            elapsed_time = str(min_pct_from_avg.iloc[0]['elapsed_time'])
            
            devs = str(min_pct_from_avg.iloc[0]['no_of_std_devs'])

            ddf_overall = ddf_overall[(ddf_overall['ask_price'] != 0) & (ddf_overall['symbol'] ==symbol_to_return)]

            min_ask_price = ddf_overall['ask_price'].min()

            if (check_enabled == True):
                while (elapsed_check <= time_to_check_in_seconds):
    
                    new_symbol_price = float(GetBidPriceOnBinanceOB(symbol_to_return))
                    
                    percent_change = ((new_symbol_price -
                                        float(price_to_return)) / float(price_to_return))*100

                    new_prices_pct.append(percent_change)

                    print("checking..." +str(percent_change))
                
            
                    end_check = time.time()
                    elapsed_check = end_check - start_check

                if(Average(new_prices_pct) >= threshold_for_check_as_pct):
                    main("Detail!A:F", rows=[
                    [symbol_to_return, str(datetime.datetime.now()), price_to_return, bid_ask_spread, pct_from_mvg,elapsed_time]])

                    error_generating = False
            else:
                error_generating = False 

        except Exception as e:
            # traceback.print_exc()   
            print(e)       
            time.sleep(0.5)            
            #subprocess.Popen("cls", shell=True).communicate()
            # if (elapsed_time > 5):
            #     print("Resetting")
            #     Correction()
            #pass
   
    ddf.to_csv("assets_bought.csv", index=False, mode='w+')
    return symbol_to_return, float(price_to_return),float(min_ask_price),float(pct_from_mvg),float(bid_ask_spread),float(devs)


"Functions not used"

def IncreasingMomentum():
    
    # find your own number of partitions    start = time.time()
    symbols = ['ADA-BTC', 'ETH-BTC', 'DOT-BTC', 'LTC-BTC', 'LINK-BTC', 'UNI-BTC', 'XRP-BTC', 'XLM-BTC', 'BCH-BTC',
    'XEM-BTC', 'EOS-BTC','BNB-BTC','NEO-BTC']

    # symbols = [ 'ETH-BTC']

    #price_data = pd.DataFrame(symbols, columns=['symbol'])

    price_data = pd.DataFrame({'symbol': symbols})
    
    ddf = price_data
    # ddf = dd.from_pandas(price_data, chunksize=1)
    # ddf = ddf.persist()
    ddf['ask_price'] = 0
    ddf['bid_price'] = 0
    ddf['bid_price_cumul'] = 0
    ddf['ask_price_cumul'] = 0
    ddf['ask_price_mvg'] = 0
    ddf['bid_price_mvg'] = 0
    ddf['incr_ctr'] = 0
    ddf['pct_from_mvg_cumul'] = 0
    counter = 1
    start = time.time()

    while True:
        # start = time.time()

        
        # start = time.time()
        # price_data['bid_price'] = price_data['symbol'].apply(
        # GetBidPriceOnBinanceOB)
        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(ddf.head())

        with ThreadPoolExecutor(max_workers=10000) as pool:
            ddf['bid_price'] = list(pool.map(GetBidPriceOnBinanceOB, ddf['symbol']))
            ddf['ask_price'] = list(pool.map(GetAskPriceOnBinanceOB, ddf['symbol']))

        # ddf['bid_price'] = ddf.symbol.map(
        #     lambda x: float(GetBidPriceOnBinanceOB(x)), meta=('symbol', float))

        ddf['pct_from_mvg'] = ((ddf['bid_price'] - ddf['ask_price_mvg']) / ddf['ask_price_mvg']) * 100

        ddf = ddf.replace([np.inf, -np.inf], 0)

        ddf['pct_from_mvg_abs'] = abs(ddf['pct_from_mvg'])

        ddf['pct_from_mvg_cumul'] = ddf['pct_from_mvg_cumul'] + ddf['pct_from_mvg']

        ddf.loc[ddf['ask_price'] > ddf['ask_price_mvg'], 'incr_ctr'] = ddf['incr_ctr'] + 1 
                
        ddf['bid_price_cumul'] = (ddf['bid_price_cumul'] + ddf['bid_price'])

        ddf['bid_price_mvg'] = (ddf['bid_price_cumul'])/counter

        ddf['ask_price_cumul'] = (ddf['ask_price_cumul'] + ddf['ask_price'])
        
        ddf['ask_price_mvg'] = (ddf['ask_price_cumul']) / counter
        
        ddf['bid_ask_spread'] = ((ddf['bid_price'] - ddf['ask_price']) / ddf['ask_price']) * 100

        ddf['mtnm_fct'] = ddf['pct_from_mvg_cumul']*ddf['incr_ctr']
        
        # ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -0.05) & (ddf['pct_from_mvg'] < -0.5)]

        ddf_filtered = ddf[(ddf['bid_ask_spread'] >= -0.05) &(ddf['mtnm_fct'] > 1)]
        
        print(ddf)
        #print(ddf_filtered)
        end = time.time()
        elapsed_time = (end - start)/60
        
        try:
            
            min_pct_from_avg = ddf_filtered[ddf_filtered['mtnm_fct'] == ddf_filtered['mtnm_fct'].max()]
            
            # min_pct_from_avg = ddf_filtered[ddf_filtered['pct_from_mvg']==ddf_filtered['pct_from_mvg'].min()]
           
            symbol_to_return = str(min_pct_from_avg.iloc[0]['symbol'])
            price_to_return = str(min_pct_from_avg.iloc[0]['ask_price'])
            bid_ask_spread = str(min_pct_from_avg.iloc[0]['bid_ask_spread'])
            pct_from_mvg = str(min_pct_from_avg.iloc[0]['pct_from_mvg'])
            #print(min_pct_from_avg)
            #print(min_pct_from_avg)
            if (elapsed_time > 0.5):
                
                main("Detail!A:E", rows=[
                [symbol_to_return, str(datetime.datetime.now()), price_to_return, bid_ask_spread, pct_from_mvg]])

                break

        except Exception as e:
            print(e)
            if (elapsed_time > 0.5):
                IncreasingMomentum()
            #pass
        counter = counter + 1
        time.sleep(0.2)
        # end = time.time()
        # elapsed_time = (end - start)

        # with pd.option_context('display.float_format', '{:0.8f}'.format):
        #     print(sum(ddf['ask_price'].compute()) - sum(ddf['ask_price'].compute()))

        # print(elapsed_time)

    return symbol_to_return, float(price_to_return)

"Binance Functions"

def GetBidPriceOnBinanceOB(Coin):
    Coin2 = Coin.split("-", 1)[1]
    Coin1 = Coin.split("-", 1)[0]
    Price = 0
    
    while ~(float(Price) != None and (~ (np.isnan(float(Price)))) and float(Price) != 0 and float(Price)>0.0000001):
        try:
            url = 'https://api.binance.com/api/v3/ticker/bookTicker?symbol='+Coin1+Coin2
            response = urllib.request.urlopen(url,timeout=50)
            data4 = json.loads(response.read())
            Price = data4['bidPrice']
            #print(Price)

            if (float(Price) != None and (~ (np.isnan(float(Price)))) and float(Price) != 0 and float(Price)>0.0000001):
                return float(Price)

            print(data4)
        except Exception as e:
            print(e)
            traceback.print_exc()
            time.sleep(1)
            #GetBidPriceOnBinanceOB(Coin)

def GetAvgPriceOnBinance(Coin):
    Price = 0
    try:
        url = 'https://api.binance.com/api/v3/avgPrice?symbol='+Coin+'BTC'
        response = urllib.request.urlopen(url)
        data4 = json.loads(response.read())
        Price = data4['price']
        #print(Price)
    except Exception as e:
        traceback.print_exc()
        GetAvgPriceOnBinance(Coin)

    return Price

def GetAskPriceOnBinanceOB(Coin):
    Coin2 = Coin.split("-", 1)[1]
    Coin1 = Coin.split("-", 1)[0]
    Price = 0
    
    while ~(float(Price) != None and (~ (np.isnan(float(Price)))) and float(Price) != 0 and float(Price)>0.0000001):
        try:
            url = 'https://api.binance.com/api/v3/ticker/bookTicker?symbol='+Coin1+Coin2
            response = urllib.request.urlopen(url,timeout=50)
            data4 = json.loads(response.read())
            Price = data4['askPrice']
            #print(Price)

            if (float(Price) != None and (~ (np.isnan(float(Price)))) and float(Price) != 0 and float(Price)>0.0000001):
                return float(Price)

            #print(Price)
        except Exception as e:
            print(e)
        #traceback.print_exc()
            time.sleep(1)
            #GetBidPriceOnBinanceOB(Coin)

def GetPriceOnBinance(Coin):
    Price = 0
    try:
        url = 'https://api.binance.com/api/v3/ticker/price?symbol='+Coin+'BTC'
        response = urllib.request.urlopen(url)
        data4 = json.loads(response.read())
        Price = data4['price']
        #print(Price)
    except Exception as e:
        traceback.print_exc()
        GetPriceOnBinance(Coin)

    return Price

def GetSellOrderBookOnBinance(Coin):
    df = pd.DataFrame()
    try:
        url = "https://api.binance.com/api/v1/depth?symbol="+Coin+'BTC'
        response = urllib.request.urlopen(url)
        data4 = json.loads(response.read())
        df = pd.DataFrame.from_dict(data4['bids'], orient='columns')
        df.rename(columns={0: 'Price',1:'Qty'}, inplace=True)
        df = df.apply(pd.to_numeric, errors='coerce', axis=1)
        #cols = ['col1', 'col2', 'col3'] for converting select columns to numbers
        #data[cols] = data[cols].apply(pd.to_numeric, errors='coerce', axis=1)
        df['Total'] = df['Price']*df['Qty']
    except Exception as e:
        traceback.print_exc()
        time.sleep(15)
        GetSellOrderBookOnBinance(Coin)

    return df

def GetBuyOrderBookOnBinance(Coin):
    df = pd.DataFrame()
    try:
        url = "https://api.binance.com/api/v1/depth?symbol="+Coin+'BTC'
        response = urllib.request.urlopen(url)
        data4 = json.loads(response.read())
        df = pd.DataFrame.from_dict(data4['asks'], orient='columns')
        df.rename(columns={0: 'Price',1:'Qty'}, inplace=True)
        df = df.apply(pd.to_numeric, errors='coerce', axis=1)
        df['Total'] = df['Price']*df['Qty']
    except Exception as e:
        traceback.print_exc()
        GetBuyOrderBookOnBinance(Coin)

    return df

def GetSellOrderBookVolumeOnBinance(Coin,SellingPrice):
    OrderBookVolume2 = 0
    OB = pd.DataFrame()
    try:
        OB = GetSellOrderBookOnBinance(Coin)
        OB = OB[(OB['Price']>=SellingPrice)]
        OrderBookVolume2 = OB["Total"].sum()
    except Exception as e:
        traceback.print_exc()
        time.sleep(15)
        GetSellOrderBookVolumeOnBinance(Coin,SellingPrice)
    return OrderBookVolume2

def roundDown(n, d):
    d = int('1' + ('0' * d))
    return floor(n * d) / d

def roundUp(n, d):
    d = int('1' + ('0' * d))
    return ceil(n * d) / d

def print_full(x):
    pd.set_option('display.max_rows', len(x))
    print(x)
    pd.reset_option('display.max_rows')

def PopulateBinancePriceList(symbols):
    global control
    try:
        url = 'https://api.binance.com/api/v1/ticker/24hr'
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
    except Exception as e:
        traceback.print_exc()
        control = True

    markets2 = []
    asks2 = []
    bids2 = []

    try:
        #coin,status = GetBinanceCoinStatus()
        for i in range(len(data)):
            cont = False
            try:
                # for j in range(len(coin)):
                #     if (coin[j] in data[i]['symbol']):
                #         if (status[j] == False):

                #             cont == True
                #             break
                # if cont == True:
                #     continue
                sym = str(data[i]['symbol'])
                Coin1 = sym[:len(sym)-3]
                Coin2 = sym[len(sym)-3:len(sym)]
                markets2.append(Coin1 + "-"+Coin2)
                asks2.append(float(data[i]['askPrice']))
                bids2.append(float(data[i]['bidPrice']))
            except Exception as e:
                markets2.append(str(data[i]['symbol']))
                asks2.append(0)
                bids2.append(0)
    except Exception as e:
        traceback.print_exc()
        control = True


    BinancePriceList = pd.DataFrame(columns=['A'])
    BinancePriceList = BinancePriceList.drop(['A'], axis=1)

    BinancePriceList['symbol'] =markets2
    BinancePriceList['AskPrice'] = asks2
    BinancePriceList['BidPrice'] = bids2

    BinancePriceList = BinancePriceList[BinancePriceList['symbol'].isin(symbols)]

    return BinancePriceList

def GetBinanceAddress(CoinBought):
    print("GetBinanceAddress...")
    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/wapi/v3/depositAddress.html?'

    timestamp = int(time.time() * 1000)

    querystring = {'asset': str(CoinBought), 'timestamp' : timestamp, "recvWindow": str(10000000)}
    querystring = urllib.urlencode(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature

    r = requests.get(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    #print("GetBinanceAddress: "+str(data))
    if data['success'] == False:
        GetBinanceAddress(CoinBought)
    print("GetBinanceAddress: "+str(data))
    return str(data['address'])

def SellOnBinance(pair,Price,qty):
    print("SellOnBinance...")
    Coin2 = pair.split("-",1)[1]
    Coin1 = pair.split("-",1)[0]

    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/api/v3/order?'

    timestamp = int(time.time() * 1000)

    # querystring = {'symbol': str(Coin1 + Coin2),'side':'BUY','type': 'LIMIT','quantity':qty,'price':Price}

    #querystring = urllib.urlencode(OrderedDict(querystring))

    querystring = "&symbol=" + str(Coin1 + Coin2) + "&side=SELL" + "&type=LIMIT" + "&price="+format(Price, '.8f') + "&quantity=" + str(
        qty) + "&recvWindow="+str(50000) + "&timestamp=" + str(timestamp) + "&timeInForce=" + "GTC"

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    #print(request_url)


    r = requests.post(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    
    print("SellOnBinance: " + str(data))
    
def SellOnBinanceTest(pair, Price, qty):
    print("BuyOnBinance...")
    Coin2 = pair.split("-", 1)[1]
    Coin1 = pair.split("-", 1)[0]

    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/api/v3/order/test?'

    timestamp = int(time.time() * 1000)

    # querystring = {'symbol': str(Coin1 + Coin2),'side':'BUY','type': 'LIMIT','quantity':qty,'price':Price}

    #querystring = urllib.urlencode(OrderedDict(querystring))

    querystring = "&symbol=" + str(Coin1 + Coin2) + "&side=SELL" + "&type=LIMIT" + "&price="+format(Price, '.8f') + "&quantity=" + str(
        qty) + "&recvWindow="+str(50000) + "&timestamp=" + str(timestamp) + "&timeInForce=" + "GTC"

    signature = hmac.new(api_secret.encode(
        'utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    #print(request_url)

    r = requests.post(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    print("BuyOnBinance: " + str(data))

def GetBalanceOnBinance(coin):
    Coin2 = coin.split("-", 1)[1]
    Coin1 = coin.split("-", 1)[0]
    coin = Coin1
    print("GetBalanceOnBinance...")
    api_key = ''
    api_secret = ''

    #Coin1 = pair.split("-",1)[0]
    request_url = 'https://api.binance.com/api/v3/account?'

    timestamp = int(time.time() * 1000)

    querystring = {'timestamp' : timestamp}
    querystring = urllib.parse.urlencode(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature

    r = requests.get(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    #print("GetBalanceOnBinance: " + str(data))
    #print(data)

    #print(data)
    if "error" in data:
        GetBalanceOnBinance(coin)
    Balance = 0.00
    for i in range(len(data['balances'])):
        if data['balances'][i]['asset'] == coin:
            Balance = float(data['balances'][i]['free'])

    return Balance

def DownloadStepSizes():
    api_key = ''
    api_secret = ''

    #Coin1 = pair.split("-",1)[0]
    request_url = 'https://www.binance.com/api/v1/exchangeInfo'

    r = requests.get(request_url)
    data = r.json()
    print(data)


    Symbols = []
    Stepsizes = []
    for i in range(len(data['symbols'])):
        Symbols.append(data['symbols'][i]['symbol'])
        Stepsizes.append(float(data['symbols'][i]['filters'][1]['stepSize']))

    StepSizes = pd.DataFrame(columns=['A'])
    StepSizes = StepSizes.drop(['A'], axis=1)

    StepSizes['symbol'] = Symbols
    StepSizes['step'] = Stepsizes

    print(StepSizes)
    import pickle

    StepSizes.to_pickle('StepSizes.db')

def GetStepSize(Coin):
    df = pd.read_pickle('StepSizes.db')

    df = df[(df['symbol'] == Coin)]

    return float(df.head(1)['step'].values[0])

def BuyOnBinance(pair,Price,qty):
    print("BuyOnBinance...")
    Coin2 = pair.split("-",1)[1]
    Coin1 = pair.split("-",1)[0]

    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/api/v3/order?'

    timestamp = int(time.time() * 1000)

    # querystring = {'symbol': str(Coin1 + Coin2),'side':'BUY','type': 'LIMIT','quantity':qty,'price':Price}

    #querystring = urllib.urlencode(OrderedDict(querystring))

    querystring = "&symbol=" + str(Coin1 + Coin2) + "&side=BUY" + "&type=LIMIT" + "&price="+format(Price, '.8f') + "&quantity=" + str(
        qty) + "&recvWindow=" + str(50000) + "&timestamp=" + str(timestamp) + "&timeInForce=" + "GTC"
    print(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    #print(request_url)


    r = requests.post(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    print("BuyOnBinance: "+ str(data))

def BuyOnBinanceTest(pair, Price, qty):
    print("BuyOnBinance...")
    Coin2 = pair.split("-", 1)[1]
    Coin1 = pair.split("-", 1)[0]

    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/api/v3/order/test?'

    timestamp = int(time.time() * 1000)

    # querystring = {'symbol': str(Coin1 + Coin2),'side':'BUY','type': 'LIMIT','quantity':qty,'price':Price}

    #querystring = urllib.urlencode(OrderedDict(querystring))

    querystring = "&symbol=" + str(Coin1 + Coin2) + "&side=BUY" + "&type=LIMIT" + "&price="+format(Price, '.8f') + "&quantity=" + str(
        qty) + "&recvWindow=" + str(50000) + "&timestamp=" + str(timestamp) + "&timeInForce=" + "GTC"
    print(querystring)

    signature = hmac.new(api_secret.encode(
        'utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    #print(request_url)

    r = requests.post(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    print("BuyOnBinance: " + str(data))

def AnyOpenOrders(pair):
    Coin2 = pair.split("-", 1)[1]
    Coin1 = pair.split("-", 1)[0]
    print("GetBalanceOnBinance...")
    api_key = ''
    api_secret = ''

    #Coin1 = pair.split("-",1)[0]
    request_url = 'https://api.binance.com/api/v3/openOrders?'

    timestamp = int(time.time() * 1000)

    querystring = {'timestamp' : timestamp,'recvWindow':50000,'symbol':str(Coin1 + Coin2)}
    querystring = urllib.parse.urlencode(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature

    r = requests.get(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    print(str(data))
    if data == []:
        return False
    else:
        return True

def returnOrderId(pair):
    Coin2 = pair.split("-", 1)[1]
    Coin1 = pair.split("-", 1)[0]
    #print("GetBalanceOnBinance...")
    api_key = ''
    api_secret = ''

    #Coin1 = pair.split("-",1)[0]
    request_url = 'https://api.binance.com/api/v3/openOrders?'

    timestamp = int(time.time() * 1000)

    querystring = {'timestamp' : timestamp,'recvWindow':50000,'symbol':str(Coin1 + Coin2)}
    querystring = urllib.parse.urlencode(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature

    r = requests.get(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    #print(str(data))
    return data[0]['orderId']


def GetPriceOfRecentTradeOnBinance(pair):
    Coin2 = pair.split("-",1)[1]
    Coin1 = pair.split("-",1)[0]

    # wait = GetBalanceOnBinance(Coin1)
    # while wait != 0:
    #     wait = GetBalanceOnBinance(Coin1)
    #     print(wait)
    #     time.sleep(60*1)

    api_key = ''
    api_secret = ''

    request_url = 'https://api.binance.com/api/v3/myTrades?'

    timestamp = int(time.time() * 1000)

    # bal = str(GetBalanceOnBinance(Coin1))
    # A = GetStepSize(Coin1)
    # querystring = {'symbol': str(Coin1 + Coin2),'timestamp':timestamp,'limit': 1}
    #
    # querystring = urllib.urlencode(OrderedDict(querystring))

    querystring = "&symbol=" +str(Coin1)+str(Coin2)+"&limit="+str(1)+"&timestamp=" + str(timestamp) + "&recvWindow="+str(10000000)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    #print(request_url)

    r = requests.get(request_url, headers={"X-MBX-APIKEY": api_key})
    #print(r.text)
    #print(request_url)
    data = r.json()
    print("GetPriceOfRecentTradeOnBinance: " +str(data))
    if (float(data[0]['qty']) == 0):
        GetPriceOfRecentTradeOnBinance(pair)
    else:
        return float(data[0]['price'])

def GetBinanceTradingStatus():
    url2 = 'https://api.binance.com/api/v1/exchangeInfo'
    response2 = urllib.request.urlopen(url2)
    data2 = json.loads(response2.read())

    #Coin1 = pair.split("-",1)[0]
    coin = []
    status = []
    for i in range(len(data2['symbols'])):
        coin.append(data2['symbols'][i]['symbol'])
        status.append(data2['symbols'][i]['status'])

    return coin,status

def GetBinanceCoinStatus():
    url2 = 'https://www.binance.com/assetWithdraw/getAllAsset.html'
    response2 = urllib.request.urlopen(url2)
    data2 = json.loads(response2.read())

    #Coin1 = pair.split("-",1)[0]
    coin = []
    status = []
    for i in range(len(data2)):
        coin.append(data2[i]['assetCode'])
        status.append(data2[i]['enableWithdraw'])


    return coin,status

def WithdrawFromBinance(Coin,SaleOrPurchase,address, qty):
    print("WithdrawFromBinance...")
    time.sleep(2*1)
    wait = GetBalanceOnBinance(Coin)
    while wait == 0:
        time.sleep(2*1)
        wait = GetBalanceOnBinance(Coin)
        print(wait)
        time.sleep(30*1)

    

    request_url = 'https://api.binance.com/wapi/v3/withdraw.html?'

    timestamp = int(time.time() * 1000)

    # A = str(GetStepSize(Coin1+Coin2))
    # bal = GetBalanceOnBinance(Coin1)
    # qty = ''
    # print(int((A.replace('.', '')).find('1')))
    # if (int((A.replace('.', '')).find('1')) == 0):
    #     qty = str(int(bal))
    # else:
    #     qty =str(round(bal,int((A.replace('.', '')).find('1'))))

    # querystring = {'symbol': str(Coin1 + Coin2),'side':'SELL','type': 'MARKET','quantity':qty}

    # querystring = urllib.urlencode(OrderedDict(querystring))

    if (SaleOrPurchase == 'Purchase'):
        querystring = "&asset=" +Coin +  "&address=" +str(address)+ "&amount=" + str(GetBalanceOnBinance(Coin)) +"&name=Binance"+"&timestamp=" + str(timestamp)
    else:
        querystring = "&asset=" +Coin +  "&address=" + str(address)+ "&amount=" + str(qty) +"&name=Binance"+"&timestamp=" + str(timestamp)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature
    print(request_url)

    r = requests.post(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    print("WithdrawFromBinance: " + str(data))
    if ("false" in data):
        WithdrawFromBinance(Coin,SaleOrPurchase,Pair)

"Trading Mechanisms"

def InitiateOnBinance(Pair,Price,address):
    Coin1 = Pair.split("-",1)[0]
    Coin2 = Pair.split("-",1)[1]

    BuyOnBinance(Pair,Price)
    WithdrawFromBinance(Coin1,"Purchase",address,"")

def CloseOnBinance(Pair,Price,address):
    Coin1 = Pair.split("-",1)[0]
    Coin2 = Pair.split("-",1)[1]

    A = GetBalanceOnBinance(Coin2)
    SellOnBinance(Pair)
    time.sleep(15)
    B = GetBalanceOnBinance(Coin2)
    WithdrawFromBinance(Coin2,"Sale",address,B-A)

def CancelAllOpenOrders(pair):
    Coin2 = pair.split("-", 1)[1]
    Coin1 = pair.split("-", 1)[0]
    #print("GetBalanceOnBinance...")
    api_key = ''
    api_secret = ''

    #Coin1 = pair.split("-",1)[0]
    request_url = 'https://api.binance.com/api/v3/openOrders?'

    timestamp = int(time.time() * 1000)

    querystring = {'timestamp' : timestamp,'recvWindow':50000,'symbol':str(Coin1 + Coin2)}
    querystring = urllib.parse.urlencode(querystring)

    signature = hmac.new(api_secret.encode('utf-8'), querystring.encode('utf-8'), hashlib.sha256).hexdigest()

    request_url += querystring + '&signature=' + signature

    r = requests.delete(request_url, headers={"X-MBX-APIKEY": api_key})
    data = r.json()
    #print(str(data))
    print(data)