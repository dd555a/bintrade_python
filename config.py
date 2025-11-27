#Binance credentials
API_KEY = '<YOUR API KEY>'
API_SECRET = '<YOUR API SECRET KEY>'

#Chart config
extend_range_days=3 

intervals=['1min','3min','5min','15min','30min','1hour','2hour','4hour','6hour','8hour','12hour','1day','3day','1week','1month']

alines_intv=['15min','1hour','6hour']
a_intv='15min'
a_intv1='1hour'
a_intv2='6hour'

coins_of_interest=['BTCUSDT','BTCUSDC','DOGEUSDT','ETHUSDT','DOGEBTC','ETHBTC','TRUMPUSDT']
individual_coins=['BTC','USDT','USDC','DOGE','ETH','TRUMP']

###Set chart precision for specific
precision={'DOGEUSDT':5}
default_precision=2

keep_platd=True
ws_method=0

#Live chart defaults
l_interval='15min'
chart_max_wicks=9000
min_bnb_balance=25

#Move to MAIN
klines_intv=["1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d","3d","1w","1M"]

default_symbol='BTCUSDT'
default_interval='1min'
default_next_wicks=20

k0_inc=0.005
k1_inc=0.1
k2_inc=0.1

default_trade_method=0
trade_methods=['Manual']

#Line styles
stop='dashed'
stop_width=1
stop_market='large_dashed'
stop_market_width=2

limit='solid'
limit_width=2

predict='solid'
predict_width=2
predict_line_col='#bf80ff'

points_line=False
points='dashed'
points_width=2
points_line_col='#ffffff'

avg_line='dashed'
avg_width=2
avg_line_col='#33ffff'
avg_line_col1='#6666ff'
avg_line_col2='#1a1aff'

set_last_order=False
last_order='large_dashed'
last_order_width=1
fee_color='#ff6600'
fee_line='dashed'
fee_width=1
tick_color='#cccc00'
tick_width=1
tick_style='large_dashed'

active_buy_col='#00ff00'
active_sell_col='#ff0000'

inactive_buy_col='#ccffcc'
inactive_sell_col='#ffad99'

fee=0.0015

last_buy_col='#ccffcc'
last_sell_col='#ffd6cc'

last_stats_days=90
stats1_intervals=["15min","1hour","6hour","1day"]
consistency_interval=1440
hour_interval=1440

#WS settings
ws_streams=['@ticker','@kline_','@bookTicker','@trade']
ws_stream_names=['24hrTicker','kline','bookTicker','trade']

##Historic trade defaults
h_start_money=10000
h_taker_fee=0.00075
h_maker_fee=0.00075
h_default_quant=1
h_next_wicks=20
wicks=[1,2,3,5,10,15,20,30,50,100,200,300]

bought_message="Bought!"
sold_message="Sold!"

#H take screenshot every forward motion:
hscreenshot=False

#0 - wicks - high/low trigger limit orders -
#1 - open/close value strigger limit orders
h_eval_mode=0
