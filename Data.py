from binance.client import Client
import pandas as pd
import datetime
import config, csv
import json
import os

def write_file(data,path,filename):
    if not os.path.exists(path):
        os.makedirs(path)    
    with open(path+'/'+filename,'w') as file:
        json.dump(data,file)
        file.close()

def read_file(path,filename):
    with open(path+'/'+filename,'r') as file:
        data=json.load(file)
        file.close()
    return data

class logs:
    def write(self, message):
        time = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        M=time+'__'+message
        self.log.append(M)
        write_file(self.log, self.path, self.filename)

    def write_record(self,L):
        self.TD.append(L)
        write_file(self.TD, self.TD_path, self.TD_filename)

    def __init__(self, name):
        start_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

        self.log=[]
        self.path=os.getcwd()+'/LOGS/'
        self.filename=name+'__'+start_time

        self.TD=[]
        self.TD_path=os.getcwd()+'/TradeRecord/'
        self.TD_filename=name+'__TradeRecord__'+start_time


def return_symb(SYMBOL):
    #return individual coin symbols form a pair
    s1=''
    s2=''
    ic=config.individual_coins
    for c in SYMBOL:
        s1 += c
        if s1 in ic:
            S1=s1
    if S1 in SYMBOL:
        SYMBOL=SYMBOL.replace(S1,'')
    S2=SYMBOL
    return S1, S2


def pd_dict(pd_list):
    P=[]
    for S in pd_list:
        P.append(pd.DataFrame())
    PD=dict(zip(pd_list,P))
    return PD

def list_dict(l_list):
    l=[]
    for s in l_list:
        l=[]
        l.append(l)
    ll=dict(zip(l_list, l))
    return ll

def float_dict(l):
    P=[]
    for S in l:
        P.append(float)
    PD=dict(zip(l,P))
    return PD


def init_client():
    client = Client(config.API_KEY, config.API_SECRET)
    return client

#Parse interval string into dictionary with int and period
def parse_timeframe(interval):
    nostring=""
    period=""
    for c in interval:
        if c.isdigit():
            nostring += c
        else:
            period += c
    parsed_interval={"no":int(nostring),"period":period}
    return parsed_interval

def intv_to_timedelta(interval):
    parsed_interval=parse_timeframe(interval)
    n=parsed_interval["no"]
    period=parsed_interval["period"]
    match period:
        case 'min':
            timedelta=datetime.timedelta(minutes=n)
        case 'hour':
            timedelta=datetime.timedelta(hours=n)
        case 'day':
            timedelta=datetime.timedelta(days=n)
        case 'week':
            timedelta=datetime.timedelta(weeks=n)
        case 'month':
            timedelta=pd.DateOffset(months=n)
        case _:
            print("Period not found!")
    return timedelta


def intervalize_line(points,interval):
    td=intv_to_timedelta(interval)
    c_p=0.0
    n=0
    npoints=[]
    for p in points:
        if n==0:
            c_p=p
            npoints.append(p)
        else:
            if c_p[0]==p[0]+td:
                npoints.append(p)
                c_p=p
            else:
                intv_diff=p[0]-c_p[0]
                t_diff=intv_diff/td
                pric_diff=p[1]-c_p[1]
                p_diff=pric_diff/t_diff
                a=0
                while a < t_diff:
                    time=c_p[0]+a*td
                    price=c_p[1]+a*p_diff
                    k=[time,price]
                    npoints.append(k)
                    print(k)
                    a=a+1
        n=+1
    print(npoints)
    return npoints

def NAN_line(interval, start_time, k):
    df=pd.DataFrame()
    Time=start_time
    n=4
    TD=intv_to_timedelta(interval)
    #Create NAN line with 3 rows
    while n < k:
        n=n+1
        Time=Time+TD
        D={'Open Time':Time,'NAN':0.0}
        row=pd.DataFrame(D,index=[n])
        #row['Open Time']=Time
        row.set_index(["Open Time"], inplace=True)
        df=row.combine_first(df)
    df.drop(df.tail(1).index,inplace=True)
    #Extend the DF as required
    ixu = df.index + k*TD
    ixx = df.index.union(ixu)
    df= df.reindex(ixx)
    return df

def create_NAN_df(interval, start_time, k):
    #Create a DF full of Nan values for start_time+ interval
    TD=intv_to_timedelta(interval)
    n=0
    Time=start_time
    df=pd.DataFrame()
    while n < 5:
        n=n+1
        Time=Time+TD
        D={'Open Time':Time,'Open':None,'High':None,'Low':None,'Close':None,'Volume':None}
        row=pd.DataFrame(D,index=[n])
        #row['Open Time']=Time
        row.set_index(["Open Time"], inplace=True)
        df=row.combine_first(df)
    df.drop(df.tail(1).index, inplace=True)
    n=1
    while n < k:
        ixu = df.index + 4*n*TD
        ixx = df.index.union(ixu)
        df= df.reindex(ixx)
        n=n+1
    return df

def parse_filename(SYMBOL,no,period):
    pwd=os.getcwd()
    filename=pwd+'/CSVData/'+SYMBOL+'_'+str(no)+'_'+period
    return filename

def parse_filename_intv(SYMBOL,interval):
    nostring=""
    period=""
    for c in interval:
        if c.isdigit():
            nostring += c
        else:
            period += c
    pwd=os.getcwd()
    filename=pwd+'/CSVData/'+SYMBOL+'_'+nostring+'_'+period
    return filename

#parses interval into correct format for Binance API Client {"no":no,"period":period}
def client_interval2(parsed_interval):
    no=parsed_interval["no"]
    period=parsed_interval["period"]
    match period:
        case "min":
            client_interval = 'Client.KLINE_INTERVAL_'+str(no)+'MINUTE'
        case "hour":
            client_interval = 'Client.KLINE_INTERVAL_'+str(no)+'HOUR'
        case "day":
            client_interval = 'Client.KLINE_INTERVAL_'+str(no)+'DAY'
        case "week":
            client_interval = 'Client.KLINE_INTERVAL_'+str(no)+'WEEK'
        case "month":
            client_interval = 'Client.KLINE_INTERVAL_'+str(no)+'MONTH'
    return client_interval

def client_interval(parsed_interval):
    no=parsed_interval["no"]
    period=str(no)+parsed_interval["period"]
    match period:
        case "1min":
            interval = Client.KLINE_INTERVAL_1MINUTE
        case "3min":
            interval = Client.KLINE_INTERVAL_3MINUTE
        case "5min":
            interval = Client.KLINE_INTERVAL_5MINUTE
        case "15min":
            interval = Client.KLINE_INTERVAL_15MINUTE
        case "30min":
            interval = Client.KLINE_INTERVAL_30MINUTE
        case "1hour":
            interval = Client.KLINE_INTERVAL_1HOUR
        case "2hour":
            interval = Client.KLINE_INTERVAL_2HOUR
        case "4hour":
            interval = Client.KLINE_INTERVAL_4HOUR
        case "6hour":
            interval = Client.KLINE_INTERVAL_6HOUR
        case "8hour":
            interval = Client.KLINE_INTERVAL_8HOUR
        case "12hour":
            interval = Client.KLINE_INTERVAL_12HOUR
        case "1day":
            interval = Client.KLINE_INTERVAL_1DAY
        case "3day":
            interval = Client.KLINE_INTERVAL_3DAY
        case "1week":
            interval = Client.KLINE_INTERVAL_1WEEK
        case "1month":
            interval = Client.KLINE_INTERVAL_1MONTH
    return interval

##Get data from binance functions passive
def get_klines(SYMBOL,client_interval,start_time,end_time):
    client=init_client()
    klines = client.get_historical_klines(symbol=SYMBOL, interval=client_interval, start_str=str(start_time), end_str=str(end_time))
    #cilent.close_connection()
    return klines

#Convert from binance timestamp
def change_timestamp(timestamp):
    if timestamp==None:
        print('Timestamp not found')
    else:
        return datetime.datetime.fromtimestamp(int(timestamp)/1000)

def change_timestamp_chartoff(timestamp):
    if timestamp==None:
        print('Timestamp not found')
    else:
        SD = datetime.datetime.fromtimestamp(int(timestamp))-datetime.timedelta(hours=1)
        return SD

def change_timestamp_chart(timestamp):
    if timestamp==None:
        print('Timestamp not found')
    else:
        SD = datetime.datetime.fromtimestamp(int(timestamp))
        return SD

###Parse Klines into a dataframe
def parse_klines_to_DF(klines,save:bool,filename):
    df_M = pd.DataFrame(klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore']) 
    columns_to_convert = ['Open', 'High', 'Low', 'Close', 'Volume', 'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume']
    df_M['Open Time'] = df_M['Open Time'].apply(change_timestamp)
    for col in columns_to_convert:
        df_M[col] = df_M[col].astype(float)
    if save==True:
        df_M.to_csv(filename, index=False)
    if save==False:
        return df_M

def parse_tick(tick_out):
	#{"e":"24hrMiniTicker","E":1591267704450, "s":"BTCUSD_200626", "ps":"BTCUSD", "c":"9561.7", "o":"9580.9", "h":"10000.0", "l":"7000.0", "v":"487476", "q":"33264343847.22378500"}
    #time=change_timestamp(tick_out['E'])
    #price=tick_out['c']
    #colume=tick_out['v']
    #pd.DataFrame[tick_out]
    df_K=pd.DataFrame(tick_out)
    df_M=dk_K[["E","c","v"]]
    mapper={'E':"Open Time",'c':"Last Price",'v':"Volume"}
    df_M.rename(mapper=mapper)
    df_M['Open Time'] = df_M['Open Time'].apply(change_timestamp)
    for col in columns_to_convert:
        df_M[col] = df_M[col].astype(float)
    return df_M

def parse_klines_ws(df_K):
    #{'t': 1748736000000, 'T': 1751327999999, 's': 'TRUMPUSDT', 'i': '1M', 'f': 141621259, 'L': 142166556, 'o': '11.24000000', 'c': '11.19000000', 'h': '11.90000000', 'l': '10.94000000', 'v': '15876266.19100000', 'n': 545298, 'x': False, 'q': '179814040.65914000', 'V': '8111489.88500000', 'Q': '91972469.36091000', 'B': '0'}
    #List or single?
    df_M=df_K[["t","o","h","l","c","v","T","q","n","V","Q","B"]]
    print(df_M)
    df_M=df_M.rename(columns={"t":'Open Time',"o":'Open',"h":'High',"l":'Low',"c":'Close',"v":'Volume',"T":'Close Time',"q":'Quote Asset Volume',"n":'Number of Trades',"V":'Taker Buy Base Asset Volume',"Q":'Taker Buy Quote Asset Volume',"B":'Ignore'})
    columns_to_convert = ['Open', 'High', 'Low', 'Close', 'Volume', 'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume']
    df_M['Open Time'] = df_M['Open Time'].apply(change_timestamp)
    for col in columns_to_convert:
        df_M[col] = df_M[col].astype(float)
    print(df_M)
    return df_M

##Get data and save to CSV. Interval in format '1min', '1hour', '1day', 1 week and so on
##Current intervas 1min, 3min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 3 day, 1week
#SYMBOL = 'BTCUSDT'
def get_data(SYMBOL,interval,start_time,end_time,save:bool):
    parsed_interval=parse_timeframe(interval)
    no=parsed_interval["no"]
    period=parsed_interval["period"]
    cc=client_interval(parsed_interval)
    filename=parse_filename(SYMBOL,no,period)
    #check if filenames work
    klines=get_klines(SYMBOL,cc,start_time,end_time)
    if save==True:
        parse_klines_to_DF(klines,True,filename)
    else:
        df=parse_klines_to_DF(klines,False,filename)
        return df



#Get a datetime for last midnight

###Get historical data since begginging of time to last midnight. SYMBOL='BTCUSDETC'intervals=['1min','3min']
##debug the end time properly, no need for DF
##intervals=['1min','3min','5min','15min','30min','1hour','2hour','4hour','6hour','8hour','12hour','1day','3day','1week','1month']
def get_data_hist(SYMBOL):
    start_time = datetime.datetime(2007, 1, 1, 0, 0, 0)
    end_time = datetime.datetime.now()
    pwd=os.getcwd()
    ET = datetime.datetime.strftime(end_time, "%Y-%m-%d %H:%M:%S")
    print('Getting data for '+SYMBOL+' before:'+ET);
    write_file(ET,pwd+"/CSVData",SYMBOL+"_Last_Modified")
    intervals=config.intervals
    for i in intervals:
        interval=i
        get_data(SYMBOL,interval,start_time,end_time,True)

#get_data_hist("BTCUSDT")

#def process coins of interest, if doesn't exist- get hist, if not, append

def data_append(SYMBOL):
    end_time = datetime.datetime.now()
    start_time = end_time
    pwd=os.getcwd()
    ST=read_file(pwd+"/CSVData",SYMBOL+"_Last_Modified")
    ET = datetime.datetime.strftime(end_time, "%Y-%m-%d %H:%M:%S")
    start_time = datetime.datetime.strptime(ST, "%Y-%m-%d %H:%M:%S")
    print('Getting data for '+SYMBOL+' between: '+ST+' and '+ET)
    intervals=config.intervals
    for i in intervals:
        filename=parse_filename_intv(SYMBOL,i)
        try:
            append_df=get_data(SYMBOL,i,start_time,end_time,False)
            append_df.to_csv(filename, mode='a', index=False, header=False)
            success=True
        except:
            success=False
    if success==True:
        write_file(ET,pwd+"/CSVData",SYMBOL+"_Last_Modified")
    else:
        print('Data for '+SYMBOL+' could not be updated! ')

def data_append_auto_single(c):
    filename=parse_filename_intv(c,'1min')
    try:
        if not os.path.exists(filename):
            get_data_hist(c)
        data_append(c)
    except:
        print("Data for:"+c+" could not be updated")

def data_append_auto():
    coins=config.coins_of_interest
    for c in coins:
        filename=parse_filename_intv(c,'1min')
        try:
            # get_data_hist(c)
            if not os.path.exists(filename):
                get_data_hist(c)
                data_append(c)
            else: 
                data_append(c)
        except:
            print("Data for:"+c+" could not be updated")


##Date and time in DATETIME
def dataframe_prune_index(df,start_time,end_time,return_df:bool):
    if start_time=='*':
        index=df.index[(df["Open Time"] <= end_time)]
    if end_time=='*':
        index=df.index[(df["Open Time"] >= start_time)]
    else:
        index=df.index[(df["Open Time"] >= start_time) & (df["Open Time"] <= end_time)]
    if return_df==True:
        df=df.loc[index]
        return df
    else:
        return index

##Get index of nearest time value: FFFIIIX
def get_index_before(df,time):
    index=df.index[(df["Open Time"] <= time)]
    return index

##Append DF2 to DF1
def dataframe_comb_first(df1,df2):
    df3 = df2.combine_first(df1)
    return df3


def load_partial_df(SYMBOL,interval,start_time, end_time):
    ET = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    ST = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    parsed_interval=parse_timeframe(interval);
    no=parsed_interval["no"]
    period=parsed_interval["period"]
    filename=parse_filename(SYMBOL,no,period)
    df=pd.read_csv(filename, engine='c', nrows=1)
    df["Open Time"] = pd.to_datetime(df["Open Time"])
    FR=df.iloc[-1]['Open Time']
    td_i=intv_to_timedelta(interval)
    h1=datetime.timedelta(hours=1)
    rows_to_load=int((ET-ST)/td_i)
    start_row=int((ST-FR)/td_i)
    #df2=pd.read_csv(filename, engine='c', nrows=rows_to_load, skiprows=start_row)
    df2=pd.read_csv(filename, engine='c', nrows=rows_to_load, skiprows=[i for i in range(1,start_row)])
    print(df2)
    return df2

def load_chunk_df(SYMBOL,interval,start_time, end_time):
    ET = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    ST = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    parsed_interval=parse_timeframe(interval);
    no=parsed_interval["no"]
    period=parsed_interval["period"]
    filename=parse_filename(SYMBOL,no,period)
    for chunk in pd.read_csv(filename, chunksize=10000):
        #print(chunk)
        None
    return None

def read_data_CSV(SYMBOL,interval,prune:bool,start_time,end_time):
    parsed_interval=parse_timeframe(interval);
    no=parsed_interval["no"]
    period=parsed_interval["period"]
    filename=parse_filename(SYMBOL,no,period)
    df=pd.read_csv(filename, engine='c')
    df["Open Time"] = pd.to_datetime(df["Open Time"],format='mixed')
    if prune==False:
        return df
    else:
        df=dataframe_prune_index(df,start_time,end_time,True)
    return df

#extends range of a dataframe with NAN values for n days
def extend_range(df,n):
    try:
        ixu = df.index + datetime.timedelta(n)
        ixx = df.index.union(ixu)
        df= df.reindex(ixx)
        return df
    except:
        print("Error: unable to re-index")
        print("DataFrame:")
        print(df)

def get_chart_time(trade_time,preload_days):
    if type(trade_time)==str:
        TD = datetime.datetime.strptime(trade_time, "%Y-%m-%d %H:%M:%S")
    else:
        TD=trade_time
    SD = TD-datetime.timedelta(days=preload_days)
    return SD,TD


def parse_chart_settings(chart_settings:dict):
    SYMBOL=chart_settings['s']
    trade_time=chart_settings['t']
    current_interval=chart_settings['i']
    trade_method=chart_settings['m']
    return SYMBOL, trade_time, current_interval, trade_method

def h_read_config():
    next_wicks=config.h_next_wicks
    chart_type=config.h_chart_type
    preload_days=config.h_chart_preload_days
    intervals=config.intervals
    current_interval=config.h_interval
    trade_method=config.h_trade_method
    return next_wicks, chart_type, preload_days, intervals, current_interval, trade_method

def fix_data():
    #Remove duplicates from DATA
    for c in config.coins_of_interest:
        for i in config.intervals:
            start_time=datetime.datetime.now()
            end_time=start_time
            df=read_data_CSV(c,i,False,start_time,end_time)
            df["Open Time"] = pd.to_datetime(df["Open Time"])
            print(df)
            df.drop_duplicates(subset="Open Time", keep="first", inplace=True)
            print(df)
            filename=parse_filename_intv(c,i)
            df.to_csv(filename, index=False)

def fix_timestamps():
    #Generate end_data labels from 1min chart
    for c in config.coins_of_interest:
        start_time=datetime.datetime.now()
        end_time=start_time
        df=read_data_CSV(c,"1min",False,start_time,end_time)
        df["Open Time"] = pd.to_datetime(df["Open Time"])
        last_1min=df.iloc[-1]["Open Time"]
        pwd=os.getcwd()
        end_time=last_1min+datetime.timedelta(seconds=30)
        ET = datetime.datetime.strftime(end_time, "%Y-%m-%d %H:%M:%S")
        write_file(ET,pwd+"/CSVData",c+"_Last_Modified")

