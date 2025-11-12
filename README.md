# Binance Grid Trading Bot

A grid trading bot for automated trading on Binance Futures. This bot implements a grid trading strategy that automatically places buy and sell orders at predefined price levels based on grid points around a middle price.

For purchasing trading frequency and decrease the price risk, the trading bot set market order instead of limit order to have the better inventory efficiency/controls. 


## Features

- Automated grid trading on Binance Futures (USDT-M)
- Configurable grid layers and spread
- Automatic take-profit order placement
- Isolated margin mode with hedged positions
- Telegram notifications for trade events
- Real-time price monitoring and order execution

## Requirements

See `requirements.txt` for dependencies.

## Configuration

Set up your API credentials in a `.env` file:
- `API_KEY`: Your Binance API key
- `SECRET_KEY`: Your Binance secret key

Configure trading parameters in `main.py`:
- Symbol to trade
- Grid spread percentage
- Number of grid layers
- Leverage and position size