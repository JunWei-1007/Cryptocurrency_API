from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
from datetime import datetime
import time

from UnifiedTaskManager import sync_windows_time

def run_buy_script():
    now = datetime.now()
    print(f"[{now}] 等待 5 秒後執行")
    time.sleep(5)
    print(f"[{datetime.now()}] ▶ 開始執行")
    subprocess.run(["python", "BuyMarginStrategy.py"])  # 根據實際路徑修改

# 建立排程器
scheduler = BlockingScheduler()

# 每天早上 8 點與晚上 8 點執行時間同步
scheduler.add_job(sync_windows_time, 'cron', hour=8, minute=0)
scheduler.add_job(sync_windows_time, 'cron', hour=20, minute=0)

# 每整點與每 30 分鐘執行一次 Buy.py
scheduler.add_job(run_buy_script, 'cron', minute='0,30')

print("APScheduler 啟動（每日 8:00 與 20:00 同步時間，每整點與 30 分執行 Buy.py）")
scheduler.start()