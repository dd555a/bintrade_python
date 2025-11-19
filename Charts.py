import pandas as pd
import asyncio
import os

import queue
import datetime
import time
import json
import config

from lightweight_charts import Chart

from Data import read_data_CSV, get_chart_time, dataframe_prune_index, parse_chart_settings, h_read_config, change_timestamp_chart,  change_timestamp_chartoff, create_NAN_df, NAN_line

###CHART BUTTONS####
def on_timeframe_selection(chart):  # Called when the user changes the timeframe.
    #print(chart.topbar['symbol'].value)
    #print(chart.topbar['timeframe'].value)
    None

def on_forward_button_press(chart):
    chart.topbar['forward_button'].value='>>>'

def on_backward_button_press(chart):
    chart.topbar['backward_button'].value='<<<'

def toggle_percent(chart):
    new_button_value = '%' if chart.topbar['toggle_percent'].value == '$' else '$'
    chart.topbar['toggle_percent'].set(new_button_value)

###CHART_TABLES###
def dummy(dummy):
    None

class asset_table:
    def __init__(self, chart):
        self.chart=chart
        self.table = self.chart.create_table(width=0.09, height=0.2,
                      headings=('Asset', 'Amount', 'chg %'),
                      widths=(0.03, 0.03, 0.03 ),
                      alignments=('center', 'center', 'center'),
                      position='left', func=dummy)

        self.table.format('Chg %', f'{self.table.VALUE} %')
        self.r1=self.table.new_row('Asset1', 0, 0)
        self.r2=self.table.new_row('Asset2', config.h_start_money, 0)
    def update(self, S1, S2, asset1, asset2,ch1,ch2):
        self.r1.delete()
        self.r2.delete()
        self.r1=self.table.new_row(S1, asset1, ch1)
        self.r2=self.table.new_row(S2, asset2, ch2)

##CHART ORDER FUNCTIONS##
def create_line(chart,pd, name, color, style, width):
    line = chart.create_line(name, color, style,  width, False, True)
    line.set(pd)

def del_lines(chart):
    for i in chart.lines():
        i.delete()

def h_line(chart, price, color, width, style):
    l1=chart.horizontal_line(price, color, width, style)
    return l1

def stop_line(chart,  price, color):
    style=config.stop
    width=int(config.stop_width)
    line=h_line(chart, price, color, width, style)
    return line

def stop_market_line(chart, price, color):
    style=config.stop_market
    width=int(config.stop_market_width)
    line=h_line(chart, price, color, width, style)
    return line

def limit_line(chart, price, color):
    style=config.limit
    width=int(config.limit_width)
    line=h_line(chart, price, color, width, style)
    return line

def last_order_lineF(chart, price, color):
    style=config.last_order
    width=int(config.last_order_width)
    line=chart.horizontal_line(price, color, width, style,'',False)
    return line

def fee_line(chart,  price, color):
    style=config.fee_line
    width=int(config.fee_width)
    line=chart.horizontal_line(price, color, width, style,'',False)
    return line

class line_order:
    def __init__(self, chart,keys):
        self.chart=chart
        self.keys=keys
        self.order_init=False
        self.order_active=False

        self.active_buy_col=config.active_buy_col
        self.active_sell_col=config.active_sell_col

        self.inactive_buy_col=config.inactive_buy_col
        self.inactive_sell_col=config.inactive_sell_col
        self.order_type=None

    def set(self, color, K):
        match self.order_type:
            case 1:
                self.limit_order=limit_line(self.chart,K[0], color)
            case 2:
                Lline=limit_line(self.chart,K[0], color)
                Sline=stop_line(self.chart,K[1], color)
                self.stop_limit_order=[Sline, Lline]
            case 3:
                self.stop_market_order=stop_line(self.chart, K[0], color)
            case 4:
                w=1
                ###?????
            case 5:
                L1=limit_line(self.chart,K[1], color)
                S1=stop_line(self.chart,K[2], color)
                self.oco_sm_order=[L1,S1]
            case 6:
                L2=limit_line(self.chart,K[0], color)
                L1=limit_line(self.chart,K[1], color)
                S1=stop_line(self.chart,K[2], color)
                self.oco_sl_order=[L2,L1,S1]
            case _:
                print("Order type not found")
        self.order_init=True

    def set_buy(self, K1):
        self.buy_sell=0
        if self.order_init==True:
            self.delete('')
        self.order_type=int(K1)
        if self.order_active==True:
            self.color=self.active_buy_col
        else:
            self.color=self.inactive_buy_col
        k0=self.keys[0]
        k1=k0*(1+self.keys[1])
        k2=k0*(1+self.keys[2])
        K=[k0,k1,k2]
        self.set(self.color,K)

    def set_sell(self, K1):
        self.buy_sell=1
        if self.order_init==True:
            self.delete('')
        self.order_type=int(K1)
        if self.order_active==True:
            self.color=self.active_sell_col
        else:
            self.color=self.inactive_sell_col
        k0=self.keys[0]
        k1=k0*(1-self.keys[1])
        k2=k0*(1-self.keys[2])
        K=[k0,k1,k2]
        self.set(self.color, K)

    def read(self):
        if self.order_init==True:
            #T=self.buy_sell, self.order_type, self.keys
            #print(T)
            return self.buy_sell, self.order_type, self.keys
        else:
            return None, None, self.keys

    def adjust(self, keys):
        self.keys=keys
        if self.order_init==True:
            self.delete('')
        if self.buy_sell==0:
            self.set_buy(str(self.order_type))
        else:
            self.set_sell(str(self.order_type))

    def activate(self, key):
        if self.order_init==True:
            if self.order_active==True:
                self.delete('')
            else:
                self.delete('')
                self.order_active=True
            K1=str(self.order_type)
            if self.buy_sell==0:
                self.set_buy(K1)
            else:
                self.set_sell(K1)

    def delete_all(self):
        try:
            self.limit_order.delete()
            self.stop_limit_order[0].delete()
            self.stop_limit_order[1].delete()
            self.stop_market_order.delete()
        except:
            None

    def delete(self,key):
        if self.order_init==True:
            match self.order_type:
                case 1:
                    self.limit_order.delete()
                case 2:
                    self.stop_limit_order[0].delete()
                    self.stop_limit_order[1].delete()
                case 3:
                    self.stop_market_order.delete()
        self.order_init=False
        self.order_active=False

class last_order_line:
    def __init__(self, chart):
        self.chart=chart
        self.init=False
        self.fee=config.fee

        self.fee_color=config.fee_color
        self.last_buy_col=config.last_buy_col
        self.last_sell_col=config.last_sell_col
        self.buy_sell=int
    def set(self,p,buy_sell):
        if self.init==True:
            self.delete()
        if buy_sell==0:
            color=self.last_buy_col
            F=1+self.fee
        else:
            color=self.last_sell_col
            F=1-self.fee
        self.LB=last_order_lineF(self.chart,p, color)
        self.F=fee_line(self.chart,p*F, self.fee_color)
        self.init=True
    def delete(self):
        if self.init==True:
            self.F.delete()
            self.LB.delete()
            self.init=False

class tick_line:
    def __init__(self, chart):
        self.init=False
        self.chart=chart
        self.color=config.tick_color
        self.width=config.tick_width
        self.style=config.tick_style
    def set(self,price):
        if self.init==True:
            self.delete()
        self.line=self.chart.horizontal_line(price, self.color, self.width, self.style,'',True)
        self.init=True

    def delete(self):
        if self.init == True:
            self.line.delete()
            self.init=False

class predict_line:
    def __init__(self, chart):
        self.chart=chart
        self.init=False

        self.col=config.predict_line_col
        self.style=config.predict
        self.width=config.predict_width

        self.predict_line_end=None
        self.predict_line_start=None
    def set(self,line_pd):
        if self.init==True:
            self.line.set(None)
            self.reset(line_pd)
        else:
            self.line=self.chart.create_line('Predict' ,color=self.col,width=self.width,style=self.style,price_line=False,price_label=False)

            LL=line_pd.set_index(['Open Time'])
            self.line.set(LL)
            self.init=True
    def reset(self,line_pd):
        LL=line_pd.set_index(['Open Time'])
        self.line.set(LL)
    def delete(self):
        if self.init==True:
            self.line.set(None)

class points_line:
    def __init__(self, chart):
        self.chart=chart
        self.init=False

        self.col=config.points_line_col
        self.style=config.points
        self.width=config.points_width

        self.predict_line_end=None
        self.predict_line_start=None
    def set(self,line_pd):
        if self.init==True:
            self.line.set(None)
            self.reset(line_pd)
        else:
            self.line=self.chart.create_line('Points' ,color=self.col,width=self.width,style=self.style,price_line=False,price_label=False)

            LL=line_pd.set_index(['Open Time'])
            self.line.set(LL)
            self.init=True
    def reset(self,line_pd):
        LL=line_pd.set_index(['Open Time'])
        self.line.set(LL)
    def delete(self):
        if self.init==True:
            self.line.set(None)

class avg_line:
    def __init__(self, chart, color):
        self.chart=chart
        self.init=False

        self.col=color
        self.style=config.avg_line
        self.width=config.avg_width
    def set(self, line_pd):
        if type(line_pd)!=pd.DataFrame:
            if self.init !=False:
                self.line.set(None)
        else:
            if self.init==True:
                self.line.set(None)
                line_pd.set_index(['Open Time'], inplace=True)
                self.line.set(line_pd)
            else:
                L=line_pd.columns.tolist()
                name=L[1]
                line_pd.set_index(['Open Time'], inplace=True)

                self.line=self.chart.create_line(name,color=self.col,width=self.width,style=self.style,price_line=False,price_label=False)
                self.line.set(line_pd)
                self.init=True

    def delete(self):
        if self.init==True:
            self.line.set(None)

class nan_line:
    def __init__(self, chart, color):
        self.chart=chart
        self.init=False

        self.col=color
        self.style=config.avg_line
        self.width=config.avg_width
    def set(self, line_pd):
        if type(line_pd)!=pd.DataFrame:
            if self.init !=False:
                self.line.set(None)
        else:
            if self.init==True:
                self.line.set(None)
                self.line.set(line_pd)
            else:
                L=line_pd.columns.tolist()
                name='Nan'
                self.line=self.chart.create_line(name,color=self.col,width=self.width,style=self.style,price_line=False,price_label=False)
                self.line.set(line_pd)
                self.init=True

    def delete(self):
        if self.init==True:
            self.line.set(None)

###CHART INIT FUNCTIONS######


def chart_type_buttons(chart,chart_type):
    match chart_type:
        case 0:
            chart.topbar.textbox('w',"W:")
            chart.topbar.textbox('next_wicks', config.h_next_wicks)
            chart.topbar.button('backward_button', '<<', func=on_backward_button_press)
            chart.topbar.button('forward_button', '>>', func=on_forward_button_press)
        case 1:
            None
        case _:
            print("Chart type not found!")
    return chart




class live_chart: 
    def toggle_live(self, chart):
        new_button_value = 'Hist' if chart.topbar['toggle_live'].value == 'Live!' else 'Live!'
        chart.topbar['toggle_live'].set(new_button_value)
        if self.live==True:
            self.live=False
        else:
            self.live=True

    def chart_set_intervals(self, chart, chart_type):
        chart.topbar.switcher('timeframe',config.intervals , default=config.default_interval,func=on_timeframe_selection)
        chart.topbar.button('toggle_percent', '$', func=toggle_percent)
        if chart_type==0:
            chart.topbar.button('toggle_live', 'Hist', func=self.toggle_live)
        else:
            chart.topbar.button('toggle_live', 'Live!', func=self.toggle_live)
        return chart

    def search_symbol(self, chart,SYMBOL):
        if SYMBOL not in config.coins_of_interest:
            
            print(f'No data for "{SYMBOL}"')
        else:
            chart.topbar['symbol'].value=SYMBOL
        return chart

    def search_input(self, chart, string):
        out_string=''
        date=bool
        for c in string:
            if c.isdigit() or c=='-':
                out_string += c
                date=True
            else:
                out_string += c
                date=False
        if date==False:
            chart = self.search_symbol(chart, out_string)
            return chart
        else:
            self.tradetime=out_string
            return chart

    def rinit_chart(self, SYMBOL, trade_method):
        chart = Chart(width=1000, inner_width=1, inner_height=0.85,toolbox=True)
        chart.legend(True, True,True,True)
        chart.price_line(True, True)
        chart.topbar.textbox('symbol', SYMBOL)
        chart.topbar.button('trade_method', 'Manual', func=self.cycle_tm)
        chart=self.chart_set_intervals(chart, self.chart_type)
        return chart

    def set_points_line(self,chart,time,price):
        #t=change_timestamp_chart(time)
        t=change_timestamp_chartoff(time)
        row=[t,price]
        self.points.append(row)
        if config.points_line==True:
            pline_pd=pd.DataFrame(self.points, columns=['Open Time','Points'])
            self.points_line.set(pline_pd)
        print(self.points)
        #BLue red line

    def clear_points(self,key):
        self.points=[]
        if config.points_line==True:
            self.points_line.delete()
        print("Points cleared!")

    def clear_predict_line(self,key):
        self.predict_line.delete()
        self.predict_line_init=False
        self.clear_points(key)
        print("Predict line cleared!")

    def set_ktop(self,k):
        if self.points != []:
            self.keys[0]=self.points[-1][1]
            self.line_order.adjust(self.keys)
        else:
            print("No points set!")

    def set_predict_line(self,key):
        if len(self.points) < 2:
            print("Not enough points to set line!")
            self.predict_line.set(None)
        else:
            self.points_line.delete()
            self.predict_line_init=True

    def adjust_k(self):
        match self.trade_method:
            case 0:
                self.line_order.adjust(self.keys)
            case _:
                print('Trade method not found:', self.trade_method)

    def adjust_key0_up(self,k):
        self.keys[0]=round(self.keys[0]*(1+self.k0_inc),4)
        self.adjust_k()
        self.check_keys()

    def adjust_key0_down(self,k):
        self.keys[0]=round(self.keys[0]*(1-self.k0_inc),4)
        self.adjust_k()
        self.check_keys()

    def adjust_key1_up(self,k):
        self.keys[1]=round(self.keys[1]*(1+self.k1_inc),4)
        self.adjust_k()
        self.check_keys()

    def adjust_key1_down(self,k):
        self.keys[1]=round(self.keys[1]*(1-self.k1_inc),4)
        self.adjust_k()
        self.check_keys()

    def adjust_key2_up(self,k):
        self.keys[2]=round(self.keys[2]*(1+self.k2_inc),4)
        self.adjust_k()
        self.check_keys()

    def adjust_key2_down(self,k):
        self.keys[2]=round(self.keys[2]*(1-self.k2_inc),4)
        self.adjust_k()
        print('K2',self.keys[2])
        self.check_keys()

    def set_marker(self, time, marker_type:int):
        if marker_type==0:
            self.chart.marker(time, 'below' , 'arrow_up', config.active_buy_col, 'He bought!')
        if marker_type==1:
            self.chart.marker(time, 'above' , 'arrow_down', config.active_sell_col, 'He sold!')

    def del_markers(self):
        self.chart.clear_markers()

    def reset_keys(self):
        self.keys=[self.keys[0],0.01,0.015]

    def s_set(self, key):
        self.line_order.keys=self.keys
        if self.asset1_held==False:
            self.line_order.set_buy(str(key))
        else:
            self.line_order.set_sell(str(key))

    def set_none(self, key):
        None

    def chart_set_hotkeys(self):
        match self.trade_method:
            case 0:
                self.chart.hotkey('shift', 1, self.s_set)
                self.chart.hotkey('shift', 2, self.s_set)
                self.chart.hotkey('shift', 3, self.s_set)
                self.chart.hotkey('shift', 'A', self.line_order.activate)
                self.chart.hotkey('shift', 'D', self.line_order.delete)
                self.chart.hotkey('shift', 'K', self.adjust_key0_up)
                self.chart.hotkey('shift', 'J', self.adjust_key0_down)
                self.chart.hotkey('ctrl', 'j', self.adjust_key1_up)
                self.chart.hotkey('ctrl', 'k', self.adjust_key1_down)
                self.chart.hotkey('alt', 'j', self.adjust_key2_up)
                self.chart.hotkey('alt', 'k', self.adjust_key2_down)
            case _:
                print("Chart type not found!")


    def cycle_wicks(self, key):
        current=self.chart.topbar['next_wicks'].value
        last=self.wicks[-1]
        i=self.wicks.index(current)+1
        if self.wicks.index(last) < i:
            i=0
        n=self.wicks[i]
        print("Selected next wicks: "+str(n))
        self.chart.topbar['next_wicks'].value=n


    def chart_update_hist(self,update_df):
        update_df.set_index(["Open Time"], inplace=True)
        for i, series in update_df.iterrows():
            self.chart.update(series)
            time.sleep(0.05)


    def cycle_tm(self, key):
        self.trade_method=self.trade_method+1
        if self.tm[-1] < self.trade_method:
            self.trade_method=0
            #Change TM table here
        print("Selected trade method: "+str(self.trade_methods[self.trade_method]))

    def screenshot(self,filename):
        pwd=os.getcwd()
        img = self.chart.screenshot()
        with open(pwd+'/Screenshots/'+filename+'.png', 'wb') as f:
            f.write(img)

    def restart_lines(self):
        self.line_order.delete('')
        self.last_order_line.delete()

        self.avg_line.delete()
        self.avg_line1.delete()
        self.avg_line2.delete()

        self.predict_line.delete()
        self.points_line.delete()
        self.tick_line.delete()


        self.nan_line.delete()

    def restart_chart(self,df):
        self.restart_lines()
        self.chart.exit()
        if self.trade_platform==0:
            self.chart_type=0
        else:
            self.chart_type=1
        print(self.trade_platform)
        print(self.chart_type)

        self.init_chart()
        self.r_chart=False
        self.set_chart(df)

    def tick_line_set(self,price):
        self.tick_line.set(price)

    async def show_chart(self):
        while True:
            if self.r_chart !=True:
                await self.chart.show_async()
            await asyncio.sleep(0.001)

    def write_asset_table(self,S1, S2, asset1, asset2, ch1, ch2):
        self.asset_table.update(S1, S2, asset1, asset2, ch1, ch2)

    def init_hist(self):
        self.trade_platform=0
        self.chart_type=0
        self.chart.hotkey('shift', 'W', self.cycle_wicks)

        self.forward=False
        self.backward=False

    def init_live(self):
        self.chart_type=1
        ##OTHER LIVE INIT FUNCTIONS GO HERE!

    def init_lines(self):
        self.line_order=line_order(self.chart, self.keys)
        self.last_order_line=last_order_line(self.chart)

        self.predict_line=predict_line(self.chart)
        self.predict_line_init=False
        self.points_line=points_line(self.chart)

        self.tick_line=tick_line(self.chart)

        self.avg_line=avg_line(self.chart, config.avg_line_col)
        self.avg_line1=avg_line(self.chart, config.avg_line_col1)
        self.avg_line2=avg_line(self.chart, config.avg_line_col2)

        self.nan_line=nan_line(self.chart, config.avg_line_col2)

    def init_tables(self):
        self.asset_table=asset_table(self.chart)

    def init_chart(self):
        self.chart=self.rinit_chart(self.SYMBOL,self.trade_method)

        self.chart=chart_type_buttons(self.chart,self.chart_type) 
        self.chart.hotkey('shift', 'R', self.re_chart)
        self.chart.precision(self.precision)
        self.init_lines()

        self.chart.hotkey('shift', 'T', self.cycle_tm)
        self.chart.hotkey('shift', 'X', self.clear_points)
        self.chart.hotkey('shift', 'I', self.set_ktop)
        self.chart.hotkey('shift', 'U', self.reset_keys)
        self.chart.hotkey('shift', 'P', self.set_predict_line)
        self.chart.hotkey('shift', '{', self.clear_predict_line)

        self.init_tables()

        self.chart.events.click += self.set_points_line
        self.chart.events.search += self.search_input
        self.chart_set_hotkeys()

        match self.trade_platform:
            case 0:
                #Binance Hist
                self.init_hist()
            case 1:
                #Binance Live
                self.init_live()


    def set_chart(self,df):
        start_time=df.iloc[-1].name
        if self.keys_init==False:
            self.keys=[df.iloc[-1]['Close'],0.01,0.015]
            self.keys_init==True
        if self.current_interval not in ['1week','1month']:
            nan_df=create_NAN_df(self.current_interval,start_time,100)
            self.chart.set(nan_df.combine_first(df))
        else:
            self.chart.set(df)

    def update_tick(self,tick):
        if self.asset1_held==False:
            price=tick[0]
        else:
            price=tick[2]
        self.tick_line_set(price)

    def re_chart(self,key):
        self.r_chart=True

    def __init__(self, chart_type, trade_platform):
        self.trade_platform=trade_platform
        self.SYMBOL=config.default_symbol
        self.current_interval=config.default_interval

        self.trade_method=config.default_trade_method
        self.trade_methods=config.trade_methods

        self.order_status=0

        self.tradetime=''
        if self.trade_platform==0:
            self.live=False
            self.last_live=False
        else:
            self.live=True
            self.last_live=True

        self.tm=range(0,len(config.trade_methods),1)

        self.points=[]
        self.keys=[0.0,0.01,0.015]
        self.d_keys=self.keys
        self.last_order_k0=0.0
        self.iup_method=0
        self.keys_init=False
        self.r_chart=False
        self.order_active=False
        self.next_wicks=config.default_next_wicks
        self.wicks=config.wicks

        self.change_time=False
        self.change_TD=None

        self.k0_inc=config.k0_inc
        self.k1_inc=config.k1_inc
        self.k2_inc=config.k2_inc
        try:
            self.precision=config.precision[self.SYMBOL]
        except:
            self.precision=config.default_precision

        self.asset1_held=False
        self.chart_type=chart_type
        self.init_chart()

    def read_settings(self):
        return self.order_active, self.keys, self.SYMBOL, self.current_interval, self.trade_method, self.trade_platform, self.predict_line_init 

    def switch_tm(self):
        match self.trade_method:
            case 0:
                #Manual
                None
            case _:
                print("Chart type not found!")

    def check_active(self):
        match self.trade_method:
            case 0:
                if self.order_active != self.line_order.order_active:
                    self.order_active=self.line_order.order_active
                    if self.order_active==True:
                        B='True'
                    else:
                        B='False'
                    V=[self.keys[0],self.last_order_k0, B]
            case _:
                print('Trade method not found:', self.trade_method)

    def check_keys(self):
        match self.trade_method:
            case 0:
                None
            case _:
                print('Trade method not found:', self.trade_method)

    async def check_chart_state(self):
        while True:
            if self.current_interval != self.chart.topbar['timeframe'].value:
                self.current_interval = self.chart.topbar['timeframe'].value

            if self.chart.topbar['toggle_percent'].value=='%':
                self.chart.price_scale(True,'normal')

            if self.chart.topbar['toggle_percent'].value=='$':
                self.chart.price_scale(True,'percentage')

            if self.live != self.last_live:
                if self.live==False:
                    self.trade_platform=0
                    self.r_chart=True
                else:
                    self.trade_platform=1
                    self.r_chart=True
                self.last_live=self.live

            if self.chart.topbar['symbol'].value != self.SYMBOL:
                self.SYMBOL=self.chart.topbar['symbol'].value
                self.chart.topbar['symbol'].set(self.SYMBOL)
                try:
                    self.precision=config.precision[self.SYMBOL]
                except:
                    self.precision=config.default_precision
                self.chart.precision(self.precision)

            if self.chart.topbar['trade_method'].value != self.trade_methods[self.trade_method]:
                self.chart_set_hotkeys()
                self.chart.topbar['trade_method'].value=self.trade_methods[self.trade_method]
                self.chart.topbar['trade_method'].set(self.trade_methods[self.trade_method])
                self.switch_tm()

            self.check_active()
            await asyncio.sleep(0.001)

    async def check_hist_chart_state(self):
        while True:
            if self.trade_platform ==0 and self.r_chart !=True:
                if self.chart.topbar['forward_button'].value=='>>>':
                    self.forward=True
                    self.chart.topbar['forward_button'].value='>>'

                if self.chart.topbar['backward_button'].value=='<<<':
                    self.backward=True
                    self.chart.topbar['backward_button'].value='<<'

                if self.chart.topbar['next_wicks'].value != self.next_wicks:
                    self.next_wicks=self.chart.topbar['next_wicks'].value 
                    self.chart.topbar['next_wicks'].set(self.next_wicks)

                if self.tradetime != '':
                    self.change_TD=self.tradetime
                    self.change_time=True
                    self.tradetime=''
            await asyncio.sleep(0.001)

    async def display_chart(self):
        await asyncio.gather(self.show_chart(), self.check_chart_state(), self.check_hist_chart_state())
