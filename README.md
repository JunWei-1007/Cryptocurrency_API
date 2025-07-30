# 🚀 Crypto Margin Trading Bot

自動化槓桿交易機器人，基於 **Binance API**，使用 **EVEREX 技術指標策略**，並整合 **Notion、Telegram、Email 通知**，支援 **APScheduler** 進行自動化排程。

---

## ✅ 功能特色
- **Binance 槓桿交易**
  - 自動判斷多單/空單進出場
- **技術策略**
  - 基於 EVEREX 指標計算
- **多種通知整合**
  - Notion 自動記錄
  - Telegram 即時推播
  - Email 通知
- **自動排程**
  - APScheduler 定時執行策略

---

## 📂 專案架構與檔案說明
```
.
├── UnifiedTaskManager.py   # 通知與工具模組
├── Strategy.py             # 技術指標策略
├── BuyMarginStrategy.py    # 核心交易邏輯
├── Scheduler.py            # 任務排程器
├── .env                    # 環境變數設定（需自行建立）
```

### **1️⃣ UnifiedTaskManager.py**
- 功能：提供通知與資料同步工具。
- **包含：**
  - `Notion()`：上傳交易訊號至 Notion Database。
  - `send_telegram()`：推播訊息至 Telegram。
  - `send_email()`：發送 Gmail 通知。
  - `sync_windows_time()`：同步 Windows 系統時間。

---

### **2️⃣ Strategy.py**
- 功能：實作 **EVEREX 技術指標**。
- **主要特色：**
  - 計算 RROF、Signal 指標。
  - 判斷多空訊號（`LongEntry`、`ShortEntry`、`Exit` 條件）。

---

### **3️⃣ BuyMarginStrategy.py**
- 功能：交易策略主程式。
- **職責：**
  - 讀取 `.env` 中的 Binance API Key。
  - 取得槓桿帳戶餘額。
  - 依據策略訊號，自動下單。
  - 記錄結果並透過 Telegram & Notion 通知。

---

### **4️⃣ Scheduler.py**
- 功能：使用 APScheduler 排程任務。
- **排程設定：**
  - 每整點與半點 → 執行交易策略。
  - 每日 08:00 & 20:00 → 系統時間同步。

---

## 🔧 安裝與設定

### 設定 `.env`
建立 `.env` 並填入：
```
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id
GMAIL_USER=your_gmail_address
GMAIL_APP_PASSWORD=your_gmail_app_password
TO_EMAIL=receiver_email
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## ▶ 使用方法
- **手動執行策略**
```bash
python BuyMarginStrategy.py
```

- **啟動排程器**
```bash
python Scheduler.py
```
