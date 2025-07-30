from binance.client import Client
from decimal import Decimal, ROUND_DOWN
import pandas as pd
import time

from dotenv import load_dotenv
import os
load_dotenv()  # 載入 .env 檔案

from Strategy import compute_everex
from UnifiedTaskManager import send_telegram, Notion

# === API 設定 ===
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)

# === 工具方法 ===
# 根據 USDT 數量與當前市價，計算合法可下單的幣種數量
def calculate_buy_qty_by_usdt(symbol, usdt):
    # 取得現價
    price = float(client.get_symbol_ticker(symbol=symbol)['price'])

    # 查詢交易對的最小下單數量與步進單位（stepSize）
    info = client.get_symbol_info(symbol)
    lot_filter = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
    min_qty = Decimal(lot_filter['minQty']).normalize()
    step_size = Decimal(lot_filter['stepSize']).normalize()

    # 根據 USDT 計算原始數量
    raw_qty = Decimal(str(usdt / price))

    # 四捨五入（向下）調整為合法下單數量
    fixed_qty = raw_qty.quantize(step_size, rounding=ROUND_DOWN)

    # 若不足最小下單量，則不下單（回傳 None）
    if fixed_qty < min_qty:
        return min_qty, step_size, None

    return min_qty, step_size, fixed_qty

# 查詢「槓桿帳戶」中某資產的可用餘額
def get_margin_balance(asset):
    info = client.get_margin_account()
    for a in info['userAssets']:
        if a['asset'] == asset:
            return float(a['free'])  # 回傳可用數量
    return 0.0

# 查詢「槓桿帳戶」中某資產的借貸總額（本金 + 累積利息）
def get_borrowed_amount(asset):
    info = client.get_margin_account()
    for a in info['userAssets']:
        if a['asset'] == asset:
            return round(float(a['borrowed']) + float(a['interest']), 8)
    return 0.0

# 下單函式（適用於槓桿帳戶）：傳入方向 BUY 或 SELL、市價下單
def place_order(symbol, side, qty):
    return client.create_margin_order(
        symbol=symbol,
        side=side,         # 'BUY' 或 'SELL'
        type='MARKET',     # 使用市價下單
        quantity=str(qty)  # 下單數量（字串格式）
    )

def extract_price_and_qty(order_response):
    fills = order_response.get('fills', [])
    if not fills:
        return 0, 0  # 沒有成交紀錄

    total_qty = sum(float(f['qty']) for f in fills)
    total_cost = sum(float(f['price']) * float(f['qty']) for f in fills)
    avg_price = total_cost / total_qty if total_qty > 0 else 0

    return round(avg_price, 2), round(total_qty, 8)

# 取得並處理技術指標用的 K 線資料，回傳經 compute_everex 處理後的 DataFrame
def get_everex_dataframe(symbol, strategy_params):
    # 下載近 100 根 30 分線 K 線
    klines = client.get_klines(
        symbol=symbol,
        interval=Client.KLINE_INTERVAL_30MINUTE,
        limit=100
    )

    # 建立 DataFrame 並轉換欄位
    df = pd.DataFrame(klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])

    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('open_time', inplace=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # 套用策略函式（使用者自定義的 compute_everex）
    return compute_everex(df, **strategy_params)

# === 策略主邏輯 ===
def execute_strategy(usdt_to_use, symbol, params):
    base = symbol.replace('USDT', '')
    usdt = get_margin_balance('USDT')
    coin = get_margin_balance(base)
    df = get_everex_dataframe(symbol, params)
    last = df.iloc[-2]

    print(f"\n{symbol} 最新策略：")
    print(last[['close', 'RROF_s', 'Signal', 'LongEntry', 'ShortEntry', 'LongExit', 'ShortExit']])

    min_qty, step_size, qty = calculate_buy_qty_by_usdt(symbol, usdt_to_use)

    # === 多單進場 ===
    if coin * last['close'] <= 12 and last['LongEntry']:
        try:

            # 下單
            order = place_order(symbol, 'BUY', qty)

            # 通知
            price, qty = extract_price_and_qty(order)
            msg = f"📈 多單下單成功：{price} @ {qty}\n{order}"
            send_telegram("多單成功", msg)
            Notion("多單進場", float(price), float(qty), last['RROF_s'], last['Signal'])
            print(msg)

        except Exception as e:
            send_telegram("多單失敗", str(e))
            Notion("多單失敗", 0, 0, 0, 0)

    # === 多單平倉 ===
    elif coin * last['close'] >= 12 and last.get('LongExit', False):
        try:

            # 下單
            sell_qty = Decimal(str(coin)).quantize(step_size, rounding=ROUND_DOWN)
            order = place_order(symbol, 'SELL', sell_qty)

            # 通知
            price, qty = extract_price_and_qty(order)
            msg = f"📉 多單平倉成功：{price} @ {qty}\n{order}"
            send_telegram("多單平倉成功", msg)
            Notion("多單出場", float(price), float(qty), last['RROF_s'], last['Signal'])
            print(msg)

        except Exception as e:
            send_telegram("多單平倉失敗", str(e))
            Notion("多單平倉失敗", 0, 0, 0, 0)

    # === 空單進場 ===
    elif usdt <= 55 and last['ShortEntry']:
        try:

            # 借錢
            client.create_margin_loan(asset=base, amount=str(qty))

            # 下單
            order = place_order(symbol, 'SELL', qty)

            # 通知
            price, qty = extract_price_and_qty(order)
            msg = f"📉 空單下單成功：{price} @ {qty}\n{order}"
            send_telegram("空單成功", msg)
            Notion("空單進場", float(price), float(qty), last['RROF_s'], last['Signal'])
            print(msg)

        except Exception as e:
            send_telegram("空單失敗", str(e))
            Notion("空單失敗", 0, 0, 0, 0)

    # === 空單平倉 ===
    elif usdt >= 55 and last.get('ShortExit', False):
        try:

            # 下單
            repay_qty = get_borrowed_amount(base)
            qty_str = Decimal(str(repay_qty * 1.005)).quantize(step_size, rounding=ROUND_DOWN)
            order = place_order(symbol, 'BUY', qty_str)

            # 還錢
            time.sleep(1.5)
            btc_free = get_margin_balance(base)
            if btc_free >= float(repay_qty):
                client.repay_margin_loan(asset=base, amount=str(repay_qty))

                # 通知
                price, qty = extract_price_and_qty(order)
                msg = f"📈 市價買回 {price} @ {qty}\n{order}"
                send_telegram("空單平倉成功", msg)
                Notion("空單出場", float(price), float(qty), last['RROF_s'], last['Signal'])
                print(msg)

            else:
                msg = f"⚠️ 餘額不足（可用: {btc_free}），無法還款 {repay_qty}"
                send_telegram("空單還款失敗", msg)
                Notion("空單平倉失敗", 0, 0, 0, 0)
                print(msg)


        except Exception as e:
            send_telegram("空單平倉失敗", str(e))
            Notion("空單平倉失敗", 0, 0, 0, 0)

    else:
        print(f"📊 {symbol} 無交易信號")
        Notion("無訊號", 0, 0, 0, 0)

# === 主程式入口 ===
if __name__ == '__main__':
    configs = {
        'BTCUSDT': {
            'length': 10,
            'ma_type': 'WMA',
            'smooth': 3,
            'sig_length': 5,
            'lookback': 20,
            'lkbk_calc': 'WMA'
        }
    }

    for symbol, param in configs.items():
        execute_strategy(40, symbol, param)

    print("\n")
