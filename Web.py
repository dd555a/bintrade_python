import json
import config
import time
import os
import websockets
import asyncio


from websockets.asyncio.server import serve
import traceback
import datetime

import binance
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
#from binance import AsyncClient, BinanceSocketManager


from multiprocessing import Queue
from Data import change_timestamp,  return_symb, read_file


def init_client():
    pwd = os.getcwd()
    #key=read_file(pwd,"key")
    #key_secret=read_file(pwd,"key_secret")
    client = Client(config.API_KEY, config.API_SECRET) #TODO change back...
    client = Client(key, key_secret) 
    return client

def parse_to_binance(SYMBOL, order_type, quantity, buy_sell, keys):
    if buy_sell==0:
        BUY_SELL='BUY'
        k2=keys[0]*(1+keys[1])
        k3=keys[0]*(1+keys[2])
    else:
        BUY_SELL='SELL'
        k2=keys[0]*(1-keys[1])
        k3=keys[0]*(1-keys[2])
    STOP_PRICE=None
    TD=None
    TT=None
    TIF=None
    match order_type:
        case 0:
            PRICE=None
            TYPE='MARKET'
        case 1:
            PRICE=keys[0]
            TYPE='LIMIT'
        case 2:
            PRICE=keys[0]
            STOP_PRICE=k2
            TYPE='STOP_LIMIT'
        case 3:
            STOP_PRICE=keys[0]
            PRICE=None
            TYPE='STOP_LOSS'
            qantity=None
    print(PRICE)
    print(STOP_PRICE)
    quantity='{0:.8f}'.format(quantity)
    print(quantity)
    params={"symbol":SYMBOL,"side":BUY_SELL,"type":TYPE,"stopPrice":STOP_PRICE,"price":PRICE,"quantity":quantity,"trailingDelta":TD,"trailingTime":TT, "timeInForce": TIF}
    return params

def parse_params(SYMBOL):
    streams=config.ws_streams
    params=[]
    for S in streams:
        params.append(SYMBOL.lower()+S)
        if S=='@kline_':
            intervals=config.klines_intv
            for i in intervals:
                param=SYMBOL.lower()+'@kline_'+i
                params.append(param)
    return params




class ws_client_hybrid: 
    def __init__(self, SYMBOL, mp_queues):
        self.mp_queues=mp_queues
        self.SOCKET='wss://stream.binance.com:9443/ws'
        self.SYMBOL=SYMBOL
        self.d_SYMBOL=SYMBOL
        self.S1, self.S2=return_symb(self.SYMBOL)
        self.klines=[]
        self.order_update=False
        print('WS hybrid started')

        params=parse_params(self.SYMBOL)
        self.subscribe_message = {"method": "SUBSCRIBE", "params":params, "id": 1 }
        self.stream_names=config.ws_stream_names
        self.number_of_klines=len(config.intervals)
        self.order_init=False

        self.client=init_client()
        self.ws_restart=False
        self.last_price=float

        self.bid_price=float
        self.bid_qnt=float
        self.ask_price=float
        self.ask_qnt=float
        self.asset1, self.asset2=self.get_assets()

    def get_assets(self):
        balance= self.client.get_asset_balance(asset=self.SYMBOL)
        asset1 = float(self.client.get_asset_balance(asset=self.S1)['free'])
        asset2 = float(self.client.get_asset_balance(asset=self.S2)['free'])
        return asset1, asset2

    def test_conn(self):
        start_time=datetime.datetime.now()
        ws_ping= self.client.ws_get_time()
        server_time=change_timestamp(ws_ping['serverTime'])
        print('ws time delay(client initiated):')
        print(server_time-start_time)

    def test_connection(self):
        start_time=datetime.datetime.now()
        self.client = init_client()
        ws_ping= self.client.ws_get_time()
        start_time=datetime.datetime.now()
        server_time=change_timestamp(ws_ping['serverTime'])
        print('WS time delay(client not initiated):')
        print(server_time-start_time)

        n=0
        while n <= 3:
            time.sleep(3)
            self.test_conn()
            n=n+1

    def cancel_all_orders(self):
        self.client.cancel_all_open_orders()

    def parse_quant100(self, buy_sell, k):
        if buy_sell==0:
            Q=self.ask_qnt
            p=self.ask_price
            A=self.asset2
        else:
            Q=self.bid_qnt
            p=self.bid_price
            A=self.asset1
        print(type(p))
        quantity=0.5*A/k
        print(k)
        print(quantity)
        print(type(quantity))
        return quantity
        try:
            None
        except:
            print('Could not parse quantity!')

    def market_buy(self):
        if self.order_init==true:
            self.cancel_current_order()
        quant=self.parse_quant100(0)
        self.current_order = self.client.order_market_buy(symbol=self.symbol, quantity=quant)

    def market_sell(self):
        if self.order_init==true:
            self.cancel_current_order()
        quant=self.parse_quant100(1)
        self.current_order = self.client.order_market_sell(symbol=self.symbol, quantity=quant)

    def cancel_replace_order(self, O):
        SYMBOL=O[0]
        order_type=O[1]
        buy_sell=O[2]
        keys=O[3]
        quant=self.parse_quant100(buy_sell)
        if self.order_init ==True:
            params=parse_to_binance(SYMBOL, order_type, quant, buy_sell, keys)
            pnew={'cancelReplaceMode':'ALLOW_FAILURE','orderId':self.orderId}
            params.update(pnew)
            response= self.client.cancel_replace_order(params)
            print(response['cancelResult'])
            print(response['newOrderResul'])
        else:
            print('No order placed, placing now')
            try:
                self.current_order = self.client.create_order(params)
                self.order_init=True
                self.orderid=self.current_order['orderid']
            except BinanceAPIException as e:
                print(e)
            except BinanceOrderException as e:
                print(e)
            

    def place_order(self, O):
        print(O)
        SYMBOL=self.SYMBOL
        order_type=O[1]
        buy_sell=O[2]
        keys=O[3]
        #order=[5, self.order_active, self.order_type, self.buy_sell, self.keys]
        quantity=self.parse_quant100(buy_sell,keys[0])
        print(quantity)
        params=parse_to_binance(SYMBOL, order_type, quantity, buy_sell, keys)
        try:
            self.current_order = self.client.create_order(symbol=params['symbol'],side=params['side'], type=params['type'],stopPrice=params['stopPrice'], price=params['price'], quantity=params['quantity'], trailingDelta=params['trailingDelta'], trailingTime=params['trailingTime'], timeInForce=params['timeInForce'])
            self.order_init=True
            self.orderid=self.current_order['orderid']
        except BinanceAPIException as e:
            print(e)
        except BinanceOrderException as e:
            print(e)

    def cancel_all(self):
        self.client.cancel_all()

    def cancel_current_order(self):
        if self.order_init != True:
            response=self.client.cancel_order(orderId=self.orderId)
        else:
            print('WS no order initiated!')

    def get_status(self):
        O=[]
        O[0]=self.order_time
        O[1]=self.order_status
        O[2]=self.order_type
        O[3]=self.asset1
        O[4]=self.asset2
        return self.status

    def parse_status(self, status):
        parsed_status=[]
        parsed_status.append(change_timestamp(status['time']))
        s=int
        match status['status']:
            case "NEW":
                s=0
            case "FILLED":
                s=1
            case _:
                print('Status stype not found:',s)
        parsed_status.append(s)
        t=int
        match status['type']:
            case "MARKET":
                t=0
            case "LIMIT":
                t=1
            case "STOP_LOSS_LIMIT":
                t=2
            case "STOP_LOSS":
                t=3
            case _:
                print('Order type not found:',t )
        parsed_status.append(t)

    async def status_update(self):
        while True:
            if self.order_init==True:
                status=self.client.ws_get_order(orderId=self.orderId)
                parsed_status=parse_status(status)
                if parsed_status != self.status:
                    self.status=parsed_status
                    self.status_update=True
            await asyncio.sleep(1)

    async def run_ws(self):
        start_time=time.time()
        async with websockets.connect(self.SOCKET) as ws:
               await ws.send(json.dumps(self.subscribe_message))
               while True:
                   if self.ws_restart !=True:
                       if self.d_SYMBOL != self.SYMBOL:
                            self.d_SYMBOL=self.SYMBOL
                            self.S1, self.S2=return_symb(self.SYMBOL)
                            self.klines=[]
                            params=parse_params(self.SYMBOL)
                            self.subscribe_message = {"method": "SUBSCRIBE", "params":params, "id": 1 }
                            print("Restarting WS module!")
                            self.ws_restart=True
                            break
                       try:
                           msg = await ws.recv()
                           M=json.loads(msg)
                           #Connect message = 2
                           #Trade = 9
                           #24H ticker = 23
                           #Kline = 4
                           match len(M):
                               case 2:
                                   print("--- %s seconds to connect ---" %(round(time.time() - start_time,4)))
                               case 6:
                                   self.mp_queues['bookTicker'].put(M, block=False)
                                   self.bid_price=M['b']
                                   self.bid_qnt=M['B']
                                   self.ask_price=M['a']
                                   self.ask_qnt=M['A']
                               case 9:
                                   self.mp_queues['trade'].put(M, block=False)
                               case 23:
                                   self.mp_queues['24hrTicker'].put(M, block=False)
                               case 4:
                                   if len(self.klines) <= self.number_of_klines:
                                       self.klines.append(M['k'])
                                   else:
                                       self.mp_queues['kline'].put(self.klines, block=False)
                                       #print(self.klines)
                                       self.klines=[]
                            
                               case _:
                                   None
                                   #print(M)
                                   #print(len(M))
                       except Exception: 
                           traceback.print_exc()
                           self.ws_restart=True
                           break
                    
                   await asyncio.sleep(0.001)
    async def run(self):
        await asyncio.gather(self.run_ws(), self.status_update())

class ws_async:
    async def place_order(self,SYMBOL, order_type, quantity, buy_sell, keys):
        #client.create_test_order()
        start_time=datetime.datetime.now()
        params=parse_to_binance(SYMBOL, order_type, quantity, buy_sell, keys)
        try:
            response=await self.client.ws_create_order(params)
        except BinanceAPIException as e:
            print(e)
        except BinanceOrderException as e:
            print(e)
        print(response)
        self.orderId=response['orderId']
        placed_time=change_timestamp(response['transactTime'])
        print(placed_time)
        print('Time delay:')
        print(placed_time-start_time)
        self.order_placed=True

    async def cancel_all(self, SYMBOL):
        #params={'symbol':SYMBOL}
        response=await self.client.cancel_all_open_orders(symbol=SYMBOL)
        print(response)

    async def cancel_replace_order(self, SYMBOL, order_type, quantity, buy_sell, keys):
        if self.order_placed !=True:
            params=parse_to_binance(SYMBOL, order_type, quantity, buy_sell, keys)
            pnew={'cancelReplaceMode':'ALLOW_FAILURE','orderId':self.orderId}
            params.update(pnew)
            response= await self.client.cancel_replace_order(params)
            print(response['cancelResult'])
            print(response['newOrderResul'])
        else:
            print('No order placed')

    async def cancel_current_order(self):
        response=await self.client.cancel_order(orderId=self.orderId)
        print(response)
    async def get_order(self, SYMBOL, Id):
        response=await self.client.get_order(symbol=SYMBOL,orderId=Id)
        print(response)

    async def get_all_orders(self,SYMBOL):
        response=await self.client.get_all_orders(symbol=SYMBOL,orderId=Id)
        print(response)

    async def get_assets(self):
        balance= await self.client.get_asset_balance(asset=self.SYMBOL)
        asset1 = float(self.client.get_asset_balance(asset=self.S1)['free'])
        asset2 = float(self.client.get_asset_balance(asset=self.S2)['free'])
        return asset1, asset2

    async def test_conn(self):
        start_time=datetime.datetime.now()
        ws_ping= await self.client.ws_get_time()
        server_time=change_timestamp(ws_ping['serverTime'])
        print('ws time delay(client initiated):')
        print(server_time-start_time)

    async def test_connection(self):
        start_time=datetime.datetime.now()
        self.client = await AsyncClient.create(self.API_KEY, self.API_SECRET)
        ws_ping= await self.client.ws_get_time()
        start_time=datetime.datetime.now()
        server_time=change_timestamp(ws_ping['serverTime'])
        print('WS time delay(client not initiated):')
        print(server_time-start_time)

        n=0
        while n <= 3:
            await asyncio.sleep(3)
            await self.test_conn()
            n=n+1

        await self.stop()

    def __init__(self, SYMBOL, mp_queues):
        self.API_KEY=config.API_KEY
        self.API_SECRET=config.API_SECRET
        self.order_placed=False
        self.mp_queues=mp_queues

        self.SYMBOL=SYMBOL
        self.d_SYMBOL=SYMBOL

        self.S1, self.S2=return_symb(self.SYMBOL)
        self.klines=[]
        self.order_update=False

        params=parse_params(self.SYMBOL)
        self.stream_names=config.ws_stream_names
        self.number_of_klines=len(config.intervals)

        self.client=init_client()
        self.stop=False
        self.last_price=float


    async def start(self):
        self.client = await AsyncClient.create(self.API_KEY, self.API_SECRET)
        self.BM= BinanceSocketManager(self.client, None,None)

        self.USER=self.BM.user_socket()
        params=parse_params(self.SYMBOL)
        self.MULTI=self.BM.multiplex_socket(params)
        #self.test_connection()
        #Convert to BNB
        #self.client.transfer_dust()
        #self.account=await self.client.get_account()
        #Fastest way - TRADE.send()
        #Top up BNB if needed
    async def sstop(self):
        await self.client.close_connection()
        self.stop=True

    async def topup_bnb(self):
        bnb_balance = await self.client.get_asset_balance(asset='BNB')
        bnb_balance = float(bnb_balance['free'])
        min_balance=config.min_bnb_balance

        if bnb_balance < min_balance:
            topup=(min_balance-bnb_balance)*2
            qty = round(topup, 5)
            print(qty)
            order = await self.client.order_market_buy(symbol='BNBUSDT', quantity=qty)
            return order
        else:
	        return False

    async def run_ws(self):
        self.stop=False
        async with self.MULTI as ws:
               while True:
                   if self.stop==True:
                       break
                   if self.ws_restart !=True:
                       if self.d_SYMBOL != self.SYMBOL:
                            self.d_SYMBOL=self.SYMBOL
                            self.S1, self.S2=return_symb(self.SYMBOL)
                            self.klines=[]
                            params=parse_params(self.SYMBOL)
                            self.ws_restart=True
                            break
                       try:
                           msg = await ws.recv()
                           M=json.loads(msg)
                           #Connect message = 2
                           #Trade = 9
                           #24H ticker = 23
                           #Kline = 4
                           match len(M):
                               case 2:
                                   print("--- %s seconds to connect ---" %(round(time.time() - start_time,4)))
                               case 6:
                                   self.mp_queues['bookTicker'].put(M, block=False)
                               case 9:
                                   self.mp_queues['trade'].put(M, block=False)
                               case 23:
                                   self.mp_queues['24hrTicker'].put(M, block=False)
                               case 4:
                                   if len(self.klines) <= self.number_of_klines:
                                       self.klines.append(M['k'])
                                   else:
                                       self.mp_queues['kline'].put(self.klines, block=False)
                                       #print(self.klines)
                                       self.klines=[]
                            
                               case _:
                                   None
                                   #print(M)
                                   #print(len(M))
                       except Exception: 
                           traceback.print_exc()
                           self.ws_restart=True
                           break
                   await asyncio.sleep(0.001)
