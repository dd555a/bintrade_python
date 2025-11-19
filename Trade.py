import asyncio
import pandas as pd
import config
import datetime
import os
import requests
import numpy as np

import multiprocessing as mp
from multiprocessing import Process, Queue
import keyboard
from Data import read_data_CSV, get_chart_time, extend_range, dataframe_prune_index, parse_chart_settings, h_read_config, change_timestamp_chart, data_append, read_file, data_append_auto_single, data_append_auto, parse_klines_ws, parse_tick, return_symb, get_data, pd_dict, list_dict, logs, get_index_before, intv_to_timedelta, intervalize_line

from Charts import live_chart

from Web import ws_client_hybrid, ws_async

from Stats import stats_1_MP, stats, read_stats_CSV

####HIST EVAL FUNCTIONS
def exec_order(asset1, asset2, P, quant, buy_sell , fee):
    #Asset1=key asset
    if buy_sell==0:
        asset1=(asset2/P)*quant*(1-fee)
        asset2=asset1*P*(1-quant)
    else:
        asset2=(asset1*P)*quant*(1-fee)
        asset1=(asset2/P)*(1-quant)
    return asset1, asset2


def eval_stop(S, h, o, c, l):
    if o>S:
        if l <= S:
            return True, l
        else:
            return False, None
    if o==S:
        return True, o
    else:
        if h >= S:
            return True, h
        else:
            return False, None

def eval_limit(L, h, o, c, l,buy_sell,eval_mode):
    if eval_mode==1:
        if o>c:
            h=o
            l=c
        else:
            h=c
            l=o
    if buy_sell==0:
        if l <= L:
            return True, L
        else:
            return False, None
    if buy_sell==1:
            if h >= L:
                return True, L
            else:
                return False, None

def eval_order_basic(h, o, c, l, asset1, asset2, quant, buy_sell, order_type, keys):
    eval_mode=config.h_eval_mode
    last_order_price=0.0
    m_fee=config.h_maker_fee
    t_fee=config.h_taker_fee
    match order_type:
        case 0:
            #Market order
            asset1, asset2 = exec_order(asset1, asset2, o, quant, buy_sell, t_fee)
            to_exec =True
            condition=[to_exec]
            last_order_price=o
            return condition, asset1, asset2, last_order_price
        case 1:
            #Limit order
            L=keys[0]
            to_exec, P= eval_limit(L, h, o, c, l,buy_sell,eval_mode)
            if to_exec ==True:
                asset1, asset2 =exec_order(asset1, asset2, o, quant, buy_sell, m_fee)
                last_order_price=P
            condition=[to_exec]
            return condition, asset1, asset2, last_order_price
        case 2:
            #Stop limit order
            L=keys[0]
            if buy_sell==0:
                S=keys[0]*(1+keys[1])
            else:
                S=keys[0]*(1-keys[1])

            stop_triggered, P = eval_stop(S, h, o, c, l)
            to_exec=False
            if stop_triggered ==True:
                to_exec, P= eval_limit(L, h, o, c, l,buy_sell,eval_mode)
                if to_exec ==True:
                    asset1, asset2 =exec_order(asset1, asset2, P, quant, buy_sell, m_fee)
                    last_order_price=P
            condition=[stop_triggered,to_exec]
            return condition, asset1, asset2, last_order_price
        case 3:
            #Stop market order
            S=keys[0]
            to_exec, P = eval_stop(S, h, o, c, l)
            if to_exec ==True:
                asset1, asset2 = exec_order(asset1, asset2, P, quant, buy_sell, t_fee)
                last_order_price=P
            condition=[to_exec]
            return condition, asset1, asset2, last_order_price

def eval_basic_condition(condition,order_type):
    order_update=False
    match order_type:
        case 0:
            #Market order
            if condition[0]==True:
                order_type = 0
                status=1
            else:
                order_type = 0
                status=0
        case 1:
            #Limit order
            if condition[0]==True:
                order_type = 1
                status=1
            else:
                order_type = 1
                status=0
        case 2:
            #Stop limit order
            if condition[0]==True:
                order_type = 2
                status=1
            else:
                order_type = 1
                status=0
                order_update=True
        case 3:
            #Stop Market Order
            if condition[0]==True:
                order_type = 3
                status=1
            else:
                order_type = 3
                status=0
        case _:
            print("Order not found")
    return order_type, status, order_update

def trade_hist(trade_df,asset1, asset2, order):
    order_type=order[0]
    quant=order[1]
    buy_sell=order[2]
    keys=order[3]
    for i, series in trade_df.iterrows():
        h=series['High']
        l=series['Low']
        o=series['Open']
        c=series['Close']
        if order_type in [0,1,2,3]:
            condition, asset1, asset2, last_order_price = eval_order_basic(h, o, c, l, asset1, asset2, quant, buy_sell, order_type, keys)
            order_type, status, order_update = eval_basic_condition(condition, order_type)
            if status==1:
                break
        else:
            print("Error: order type not found")
    return series['Open Time'], status, order_type, asset1, asset2, last_order_price, order_update



class coin_data:
    def init_df(self,interval):
        self.DFK[interval]=read_data_CSV(self.SYMBOL,interval , False, None, None)
        if interval == '1min':
            self.data_start_date=self.DFK[interval].iloc[0]['Open Time']
            self.data_end_date=self.DFK[interval].iloc[-1]['Open Time']

    def init_dfs(self):
        for i in self.intervals:
            self.init_df(i)

    def __init__(self,SYMBOL,chart_queues):
        self.SYMBOL=SYMBOL
        self.intervals=config.intervals
        self.DFK=pd_dict(self.intervals)
        self.init_dfs()
        print('All historic data for '+SYMBOL+' loaded!')
        self.chart_queues=chart_queues
        self.pline_pd=pd.DataFrame

    def i(self,interval):
        return self.DFK[interval]

    def init_stats(self):
        self.stats=stats(self.intervals)
        for i in config.alines_intv:
            self.stats.stats_pd[i]=read_stats_CSV(self.SYMBOL,i,False ,None,None)

    def plot_live_alines(self, intervals, current_interval, trade_time):
        L=[0]
        for i in intervals:
            if i==None:
                L.append(None)
            else:
                index=self.stats.get_index(i, current_interval, trade_time)
                A1,A2=self.stats.get_alines(i,index)
                A1L, A2L=self.stats.get_live_alines(i,index)
                A1=A1L.combine_first(A1L)
                A1.rename(columns={'A1': i+' Average'}, inplace=True)
                L.append(A1)
        self.chart_queues['stats'].put(L, block=False)

    def plot_alines(self, intervals, current_interval, trade_time):
        L=[0]
        for i in intervals:
            if i==None:
                L.append(None)
            else:
                index=self.stats.get_index(i, current_interval, trade_time)
                A1,A2=self.stats.get_alines(i,index)
                A1.rename(columns={'A1': i+' Average'}, inplace=True)
                L.append(A1)
        self.chart_queues['stats'].put(L, block=False)


def get_record(SYMBOL, record_time):
    TD_path=os.getcwd()+'/TradeRecord/'
    if record_time==0:
        ##Get latest by modtime
        None
        start_time=None
        TD_name='Hist trading __TradeRecord__'+start_time
    else:
        #Search for right time
        TD_name='Hist trading __TradeRecord__'+start_time
    try:
        record=read_file(TD_path,TD_name)
        return record
    except:
        print('Record for :', record_time, 'could not be found, proceeding with defaults')
        return None


class hist_data:
    def send_df(self):
        try:
            df=self.coin_data.i(self.current_interval).loc[self.current_index]
        except:
            print(self.trade_time+' - Trade time out of bounds!')
            pass
        #df.set_index(["Open Time"], inplace=True)
        df=df.tail(self.MW)
        self.chart_queues['kline'].put(df, block=False)

    def trade_index(self):
        self.wicks_left=self.end_index-self.current_index[-1]
        #self.coin_data.i(self.current_interval)
        if int(self.current_index[-1]+self.next_wicks) < int(self.end_index):
            self.next_trade_index=(self.current_index+self.next_wicks).difference(self.current_index)
            self.trade_df=self.coin_data.i(self.current_interval).loc[self.next_trade_index]
        else:
            if self.wicks_left !=0:
                self.next_trade_index=(self.current_index+self.wicks_left).difference(self.current_index)
                self.trade_df=self.coin_data.i(self.current_interval).loc[self.next_trade_index]
            else:
                print("End of data reached!")

    def a_lines(self):
        intervals=config.alines_intv
        all_intervals=config.intervals
        ic=config.intervals.index(self.current_interval)
        alines=[]
        for i in intervals:
            index=all_intervals.index(i)
            if index <= ic:
                alines.append(None)
            else:
                alines.append(i)
        self.coin_data.plot_alines(alines, self.current_interval, self.trade_time)

    def forward(self):
        if self.next_wicks < self.wicks_left:
            self.current_index=self.current_index+self.next_wicks
        else:
            self.current_index=self.current_index+self.wicks_left
        self.send_df()
        self.trade()
        #self.coin_data.eval_predict_line(self.current_interval, self.next_trade_index)
        #self.log
        self.trade_time=self.coin_data.i(self.current_interval).loc[self.current_index].iloc[-1]["Open Time"]
        self.a_lines()

    def backward(self):
        wicks_left_at_start=self.current_index[-1]-self.next_wicks
        if wicks_left_at_start > self.next_wicks:
            self.current_index= pd.RangeIndex.from_range(range(0,(self.current_index[-1]-self.next_wicks+1)))
        else:
            self.current_index= pd.RangeIndex.from_range(range(0,(self.current_index[-1]-wicks_left_at_start+1)))
            self.trade_time=self.coin_data.i(self.current_interval).loc[self.current_index].iloc[-1]["Open Time"]
            self.send_df()
            self.a_lines()

    def trade(self):
        if self.wicks_left !=0:
            match self.trade_method:
                case 0:
                    if self.order_active==True:
                        order=[self.order_type, 1, self.buy_sell, self.keys]
                        #[order_type,quant,buy_sell, keys]
                        time, status, order_type, self.asset1, self.asset2, price, order_update = trade_hist(self.trade_df, self.asset1, self.asset2, order)
                        self.status=[time, status, order_type, self.asset1, self.asset2, price, order_update]
                        self.send_status=True
                    None 
                case 1:
                    None 
                    ### Inch UP ###
                case 2:
                    None 
                    ### Fee Digger ###
                case 4:
                    None 
                    ### predict line eval ###
                    for i, series in self.trade_df.iterrows():
                        #asset1, asset2=self.PLINE_ALGO.eval_wick(series, self.asset1, self.asset2)
                        None
                    #self.send_status()
            self.trade_index()
        else:
            print("Last wick reached!")

    def place_order(self, O):
        self.order_active=True
        self.order_type=O[1]
        self.buy_sell=O[2]
        self.keys=O[3]

    def delete_order(self):
        self.order_active=False

    def __init__(self, coin_data, current_interval, trade_time, chart_queues):
        self.current_interval=current_interval
        self.d_current_interval=self.current_interval
        self.trade_method=config.default_trade_method
        self.d_trade_method=self.trade_method
        self.coin_data=coin_data
        self.MW=config.chart_max_wicks

        self.stop=False


        self.a_intv=config.a_intv
        self.a_intv1=config.a_intv1
        self.a_intv2=config.a_intv2

        self.intervals=config.intervals
        self.order_active=False
        self.send_status=False

        self.pline_start=None
        self.pline_end=None
        #self.pline_pd=pd.DataFrame
        self.pline_init=False

        self.asset1=0
        self.asset2=config.h_start_money

        self.next_wicks=config.default_next_wicks
        self.trade_time=trade_time

        self.chart_queues=chart_queues

        self.change_trade_time=False
        self.d_trade_time=None

        self.r=False


        self.end_index=self.coin_data.i(self.current_interval).index[-1]
        self.current_index=get_index_before(self.coin_data.i(self.current_interval), self.trade_time)
    
        self.send_df()
        self.order_update=False
        self.coin_data.init_stats()
        self.a_lines()
        self.trade_index()

    async def update_settings(self):
        while True:
            if self.stop==True:
                break
            if self.d_current_interval!=self.current_interval:
                self.d_current_interval=self.current_interval
                self.end_index=self.coin_data.i(self.current_interval).index[-1]
                self.current_index=get_index_before(self.coin_data.i(self.current_interval), self.trade_time)
                self.trade_time=self.coin_data.i(self.current_interval).loc[self.current_index].iloc[-1]["Open Time"]

                self.send_df()
                self.a_lines()
                self.trade_index()

            if self.change_trade_time==True:
                old_time=self.trade_time
                old_index=self.current_index

                try:
                    self.trade_time=self.d_trade_time
                    self.current_index=get_index_before(self.coin_data.i(self.current_interval), self.trade_time)
                    self.trade_time=self.coin_data.i(self.current_interval).loc[self.current_index].iloc[-1]["Open Time"]
                except:
                    self.trade_time=old_time
                    self.current_index=old_index
                    print(self.d_trade_time+' - Trade time out of bounds!')
                    pass

                self.send_df()
                self.a_lines()
                self.trade_index()

                self.change_trade_time=False

            if self.d_trade_method!=self.trade_method:
                self.trade_method=self.d_trade_method

            if self.pline_init==True:
                self.pline_init=False

            if self.r==True:
                #self.r=False
                break
            await asyncio.sleep(0.001)
    def sstop(self):
        self.stop=True
    async def run(self):
        self.stop=False
        await asyncio.gather(self.update_settings())


############################################LIVE TRADE CLASSES###################################
class live_data: 
    def append_dfs(self,series,interval):
        T=datetime.datetime.fromtimestamp(int(series["t"])/1000)
        D={'Open Time':T,'Open':float(series["o"]),'High':float(series["h"]),'Low':float(series["l"]),'Close':float(series["c"]),'Volume':float(series["v"]),'Close Time':float(series["T"]),'Quote Asset Volume':float(series["q"]),'Number of Trades':float(series["n"]),'Taker Buy Base Asset Volume':float(series["V"]),'Taker Buy Quote Asset Volume':float(series["Q"]),'Ignore':series["B"]}
        last_value=self.DFK[interval].index[-1]
        last_time=self.DFK[interval].iloc[-1]['Open Time']
        row=pd.DataFrame(D,index=[last_value+1])
        #row.set_index(["Open Time"], inplace=True)
        if last_time != T:
            self.DFK[interval]=row.combine_first(self.DFK[interval])
        if self.GUI==True:
            if interval==self.current_interval:
                self.send_df()
        if config.live_stats==True:
            #self.append_stats(row, interval)
            if interval in config.gstats_intv:
                None
                #self.coin_data.send_live_gstats(self.current_interval, self.trade_time)
            if interval in config.alines_intv:
                #self.coin_data.plot_live_alines(interval)
                None

    def send_df(self):
        if self.GUI==True:
            if config.live_load_hist==True:
                df1=self.DFK[self.current_interval]
                df2=self.coin_data.i(self.current_interval)
                last_value=df2.index[-1]
                df1.index=df1.index+last_value
                df=df2.combine_first(df1)
            else:
                df=self.DFK[self.current_interval]
            df=df.tail(self.MW)
            self.chart_queues['kline'].put(df.tail(self.MW), block=False)

    def send_tick(self,tick):
        self.chart_queues['tick'].put(tick, block=False)

    def init_df(self,interval):
        TT=datetime.datetime.now()
        self.trade_time=TT
        pwd=os.getcwd()
        STi=read_file(pwd+"/CSVData",self.SYMBOL+"_Last_Modified")
        start_time = datetime.datetime.strptime(STi, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.now()

        #df_1=read_data_CSV(self.SYMBOL,interval , False, ST, ET)
        df_2=get_data(self.SYMBOL, interval, start_time, end_time, False)
        #USE WS CLIENT TO GET DATA?
        #Client.close in get_data?
        df_2["Open Time"] = pd.to_datetime(df_2["Open Time"])
        self.DFK[interval]=df_2
        #self.DFK[interval].set_index(["Open Time"], inplace=True)

    def init_dfs(self):
        for i in self.intervals:
            if i!=self.current_interval:
                self.init_df(i)

    def calc_live_stats(self):
        for interval in self.intervals:
            self.coin_data.stats.calc_stats_live(self.DFK[interval], interval)

    def append_stats(self, wick_df, interval):
        self.coin_data.stats.append_stats_single(wick_df, interval)

    def a_lines(self):
        intervals=config.alines_intv
        all_intervals=config.intervals
        ic=config.intervals.index(self.current_interval)
        alines=[]
        for i in intervals:
            index=all_intervals.index(i)
            if index <= ic:
                alines.append(None)
            else:
                alines.append(i)
        self.coin_data.plot_live_alines(alines, self.current_interval, self.trade_time)

    def __init__(self,GUI:bool, SYMBOL, ws_queues, chart_queues, coin_data):
        self.SYMBOL=SYMBOL
        self.current_interval=config.default_interval
        self.d_current_interval=self.current_interval
        self.d_SYMBOL=self.SYMBOL
        self.intervals=config.intervals
        self.GUI=GUI
        self.MW=config.chart_max_wicks
        if config.live_load_hist==True:
            self.coin_data=coin_data

        self.kline_intervals=config.klines_intv
        self.intv_dict=dict(zip(self.kline_intervals, self.intervals))
        self.ws_queues=ws_queues
        self.chart_queues=chart_queues
        self.DFK=pd_dict(self.intervals)
        self.r=False
        self.stop=False

        self.init_df(self.current_interval)
        self.send_df()
        self.klines=list_dict(self.intervals)

    async def collect_tick(self):
        while True:
            if self.stop==True:
                break
            if self.ws_queues['bookTicker'].empty()==False:
                tick= self.ws_queues['bookTicker'].get(block=False)
                TT=[float(tick['a']),float(tick['b'])]
                self.send_tick(TT)
            await asyncio.sleep(0.001)

    async def collect_klines(self):
        while True:
            if self.stop==True:
                break
            if self.ws_queues['kline'].empty()==False:
                K= self.ws_queues['kline'].get(block=False)
                df_K=pd.DataFrame(K)
                n=0
                for i,series in df_K.iterrows():
                    interval=self.intv_dict[series['i']]
                    if series['x']==True:
                        self.append_dfs(series,interval)
                    else:
                        None
                        #Kline tick
                        #if interval==self.current_interval:
                        #    t=datetime.datetime.now()
                        #    T={'time':t,'price:'float(series["c"]),'volume':float(series["v"])}
                        #    TT=pd.DataFrame(T,index=[0])
            if self.r==True:
                #self.r=False
                break
            await asyncio.sleep(0.001)

    async def update_settings(self):
        self.init_dfs()
        print('All dfs loaded!')
        if config.live_stats==True:
            self.calc_live_stats()
            #self.coin_data.send_live_gstats(self.current_interval, self.trade_time)
            self.a_lines()
        while True:
            if self.stop==True:
                break
            if self.d_current_interval!=self.current_interval:
                self.send_df()
                self.d_current_interval=self.current_interval
            if self.d_SYMBOL!=self.SYMBOL:
                self.d_SYMBOL=self.SYMBOL
                self.DFK=pd_dict(self.intervals)
                self.init_df(self.current_interval)
                self.init_dfs()
                self.send_df()
            if self.r==True:
                #self.r=False
                break
            await asyncio.sleep(0.001)

    def sstop(self):
        self.stop=True
    async def run(self):
        self.stop=False
        await asyncio.gather(self.update_settings(), self.collect_klines(), self.collect_tick())
    
def mp_qdict(q_list):
    queues=[]
    for S in q_list:
        queues.append(Queue())
    QQ=dict(zip(q_list,queues))
    return QQ

class data_module:
    def __init__(self, GUI, trade_platform, trade_time, order_queues, ws_queues,chart_queues,settings_queue, trade_queues,remote): 
        self.SYMBOL=config.default_symbol
        self.trade_method=config.default_trade_method
        self.current_interval=config.default_interval
        self.next_wicks=config.h_next_wicks

        self.GUI=GUI
        self.coin_data=coin_data(self.SYMBOL, chart_queues)

        self.trade_platform=trade_platform
        self.trade_time=trade_time
        self.ws_queues=ws_queues
        self.chart_queues=chart_queues
        self.settings_queue=settings_queue
        self.trade_queues=trade_queues
        self.order_queues=order_queues
        self.trade_plat()
        self.stop=False

    def switch_settings(self):
        match self.trade_platform:
            case 0:
                self.hist_data.current_interval=self.current_interval
                self.hist_data.SYMBOL=self.SYMBOL
                self.hist_data.trade_method=self.trade_method
                self.hist_data.next_wicks=self.next_wicks
            case 1:
                self.live_data.current_interval=self.current_interval
                self.live_data.SYMBOL=self.SYMBOL
                self.live_data.trade_method=self.trade_method

    def send_assets(self):
        B=[0,self.hist_data.asset1, self.hist_data.asset2]
        self.trade_queues['tradecomms_from_hist'].put(B)

    def change_trade_time(self, string):
        out_string=''
        out_string_year=''
        parsed_date=[]
        l=len(string)
        n=1
        for c in string:
            if c.isdigit():
                #if c != '0':
                out_string += c
            if c == '-':
                parsed_date.append(int(out_string))
                out_string=''
            if n==l:
                parsed_date.append(int(out_string))
            n=n+1
        if type(self.hist_data.trade_time) == str:
            DT = datetime.datetime.strptime(self.hist_data.trade_time, "%Y-%m-%d %H:%M:%S")
        else:
            DT=self.hist_data.trade_time
        match len(parsed_date):
            case 1:
                #go to XX of that month
                try:
                    DT=DT.replace(day=parsed_date[0])
                    self.hist_data.d_trade_time = datetime.datetime.strftime(DT, "%Y-%m-%d %H:%M:%S")
                    self.hist_data.change_trade_time=True
                except:
                    print('Date invalid')
                    pass
            case 2:
                #if 02-01 go to date in this year
                try:
                    DT=DT.replace(month=parsed_date[0], day=parsed_date[1])
                    self.hist_data.d_trade_time = datetime.datetime.strftime(DT, "%Y-%m-%d %H:%M:%S")
                    self.hist_data.change_trade_time=True
                except:
                    print('Date invalid')
                    pass
            case 3:
                #if 20XX-02-01 - go to that date
                try:
                    DT=DT.replace(year=parsed_date[0], month=parsed_date[1], day=parsed_date[2])
                    self.hist_data.d_trade_time = datetime.datetime.strftime(DT, "%Y-%m-%d %H:%M:%S")
                    self.hist_data.change_trade_time=True
                except:
                    print('Date invalid')
                    pass
            case _:
                print(parsed_date)
                print('date could not be parsed!')

    def parse_trade_comms(self, comm):
        if type(comm)==list:
            match comm[0]:
                case 4:
                    ## [Active, Order Type, Buy_Sell, Keys]
                    self.hist_data.coin_data.pline_pd=comm[1]
                    self.hist_data.pline_start=comm[2]
                    self.hist_data.pline_end=comm[3]
                    self.hist_data.pline_init=True
                case 7:
                    self.change_trade_time(comm[1])
                case _:
                    print("Trade comm type not found!")
        else:
            match comm:
                case 0:
                    self.send_assets()
                case 2:
                    self.hist_data.forward()
                case 3:
                    self.hist_data.backward()
                case 5:
                    self.hist_data.a_lines()
                case 6:
                    self.hist_data.delete_order()
                    print('Order Deleted')
                case 8:
                    self.hist_data.gstats()
                case _:
                    print("Trade comm type not found??")
    def place_hist_order(self, O):
        if type(O)== int:
            match O:
                case 2:
                    self.hist_data.delete_order()
                case _:
                    print('Hist order command not found!')
        if type(O)==list:
            command=O[0]
            del O[0]
            match command:
                case 5:
                    #Cancel order and replace with O
                    self.hist_data.place_order(O)
                case _:
                    print('Hist order command not found!')

    def stop_hist(self):
        self.hist_data.sstop()
    def hist_init(self):
        self.hist_data= hist_data(self.coin_data, self.current_interval, self.trade_time, self.chart_queues)
    def hist_restart(self):
        self.stop_hist()
        self.hist_init()

    def stop_live(self):
        self.live_data.sstop()
    def live_init(self):
        self.live_data = live_data(self.GUI, self.SYMBOL, self.ws_queues, self.chart_queues, self.coin_data)
    def live_restart(self):
        self.stop_live()
        self.live_init()

    def trade_plat(self):
        match self.trade_platform:
            case 0:
                self.hist_init()
                self.r=False
            case 1:
                self.live_init()
                self.r=False

    def restart_lv(self):
        self.r=True
        self.trade_plat()

    async def run_lv(self):
        while True:
            if self.stop==True:
                break
            if self.r != True:
                if self.trade_platform ==0:
                   await self.hist_data.run()
                else:
                   await self.live_data.run()
                await asyncio.sleep(0.001)

    async def run_hist(self):
        while True:
            if self.trade_platform==0:
                if self.stop==True:
                    break
                if self.hist_data.send_status == True:
                    self.order_queues['order_status_from_hist'].put(self.hist_data.status, block=False)
                    self.hist_data.send_status=False

                if self.order_queues['orders_to_hist'].empty() == False:
                    O=self.order_queues['orders_to_hist'].get(block=False)
                    self.place_hist_order(O)

                if self.trade_queues['tradecomms_to_hist'].empty() == False:
                    T=self.trade_queues['tradecomms_to_hist'].get(block=False)
                    self.parse_trade_comms(T)
            await asyncio.sleep(0.001)
    async def update_settings(self):
        while True:
            if self.stop==True:
                break
            if self.settings_queue.empty()==False:
                S= self.settings_queue.get(block=False)
                if self.SYMBOL != S[0]:
                    self.SYMBOL=S[0]
                    self.switch_settings()
                    self.coin_data=coin_data(self.SYMBOL, self.chart_queues)
                    self.restart_lv()

                if self.current_interval != S[1]:
                    self.current_interval = S[1]
                    self.switch_settings()

                if self.trade_method != S[2]:
                    self.trade_method = S[2]
                    self.switch_settings()

                if self.trade_platform != S[3]:
                    if self.trade_platform ==0:
                        self.stop_hist()
                        #Stop and init?
                    else:
                        self.stop_live()
                    self.trade_platform = S[3]
                    self.restart_lv()

                if self.next_wicks != S[4]:
                    self.next_wicks = S[4]
                    self.switch_settings()

            await asyncio.sleep(0.001)

    def stop(self):
        self.stop=True
    async def rrun(self):
        await asyncio.gather(self.run_lv(), self.update_settings(), self.run_hist())
    def run(self):
        self.stop=False
        asyncio.run(self.rrun())
    def restart(self):
        self.stop()
        self.run()

class ws_module:
    def __init__(self, ws_queues, trade_queues, order_queues, settings_queue): 
        self.SYMBOL=config.default_symbol
        self.trade_method=config.default_trade_method
        self.current_interval=config.default_interval

        self.settings_queue=settings_queue
        self.trade_queues=trade_queues
        self.order_queues=order_queues
        self.ws_queues=ws_queues
        self.sstop=False

        match config.ws_method:
            case 0:
                self.WS=ws_client_hybrid(self.SYMBOL,ws_queues)
            case 1:
                self.WS=ws_async(self.SYMBOL, ws_queues)
        ##LIVE TRADE ALGOS GO HERE
        self.r_ws=False
        self.connection_lost=False
        #Send a restart to LV if happens?

    def restart_ws(self):
        self.r_ws=True
        self.WS=ws_client_hybrid(self.SYMBOL,self.ws_queues)
        print("Restarted WS module!")
        self.r_ws=False

    def parse_trade_comms(self, comm):
        match comm:
            case 0:
                asset1,asset2=self.WS.get_assets()
                B=[0,asset1, asset2]
                self.trade_queues['tradecomms_from_live'].put(B)
            case _:
                print("Trade comm type not found(Live)")

    def place_order(self, O):
        if type(O)== int:
            match O:
                case 1:
                    self.WS.cancel_current_order()
                case 2:
                    self.WS.cancel_all_orders()
                case 3:
                    self.WS.market_buy()
                case 4:
                    self.WS.market_sell()
                case _:
                    print('LIVE WS trade command not found!')
        if type(O)==list:
            command=O[0]
            del O[0]
            match command:
                case 5:
                    #Place order O
                    self.WS.place_order(O)
                case 6:
                    #Cancel order and replace with O
                    self.WS.replace_order(O)
                case _:
                    print('LIVE WS trade command not found!')

    async def run_ws(self):
        while True:
            if self.sstop==True:
                break
            if self.r_ws != True:
                if self.trade_queues['tradecomms_to_live'].empty() == False:
                    T=self.trade_queues['tradecomms_to_live'].get(block=False)
                    self.parse_trade_comms(T)

                if self.order_queues['orders_to_live'].empty() == False:
                    O=self.order_queues['orders_to_live'].get(block=False)
                    self.place_order(O)

                if self.WS.status_update == True:
                    S=self.WS.get_status()
                    self.order_queues['order_status_from_live'].put(S, block=False)

                if self.WS.ws_restart==True:
                    self.restart_ws()

                if self.settings_queue.empty()==False:
                    S=self.settings_queue.get(block=False)
                    if self.SYMBOL != S[0]:
                        self.SYMBOL=S[0]
                        self.WS.SYMBOL=self.SYMBOL
                        self.restart_ws()
            await asyncio.sleep(0.001)
    def stop(self):
        self.sstop=True
    async def rrun(self):
        await asyncio.gather(self.run_ws(), self.WS.run())
    def run(self):
        asyncio.run(self.rrun())
    def restart(self):
        self.stop()
        self.run()
class MP_wrapper:
    def __init__(self,GUI,trade_platform,trade_time): 
        CQ=['kline','tick' ,'stats', 'order_status']
        TQ=['tradecomms_to_live', 'tradecomms_from_live', 'tradecomms_to_hist', 'tradecomms_from_hist']
        OQ=['orders_to_live', 'order_status_from_live', 'orders_to_hist', 'order_status_from_hist']
        self.trade_queues=mp_qdict(TQ)
        self.order_queues=mp_qdict(OQ)
        self.chart_queues=mp_qdict(CQ)

        self.trade_platform=trade_platform
        self.ws_queues=mp_qdict(config.ws_stream_names)
        self.ws_settings_queue=Queue()

        self.data_settings_queue=Queue()
        self.DM1=data_module(GUI, self.trade_platform, trade_time, self.order_queues, self.ws_queues, self.chart_queues, self.data_settings_queue, self.trade_queues, False)
        self.p2_DM1= Process(target=self.DM1.run, daemon=True)
        self.p2_DM1.start()

        self.stop=False


    def parse_remote_comms(self, message):
        M=message(0)
        del message[0]
        match M:
            case 0:
                self.trade_queues['from_live'].put(message, block=False)
            case 2:
                self.order_queues['from_live'].put(message, block=False)

    def init_ws(self):
        self.WTM=ws_module(self.ws_queues, self.trade_queues, self.order_queues, self.ws_settings_queue)
        self.p1_WTM = Process(target=self.WTM.run, daemon=True)
        print('WS initiated')
        self.p1_WTM.start()

    def kill_ws(self):
        try:
            self.p1_WTM.kill()
        except:
            None

    def kill_data(self):
        self.p2_DM1.kill()
        self.p2_DM1.join()

    def re_data(self):
        self.kill_data()
        self.p2_DM1= Process(target=self.DM1.run, daemon=True)
        self.p2_DM1.start()

class trade_live:
    #Remote keys
    # 0 - trade queues
    # 1 - settings queues
    # 2 - order queues
    def send_trade_comms(self, command:int):
                    ## [Active, Order Type, Buy_Sell, Keys]
        if command in [1,4,7]:
            if command==1:
                None

            if command==4:
                self.pline_pd=pd.DataFrame(self.LChart.points, columns=['Open Time','Predict'])
                self.pline_start=self.pline_pd['Open Time'].iloc[0]
                self.pline_end=self.pline_pd['Open Time'].iloc[-1]

                C=[4, self.pline_pd, self.pline_start, self.pline_end]
                self.trade_queues['tradecomms_'+self.send_platform].put(C)
                line_pd=pd.DataFrame
                line_pd=self.pline_pd
                self.LChart.predict_line.set(line_pd)
            if command==7:
                time_change=[7,self.LChart.change_TD]
                self.trade_queues['tradecomms_'+self.send_platform].put(time_change)
        else:
            self.trade_queues['tradecomms_'+self.send_platform].put(command)
        #0 - get assets [0, asset1, asset2]
        #1 - send order
        #2 - hist-forward
        #3 - hist_backward
        #4 - send predict line
        #5 - cancel all open orders
        #6 - get GSTATS
        #10 - wick


    def parse_trade_comms(self, comm):
        match comm[0]:
            case 0:
                self.asset1=comm[1]
                self.asset2=comm[2]
                if self.asset1>self.asset2:
                    self.asset1_held=True
                    self.LChart.asset1_held=True
                else:
                    self.asset1_held=False
                    self.LChart.asset1_held=False
                if self.GUI==True:
                    self.write_asset_table()
            case _:
                print("Trade comm type not found!")

    def write_asset_table(self):
        A1=round(self.asset1,2)
        A2=round(self.asset2,2)
        self.LChart.write_asset_table(self.S1, self.S2, A1, A2, self.ch1, self.ch2)

    def read_chart_order(self):
        self.buy_sell, self.order_type, self.keys = self.LChart.line_order.read()

    def delete_chart_order(self):
        self.LChart.line_order.delete('Lmfao')


    def init_platform(self, trade_time):
        match self.trade_platform:
            case 0:
                self.MP_wrapper.kill_ws()
                self.send_platform='to_hist'
                self.recv_platform='from_hist'
                self.trade_time=trade_time
                self.chart_type=0
                self.forward=False
                self.backward=False
                self.next_wicks=config.default_next_wicks
                self.log=logs('Hist trading ')
                self.send_trade_comms(0)

            case 1:

                #binance live
                self.send_platform='to_live'
                self.recv_platform='from_live'
                self.trade_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
                self.chart_type=1
                self.log=logs('Live trading ')
                self.MP_wrapper.init_ws()
                self.send_trade_comms(0)
        self.asset1_held=False

    def change_trade_platform(self):
        #self.MP_wrapper.re_data()
        self.cplatform =True
        match self.trade_platform:
            case 0:
                self.init_platform(self.trade_time)
            case 1:
                self.init_platform(None)
        self.cplatform =False
        #self.LChart.change_trade_platform(self.trade_platform)

    def __init__(self): 
        pwd=os.getcwd()
        self.trade_method=config.default_trade_method
        self.keys=[]
        self.buy_sell=int
        self.order_type=int
        self.trade_time=read_file(pwd+"/CSVData",config.default_symbol+"_Last_Modified")

        self.asset1=0.0
        self.asset2=0.0

        self.last_asset1=1.0
        self.last_asset2=1.0

        self.ch1=0.0
        self.ch2=0.0

        self.GUI=True
        self.set_last_order=config.set_last_order
        self.trades_made=0
        self.SYMBOL=config.default_symbol
        self.S1,self.S2=return_symb(self.SYMBOL)
        self.current_interval=config.default_interval
        self.trade_platform=0
        self.trade_record=[]

        self.predict_line_init=False
        self.pline_start=None
        self.pline_end=None
        self.pline_pd=pd.DataFrame

        self.alines=None
        self.k0_sent=False
        self.order_active=False

        self.order_time=None
        self.order_price=None
        self.order_status=None

        self.MP_wrapper=MP_wrapper(self.GUI, self.trade_platform, self.trade_time)
        self.chart_queues=self.MP_wrapper.chart_queues
        self.trade_queues=self.MP_wrapper.trade_queues
        self.data_settings_queue=self.MP_wrapper.data_settings_queue

        self.order_queues=self.MP_wrapper.order_queues
        self.ws_settings_queue=self.MP_wrapper.ws_settings_queue

        self.init_platform(self.trade_time)
        self.cplatform=False
        self.LChart=live_chart(self.chart_type, self.trade_platform)

    def send_k0(self):
        if self.k0_sent == False:
            k0=self.live_df.iloc[-1]['Close']
            self.LChart.keys[0]
            self.k0_sent=True


    def calculate_change(self):
        print(self.asset1)
        print(self.asset2)

        print(self.last_asset1)
        print(self.last_asset2)
        self.trades_made=self.trades_made+1
        if self.trades_made > 1:
            if self.asset1_held==False:
                try:
                    C=(self.asset2/self.last_asset2)-1
                    self.ch2=100*round(C,3)
                    self.last_asset2=self.asset2
                except:
                    None
            else:
                C=(self.asset1/self.last_asset1)-1
                self.ch2=100*round(C,3)
                self.last_asset1=self.asset1


    def send_settings_to_data(self):
        S=[self.SYMBOL, self.current_interval, self.trade_method, self.trade_platform, self.next_wicks]
        self.data_settings_queue.put(S, block=False)

    def send_settings_to_ws(self):
        S=[self.SYMBOL, self.current_interval, self.trade_method, self.trade_platform]
        self.ws_settings_queue.put(S, block=False)

    def update_alines(self, alines):
        n=0
        for df in alines:
            if n==0:
                self.LChart.avg_line.set(df)
            if n==1:
                self.LChart.avg_line1.set(df)
            if n==2:
                self.LChart.avg_line2.set(df)
            n=n+1

    def change_trade_method(self):
        self.MP_wrapper.trade_platform=self.trade_platform
        match self.trade_method:
            case 0:
                #Manual
                None
            case _:
                print('Trade method not found!', sefl.trade_method)

        self.send_settings_to_data()
        self.send_settings_to_ws()

    def send_order(self):
        order=[5,  self.order_active, self.order_type, self.buy_sell, self.keys]
        self.order_queues['orders_'+self.send_platform].put(order)

    def delete_current_order(self):
        self.order_queues['orders_'+self.send_platform].put(2)

    def load_from_record(self, record_name):
        #Load latest for that coin
        if record_name==0:
            record=get_record(self.coin_data.SYMBOL, 0)
        else:
            record=get_record(self.coin_data.SYMBOL, record_name)
            #Get last line of JSON file
            #D={'Time':T, 'Order Status':self.order_status, 'Order Type':self.order_type,'Buy_Sell':self.buy_sell,'Order Price':self.order_price, f'{self.S1}':self.asset1, f'{self.S2}':self.asset2, 'Change':self.ch2}
        self.asset1=record['Asset']
        self.asset2=record['Asset']
        self.trade_time=record['Time']

    async def recieve_trade_comms(self):
        while True:
            if self.stop==True:
                break
            if self.trade_queues['tradecomms_'+self.recv_platform].empty() == False:
                c =self.trade_queues['tradecomms_'+self.recv_platform].get(block=False)
                self.parse_trade_comms(c)
            await asyncio.sleep(0.001)

    async def recieve_order_status(self):
        while True:
            if self.stop==True:
                break
            if self.order_queues['order_status_'+self.recv_platform].empty() == False:
                O = self.order_queues['order_status_'+self.recv_platform].get(block=False)
                self.order_time=O[0]
                self.order_status=O[1]
                self.order_type=O[2]
                D={'Symbol':self.SYMBOL, 'Time':self.order_time, 'Order Status':self.order_status, 'Order Type':self.order_type}
                self.log.write_record(D)

                if self.asset1 != 0.0:
                    self.last_asset1=self.asset1
                if self.asset2 != 0.0:
                    self.last_asset2=self.asset2

                self.asset1=O[3]
                self.asset2=O[4]
                self.order_price=O[5]
                update_order=O[6]

                if self.order_status==1:
                    if self.buy_sell==0:
                        mb=' Bought '
                        ass=self.asset1
                    else:
                        mb=' Sold '
                        ass=self.asset2
                    self.LChart.set_marker(self.order_time, self.buy_sell)

                    if self.asset1>self.asset2:
                        self.asset1_held=True
                        self.LChart.asset1_held=True
                    else:
                        self.asset1_held=False
                        self.LChart.asset1_held=False
                    if self.GUI==True:
                        self.write_asset_table()

                    if self.set_last_order==True:
                        self.LChart.last_order_line.set(last_order_price,self.buy_sell)

                    self.calculate_change()
                    self.delete_chart_order()
                    T = datetime.datetime.strftime(self.order_time, "%Y-%m-%d %H:%M:%S")
                    M=T+': Order executed!'+ mb+' '+str(round(ass,2))+' '+self.S1+' at :'+str(self.order_price)
                    #Now change asset held!
                    #Retunr last illocs for V1 V2
                    self.log.write(M)
                    D={'Symbol':self.SYMBOL, 'Time':T, 'Order Status':self.order_status, 'Order Type':self.order_type,'Buy_Sell':self.buy_sell,'Order Price':self.order_price, f'{self.S1}':self.asset1, f'{self.S2}':self.asset2, 'Change':self.ch2}
                    self.log.write_record(D)

                if update_order==True:
                    self.delete_chart_order()
                    self.LChart.s_set(self.order_type)

                self.write_asset_table()
                #self.send_order_to_chart()
            await asyncio.sleep(0.001)


    async def recieve_order(self):
        while True:
            if self.stop==True:
                break
            if self.order_queues[self.recv_platform].empty() == False:
                O = self.order_queues[self.recv_platform].get(block=False)
            await asyncio.sleep(0.001)

    async def recieve_chart_updates(self):
        while True:
            if self.stop==True:
                break
            if self.chart_queues['kline'].empty() == False:
                self.live_df =self.chart_queues['kline'].get(block=False)
                if self.live_df.empty !=True:
                    self.live_df.set_index(['Open Time'], inplace=True)
                    self.LChart.set_chart(self.live_df)
                    if self.trade_platform==0:
                        if config.hscreenshot==True:
                            TM=self.live_df.iloc[-1].index
                            trade_time = datetime.datetime.strftime(TM, "%Y-%m-%d %H:%M:%S")
                            self.LChart.screenshot('Hist__'+trade_time)
                else:
                    print(self.live_df)
                    print('DF could not be updated!')

            if self.chart_queues['tick'].empty() == False:
                tick =self.chart_queues['tick'].get(block=False)
                self.LChart.update_tick(tick)

            if self.chart_queues['stats'].empty() == False:
                stats =self.chart_queues['stats'].get(block=False)
            await asyncio.sleep(0.001)

    async def read_chart_settings(self):
        while True:
          if self.stop==True:
              break
          d_activ, d_keys, d_SYMBOL, d_current_interval, d_trade_method, d_trade_platform, d_pline, =self.LChart.read_settings()
          if self.LChart.r_chart==True:
              if self.live_df.empty !=True:
                  self.LChart.restart_chart(self.live_df)
              self.send_trade_comms(8)
              self.write_asset_table()
              if self.order_active==True:
                  self.LChart.keys=self.keys
                  self.LChart.s_set(self.order_type)
                  self.LChart.line_order.activate('Lmfao')

          if d_pline != self.predict_line_init:
              self.predict_line_init=d_pline
              self.send_trade_comms(4)
              self.LChart.predict_line_init=False

          if d_SYMBOL != self.SYMBOL:
              self.SYMBOL=d_SYMBOL
              self.LChart.keys_init=False
              self.send_settings_to_data()
              self.send_settings_to_ws()
              self.S1,self.S2=return_symb(self.SYMBOL)
              self.send_trade_comms(0)
              self.write_asset_table()

          if d_current_interval != self.current_interval:
              self.current_interval=d_current_interval
              self.send_settings_to_data()

          if d_trade_method != self.trade_method:
              self.trade_method=d_trade_method
              self.change_trade_method()

          if d_trade_platform != self.trade_platform:
              self.trade_platform=d_trade_platform
              self.change_trade_platform()
              self.send_settings_to_data()


          if d_activ != self.order_active:
              self.order_active=d_activ
              d_buy_sell, d_order_type, d_keys= self.LChart.line_order.read()
              if d_buy_sell != self.buy_sell:
                  self.buy_sell=d_buy_sell

              if d_order_type != self.order_type:
                  self.order_type = d_order_type

              if d_keys != self.keys:
                  self.keys = d_keys
              if self.order_active==True:
                  #self.send_trade_comms(1)
                  self.send_order()
              else:
                  self.delete_current_order()
                  #self.send_trade_comms(6)
          await asyncio.sleep(0.001)

    async def read_hist_chart_settings(self):
        while True:
            if self.stop==True:
                break
            if self.trade_platform==0:
              if self.LChart.next_wicks != self.next_wicks:
                  self.next_wicks=self.LChart.next_wicks
                  self.send_settings_to_data()

              if self.LChart.forward == True:
                  self.send_trade_comms(2)
                  self.LChart.forward=False

              if self.LChart.backward == True:
                  self.send_trade_comms(3)
                  self.LChart.backward=False

              if self.LChart.change_time == True:
                  self.send_trade_comms(7)
                  self.LChart.change_time =False
            await asyncio.sleep(0.001)
    def sstop(self):
        self.stop=True
    async def display_chart(self):
        await asyncio.gather(self.LChart.display_chart(), self.read_chart_settings(), self.recieve_trade_comms(), self.recieve_order_status(), self.recieve_chart_updates() ,self.recieve_order_status(),  self.read_hist_chart_settings())

    def run(self):
        self.stop=False
        asyncio.run(self.display_chart())
