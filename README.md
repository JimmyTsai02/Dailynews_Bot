# 📰 Daily Financial News Bot 

每天早上醒來，面對海量的國內外財經新聞，我們需要的通常不是「更多的資訊」，而是「精準的洞察」。

這個專案是我為了解決日常資訊焦慮而開發的輕量級 Data Pipeline。透過自動化抓取多方權威財經媒體的 RSS 資訊，交由 LLM 進行雜訊過濾與情緒分析，並在每天早上開盤前，準時將帶有「潛在市場影響 (Actionable Insights)」的視覺化卡片推播到 Discord。


## 💡專案緣由

- **資訊過載**：手動瀏覽 WSJ、CNN、鉅亨網等十幾個網站太耗時。
- **缺乏重點**：一般的新聞摘要只是縮短字數，但我更想知道新聞資訊對總體經濟或產業板塊有什麼影響。
- **閱讀體驗差**：純文字推播很難快速抓到重點，需要有視覺化的情緒燈號（利多/利空/中立）輔助判斷。

## ✨ 核心特色

* **🚀 Concurrency**
  放棄傳統的同步請求，改用 `ThreadPoolExecutor` 同時抓取近 10 個 RSS 來源，降低 I/O 等待時間。
* **🧠 LLM 結構化輸出 **
  透過 Prompt Engineering 強制 OpenAI 輸出標準化 JSON，確保產出的不只是文字，而是包含標題、摘要、情緒分數與市場影響的「結構化數據」，方便未來接入資料庫。
* **📊 視覺化情緒卡片**
  捨棄純文字 Markdown，根據 AI 判斷的新聞情緒，動態生成帶有左側色條（綠色利多、紅色利空）的 Discord Embeds 卡片，提升手機端的閱讀體驗。
* **☁️ Serverless 雲端全自動化**
  完全依賴 GitHub Actions 的 Cron Job 進行排程部署。每天自動喚醒 Ubuntu 虛擬機執行腳本，零地端伺服器成本。

## 🛠️ Tech Stack

* **Language**: Python 3.11
* **Data Extraction**: `requests`, `feedparser`
* **AI & NLP**: `openai` (gpt-4o-mini)
* **Infrastructure**: GitHub Actions (CI/CD 排程)
* **Integration**: Discord Webhook API

## 📡 追蹤的數據源

涵蓋了全球總經、華爾街動態與台灣科技金融產業：
* **Global**: WSJ, BBC News, CNN, CNBC, FOX News
* **Local (TW)**: 中央社 (CNA), 鉅亨網 (Anue), 經濟日報, 數位時代 (Bnext)

## Quick Start

如果你也想擁有一個專屬的 AI 晨報助理，歡迎 Fork 這個專案：

1. **Fork** 此專案到你的個人 GitHub。
2. 進入專案的 **Settings > Secrets and variables > Actions**。
3. 新增兩個 Repository secrets：
   * `OPENAI_API_KEY`: 你的 OpenAI API 金鑰
   * `DISCORD_WEBHOOK_URL`: 你的 Discord 頻道 Webhook 網址
4. 進入 **Actions** 頁籤，點擊 `workflow_dispatch` 手動觸發第一次執行。
5. 完成！預設排程為每天台灣時間早上 09:00 (UTC 01:00)，你也可以在 `.github/workflows/schedule.yml` 中自由修改 Cron 時間。


