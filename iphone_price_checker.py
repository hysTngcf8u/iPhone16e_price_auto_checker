import csv
import datetime
import os
import re
import matplotlib.pyplot as plt
import requests

# --- 設定 ---
CSV_FILE = "prices.csv"
CHART_FILE = "price_trend_chart.png"

# Discord Webhook URL（環境変数から取得）
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


# --- 各サイトの価格取得関数 ---
def get_iosys_price():
    try:
        url = "https://iosys.co.jp/items/smartphone/iphone/iphone16e"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"￥([0-9,]+)", res.text)
            clean_prices = [
                int(p.replace(",", ""))
                for p in prices
                if int(p.replace(",", "")) > 50000
            ]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"イオシス取得エラー: {e}")
    return 92800  # エラー時の基準値


def get_amazon_price():
    try:
        url = "https://www.amazon.co.jp/s?k=iPhone+16e+128GB+整備済み品"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"￥([0-9,]+)", res.text)
            clean_prices = [
                int(p.replace(",", ""))
                for p in prices
                if int(p.replace(",", "")) > 50000
            ]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"Amazon取得エラー: {e}")
    return 87900  # エラー時の基準値


def get_backmarket_price():
    try:
        url = "https://www.backmarket.co.jp/ja-jp/search?q=iPhone+16e+128GB"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"([0-9,]+)\s?円", res.text)
            clean_prices = [
                int(p.replace(",", ""))
                for p in prices
                if int(p.replace(",", "")) > 50000
            ]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"BackMarket取得エラー: {e}")
    return 80100  # エラー時の基準値


# --- メイン処理 ---
def main():
    if not WEBHOOK_URL:
        print("エラー: DISCORD_WEBHOOK_URL が設定されていません。")
        return

    amazon = get_amazon_price()
    iosys = get_iosys_price()
    backmarket = get_backmarket_price()

    # 日本時間（UTC+9）の現在時刻を取得
    now = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))
    )
    time_str = now.strftime("%Y-%m-%d %H:%M")

    # 1. CSVへの保存・追記
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writerow(["Date", "Amazon", "Iosys", "BackMarket"])
        writer.writerow([time_str, amazon, iosys, backmarket])

    print(f"CSVを更新しました: {time_str}")

    # 2. 過去データから推移グラフを作成
    dates, amazon_list, iosys_list, backmarket_list = [], [], [], []
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Date") and row.get("Amazon"):
                dates.append(row["Date"])
                amazon_list.append(int(row["Amazon"]))
                iosys_list.append(int(row["Iosys"]))
                backmarket_list.append(int(row["BackMarket"]))

    plt.figure(figsize=(10, 5))
    plt.plot(dates, amazon_list, label="Amazon", marker="o", color="#FF9900")
    plt.plot(dates, iosys_list, label="Iosys", marker="s", color="#004080")
    plt.plot(
        dates, backmarket_list, label="BackMarket", marker="^", color="#00D1B2"
    )

    plt.title("iPhone 16e 128GB Price Trend")
    plt.xlabel("Date & Time")
    plt.ylabel("Price (JPY)")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

    # 3. Discordへ通知送信
    msg = (
        f"📱 **iPhone 16e (128GB) 価格レポート** ({time_str})\n"
        f"・Back Market: ¥{backmarket:,}\n"
        f"・Amazon整備品: ¥{amazon:,}\n"
        f"・イオシス: ¥{iosys:,}"
    )

    with open(CHART_FILE, "rb") as f:
        payload = {"content": msg}
        files = {"file": (CHART_FILE, f, "image/png")}
        res = requests.post(WEBHOOK_URL, data=payload, files=files)

    if res.status_code in [200, 204]:
        print("Discordへの通知に成功しました！")
    else:
        print(f"Discord通知失敗: {res.status_code} - {res.text}")


if __name__ == "__main__":
    main()
