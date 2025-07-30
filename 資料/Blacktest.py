import pandas as pd
from bokeh.plotting import figure, show, output_file
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Span, Label
from Strategy import compute_everex  # 自定義的指標計算

# === 讀取資料 ===
df = pd.read_csv('BTCUSDT_30min_kline.csv')
df.columns = [col.lower() for col in df.columns]

if 'open_time' not in df.columns:
    raise KeyError("缺少 open_time 欄位，請確認 CSV 格式")

df['timestamp'] = pd.to_datetime(df['open_time'])
df.set_index('timestamp', inplace=True)

# === 計算指標 ===
df = compute_everex(df)

# === 準備 K 棒資料 ===
df["inc"] = df.close >= df.open
df["dec"] = df.close < df.open

source = ColumnDataSource(df)

TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

p = figure(x_axis_type="datetime", tools=TOOLS, width=1200, title="BTCUSDT 30min - Bokeh K線圖")
p.xaxis.major_label_orientation = 0.785

# === K 棒繪製 ===
w = 20 * 60 * 1000  # 半小時寬度（毫秒）

p.segment(x0='timestamp', y0='high', x1='timestamp', y1='low', source=source, color="black")

source_inc = ColumnDataSource(df[df['inc']])
source_dec = ColumnDataSource(df[df['dec']])

p.vbar(x='timestamp', width=w, top='open', bottom='close', source=source_inc,
       fill_color="green", line_color="black")

p.vbar(x='timestamp', width=w, top='open', bottom='close', source=source_dec,
       fill_color="red", line_color="black")

# === 畫進出場箭頭 ===
entry = df[df['ShortEntry'] == True]
exit_ = df[df['ShortExit'] == True]

p.triangle(entry.index, entry['low'] * 0.98, size=15, color='green', legend_label='Entry')
p.inverted_triangle(exit_.index, exit_['high'] * 1.02, size=15, color='red', legend_label='Exit')

# === 畫 RROF_s 與 Signal 指標圖 ===
p2 = figure(x_axis_type="datetime", tools=TOOLS, width=1200, height=300, title="RROF_s & Signal", x_range=p.x_range)
p2.line(df.index, df['RROF_s'], color='blue', legend_label='RROF_s')
p2.line(df.index, df['Signal'], color='red', legend_label='Signal')

# === 輸出網頁 ===
output_file("everex_bokeh_plot.html")
show(column(p, p2))
