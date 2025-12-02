<div align="center">

# bintrade-python
[![Made with Python](https://img.shields.io/badge/Python-3.8+-c7a002?logo=python&logoColor=white)](https://python.org "Go to Python homepage")
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

![example](https://github.com/dd555a/bintrade_python/blob/main/examples/example1.png)


WIP - not all functionality currently available
</div>

This is a simple trading app for Linux for Binance using lightweight charts with VIM bindings. Orders can be placed, activated, using Vim bindings configuring your own. Collects tick data and uses order book data for latest price. Simulate trading as well on historic data. 



## How to use:
### Install:
```bash
./install.sh
```

Get data from Binance of coins listed in config.py (may take a while):
```bash
./get_data.sh
```

The same script will append to downloaded data if the csv exists

## Run:
```bash
./run.sh
```

## Features
1. Trade live binance assets
2. Download historic data and simulate trading
3. Calcuate an plot average lines for designated intervals
4. VIM bindings - set orders visually with lines
5. Set a predict line and evaluate it's accuracy against Average lines (using dcor correlation)
6. Switch Live/Hist mode with Hist|Live! button. Live price is displayed as a yellow line (I am unable to get the live tick working properly for some reason) taken from the order book websocket info. 

### Place orders with:
```bash
Shift+1 - Stop Market order
```
```bash
Shift+2 - Stop Limit order
```
```bash
Shift+3 - Stop 
```

### Adjust orders with:
```bash
Shift+J 
```

#### Increase price by increment in the config
Decrease price by increment in the config
```bash
Shift+K 
```
#### Adjust order key 1 - for stop limit, decrease | increase stop limit (% above or bellow order price, shown by dotted line), 
```bash
Ctrl+J | Ctrl + K 
```

### Click on the graph to set a point (price and time) then press Shift+K - set order at specific price point

### Activate/deactivate orders with (Colors for the lines can be changed in the config):
```bash
Shift+A
```

### Trade forward with:
```bash
Shift+L
```

### Undo trade with:
```bash
Shift+Z
```

### Cycle next wicks:
```bash
Shift+W
```

### Click on Hist/Live to toggle hist/live
Change asset shown or date:
Enter+"ASSETNAME", IE "BTCUSDC" to switch available asset or date in format "YYYY-MM-DD" to change the trading time for historical trading

### NOTE
NOTE: I am rewriting this project in rust as it has gotten out of hand and is hard to debug. Here:
https://github.com/dd555a/bintrade_egui
