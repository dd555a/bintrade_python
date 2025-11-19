import datetime
import numpy as np
import pandas as pd
import os
import math

import config
from multiprocesspandas import applyparallel
import multiprocessing

from Data import read_data_CSV, pd_dict, write_file, read_file, float_dict, parse_timeframe, parse_filename_intv, dataframe_prune_index, pd_dict, change_timestamp_chart, list_dict, get_chart_time, intervalize_line, intv_to_timedelta

def parse_stats_filename(SYMBOL,interval):
    pwd=os.getcwd()
    filename=pwd+'/STATSData/'+SYMBOL+'STATS_1_'+interval
    return filename

def read_stats_CSV(SYMBOL,interval,prune:bool,start_time,end_time):
    filename=parse_stats_filename(SYMBOL,interval)
    df=pd.read_csv(filename, engine='c')
    df["Open Time"] = pd.to_datetime(df["Open Time"],format='mixed')
    if prune==False:
        return df
    else:
        df=dataframe_prune_index(df,start_time,end_time,True)
    return df

def rev_list_dict(list_dict,keys):
    L=[]
    for k in keys:
        try:
            L.append(list_dict[k])
        except: None
    return L

def interval_minutes(interval):
    parsed_interval=parse_timeframe(interval)
    n=parsed_interval["no"]
    period=parsed_interval["period"]
    match period:
        case 'min':
            mins=n
        case 'hour':
            mins=60*n
        case 'day':
            mins=24*60*n
        case 'week':
            mins=24*60*7*n
        case 'month':
            mins=24*60*30.5*n
        case _:
            print("Period not found!")
    return mins

def calc_ser(x):
    t=x['Open Time']
    h=x['High']
    l=x['Low']
    o=x['Open']
    c=x['Close']
    A1=(h+l)/2
    A2=(o+c)/2
    D={'Open Time':t, 'A1':A1, 'A2':A2}
    return pd.Series(D,name=t)
    
def calc(x):
    x=calc_ser(x)
    return x

def stats_1_MP(df):
    processes=multiprocessing.cpu_count()
    df2=df.apply_parallel(calc, num_processes=processes, axis=0, n_chunks=None)
    return df2 

def stats_1(SYMBOL, interval,prune:bool, start_time, end_time):
    df=read_data_CSV(SYMBOL, interval, prune, start_time, end_time)
    df2=stats_1_MP(df)
    return df2

def STATS_1(SYMBOL):
    pwd=os.getcwd()
    last_append=read_file(pwd+"/CSVData",SYMBOL+"_Last_Modified")
    LA = datetime.datetime.strptime(last_append, "%Y-%m-%d %H:%M:%S")
    try:
        last_append_stats=read_file(pwd+'/STATSData/',SYMBOL+"_Last_Modified")
        LAP = datetime.datetime.strptime(last_append_stats, "%Y-%m-%d %H:%M:%S")
        prune=True
        start_time=LAP
        end_time=LA
        load=True
        last_end_df=pd.read_csv(pwd+'/STATSData/'+SYMBOL+'STATS_1_END', engine='c')
    except:
        write_file(last_append,pwd+'/STATSData/',SYMBOL+"_Last_Modified")
        last_append_stats='2007-08-08 00:00:00'
        LAP = datetime.datetime.strptime(last_append_stats, "%Y-%m-%d %H:%M:%S")
        prune=False
        start_time=None
        end_time=None
        load=False
    intervals=config.stats1_intervals
    n=config.last_stats_days
    st,et=get_chart_time(LA, n)
    row = pd.DataFrame()
    df_M = pd.DataFrame()
    update_end=False
    N=int
    N2=int
    if last_append != last_append_stats:
        n=0
        for i in intervals:
            mins=interval_minutes(i)
            if load==False:
                df_M=stats_1(SYMBOL,i, prune, start_time, end_time)
                if i=='1min':
                    N=len(df_M)
                    write_file(N, pwd+'/STATSData/',SYMBOL+"_N")
                df_M.to_csv(pwd+'/STATSData/'+SYMBOL+'STATS_1_'+i, index=False)
            else:
                try:
                    print(start_time)
                    print(end_time)
                    print(prune)
                    #df=read_data_CSV(SYMBOL, i, prune, start_time, end_time)
                    df_M, p1, p2=stats_1(SYMBOL, i, prune, start_time, end_time)
                    if i=='1min':
                        N2=len(df_M)
                        N=read_file(pwd+'/STATSData/',SYMBOL+"_N")
                    print(df_M)
                    df_M.to_csv(pwd+'/STATSData/'+SYMBOL+'STATS_1_'+i,mode='a', index=False, header=False)
                    if i=='1min':
                        write_file(last_append,pwd+'/STATSData/',SYMBOL+"_Last_Modified")
                        update_end=True
                except:
                    #last_append_dummy='2007-08-08 00:00:00'
                    #write_file(last_append_dummy,pwd+'/STATSData/',SYMBOL+"_Last_Modified")
                    update_end=False
                    pass
            n=n+1
        if load==True:
            if update_end==True:
                N=N+N2
                write_file(N,pwd+'/STATSData/',SYMBOL+"_N")
        else:   
            print('Ran')

def stats_append_all():
    coins=config.coins_of_interest
    for c in coins:
        print("Appending stats info for:",c)
        STATS_1(c)

class stats:
    def __init__(self, intervals): 
        self.MP=config.chart_max_wicks
        self.stats_pd=pd_dict(intervals)
        self.live_stats_pd=pd_dict(intervals)

    def calc_stats_live(self,df, interval):
        try:
            self.live_stats_pd[interval] = stats_1_MP(df.tail(self.MP))
        except:
            print('Stats could not be calculated for :', interval)

    def append_stats_single(self, wick_df, interval):
        last_value=self.stats_pd[interval].index[-1]
        print(last_value)
        print(wick_df)
        try:
            wick_stats=calc(wick_df)
            self.stats_pd[interval]=wick_stats.combine_first(self.stats_pd[interval])
        except:
            print('Wick could not be calculated for :', interval)

    def get_index(self, interval, ref_interval, trade_time):
        if type(trade_time)==str:
            TD = datetime.datetime.strptime(trade_time, "%Y-%m-%d %H:%M:%S")
        else:
            TD=trade_time
        #min1=intv_to_timedelta('1min')
        min1=intv_to_timedelta(ref_interval)
        intvd=intv_to_timedelta(interval)
        P=self.MP*min1/intvd+1
        SD = TD-P*intvd
        index=dataframe_prune_index(self.stats_pd[interval],SD,TD,False)
        return index

    def get_alines(self, interval,index):
        df=self.stats_pd[interval].loc[index].tail(self.MP)
        A1_line=df[['Open Time', 'A1']]
        A2_line=df[['Open Time', 'A2']]
        return A1_line, A2_line

    def get_live_alines(self, interval, index):
        try:
            df=self.live_stats_pd[interval].loc[index].tail(self.MP)
        except:
            A1_line, A2_line=self.get_alines(interval, index)
            return A1_line, A2_line 
        A1_line=df[['Open Time', 'A1']]
        A2_line=df[['Open Time', 'A2']]
        return A1_line, A2_line
