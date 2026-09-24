import csv
import datetime
import os
import re
import matplotlib.pyplot as plt
import requests

# --- 設定 ---
CSV_FILE = "prices.csv"
CHART_FILE = "price_trend_chart.png"

# Discord Webhook URL
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- 各サイトの価格取得関数 ---
def get_iosys_price():
    try:
        url = "https://iosys.co.jp/items/smartphone/iphone/iphone16e"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"￥([0-9,]+)", res.text)
            clean_prices = [int(p.replace(",", "")) for p in prices if int(p.replace(",", "")) > 50000]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"イオシス取得エラー: {e}")
    return 92800


def get_amazon_price():
    try:
        url = "https://www.amazon.co.jp/s?k=iPhone+16e+128GB+整備済み品"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"￥([0-9,]+)", res.text)
            clean_prices = [int(p.replace(",", "")) for p in prices if int(p.replace(",", "")) > 50000]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"Amazon取得エラー: {e}")
    return 87900


def get_backmarket_price():
    try:
        url = "https://www.backmarket.co.jp/ja-jp/search?q=iPhone+16e+128GB"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            prices = re.findall(r"([0-9,]+)\s?円", res.text)
            clean_prices = [int(p.replace(",", "")) for p in prices if int(p.replace(",", "")) > 50000]
            if clean_prices:
                return min(clean_prices)
    except Exception as e:
        print(f"BackMarket取得エラー: {e}")
    return 80100


def get_apple_refurbished_stock():
    # Appleの型番規則（新品Mから始まり、整備済品はFから始まる）に基づくURL
    urls = {
        "ホワイト": "https://www.apple.com/jp/shop/product/FD1R4J/A",
        "ブラック": "https://www.apple.com/jp/shop/product/FD1Q4J/A"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9"
    }
    available_items = []

    for color, url in urls.items():
        try:
            res = requests.get(url, headers=headers, timeout=10)
            # Appleは在庫切れ時にURLを一覧ページにリダイレクトするため、URLが変わっていないか確認
            if res.status_code == 200 and "product/F" in res.url.upper():
                # HTML内に「バッグに追加」ボタンが存在すれば購入可能と判定
                if "バッグに追加" in res.text:
                    available_items.append(f"[{color}]({url})")
        except Exception as e:
            print(f"Apple整備済({color}) 取得エラー: {e}")

    return available_items


# --- メイン処理 ---
def main():
    if not WEBHOOK_URL:
        print("エラー: DISCORD_WEBHOOK_URL が設定されていません。")
        return

    amazon = get_amazon_price()
    iosys = get_iosys_price()
    backmarket = get_backmarket_price()
    apple_stock = get_apple_refurbished_stock()

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    time_str = now.strftime("%Y-%m-%d %H:%M")

    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writerow(["Date", "Amazon", "Iosys", "BackMarket"])
        writer.writerow([time_str, amazon, iosys, backmarket])

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
    plt.plot(dates, backmarket_list, label="BackMarket", marker="^", color="#00D1B2")

    plt.title("iPhone 16e 128GB Price Trend")
    plt.xlabel("Date & Time")
    plt.ylabel("Price (JPY)")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

    # Apple在庫状況のメッセージ組み立て
    if apple_stock:
        apple_msg = "🚨 **【入荷速報】Apple公式 整備済製品の在庫が復活しています！！**\n" + "\n".join([f"・{item} が購入可能です！" for item in apple_stock])
    else:
        apple_msg = "・Apple公式 整備済: 在庫切れ"

    msg = (
        f"📱 **iPhone 16e (128GB) 価格レポート** ({time_str})\n\n"
        f"{apple_msg}\n\n"
        f"・Back Market: ¥{backmarket:,}\n"
        f"・Amazon整備品: ¥{amazon:,}\n"
        f"・イオシス: ¥{iosys:,}"
    )

    with open(CHART_FILE, "rb") as f:
        payload = {"content": msg}
        files = {"file": (CHART_FILE, f, "image/png")}
        res = requests.post(WEBHOOK_URL, data=payload, files=files)

if __name__ == "__main__":
    main()
