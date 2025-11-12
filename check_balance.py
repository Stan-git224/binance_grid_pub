from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("SECRET_KEY")

def get_asset_balance(account_info, asset_symbol):
    for asset in account_info:
        if asset['asset'] == asset_symbol:
            balance = float(asset['balance'])
            availableBalance = float(asset['availableBalance'])
            return balance, availableBalance

def check_binance_futures_balance():
    client = Client(API_KEY, API_SECRET)

    # 獲取期貨帳戶資訊
    account_info = client.futures_account_balance()
    usdt_balance, usdt_wallet_balance = get_asset_balance(account_info, "USDT")
    usdc_balance, usdc_wallet_balance = get_asset_balance(account_info, "USDC")
    print(f"USDC balance: {usdc_balance}, USDC wallet balance: {usdc_wallet_balance}")
    print(f"USDT balance: {usdt_balance}, USDT wallet balance: {usdt_wallet_balance}")


def close_all_positions():
    client = Client(API_KEY, API_SECRET)
    # get all positions
    positions = client.futures_position_information()
    print(positions)

    for p in positions:
        symbol = p['symbol']
        amount = float(p['positionAmt'])
        position_side = p['positionSide'] 

        if amount != 0:
            try:
                if position_side == 'BOTH':

                    side = 'SELL' if amount > 0 else 'BUY'
                    order_params = {
                        'symbol': symbol,
                        'side': side,
                        'type': 'MARKET',
                        'quantity': abs(amount),
                    }
                else:
                    side = 'SELL' if position_side == 'LONG' else 'BUY'

                    order_params = {
                        'symbol': symbol,
                        'side': side,
                        'type': 'MARKET',
                        'quantity': abs(amount),
                        'positionSide': position_side,
                    }

                client.futures_create_order(**order_params)
                print(f"close position {symbol}: {abs(amount)} - {position_side}")
            except Exception as e:
                print(f"some error occurred in closing position {symbol}: {str(e)}")


def cancel_all_orders():
    client = Client(API_KEY, API_SECRET)
    
    try:
        open_orders = client.futures_get_open_orders()
        
        if not open_orders:
            print("No open orders")
            return
        
        print(f"find {len(open_orders)} open orders")
        
        symbols = set(order['symbol'] for order in open_orders)
        
        for symbol in symbols:
            try:
                result = client.futures_cancel_all_open_orders(symbol=symbol)
                print(f"cancel all orders for {symbol}")
                
            except Exception as e:
                print(f"error in canceling orders for {symbol}: {str(e)}")
                
                symbol_orders = [order for order in open_orders if order['symbol'] == symbol]
                for order in symbol_orders:
                    try:
                        client.futures_cancel_order(
                            symbol=symbol,
                            orderId=order['orderId']
                        )
                        print(f"cancel single order for {symbol} - {order['orderId']}")
                    except Exception as single_error:
                        print(f"error in canceling single order for {symbol} - {order['orderId']}: {str(single_error)}")
        
        print("all orders canceled")
        
    except Exception as e:
        print(f"error in getting orders: {str(e)}")


if __name__ == "__main__":

    # check binance futures balance
    # check_binance_futures_balance()
    # close_all_positions()
    cancel_all_orders()


