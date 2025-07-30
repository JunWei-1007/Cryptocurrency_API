import pandas as pd
import numpy as np
import ta

# === 移動平均計算 ===
def get_average(series, length, ma_type='SMA'):
    if ma_type == 'EMA':
        return ta.trend.EMAIndicator(series, length).ema_indicator()
    elif ma_type == 'SMA':
        return series.rolling(length).mean()
    elif ma_type == 'HMA':
        wma1 = series.rolling(int(length / 2)).mean()
        wma2 = series.rolling(length).mean()
        return ((2 * wma1 - wma2).rolling(int(np.sqrt(length))).mean())
    elif ma_type == 'RMA':
        return series.ewm(alpha=1/length).mean()
    else:  # default WMA
        weights = np.arange(1, length + 1)
        return series.rolling(length).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)

# === Normalize 函數 ===
def normalize(value, avg):
    ratio = value / avg
    if ratio > 1.5: return 1.0
    elif ratio > 1.2: return 0.9
    elif ratio > 1.0: return 0.8
    elif ratio > 0.8: return 0.7
    elif ratio > 0.6: return 0.6
    elif ratio > 0.4: return 0.5
    elif ratio > 0.2: return 0.25
    else: return 0.1

# === 計算 EVEREX 指標 ===
def compute_everex(df, length=10, ma_type='WMA', smooth=3, sig_length=5, lookback=20, lkbk_calc='WMA'):
    v = df['volume'].replace(0, 1)
    close = df['close']
    open_ = df['open']
    high = df['high']
    low = df['low']

    ma_lkbk_type = 'SMA' if lkbk_calc == 'Simple' else ma_type
    vola = get_average(v, lookback, ma_lkbk_type)
    vola_n = [normalize(vv, vv_avg) * 100 for vv, vv_avg in zip(v, vola)]

    bar_spread = close - open_
    bar_range = high - low
    r2 = df['high'].rolling(2).max() - df['low'].rolling(2).min()
    src_shift = close.diff()

    sign_shift = np.sign(src_shift)
    sign_spread = np.sign(bar_spread)

    barclosing = 2 * (close - low) / bar_range * 100 - 100
    s2r = bar_spread / bar_range * 100

    bar_spread_abs = abs(bar_spread)
    bar_spread_avg = get_average(bar_spread_abs, lookback, ma_lkbk_type)
    bar_spread_ratio_n = [normalize(x, y) * 100 * s for x, y, s in zip(bar_spread_abs, bar_spread_avg, sign_spread)]

    barclosing_2 = 2 * (close - df['low'].rolling(2).min()) / r2 * 100 - 100
    shift2bar_to_r2 = src_shift / r2 * 100

    srcshift_abs = abs(src_shift)
    srcshift_avg = get_average(srcshift_abs, lookback, ma_lkbk_type)
    srcshift_ratio_n = [normalize(x, y) * 100 * s for x, y, s in zip(srcshift_abs, srcshift_avg, sign_shift)]

    pricea_n = (barclosing + s2r + bar_spread_ratio_n + barclosing_2 + shift2bar_to_r2 + srcshift_ratio_n) / 6
    bar_flow = pricea_n * vola_n / 100

    bulls = np.maximum(bar_flow, 0)
    bears = -np.minimum(bar_flow, 0)

    bulls_avg = get_average(pd.Series(bulls), length, ma_type)
    bears_avg = get_average(pd.Series(bears), length, ma_type)

    dx = bulls_avg / bears_avg
    rrof = 2 * (100 - 100 / (1 + dx)) - 100
    rrof_s = get_average(rrof, smooth, 'WMA')
    signal = get_average(rrof_s, sig_length, ma_type)

    df['RROF'] = rrof
    df['RROF_s'] = rrof_s
    df['Signal'] = signal

    df['LongEntry'] = (rrof_s > signal) & (rrof_s < -50)
    df['LongExit'] = (rrof_s > 0) | (rrof_s < signal)
    df['ShortEntry'] = (rrof_s < signal) & (signal > 50)
    df['ShortExit'] = (rrof_s < 0) | (rrof_s > signal)

    return df