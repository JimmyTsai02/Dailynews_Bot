import os
import json  # <--- 就是少了這行！
import feedparser
import requests
import concurrent.futures
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# ================= 設定區 =================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 新聞 RSS 來源設定
RSS_FEEDS = {
    "🌍 國際重點大事件 (含華爾街與總經)": [
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", 
        "http://feeds.bbci.co.uk/news/business/rss.xml",   
        "http://rss.cnn.com/rss/edition_world.rss",        
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", 
        "https://moxie.foxnews.com/google-publisher/world.xml" 
    ],
    "📈 國內金融與科技時事": [
        "https://www.cna.com.tw/cna2018api/api/WNSearch/GetRss?newsType=afe", 
        "https://news.cnyes.com/rss/macromind.xml",                           
        "https://money.udn.com/rssfeed/news/1001/5588/5599?ch=money",         
        "https://www.bnext.com.tw/rss"                                        
    ]
}

# ================= 執行區 =================

def process_single_feed(category, url):
    """處理單一 RSS 來源的函數 (供多執行緒使用)"""
    result_text = ""
    try:
        response = requests.get(url, timeout=10)
        feed = feedparser.parse(response.content)
        
        for entry in feed.entries[:3]:
            title = getattr(entry, 'title', '無標題')
            link = getattr(entry, 'link', url)
            summary = getattr(entry, 'summary', '')[:200]
            result_text += f"標題: {title}\n連結: {link}\n摘要: {summary}\n---\n"
    except Exception as e:
        print(f"⚠️ 讀取 {url} 失敗跳過: {e}")
        
    return category, result_text

def fetch_news():
    """使用多執行緒從 RSS 抓取最新新聞"""
    news_dict = {category: "" for category in RSS_FEEDS.keys()}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for category, urls in RSS_FEEDS.items():
            for url in urls:
                futures.append(executor.submit(process_single_feed, category, url))
        
        for future in concurrent.futures.as_completed(futures):
            category, text = future.result()
            news_dict[category] += text
            
    news_content = ""
    for category, text in news_dict.items():
        if text:
            news_content += f"[{category}]\n{text}"
            
    return news_content

def summarize_and_translate(raw_text):
    """呼叫 OpenAI API 輸出 JSON 格式，包含潛在影響 (Impact) 與情緒分數"""
    if not raw_text.strip():
        return None

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    prompt_system = """
    你是一位資深的金融市場分析師與國際新聞總編。請從素材中嚴格挑選最具代表性的 4 則國際大事，以及 4 則國內金融/科技時事。
    
    【核心任務】：
    1. 不只要做摘要，更要提供「Actionable Insights」。請特別針對台灣總經數據、台灣金融業或全球供應鏈，給出一句精準的「潛在影響 (Impact)」。
    2. 【⚠️ 語言強制要求】：所有的外文新聞素材，請務必、絕對要「全部翻譯成流暢的繁體中文（zh-TW）」。

    【輸出格式要求】：
    你必須嚴格輸出以下 JSON 格式，不要包含任何其他說明文字或 Markdown 標籤：
    {
      "news": [
        {
          "category": "分類名稱 (例如：🌍 國際重點大事件)",
          "title": "新聞標題",
          "url": "原始連結網址",
          "summary": "約 100 字的客觀重點摘要",
          "impact": "約 50 字的潛在影響分析 (So What?)",
          "sentiment": "positive, negative, 或 neutral"
        }
      ]
    }
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1 
        )
        
        result_json = json.loads(response.choices[0].message.content.strip())
        return result_json.get("news", [])
        
    except Exception as e:
        print(f"❌ OpenAI API 發生錯誤或 JSON 解析失敗: {e}")
        return None

def send_to_discord(news_list):
    """將結構化資料轉換為 Discord Embeds (視覺化卡片) 並發送"""
    if not news_list:
        print("⚠️ 沒有新聞資料可供發送。")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    embeds = []
    
    for item in news_list:
        # 根據情緒設定卡片左側的顏色色條
        sentiment = item.get("sentiment", "neutral").lower()
        if sentiment == "positive":
            color = 0x2ecc71 # 綠色 (利多)
        elif sentiment == "negative":
            color = 0xe74c3c # 紅色 (利空)
        else:
            color = 0x95a5a6 # 灰色 (中立)
            
        embed = {
            "author": {
                "name": item.get("category", "每日新聞")
            },
            "title": item.get("title", "無標題"),
            "url": item.get("url", ""),
            "description": f"**📝 摘要：**\n{item.get('summary', '無摘要')}\n\n**💡 潛在影響 (Impact)：**\n{item.get('impact', '無分析')}",
            "color": color
        }
        embeds.append(embed)

    # Discord 限制一次 Webhook 請求最多只能帶 10 個 Embeds
    if len(embeds) > 10:
        embeds = embeds[:10]

    payload = {
        "content": f"## 🌞 {today_str} 專業經理人晨報已送達",
        "embeds": embeds
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print("✅ 成功推播 Embeds 到 Discord！")
        else:
            print(f"❌ 推播失敗，狀態碼: {response.status_code}, 錯誤訊息: {response.text}")
    except Exception as e:
        print(f"❌ Discord 發送過程中發生網路錯誤: {e}")

if __name__ == "__main__":
    print("🔄 正在使用多執行緒並發抓取新聞...")
    raw_news = fetch_news()
    
    print("🤖 正在請 OpenAI 翻譯與摘要分析...")
    discord_report = summarize_and_translate(raw_news)
    
    print("💬 正在推播至 Discord...")
    send_to_discord(discord_report)