import ccxt.pro as ccxtpro
import asyncio
import logging
from dotenv import load_dotenv
import os
import tg_notify
from binance.client import Client
"""
This is a market order grid trading bot. The strategy will have long position if the ticker price (close) is below the middle price.
And it will have short position if the ticker price (close) is above the middle price.
If we got some position here, we will set the tp order to take profit.
There is no down side protection here so we must use ISOLATED mode.
"""
load_dotenv(override=True)

# set log format / output
logging.basicConfig(
    level=logging.INFO,  # set log level to INFO
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="trade_log.log",  # set log output file
    filemode="a",  # "a" for append mode, "w" for overwrite mode
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

logger = logging.getLogger()  # get root logger
logger.addHandler(console_handler)  # ensure logs are output to the terminal

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("SECRET_KEY")

alert = tg_notify.send_telegram_message

def get_asset_balance(account_info, asset_symbol):
    for asset in account_info:
        if asset['asset'] == asset_symbol:
            balance = float(asset['balance'])
            availableBalance = float(asset['availableBalance'])
            return balance, availableBalance

def check_binance_futures_balance():
    # initialize Binance client
    client = Client(API_KEY, API_SECRET)

    # fetch Account 
    account_info = client.futures_account_balance()
    # get USDT balance
    usdt_balance, usdt_wallet_balance = get_asset_balance(account_info, "USDT")
    print(f"USDT balance: {usdt_balance}, USDT wallet balance: {usdt_wallet_balance}")


async def main(symbol):

    # leverage setting
    leverage_grid = LEVERAGE_GRID

    # amount per trade
    grid_USDT_amount = GRID_USDT_AMOUNT

    # grid spread
    grid_spread = GRID_SPREAD

    # grid laye number
    grid_layer_number = GRID_LAYER_NUMBER

    binance = ccxtpro.binanceusdm(
        {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "enableRateLimit": True,
        }
    )
    # binance.set_sandbox_mode(True)

    # track previous price
    previous_price = None

    # track last triggered grid index and current grid order count
    last_triggered_grid_index = -1
    current_grid_order_count = 0

    max_grid_order_count = MAX_GRID_ORDER_COUNT

    try:
        # fetch middle price
        ticker = await binance.fetch_ticker(symbol)
        middle_price = round((ticker["high"] + ticker["low"]) / 2, 1)

        upper_grid = [
            round(middle_price * ((1 + grid_spread) ** i), 2) for i in range(1, grid_layer_number+1)
        ]
        lower_grid = [
            round(middle_price * ((1 - grid_spread) ** i), 2) for i in range(1, grid_layer_number+1)
        ]
        grid_price = sorted(lower_grid + [middle_price] + upper_grid)
        # logging.debug(f"grid price: {grid_price}")
        logging.info(f"lower grid: {sorted(lower_grid)}")
        logging.info(f"middle price: {middle_price}")
        logging.info(f"upper grid: {sorted(upper_grid)}")

        # set isolated mode
        try:
            await binance.set_margin_mode(marginMode="isolated", symbol=symbol)
        except Exception as e:
            logging.info(f"no need to set isolated mode: {e}")

        # set hedged mode
        try:
            await binance.set_position_mode(hedged=True, symbol=symbol)
        except Exception as e:
            logging.info(f"no need to set hedged mode: {e}")

        try:
            await binance.set_leverage(leverage=leverage_grid, symbol=symbol)
        except Exception as e:
            logging.info(f"error in setting leverage: {e}")
    except Exception as e:
        logging.error(f"error in getting ticker or setting position mode: {e}")
        return

    # start streaming!
    while True:
        try:
            ticker = await binance.watch_ticker(symbol)
            ticker_price = ticker["close"]
            # print(ticker_price)

            # Check the price record and calculate the cross count
            if previous_price is not None:  # ensure there is a previous price to compare
                for i, grid_p in enumerate(grid_price):
                    crossed_above = previous_price <= grid_p and ticker_price > grid_p
                    crossed_below = previous_price >= grid_p and ticker_price < grid_p
                    if crossed_above or crossed_below:
                        # if switch to new grid point, reset order count
                        if i != last_triggered_grid_index:
                            last_triggered_grid_index = i
                            current_grid_order_count = 0
                            logging.info(
                                f"switch to new grid point: {grid_p} (index {i}), reset order count"
                            )
                        if current_grid_order_count < max_grid_order_count:
                            logging.info(
                                f"price crossed grid point: {grid_p} (index {i}), start placing order"
                            )

                            orderbook = await binance.watch_order_book(symbol)
                            bid_1_price = orderbook["bids"][0][0]
                            ask_1_price = orderbook["asks"][0][0]

                            # below middle price, execute buy grid order and hedging sell order
                            if ticker_price <= middle_price:
                                logging.info(
                                    f"execute buy grid order and hedging sell order, grid price: {grid_p}, current price: {ticker_price}"
                                )
                                # print(f"DEBUG: enter buy logic, ticker_price: {ticker_price}, middle_price: {middle_price}")
                                # place market order
                                buy_order = None
                                try:
                                    buy_order = await binance.create_market_buy_order(
                                        symbol=symbol,
                                        amount=round(grid_USDT_amount / middle_price, 2),
                                        params={"positionSide": "LONG"},
                                    )
                                    current_grid_order_count += 1  # 只有市價單成功才增加計數
                                    print("BUYYY")
                                    logging.info(
                                        f"Buy order placed, price: {buy_order['average']}, quantity: {buy_order['filled']}, current grid order count: {current_grid_order_count}"
                                    )
                                    alert(f"Buy order placed, price: {buy_order['average']}, quantity: {buy_order['filled']}")
                                except Exception as e:
                                    logging.error(f"error in placing buy order: {e}")

                                # place TP order (not counted in limit)
                                if buy_order:
                                    try:
                                        tp_limit_price = round(
                                            buy_order["average"] * (1 + grid_spread), 2)
                                        tp_buy_price = round(buy_order["average"] + 0.2, 2)
                                        tp_buy_order = await binance.create_order(
                                            symbol=symbol,
                                            type="TAKE_PROFIT",
                                            side="sell",
                                            amount=buy_order["filled"],
                                            price=tp_limit_price,
                                            params={
                                                "stopPrice": tp_buy_price,
                                                "timeInForce": "GTC",
                                                "positionSide": "LONG",
                                            },
                                        )
                                        if tp_buy_order:
                                            logging.info(
                                                f"TP buy order placed, trigger price: {tp_buy_price}, take profit price: {tp_limit_price}"
                                            )
                                    except Exception as e:
                                        logging.error(f"error in placing TP buy order: {e}")
                                        # TP order failed does not affect the counter

                            elif ticker_price > middle_price:
                                logging.info(
                                    f"execute sell grid order and hedging buy order, grid price: {grid_p}, current price: {ticker_price}"
                                )
                                # place market order
                                sell_order = None
                                try:
                                    sell_order = await binance.create_market_sell_order(
                                        symbol=symbol,
                                        amount=round(grid_USDT_amount / middle_price, 2),
                                        params={"positionSide": "SHORT"},
                                    )
                                    current_grid_order_count += 1  # only count if market order is successful
                                    print("SELLLL")
                                    logging.info(
                                        f"Sell order placed, price: {sell_order['average']}, quantity: {sell_order['filled']}, current grid order count: {current_grid_order_count}"
                                    )
                                    alert(f"Sell order placed, price: {sell_order['average']}, quantity: {sell_order['filled']}")
                                except Exception as e:
                                    logging.error(f"error in placing sell order: {e}")

                                # place TP order (not counted in limit)
                                if sell_order:
                                    try:
                                        tp_sell_limit_price = round(
                                            sell_order["average"] * (1 - grid_spread), 2
                                        )
                                        tp_sell_price = round(
                                            sell_order["average"] - 0.2, 2)
                                        tp_sell_order = await binance.create_order(
                                            symbol=symbol,
                                            type="TAKE_PROFIT",
                                            side="buy",
                                            amount=sell_order["filled"],
                                            price=tp_sell_limit_price,
                                            params={
                                                "stopPrice": tp_sell_price,
                                                "timeInForce": "GTC",
                                                "positionSide": "SHORT",
                                            },
                                        )
                                        if tp_sell_order:
                                            logging.info(
                                                f"TP sell order placed, trigger price: {tp_sell_price}, take profit price: {tp_sell_limit_price}"
                                            )
                                    except Exception as e:
                                        logging.error(f"error in placing TP sell order: {e}")
                                        # TP order failed does not affect the counter

                        else:
                            logging.info(
                                f"grid point {grid_p} reached {max_grid_order_count} order limit, skip this order"
                            )
                        break  # only trigger one grid point, exit loop after triggering

            previous_price = ticker_price  # update previous price
            await asyncio.sleep(0.1)  # avoid too frequent requests

        except Exception as e:
            logging.error(f"error in placing order or watching: {e}")
            continue


if __name__ == "__main__":
    symbol = "BTCUSDT"
    # leverage setting
    LEVERAGE_GRID = 5

    # capital per trade
    GRID_USDT_AMOUNT = 100

    GRID_SPREAD = 0.008

    # grid laye number
    GRID_LAYER_NUMBER = 6

    MAX_GRID_ORDER_COUNT = 5 
    asyncio.run(main(symbol))
