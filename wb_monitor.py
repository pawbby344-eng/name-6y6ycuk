import os
import asyncio
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

# Ссылка на категорию (это пример, нужно подставить свою из запроса)
# Чтобы получить свою: открой WB, выбери категорию, открой сеть (F12 -> Network),
# найди запрос к catalog.json, скопируй URL.
WB_URL = os.getenv(
    "WB_URL",
    "https://catalog.wb.ru/catalog/new/catalog.json?appType=1&sort=newly&cat=11893",
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Фильтры — товар должен пройти все условия, чтобы попасть в уведомление
MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "0"))   # минимальная скидка, %
MIN_RATING = float(os.getenv("MIN_RATING", "0"))     # минимальный рейтинг товара
MAX_PRICE = int(os.getenv("MAX_PRICE", "0"))         # максимальная цена, руб. (0 = без ограничения)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))  # задержка между запросами, сек.

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.wildberries.ru",
    "Referer": "https://www.wildberries.ru/",
}

# Доп. задержка после ошибки 429 (слишком много запросов), сек.
RATE_LIMIT_BACKOFF = int(os.getenv("RATE_LIMIT_BACKOFF", "60"))


def passes_filters(product):
    discount = product.get("sale", 0)
    rating = product.get("reviewRating") or product.get("rating") or 0
    price = product.get("salePriceU", 0) / 100

    if discount < MIN_DISCOUNT:
        return False
    if rating < MIN_RATING:
        return False
    if MAX_PRICE and price > MAX_PRICE:
        return False
    return True


async def send_telegram(client, product):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    price = product.get("salePriceU", 0) / 100
    old_price = product.get("priceU", 0) / 100
    discount = product.get("sale", 0)
    rating = product.get("reviewRating") or product.get("rating") or "—"
    link = f"https://www.wildberries.ru/catalog/{product['id']}/detail.aspx"

    text = (
        f"🆕 <b>{product['name']}</b>\n\n"
        f"💰 Цена: {price:.0f} ₽"
        + (f" (было {old_price:.0f} ₽, -{discount}%)\n" if discount else "\n")
        + f"⭐ Рейтинг: {rating}\n"
        f"🔗 <a href=\"{link}\">Открыть на WB</a>"
    )

    try:
        await client.post(
            TELEGRAM_API,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10.0,
        )
    except Exception as e:
        print(f"Не удалось отправить в Telegram: {e}")


async def monitor():
    seen_ids = set()
    print("Запуск мониторинга...")

    async with httpx.AsyncClient(http2=True) as client:
        while True:
            try:
                response = await client.get(WB_URL, headers=HEADERS, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("data", {}).get("products", [])

                    for p in products:
                        pid = p["id"]
                        if pid in seen_ids:
                            continue
                        seen_ids.add(pid)

                        if passes_filters(p):
                            print(
                                f"[{time.strftime('%H:%M:%S')}] Подходит! "
                                f"{p['name']} | {p['salePriceU'] / 100} руб."
                            )
                            await send_telegram(client, p)

                    # Чистим память, если накопилось слишком много
                    if len(seen_ids) > 5000:
                        seen_ids.clear()

                elif response.status_code == 429:
                    print(f"Ошибка 429 (слишком много запросов), ждём {RATE_LIMIT_BACKOFF} сек...")
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue

                else:
                    print(f"Ошибка {response.status_code}, ждем...")

            except Exception as e:
                print(f"Ошибка соединения: {e}")

            # Задержка, чтобы не словить бан
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor())
