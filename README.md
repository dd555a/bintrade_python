bintrade-python


This is a simple trading app for Linux for Binance using lightweight charts with VIM bindings. Orders can be placed, activated, using Vim bindings configuring your own. Collects tick data and uses order book data for latest price. Simulate trading as well on historic data. 

Features:
-Trade live binance assets
-Download historic data and simulate trading
-Calcuate an plot average lines for designated intervals
-VIM bindings - set orders visually with lines
-Set a predict line and evaluate it's accuracy against Average lines (using dcor correlation)


How to use:
Install:
./install.sh

Get data from Binance of coins listed in config.py (may take a while):
./get_data.sh

The same script will append to downloaded data if the csv exists

Run:
./run.sh

Make sure you can run pywebview on your distro, may require to install:

Place orders with:
Shift+1 - Stop Market order
Shift+2 - Stop Limit order
Shift+3 - Stop 

Adjust orders with:
Shift+J - decrease price by increment in the config
Shift+K - Increase price by increment in the config
Ctrl+J | Ctrl + K - adjust order key 1 - for stop limit, decrease | increase stop limit (% above or bellow order price, shown by dotted line), 

Click on the graph to set a point (price and time) then press Shift+K - set order at specific price point


Activate/deactivate orders with (Colors for the lines can be changed in the config):
Shift+A

Trade forward with:
Shift+L

Undo trade with:
Shift+Z

Note:
This project is mostly unmaintained as it kind of got out of hand with what I wanted to do with it and continuing it in python became harder and harder to debug, I am redoing it in Rust here:

PRs and suggestions welcome though. 
