import os
import csv
import datetime
import re
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
---------------------------------------------------------
設定
---------------------------------------------------------
CSV_FILE = "prices.csv"
CHART_FILE = "price_trend_chart.png"
Discord Webhook URL (環境変数から取得、なければローカル用設定)
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "YOUR_LOCAL_WEBHOOK_URL_HERE")
HEADERS = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
"Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}
---------------------------------------------------------
各サイトからの価格取得スクレイピング処理
---------------------------------------------------------
def fetch_iosys_price():
"""イオシスの iPhone 16e 128GB (A/Bランク) の最安値を検索取得"""
url = "https://iosys.co.jp/items?q=iPhone+16e+128GB"
try:
res = requests.get(url, headers=HEADERS, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
    prices = []
    # イオシスの商品一覧要素から価格を取得
    for price_tag in soup.select(".item_price, .price"):
        text = price_tag.get_text()
        nums = re.findall(r'[\d,]+', text)
        if nums:
            val = int(nums[0].replace(",", ""))
            if 50000 < val < 150000: # 妥当な価格帯のみ抽出
                prices.append(val)
    return min(prices) if prices else None
except Exception as e:
    print(f"イオシス取得エラー: {e}")
    return None


def fetch_amazon_price():
"""Amazon 整備済み品 iPhone 16e 128GB の価格を取得"""
url = "https://www.amazon.co.jp/s?k=iPhone+16e+128GB+%E6%95%B4%E5%82%99%E6%B8%88%E3%81%BF%E5%93%81"
try:
res = requests.get(url, headers=HEADERS, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
    prices = []
    for price_tag in soup.select(".a-price-whole"):
        val_str = price_tag.get_text().replace(",", "").strip()
        if val_str.isdigit():
            val = int(val_str)
            if 50000 < val < 150000:
                prices.append(val)
    return min(prices) if prices else None
except Exception as e:
    print(f"Amazon取得エラー: {e}")
    return None


def fetch_backmarket_price():
"""Back Market の iPhone 16e 128GB の最安値を取得"""
url = "https://www.backmarket.co.jp/ja-jp/s?q=iPhone+16e+128GB"
try:
res = requests.get(url, headers=HEADERS, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
    prices = []
    for price_tag in soup.find_all(text=re.compile(r'￥[\d,]+|[\d,]+円')):
        nums = re.findall(r'[\d,]+', price_tag)
        if nums:
            val = int(nums[0].replace(",", ""))
            if 50000 < val < 150000:
                prices.append(val)
    return min(prices) if prices else None
except Exception as e:
    print(f"Back Market取得エラー: {e}")
    return None


---------------------------------------------------------
メイン処理
---------------------------------------------------------
def main():
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
print(f"[{now_str}] 価格取得を開始します...")
# 各価格の取得（エラー時は前回の価格やN/Aにするためのハンドリング）
p_iosys = fetch_iosys_price()
p_amazon = fetch_amazon_price()
p_backmarket = fetch_backmarket_price()

print(f"取得結果 -> イオシス: {p_iosys}, Amazon: {p_amazon}, BackMarket: {p_backmarket}")

# 1. CSVデータの保存
file_exists = os.path.isfile(CSV_FILE)
with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["Date", "Amazon", "Iosys", "BackMarket"])
    writer.writerow([now_str, p_amazon or "", p_iosys or "", p_backmarket or ""])

# 2. 履歴データ読み込みとグラフ作成
dates, amazon_list, iosys_list, bm_list = [], [], [], []

with open(CSV_FILE, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        dates.append(row["Date"])
        amazon_list.append(float(row["Amazon"]) if row["Amazon"] else None)
        iosys_list.append(float(row["Iosys"]) if row["Iosys"] else None)
        bm_list.append(float(row["BackMarket"]) if row["BackMarket"] else None)

plt.figure(figsize=(10, 5))
plt.plot(dates, amazon_list, label="Amazon整備品", marker="o", color="#FF9900")
plt.plot(dates, iosys_list, label="イオシス", marker="s", color="#004080")
plt.plot(dates, bm_list, label="Back Market", marker="^", color="#00D1B2")

plt.title("iPhone 16e 128GB Price Trend")
plt.xlabel("Date & Time")
plt.ylabel("Price (JPY)")
plt.xticks(rotation=45, ha="right")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(CHART_FILE)
plt.close()

# 3. Discordへ通知送信
if WEBHOOK_URL and "http" in WEBHOOK_URL:
    fmt_amazon = f"¥{p_amazon:,}" if p_amazon else "取得失敗/在庫なし"
    fmt_iosys = f"¥{p_iosys:,}" if p_iosys else "取得失敗/在庫なし"
    fmt_bm = f"¥{p_backmarket:,}" if p_backmarket else "取得失敗/在庫なし"

    msg = (
        f"📱 **iPhone 16e (128GB) 価格自動レポート** ({now_str})\n"
        f"・Back Market: {fmt_bm}\n"
        f"・Amazon整備品: {fmt_amazon}\n"
        f"・イオシス (A/Bランク): {fmt_iosys}"
    )

    with open(CHART_FILE, "rb") as img:
        payload = {"content": msg}
        files = {"file": (CHART_FILE, img, "image/png")}
        res = requests.post(WEBHOOK_URL, data=payload, files=files)
        if res.status_code in [200, 204]:
            print("Discord通知の送信に成功しました。")
        else:
            print(f"Discord通知失敗: {res.status_code}")


if name == "main":
main()